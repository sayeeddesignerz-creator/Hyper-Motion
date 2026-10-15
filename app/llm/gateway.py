"""
LLM Gateway - enhanced with:

* Direct multi-provider resilience (Gemini, OpenAI, OpenRouter)
* Per-agent routing policy (primary + ordered fallback + fallback_policy)
* Exponential-backoff + jitter retry for 429 / 5xx (tenacity)
* Retry-After header honoured
* Circuit breaker per provider (3 consecutive failures ? cooldown)
* Per-provider daily call/token limits in SQLite
* Prompt response cache in SQLite (configurable TTL, default 6 h)
* JSON-repair with up to 2 attempts before escalating to next provider
* Fail-closed for fact-critical agents:
  - fallback responses tagged model_tier = "fallback"
  - fact_checker claims without a real fetched source ? status "unverified"
  - if every provider fails, stage is marked "deferred" not "failed"
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import httpx

from app.config import get_settings, DATA_DIR

logger = logging.getLogger("LLMGateway")

# ---------------------------------------------------------------------------
# Constants & defaults
# ---------------------------------------------------------------------------

CIRCUIT_BREAKER_THRESHOLD = 3          # consecutive failures before open
CIRCUIT_BREAKER_COOLDOWN  = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_SECONDS", "600"))
DAILY_CALL_LIMIT          = int(os.getenv("PROVIDER_DAILY_CALL_LIMIT", "500"))
DAILY_TOKEN_LIMIT         = int(os.getenv("PROVIDER_DAILY_TOKEN_LIMIT", "2000000"))
CACHE_TTL_SECONDS         = int(os.getenv("PROMPT_CACHE_TTL_SECONDS", str(6 * 3600)))
JSON_REPAIR_ATTEMPTS      = 2

GATEWAY_DB = DATA_DIR / "gateway_state.db"

# Agents whose fallback tagging is "flag" (fail-closed)
FACT_CRITICAL_AGENTS = {"fact_checker", "script_forge", "strategist"}

# Per-agent routing policy -------------------------------------------------
#   primary  : provider key used first
#   fallback : ordered list of provider keys to try
#   fallback_policy: "allow" | "flag"
_DEFAULT_FALLBACK_ORDER = ["gemini", "openai", "openrouter"]

AGENT_ROUTING: Dict[str, Dict[str, Any]] = {
    "trend_hunter":   {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "allow"},
    "seo_optimizer":  {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "allow"},
    "audience_miner": {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "allow"},
    "learner":        {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "allow"},
    "fact_checker":   {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "flag"},
    "script_forge":   {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "flag"},
    "strategist":     {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "flag"},
}
_DEFAULT_ROUTING = {"primary": "gemini", "fallback": _DEFAULT_FALLBACK_ORDER, "fallback_policy": "allow"}

# ---------------------------------------------------------------------------
# Provider-ID → gateway handle key mapping
# Maps the provider_id strings stored in the DB omni_routes table to the
# logical provider keys used by LLMGateway._handles ("gemini", "openai", …)
# ---------------------------------------------------------------------------
_PROVIDER_ID_TO_HANDLE: Dict[str, str] = {
    "gemini_primary":    "gemini",
    "gemini":            "gemini",
    "openrouter_free":   "openrouter",
    "openrouter":        "openrouter",
    "openai_cloud":      "openai",
    "openai":            "openai",
}

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _cache_key(prompt: str, system_instruction: Optional[str], temperature: float) -> str:
    blob = f"{prompt}||{system_instruction or ''}||{temperature}"
    return hashlib.sha256(blob.encode()).hexdigest()

def _parse_retry_after(headers: httpx.Headers) -> Optional[float]:
    """Parse Retry-After header (seconds or HTTP-date)."""
    val = headers.get("retry-after") or headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None

def _extract_cooldown_from_text(error_str: str) -> float:
    match = re.search(r"retryDelay':\s*'(\d+)", error_str)
    if match:
        return min(float(match.group(1)), 3600.0)
    match = re.search(r"in\s+(\d+)s", error_str)
    if match:
        return min(float(match.group(1)), 3600.0)
    return 180.0

def _jitter(base: float) -> float:
    return base * (0.5 + random.random())

# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Per-provider in-memory circuit breaker."""

    def __init__(self, name: str, threshold: int = CIRCUIT_BREAKER_THRESHOLD, cooldown: float = CIRCUIT_BREAKER_COOLDOWN):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._open_until: float = 0.0

    @property
    def is_open(self) -> bool:
        return time.monotonic() < self._open_until

    def record_success(self) -> None:
        self._failures = 0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._open_until = time.monotonic() + self.cooldown
            logger.warning(
                "Circuit breaker OPEN for provider '%s' after %d consecutive failures. "
                "Cooldown: %ds.",
                self.name, self._failures, int(self.cooldown),
            )

    def reset_if_recovered(self) -> None:
        """Allow one probe attempt when cooldown expires."""
        if not self.is_open:
            self._failures = 0

    def status(self) -> str:
        return "open" if self.is_open else "closed"

