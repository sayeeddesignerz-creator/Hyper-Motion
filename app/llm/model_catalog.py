"""Provider API-key detection + live model catalog with free/paid tiers.

Powers the dashboard "Add Provider" wizard:

1. the user pastes an API key
2. we detect the provider from the key format (``AIza…`` → Gemini, ``sk-or-…`` → OpenRouter, …)
3. the key is verified against the live vendor API
4. every model the key can access is listed and classified as **free** or **paid**
   (free-tier models first — the wizard splits them into two pick-lists)

Everything here is network-light and bounded: the only fan-out is a single
``GET`` (two for OpenRouter) per verification with a 12s client timeout.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

DISPLAY_NAMES: Dict[str, str] = {
    "gemini": "Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "custom": "Custom",
    "local": "Local",
}

# Ordered — first match wins. The generic OpenAI ``sk-`` pattern goes last
# because OpenRouter (``sk-or-``) and Anthropic (``sk-ant-``) share the prefix.
_KEY_PATTERNS: List[tuple] = [
    ("gemini", re.compile(r"^AIza[0-9A-Za-z_\-]{16,}$")),
    ("openrouter", re.compile(r"^sk-or-[0-9A-Za-z\-_]{8,}$", re.IGNORECASE)),
    ("anthropic", re.compile(r"^sk-ant-[0-9A-Za-z\-_]{8,}$", re.IGNORECASE)),
    ("groq", re.compile(r"^gsk_[0-9A-Za-z]{20,}$")),
    ("openai", re.compile(r"^sk-(proj-)?[0-9A-Za-z\-_]{20,}$")),
]


def detect_provider_from_key(api_key: str) -> Optional[str]:
    """Guess the provider type from the raw API key format (``None`` = unknown)."""
    key = (api_key or "").strip()
    if not key:
        return None
    for provider_type, pattern in _KEY_PATTERNS:
        if pattern.match(key):
            return provider_type
    return None


def masked_key(api_key: str) -> str:
    """``AIzaSy…4f2a`` style preview — never expose the full secret."""
    key = (api_key or "").strip()
    if len(key) <= 10:
        return "•" * len(key)
    return f"{key[:6]}…{key[-4:]}"


# ---------------------------------------------------------------------------
# Free / paid tier classification
# ---------------------------------------------------------------------------

def guess_model_tier(provider_type: str, model_id: str) -> str:
    """Classify a model as ``free`` or ``paid`` (per-vendor heuristics).

    * OpenRouter — real pricing data decides (0/0 = free) or a ``:free`` suffix.
    * Gemini    — the *flash* / *lite* families carry a usable free tier.
    * Groq      — the whole catalog is rate-limited-free.
    * OpenAI / Anthropic — token billed, i.e. paid.
    """
    ptype = (provider_type or "").lower()
    mid = (model_id or "").lower()
    if ptype == "openrouter":
        return "free" if mid.endswith(":free") else "paid"
    if ptype == "gemini":
        return "free" if ("flash" in mid or "lite" in mid) else "paid"
    if ptype == "groq":
        return "free"
    if ptype in ("local", "custom"):
        return "free"
    return "paid"


# ---------------------------------------------------------------------------
# Payload parsers (pure — unit-testable without any network)
# ---------------------------------------------------------------------------

def _mk(model_id: str, label: str, provider_type: str) -> Dict[str, str]:
    return {"id": model_id, "label": label or model_id, "tier": guess_model_tier(provider_type, model_id)}


def parse_gemini_models(payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in (payload or {}).get("models", []) or []:
        name = (m.get("name") or "").replace("models/", "").strip()
        if not name:
            continue
        methods = m.get("supportedGenerationMethods") or []
        if methods and "generateContent" not in methods:
            continue  # embeddings & friends can't be used as chat engines
        out.append(_mk(name, m.get("displayName") or name, "gemini"))
    return out


def parse_openai_models(payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    skip = ("audio", "realtime", "transcribe", "tts", "whisper", "dall", "embedding", "moderation", "image", "search")
    for m in (payload or {}).get("data", []) or []:
        mid = (m.get("id") or "").strip()
        low = mid.lower()
        if not mid:
            continue
        chat_like = low.startswith(("gpt", "o1", "o3", "o4", "chatgpt"))
        if not chat_like or any(s in low for s in skip):
            continue
        out.append(_mk(mid, mid, "openai"))
    return out


def parse_groq_models(payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    skip = ("whisper", "tts", "guard")
    for m in (payload or {}).get("data", []) or []:
        mid = (m.get("id") or "").strip()
        if not mid or any(s in mid.lower() for s in skip):
            continue
        out.append(_mk(mid, mid, "groq"))
    return out


def _price_is_zero(value: Any) -> bool:
    try:
        return float(value or 0) == 0.0
    except (TypeError, ValueError):
        return False


def parse_openrouter_models(payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in (payload or {}).get("data", []) or []:
        mid = (m.get("id") or "").strip()
        if not mid:
            continue
        pricing = m.get("pricing") or {}
        genuinely_free = _price_is_zero(pricing.get("prompt")) and _price_is_zero(pricing.get("completion"))
        item = _mk(mid, m.get("name") or mid, "openrouter")
        if genuinely_free:
            item["tier"] = "free"
        out.append(item)
    return out


def parse_anthropic_models(payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in (payload or {}).get("data", []) or []:
        mid = (m.get("id") or "").strip()
        if not mid:
            continue
        out.append(_mk(mid, m.get("display_name") or mid, "anthropic"))
    return out


def sort_catalog(models: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Free tier first, then paid — alphabetical inside each group."""
    return sorted(models, key=lambda m: (0 if m.get("tier") == "free" else 1, m.get("id", "").lower()))


