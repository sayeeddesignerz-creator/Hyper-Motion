"""
tests/test_gateway.py � Full test suite for the enhanced LLMGateway.

All HTTP calls are intercepted with unittest.mock;
no real API keys are needed.
"""
from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixture: lightweight LLMGateway with temp SQLite DB, no real providers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_gateway(tmp_path):
    """
    Return an LLMGateway instance whose _handles dict is empty (tests fill it).
    GatewayDB points at a temp SQLite file.
    """
    import app.llm.gateway as gw_mod
    original_db = gw_mod.GATEWAY_DB
    gw_mod.GATEWAY_DB = tmp_path / "gw_test.db"

    from app.llm.gateway import LLMGateway, GatewayDB

    # Bypass __init__ so we don't touch real env vars / providers
    gw = object.__new__(LLMGateway)
    gw._db = GatewayDB(tmp_path / "gw_test.db")
    gw._handles = {}
    gw._live_routes = {}
    from app.llm.gateway import _PROVIDER_ID_TO_HANDLE
    gw._provider_map = dict(_PROVIDER_ID_TO_HANDLE)
    gw.settings = MagicMock()

    yield gw

    gw_mod.GATEWAY_DB = original_db


def _mock_handle(
    key: str,
    label: str,
    text_exc=None,
    json_exc=None,
    text_ret=None,
    json_ret=None,
):
    """Build a minimal ProviderHandle-like object with mocked async methods."""
    from app.llm.gateway import CircuitBreaker

    class _Handle:
        def __init__(self):
            self.key = key
            self.label = label
            self.cb = CircuitBreaker(key)

        async def generate_text(self, db, *a, **kw):
            if text_exc is not None:
                raise text_exc
            return text_ret or "ok"

        async def generate_json(self, db, *a, **kw):
            if json_exc is not None:
                raise json_exc
            return json_ret or {"status": "ok"}

    return _Handle()


# ============================================================================
# 1. 429 on Gemini triggers fallback to OpenAI
# ============================================================================

@pytest.mark.asyncio
async def test_429_on_gemini_falls_back_to_openai(tmp_gateway):
    """Rate-limit error from Gemini should route the call to OpenAI."""
    from app.llm.gateway import AGENT_ROUTING

    gemini_exc = Exception("429 RESOURCE_EXHAUSTED quota exceeded")
    gemini = _mock_handle("gemini", "Gemini", text_exc=gemini_exc)
    openai_h = _mock_handle("openai", "OpenAI", text_ret="fallback answer")

    tmp_gateway._handles = {"gemini": gemini, "openai": openai_h}

    result = await tmp_gateway.generate_text("hello", agent_name="trend_hunter")
    assert result == "fallback answer"


# ============================================================================
# 2. Circuit breaker opens after 3 failures and recovers after cooldown
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_open_and_recovery():
    """After 3 consecutive failures the circuit opens; after cooldown it closes."""
    from app.llm.gateway import CircuitBreaker

    cb = CircuitBreaker("test-prov", threshold=3, cooldown=0.1)

    assert not cb.is_open
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open, "Circuit should be open after threshold failures"

    await asyncio.sleep(0.15)
    assert not cb.is_open, "Circuit should be closed after cooldown expires"


# ============================================================================
# 3. Daily cap skips a provider
# ============================================================================

@pytest.mark.asyncio
async def test_daily_cap_skips_provider(tmp_gateway):
    """When daily call limit is reached for gemini, the gateway uses the next provider."""
    from app.llm.gateway import DAILY_CALL_LIMIT

    # Exhaust gemini's daily limit
    for _ in range(DAILY_CALL_LIMIT):
        await tmp_gateway._db.increment_usage("gemini", tokens=1)

    assert await tmp_gateway._db.is_daily_limit_reached("gemini")

    # Build handles: gemini raises (daily limit), openai answers
    async def _capped(db, *a, **kw):
        raise RuntimeError("Daily limit reached for Gemini")

    from app.llm.gateway import CircuitBreaker

    class _CappedHandle:
        key = "gemini"
        label = "Gemini"
        cb = CircuitBreaker("gemini")
        generate_text = _capped
        generate_json = _capped

    openai_h = _mock_handle("openai", "OpenAI", text_ret="openai answer")
    tmp_gateway._handles = {"gemini": _CappedHandle(), "openai": openai_h}

    result = await tmp_gateway.generate_text("what is 2+2?", agent_name="seo_optimizer")
    assert result == "openai answer"


# ============================================================================
# 4. Invalid JSON from a provider escalates to next provider
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_json_escalates_to_next_provider(tmp_gateway):
    """A provider raising ValueError (bad JSON) should escalate to the next provider."""
    bad_json_exc = ValueError("Could not parse valid JSON: {{broken")
    gemini = _mock_handle("gemini", "Gemini", json_exc=bad_json_exc)
    openai_h = _mock_handle("openai", "OpenAI", json_ret={"result": "openai json"})

    tmp_gateway._handles = {"gemini": gemini, "openai": openai_h}

    result = await tmp_gateway.generate_json("summarise facts", agent_name="fact_checker")
    # Should have come from openai; fact_checker + fallback ? tagged
    assert "result" in result or "model_tier" in result


# ============================================================================
# 5. fact_checker on a fallback model: claims without source_url ? unverified
# ============================================================================

