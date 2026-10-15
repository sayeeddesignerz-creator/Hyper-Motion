"""
tests/test_model_catalog.py — key detection, tier classification and live
verification for the Add-Provider wizard (``app/llm/model_catalog.py``).

All HTTP is mocked; no real API keys or network access required.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import model_catalog as mc


# ---------------------------------------------------------------------------
# Key format detection
# ---------------------------------------------------------------------------

def test_detect_gemini_key():
    assert mc.detect_provider_from_key("AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r") == "gemini"


def test_detect_openrouter_before_openai():
    # sk-or-… must win over the generic sk-… OpenAI pattern
    assert mc.detect_provider_from_key("sk-or-v1-0123456789abcdef0123456789abcdef") == "openrouter"


def test_detect_anthropic_before_openai():
    assert mc.detect_provider_from_key("sk-ant-api03-abcdefghijklmnopqrstuvwxyz012345") == "anthropic"


def test_detect_groq_key():
    assert mc.detect_provider_from_key("gsk_abcdefghijklmnopqrstuvwxyz0123456789") == "groq"


def test_detect_openai_keys():
    assert mc.detect_provider_from_key("sk-abcdefghijklmnopqrstuvwx1234567890") == "openai"
    assert mc.detect_provider_from_key("sk-proj-abcdefghijklmnopqrstuvwx123456") == "openai"


def test_detect_unknown_and_empty():
    assert mc.detect_provider_from_key("hello-world") is None
    assert mc.detect_provider_from_key("") is None
    assert mc.detect_provider_from_key(None) is None


def test_masked_key_never_exposes_secret():
    masked = mc.masked_key("AIzaSyVeryLongSecretValue1234")
    assert masked.startswith("AIzaSy")
    assert masked.endswith("1234")
    assert "VeryLongSecretValue" not in masked


# ---------------------------------------------------------------------------
# Free / paid classification
# ---------------------------------------------------------------------------

def test_gemini_tiers():
    assert mc.guess_model_tier("gemini", "gemini-2.5-flash") == "free"
    assert mc.guess_model_tier("gemini", "gemini-2.0-flash-lite") == "free"
    assert mc.guess_model_tier("gemini", "gemini-2.5-pro") == "paid"


def test_groq_is_free_and_openai_paid():
    assert mc.guess_model_tier("groq", "llama-3.3-70b-versatile") == "free"
    assert mc.guess_model_tier("openai", "gpt-4o-mini") == "paid"
    assert mc.guess_model_tier("anthropic", "claude-sonnet-4") == "paid"


def test_openrouter_suffix_rule():
    assert mc.guess_model_tier("openrouter", "meta-llama/llama-3.3-70b-instruct:free") == "free"
    assert mc.guess_model_tier("openrouter", "openai/gpt-4o") == "paid"


# ---------------------------------------------------------------------------
# Payload parsers
# ---------------------------------------------------------------------------

def test_parse_gemini_models_filters_embeddings():
    payload = {
        "models": [
            {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-pro", "displayName": "Gemini 2.5 Pro",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding-001", "displayName": "Embedding 001",
             "supportedGenerationMethods": ["embedContent"]},
        ]
    }
    models = mc.parse_gemini_models(payload)
    ids = [m["id"] for m in models]
    assert ids == ["gemini-2.5-flash", "gemini-2.5-pro"]
    assert models[0]["tier"] == "free" and models[1]["tier"] == "paid"


def test_parse_openai_models_filters_non_chat():
    payload = {"data": [
        {"id": "gpt-4o-mini"},
        {"id": "o3-mini"},
        {"id": "text-embedding-3-small"},
        {"id": "whisper-1"},
        {"id": "dall-e-3"},
        {"id": "gpt-4o-audio-preview"},
    ]}
    ids = [m["id"] for m in mc.parse_openai_models(payload)]
    assert ids == ["gpt-4o-mini", "o3-mini"]
    assert all(m["tier"] == "paid" for m in mc.parse_openai_models(payload))


def test_parse_groq_models_skips_whisper_and_tts():
    payload = {"data": [
        {"id": "llama-3.3-70b-versatile"},
        {"id": "whisper-large-v3"},
        {"id": "playai-tts"},
        {"id": "llama-guard-3-8b"},
    ]}
    ids = [m["id"] for m in mc.parse_groq_models(payload)]
    assert ids == ["llama-3.3-70b-versatile"]


def test_parse_openrouter_uses_real_pricing():
    payload = {"data": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B (free)",
         "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "openai/gpt-4o", "name": "GPT-4o",
         "pricing": {"prompt": "0.0000025", "completion": "0.00001"}},
        {"id": "qwen/qwen-2.5-72b", "name": "Qwen 2.5 72B",
         "pricing": {"prompt": "0", "completion": "0"}},
    ]}
    models = {m["id"]: m["tier"] for m in mc.parse_openrouter_models(payload)}
    assert models["meta-llama/llama-3.3-70b-instruct:free"] == "free"
    assert models["qwen/qwen-2.5-72b"] == "free"      # zero price despite no :free suffix
    assert models["openai/gpt-4o"] == "paid"


def test_sort_catalog_free_first():
    models = [
        {"id": "b-paid", "label": "b", "tier": "paid"},
        {"id": "a-free", "label": "a", "tier": "free"},
        {"id": "a-paid", "label": "a", "tier": "paid"},
    ]
    ordered = mc.sort_catalog(models)
    assert [m["id"] for m in ordered] == ["a-free", "a-paid", "b-paid"]


# ---------------------------------------------------------------------------
# Live verification (mocked httpx)
# ---------------------------------------------------------------------------

def _mock_client(responses):
    """Patch-able httpx.AsyncClient replacement returning queued responses."""
    queue = list(responses)
    client = MagicMock()

    async def _get(*args, **kwargs):
        return queue.pop(0)

    client.get = AsyncMock(side_effect=_get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _resp(status_code: int, payload):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=payload)
    return r


@pytest.mark.asyncio
async def test_verify_gemini_ok():
    client = _mock_client([_resp(200, {"models": [
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
    ]})])
    with patch("app.llm.model_catalog.httpx.AsyncClient", return_value=client):
        info = await mc.verify_and_list_models("gemini", "AIzaTest")
    assert info["provider_type"] == "gemini"
    assert info["free_count"] == 1 and info["paid_count"] == 0
    assert info["models"][0]["id"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_verify_rejects_bad_key():
    client = _mock_client([_resp(401, {"error": "bad key"})])
    with patch("app.llm.model_catalog.httpx.AsyncClient", return_value=client):
        with pytest.raises(mc.KeyVerificationError):
            await mc.verify_and_list_models("openai", "sk-bad")


@pytest.mark.asyncio
async def test_verify_openrouter_checks_key_then_models():
    client = _mock_client([
        _resp(200, {"data": {"label": "my key"}}),   # /key validates the credential
        _resp(200, {"data": [
            {"id": "x:free", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "y", "pricing": {"prompt": "0.001", "completion": "0.002"}},
        ]}),
    ])
    with patch("app.llm.model_catalog.httpx.AsyncClient", return_value=client):
        info = await mc.verify_and_list_models("openrouter", "sk-or-v1-test")
    assert info["free_count"] == 1 and info["paid_count"] == 1
    assert info["models"][0]["id"] == "x:free"


@pytest.mark.asyncio
async def test_verify_unknown_provider_returns_manual_note():
    info = await mc.verify_and_list_models("custom", "whatever")
    assert info["models"] == []
    assert "manually" in info["notes"]