# ---------------------------------------------------------------------------
# Live verification
# ---------------------------------------------------------------------------

class KeyVerificationError(Exception):
    """The provider rejected the key (401/403) or refused verification."""


def _require_ok(response: httpx.Response, vendor: str) -> None:
    code = response.status_code
    if code in (401, 403):
        raise KeyVerificationError(f"{vendor} rejected this API key (HTTP {code}). Double-check and paste it again.")
    if code == 429:
        raise KeyVerificationError(f"{vendor} rate-limited the verification call (HTTP 429). Try again in a minute.")
    if code >= 400:
        raise KeyVerificationError(f"{vendor} verification failed (HTTP {code}).")


async def verify_and_list_models(provider_type: str, api_key: str) -> Dict[str, Any]:
    """Verify ``api_key`` live and return a ranked model catalog for the provider."""
    ptype = (provider_type or "").lower()
    vendor = DISPLAY_NAMES.get(ptype, ptype.title() or "Provider")

    async with httpx.AsyncClient(timeout=12.0) as client:
        if ptype == "gemini":
            r = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key, "pageSize": 200},
            )
            _require_ok(r, vendor)
            models = parse_gemini_models(r.json())

        elif ptype == "openrouter":
            # The /models list is public — /key is what actually validates the credential.
            r = await client.get(
                "https://openrouter.ai/api/v1/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            _require_ok(r, vendor)
            r2 = await client.get("https://openrouter.ai/api/v1/models")
            _require_ok(r2, vendor)
            models = parse_openrouter_models(r2.json())

        elif ptype == "groq":
            r = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            _require_ok(r, vendor)
            models = parse_groq_models(r.json())

        elif ptype == "openai":
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            _require_ok(r, vendor)
            models = parse_openai_models(r.json())

        elif ptype == "anthropic":
            r = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
            _require_ok(r, vendor)
            models = parse_anthropic_models(r.json())

        else:
            return {
                "provider_type": ptype,
                "display_name": DISPLAY_NAMES.get(ptype, ptype.title()),
                "masked_key": masked_key(api_key),
                "models": [],
                "free_count": 0,
                "paid_count": 0,
                "notes": "This provider type cannot be verified automatically — configure it manually.",
            }

    models = sort_catalog(models)
    free_count = sum(1 for m in models if m.get("tier") == "free")
    paid_count = len(models) - free_count
    return {
        "provider_type": ptype,
        "display_name": DISPLAY_NAMES.get(ptype, ptype.title()),
        "masked_key": masked_key(api_key),
        "models": models,
        "free_count": free_count,
        "paid_count": paid_count,
        "notes": f"{free_count} free-tier · {paid_count} paid model{'s' if paid_count != 1 else ''}",
    }