# ---------------------------------------------------------------------------
# GatewayDB - SQLite for daily limits and prompt cache
# ---------------------------------------------------------------------------

class GatewayDB:
    """
    Tiny async SQLite helper for:
      - provider_daily_usage  (calls/tokens per provider per UTC date)
      - prompt_cache          (sha256 ? response, expires_at)
      - provider_status       (last_error, error_time, for /api/providers)
    """

    def __init__(self, db_path=GATEWAY_DB):
        self.db_path = db_path
        self._initialised = False

    async def _ensure_init(self) -> None:
        if self._initialised:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS provider_daily_usage (
                    provider TEXT NOT NULL,
                    date     TEXT NOT NULL,
                    calls    INTEGER DEFAULT 0,
                    tokens   INTEGER DEFAULT 0,
                    PRIMARY KEY (provider, date)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS prompt_cache (
                    cache_key  TEXT PRIMARY KEY,
                    response   TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS provider_status (
                    provider   TEXT PRIMARY KEY,
                    last_error TEXT,
                    error_time REAL
                )
            """)
            await db.commit()
        self._initialised = True

    # --- daily limits ---

    async def increment_usage(self, provider: str, tokens: int = 0) -> None:
        await self._ensure_init()
        today = _utc_date()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO provider_daily_usage (provider, date, calls, tokens)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(provider, date) DO UPDATE SET
                    calls  = calls  + 1,
                    tokens = tokens + excluded.tokens
            """, (provider, today, tokens))
            await db.commit()

    async def get_usage(self, provider: str) -> Tuple[int, int]:
        """Returns (calls_today, tokens_today)."""
        await self._ensure_init()
        today = _utc_date()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT calls, tokens FROM provider_daily_usage WHERE provider=? AND date=?",
                (provider, today)
            )
            row = await cursor.fetchone()
        return (row[0], row[1]) if row else (0, 0)

    async def is_daily_limit_reached(self, provider: str) -> bool:
        calls, tokens = await self.get_usage(provider)
        return calls >= DAILY_CALL_LIMIT or tokens >= DAILY_TOKEN_LIMIT

    # --- prompt cache ---

    async def cache_get(self, key: str) -> Optional[str]:
        await self._ensure_init()
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT response FROM prompt_cache WHERE cache_key=? AND expires_at>?",
                (key, now)
            )
            row = await cursor.fetchone()
        return row[0] if row else None

    async def cache_set(self, key: str, response: str) -> None:
        await self._ensure_init()
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO prompt_cache (cache_key, response, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (key, response, now, now + CACHE_TTL_SECONDS))
            # Evict expired entries periodically
            await db.execute("DELETE FROM prompt_cache WHERE expires_at < ?", (now,))
            await db.commit()

    # --- provider status ---

    async def set_last_error(self, provider: str, error: str) -> None:
        await self._ensure_init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO provider_status (provider, last_error, error_time)
                VALUES (?, ?, ?)
            """, (provider, error[:500], time.time()))
            await db.commit()

    async def get_provider_statuses(self) -> List[Dict[str, Any]]:
        await self._ensure_init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM provider_status")
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_all_usage(self) -> List[Dict[str, Any]]:
        await self._ensure_init()
        today = _utc_date()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM provider_daily_usage WHERE date=?", (today,)
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# ProviderHandle - wraps a provider with circuit breaker metadata
# ---------------------------------------------------------------------------

class ProviderHandle:
    def __init__(self, key: str, provider, label: str):
        self.key = key          # logical name: "gemini", "omniroute", etc.
        self.provider = provider
        self.label = label
        self.cb = CircuitBreaker(key)

    async def generate_text(self, db: GatewayDB, *args, **kwargs) -> str:
        if self.cb.is_open:
            raise RuntimeError(f"Circuit breaker OPEN for {self.label}")
        if await db.is_daily_limit_reached(self.key):
            raise RuntimeError(f"Daily limit reached for {self.label}")

        try:
            result = await self.provider.generate_text(*args, **kwargs)
            self.cb.record_success()
            est_tokens = max(len(result) // 4, 1)
            await db.increment_usage(self.key, est_tokens)
            return result
        except Exception as exc:
            self.cb.record_failure()
            await db.set_last_error(self.key, str(exc))
            raise

    async def generate_json(self, db: GatewayDB, *args, **kwargs) -> Dict[str, Any]:
        if self.cb.is_open:
            raise RuntimeError(f"Circuit breaker OPEN for {self.label}")
        if await db.is_daily_limit_reached(self.key):
            raise RuntimeError(f"Daily limit reached for {self.label}")

        try:
            result = await self.provider.generate_json(*args, **kwargs)
            self.cb.record_success()
            est_tokens = max(len(json.dumps(result)) // 4, 1)
            await db.increment_usage(self.key, est_tokens)
            return result
        except Exception as exc:
            self.cb.record_failure()
            await db.set_last_error(self.key, str(exc))
            raise

# ---------------------------------------------------------------------------
# JSON repair helper
# ---------------------------------------------------------------------------

async def _attempt_json_repair(raw: str, attempt: int) -> Optional[Dict[str, Any]]:
    """Try up to JSON_REPAIR_ATTEMPTS times to extract valid JSON."""
    if attempt >= JSON_REPAIR_ATTEMPTS:
        return None
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    # Remove trailing commas
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None

# ---------------------------------------------------------------------------
# Retry helper with Retry-After awareness
# ---------------------------------------------------------------------------

async def _retry_call(coro_factory, *, provider_key: str, max_retries: int = 3):
    """
    Retry coro_factory() on 429/5xx with exponential backoff + jitter.
    Respects Retry-After header when present in httpx.HTTPStatusError.
    """
    delay = 1.0
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429 or status >= 500:
                retry_after = _parse_retry_after(exc.response.headers)
                wait = retry_after if retry_after else _jitter(delay)
                logger.warning(
                    "Provider %s got HTTP %d on attempt %d/%d - waiting %.1fs",
                    provider_key, status, attempt + 1, max_retries + 1, wait,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, 60.0)
                last_exc = exc
            else:
                raise
        except Exception as exc:
            err = str(exc)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "rate" in err.lower():
                wait = _jitter(delay)
                logger.warning(
                    "Provider %s rate-limited on attempt %d/%d - waiting %.1fs",
                    provider_key, attempt + 1, max_retries + 1, wait,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, 60.0)
                last_exc = exc
            else:
                raise
    raise last_exc  # type: ignore[misc]

# ---------------------------------------------------------------------------
# LLMGateway
# ---------------------------------------------------------------------------

class LLMGateway:
    """
    Public interface for all agents. Handles:
      - Provider construction from env
      - Routing policy lookup per agent
      - Exponential-backoff retries
      - Circuit breaker per provider
      - Daily usage limits
      - Prompt cache
      - JSON repair fallback
      - Fail-closed fact-critical tagging
      - Deferred-stage when all providers fail
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._db = GatewayDB()
        self._handles: Dict[str, ProviderHandle] = {}
        # Live routing table — overrides AGENT_ROUTING when populated from DB.
        # Updated atomically by reload_from_db_routes(); never written directly.
        self._live_routes: Dict[str, Dict[str, Any]] = {}
        self._build_handles()

    # ------------------------------------------------------------------
    # Provider construction
    # ------------------------------------------------------------------

    def _build_handles(self) -> None:
        from app.llm.gemini_provider import GeminiProvider
        from app.llm.openai_provider import OpenAIProvider

        s = self.settings

        # --- Gemini (primary for most agents) ---
        gemini_key = os.getenv("GEMINI_API_KEYS", "") or s.gemini_api_key or ""
        gemini_key = gemini_key.split(",")[0].strip()
        if gemini_key:
            p = GeminiProvider(api_key=gemini_key)
            if p.is_configured():
                self._handles["gemini"] = ProviderHandle("gemini", p, "Gemini")

        # --- OpenAI ---
        openai_key = os.getenv("OPENAI_API_KEY") or s.openai_api_key
        if openai_key:
            p_oa = OpenAIProvider(api_key=openai_key)
            if p_oa.is_configured():
                self._handles["openai"] = ProviderHandle("openai", p_oa, "OpenAI")

        # --- OpenRouter ---
        or_key = os.getenv("OPENROUTER_API_KEY") or s.openrouter_api_key
        if or_key:
            p_or = OpenAIProvider(
                api_key=or_key,
                model_name=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
                base_url="https://openrouter.ai/api/v1",
            )
            if p_or.is_configured():
                self._handles["openrouter"] = ProviderHandle("openrouter", p_or, "OpenRouter")

        logger.info(
            "LLMGateway initialised with providers: %s",
            list(self._handles.keys()),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        return len(self._handles) > 0

    # ------------------------------------------------------------------
    # Live route management — called by api.py after every DB mutation
    # ------------------------------------------------------------------

    def reload_from_db_routes(self, db_routes: List[Dict[str, Any]]) -> None:
        """
        Convert rows from the ``omni_routes`` DB table into the gateway's
        internal routing format and swap the live table atomically.

        The mapping is:
          route_name          → used as an agent-name key (e.g. ``"fact_check"``
                                matches ``"fact_checker"`` agent via the
                                ``_PROVIDER_ID_TO_HANDLE`` translation).
          primary_provider_id → mapped to a gateway handle key.
          fallback_chain      → list of {provider_id, model} dicts; each
                                provider_id is mapped to a handle key.
        """
        live: Dict[str, Dict[str, Any]] = {}
        for r in db_routes:
            route_name = (r.get("route_name") or "").strip()
            if not route_name:
                continue

            primary_key = _PROVIDER_ID_TO_HANDLE.get(
                r.get("primary_provider_id", ""), "gemini"
            )

            # Build ordered fallback list starting from primary
            fb_keys: List[str] = [primary_key]
            for step in (r.get("fallback_chain") or []):
                pid  = step.get("provider_id", "")
                hkey = _PROVIDER_ID_TO_HANDLE.get(pid, pid)
                if hkey and hkey not in fb_keys:
                    fb_keys.append(hkey)
            # Append global defaults as last-resort
            for k in _DEFAULT_FALLBACK_ORDER:
                if k not in fb_keys:
                    fb_keys.append(k)

            # Inherit fact-critical policy when the route name matches a
            # known critical agent (e.g. "fact_check" → flag)
            is_critical = any(
                route_name == a or route_name in a or a in route_name
                for a in FACT_CRITICAL_AGENTS
            )
            policy = "flag" if is_critical else "allow"

            live[route_name] = {
                "primary":          primary_key,
                "fallback":         fb_keys,
                "fallback_policy":  policy,
                "cooldown_seconds": r.get("cooldown_seconds", 300),
                "max_retries":      r.get("max_retries", 3),
                "_source":          "db",
            }

        self._live_routes = live
        logger.info(
            "[RouteSync] Live routing table updated — %d DB route(s) active: %s",
            len(live), list(live.keys()),
        )

    def get_live_routes(self) -> Dict[str, Dict[str, Any]]:
        """Return a copy of the current live routing table (for API inspection)."""
        return dict(self._live_routes)

    # ------------------------------------------------------------------
    # Routing lookup
    # ------------------------------------------------------------------

    def get_agent_routing(self, agent_name: Optional[str]) -> Dict[str, Any]:
        """
        Priority order:
          1. Exact match in live (DB-sourced) routes.
          2. Fuzzy match — live route whose name is contained in agent_name
             or vice-versa (e.g. ``"fact_check"`` matches ``"fact_checker"``)
          3. ``"default"`` live route as a catch-all DB override.
          4. Static ``AGENT_ROUTING`` table (hard-coded defaults).
          5. ``_DEFAULT_ROUTING``.
        """
        if agent_name and self._live_routes:
            # 1. Exact match
            if agent_name in self._live_routes:
                return self._live_routes[agent_name]
            # 2. Fuzzy match
            for rname, routing in self._live_routes.items():
                if rname == "default":
                    continue
                if rname in agent_name or agent_name in rname:
                    return routing
            # 3. DB-level "default" catch-all
            if "default" in self._live_routes:
                return self._live_routes["default"]

        if agent_name:
            return AGENT_ROUTING.get(agent_name, _DEFAULT_ROUTING)
        # 5. No agent name at all
        if "default" in self._live_routes:
            return self._live_routes["default"]
        return _DEFAULT_ROUTING

    def _ordered_handles(self, routing: Dict[str, Any]) -> List[ProviderHandle]:
        """Return provider handles in priority order for this routing policy."""
        seen = set()
        ordered: List[ProviderHandle] = []

        def _add(key: str) -> None:
            if key not in seen and key in self._handles:
                seen.add(key)
                ordered.append(self._handles[key])

        _add(routing["primary"])
        for k in routing["fallback"]:
            _add(k)
        # Any remaining registered handles as last resort
        for k in self._handles:
            _add(k)
        return ordered

    def _is_fact_critical(self, agent_name: Optional[str]) -> bool:
        return (agent_name or "") in FACT_CRITICAL_AGENTS

    # ------------------------------------------------------------------
    # Core generate_text
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        agent_name: Optional[str] = None,
    ) -> str:
        # --- Cache check ---
        ck = _cache_key(prompt, system_instruction, temperature)
        cached = await self._db.cache_get(ck)
        if cached is not None:
            logger.debug("Cache HIT for prompt (key=%s?)", ck[:12])
            return cached

        routing = self.get_agent_routing(agent_name)
        handles = self._ordered_handles(routing)
        primary_key = routing["primary"]
        fallback_policy = routing["fallback_policy"]
        is_fact_critical = self._is_fact_critical(agent_name)

        last_exc: Optional[Exception] = None
        used_fallback = False

        for handle in handles:
            if handle.key != primary_key:
                used_fallback = True

            try:
                result = await _retry_call(
                    lambda h=handle: h.generate_text(
                        self._db, prompt,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    provider_key=handle.key,
                )
                await self._db.cache_set(ck, result)
                if used_fallback and fallback_policy == "flag":
                    logger.warning(
                        "FALLBACK MODEL used for agent '%s' via %s",
                        agent_name, handle.label,
                    )
                return result
            except Exception as exc:
                logger.warning(
                    "Provider %s failed for agent '%s': %s",
                    handle.label, agent_name, exc,
                )
                last_exc = exc
                continue

        # All providers failed ? deferred
        logger.error(
            "All providers failed for agent '%s'. Marking stage deferred. Last error: %s",
            agent_name, last_exc,
        )
        raise DeferredStageError(
            f"All providers failed for agent '{agent_name}'. Stage deferred for retry.",
            last_error=str(last_exc),
        )

    # ------------------------------------------------------------------
    # Core generate_json
    # ------------------------------------------------------------------

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        ck = _cache_key(prompt, system_instruction, temperature)
        cached_raw = await self._db.cache_get(ck)
        if cached_raw is not None:
            try:
                return json.loads(cached_raw)
            except json.JSONDecodeError:
                pass

        routing = self.get_agent_routing(agent_name)
        handles = self._ordered_handles(routing)
        primary_key = routing["primary"]
        fallback_policy = routing["fallback_policy"]
        is_fact_critical = self._is_fact_critical(agent_name)

        last_exc: Optional[Exception] = None
        used_fallback = False

        for handle in handles:
            if handle.key != primary_key:
                used_fallback = True

            # --- JSON repair loop ---
            for repair_attempt in range(JSON_REPAIR_ATTEMPTS + 1):
                try:
                    result = await _retry_call(
                        lambda h=handle: h.generate_json(
                            self._db, prompt,
                            system_instruction=system_instruction,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        ),
                        provider_key=handle.key,
                    )
                    # Tag fallback for fact-critical agents
                    if used_fallback and is_fact_critical:
                        result["model_tier"] = "fallback"
                        result["_fallback_provider"] = handle.label
                        if fallback_policy == "flag":
                            # Downgrade any "verified" claims that have no source_url
                            result = _downgrade_unverified_claims(result)
                    elif used_fallback and fallback_policy == "flag":
                        result["model_tier"] = "fallback"
                        result["_fallback_provider"] = handle.label

                    await self._db.cache_set(ck, json.dumps(result))
                    return result

                except json.JSONDecodeError as jexc:
                    logger.warning(
                        "JSON decode error from %s (repair attempt %d/%d): %s",
                        handle.label, repair_attempt + 1, JSON_REPAIR_ATTEMPTS, jexc,
                    )
                    if repair_attempt >= JSON_REPAIR_ATTEMPTS - 1:
                        last_exc = jexc
                        break  # escalate to next provider
                    # Else retry same provider
                except ValueError as vexc:
                    # Provider returned valid text but unparseable - attempt repair
                    logger.warning(
                        "ValueError from %s (repair attempt %d/%d): %s",
                        handle.label, repair_attempt + 1, JSON_REPAIR_ATTEMPTS, vexc,
                    )
                    if repair_attempt >= JSON_REPAIR_ATTEMPTS - 1:
                        last_exc = vexc
                        break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "Provider %s failed for agent '%s': %s",
                        handle.label, agent_name, exc,
                    )
                    break  # don't retry bad providers in inner loop

        # All providers failed
        logger.error(
            "All providers failed (JSON) for agent '%s'. Stage deferred. Last: %s",
            agent_name, last_exc,
        )
        raise DeferredStageError(
            f"All providers failed for agent '{agent_name}'. Stage deferred.",
            last_error=str(last_exc),
        )

    # ------------------------------------------------------------------
    # Provider status (for /api/providers)
    # ------------------------------------------------------------------

    async def get_providers_status(self) -> List[Dict[str, Any]]:
        """
        Returns per-provider status info. API keys are NEVER included.
        """
        usage_rows = await self._db.get_all_usage()
        error_rows = await self._db.get_provider_statuses()

        usage_map = {r["provider"]: r for r in usage_rows}
        error_map = {r["provider"]: r for r in error_rows}

        result = []
        for key, handle in self._handles.items():
            cb = handle.cb
            u = usage_map.get(key, {})
            e = error_map.get(key, {})

            calls_today = u.get("calls", 0)
            tokens_today = u.get("tokens", 0)
            daily_cap_calls = calls_today >= DAILY_CALL_LIMIT
            daily_cap_tokens = tokens_today >= DAILY_TOKEN_LIMIT

            if cb.is_open:
                status_str = "cooling_down"
            elif daily_cap_calls or daily_cap_tokens:
                status_str = "limit_reached"
            else:
                status_str = "ok"

            result.append({
                "provider": key,
                "label": handle.label,
                "status": status_str,
                "circuit_state": cb.status(),
                "calls_today": calls_today,
                "tokens_today": tokens_today,
                "daily_call_limit": DAILY_CALL_LIMIT,
                "daily_token_limit": DAILY_TOKEN_LIMIT,
                "last_error": e.get("last_error"),
                "error_time": e.get("error_time"),
                # NOTE: API keys are deliberately excluded
            })
        return result


# ---------------------------------------------------------------------------
# Fail-closed fact-checker claim downgrading
# ---------------------------------------------------------------------------

def _downgrade_unverified_claims(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    For fact_checker running on a fallback model:
    any claim without a real fetched source_url must be marked unverified.
    'verified' is only allowed when source_url is present and non-empty.
    """
    claims = data.get("claims", [])
    for claim in claims:
        status = str(claim.get("status", "")).lower()
        if "verified" in status and "partially" not in status:
            source_url = claim.get("source_url", "")
            if not source_url or not str(source_url).startswith("http"):
                claim["status"] = "unverified"
                claim["_downgrade_reason"] = (
                    "Fallback model: no fetched source_url - cannot confirm verified status."
                )
    data["claims"] = claims
    return data


# ---------------------------------------------------------------------------
# DeferredStageError
# ---------------------------------------------------------------------------

class DeferredStageError(Exception):
    """
    Raised when all providers fail.
    The scheduler or operator should catch this and mark the pipeline stage
    as 'deferred' (not 'failed') so it can be retried later.
    """

    def __init__(self, message: str, last_error: Optional[str] = None):
        super().__init__(message)
        self.last_error = last_error