def test_fact_checker_fallback_downgrades_unverified_claims():
    """Claims marked 'verified' without a source_url must be downgraded."""
    from app.llm.gateway import _downgrade_unverified_claims

    data = {
        "claims": [
            {
                "claim_text": "The sky is blue",
                "status": "verified",
                "source_url": "https://science.org/sky",
                "confidence": 99.0,
            },
            {
                "claim_text": "Water is dry",
                "status": "verified",
                # No source_url � should be downgraded
                "confidence": 88.0,
            },
            {
                "claim_text": "Gravity exists",
                "status": "unverified",
                "confidence": 50.0,
            },
        ]
    }

    result = _downgrade_unverified_claims(data)
    claim_map = {c["claim_text"]: c for c in result["claims"]}

    assert claim_map["The sky is blue"]["status"] == "verified"
    assert claim_map["Water is dry"]["status"] == "unverified"
    assert "_downgrade_reason" in claim_map["Water is dry"]
    assert claim_map["Gravity exists"]["status"] == "unverified"


# ============================================================================
# 6. Cache hit makes no provider call
# ============================================================================

@pytest.mark.asyncio
async def test_cache_hit_skips_provider(tmp_gateway):
    """A prompt with a cached response is returned without hitting any provider."""
    from app.llm.gateway import _cache_key

    prompt = "What is the capital of France?"
    sys = "You are helpful."
    temp = 0.3

    ck = _cache_key(prompt, sys, temp)
    await tmp_gateway._db.cache_set(ck, "Paris")

    call_log = []

    class _SpyHandle:
        key = "gemini"
        label = "Gemini"

        from app.llm.gateway import CircuitBreaker
        cb = CircuitBreaker("gemini")

        async def generate_text(self, db, *a, **kw):
            call_log.append("called")
            return "SHOULD NOT BE CALLED"

    tmp_gateway._handles = {"gemini": _SpyHandle()}

    result = await tmp_gateway.generate_text(prompt, system_instruction=sys, temperature=temp)
    assert result == "Paris"
    assert len(call_log) == 0, "Provider should NOT have been called � cache hit expected"


# ============================================================================
# 7. Dashboard-saved providers (DB) become live gateway handles
# ============================================================================

@pytest.mark.asyncio
async def test_db_providers_become_live_handles(tmp_path):
    """Providers saved via the dashboard must register as real routing handles,
    and routes referencing them must resolve through the provider map."""
    from app.db import Database
    from app.llm.gateway import LLMGateway, GatewayDB, _PROVIDER_ID_TO_HANDLE

    gw = object.__new__(LLMGateway)
    gw._db = GatewayDB(tmp_path / "gw_sync.db")
    gw._handles = {}
    gw._live_routes = {}
    gw._provider_map = dict(_PROVIDER_ID_TO_HANDLE)
    gw.settings = MagicMock()
    gw.settings.gemini_api_key = None
    gw.settings.openai_api_key = None
    gw.settings.openrouter_api_key = None

    db = Database(tmp_path / "app_test.db")
    await db.initialize()
    await db.save_omni_provider(
        provider_id="groq_fast",
        provider_type="groq",
        name="Groq Cloud",
        api_key="test_key_not_real",
        base_url="https://api.groq.com/openai/v1",
        models=["llama-3.3-70b-versatile"],
        enabled=True,
    )

    await gw.sync_providers_from_db(db)
    assert "groq_fast" in gw._handles, "DB provider must become a live handle"
    assert gw._provider_map["groq_fast"] == "groq_fast"

    route = {
        "route_name": "default",
        "primary_provider_id": "groq_fast",
        "fallback_chain": [{"provider_id": "gemini_primary"}],
    }
    gw.reload_from_db_routes([route])
    assert gw._live_routes["default"]["primary"] == "groq_fast"
    assert "gemini" in gw._live_routes["default"]["fallback"]

    # Deleting the provider must drop its handle and revert to the alias mapping
    await db.delete_omni_provider("groq_fast")
    await gw.sync_providers_from_db(db)
    assert "groq_fast" not in gw._handles
    assert gw._provider_map.get("groq_fast") == "groq"

    gw.reload_from_db_routes([route])
    assert gw._live_routes["default"]["primary"] == "groq"


# ============================================================================
# 8. Route referencing an unknown provider falls back to the gemini handle
# ============================================================================

@pytest.mark.asyncio
async def test_unknown_provider_route_falls_back_to_gemini(tmp_gateway):
    """A route whose provider no longer exists must not break route ingestion."""
    tmp_gateway._handles = {"gemini": _mock_handle("gemini", "Gemini", text_ret="ok")}
    tmp_gateway.reload_from_db_routes([{
        "route_name": "ghost_route",
        "primary_provider_id": "provider_that_never_existed",
        "fallback_chain": [],
    }])
    assert tmp_gateway._live_routes["ghost_route"]["primary"] == "gemini"


# ============================================================================
# 9. API keys never appear in /api/providers response
# ============================================================================

@pytest.mark.asyncio
async def test_keys_never_in_providers_response(tmp_gateway):
    """/api/providers must never return API key values."""
    from app.llm.gateway import CircuitBreaker

    class _FakeHandle:
        key = "gemini"
        label = "Gemini"
        cb = CircuitBreaker("gemini")

        async def generate_text(self, db, *a, **kw):
            return "ok"

    tmp_gateway._handles = {"gemini": _FakeHandle()}

    statuses = await tmp_gateway.get_providers_status()
    assert isinstance(statuses, list)
    for entry in statuses:
        # Key fields must be absent
        assert "api_key" not in entry, f"api_key found in provider status: {entry}"
        assert "secret" not in entry
        # Required safe fields must be present
        assert "provider" in entry
        assert "status" in entry
        assert "calls_today" in entry
        assert "tokens_today" in entry
        assert "circuit_state" in entry
