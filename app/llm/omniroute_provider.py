"""
OmniRoute LLM Provider - OpenAI-compatible client using httpx.

Reads:
  OMNIROUTE_BASE_URL  (default: http://localhost:20128/v1)
  OMNIROUTE_API_KEY   (required for non-localhost targets)
  OMNIROUTE_MODEL     (default: auto)

Logs a clear WARNING if the base URL is not localhost/127.0.0.1.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from app.llm.base import BaseLLMProvider

logger = logging.getLogger("OmniRouteProvider")

_DEFAULT_BASE_URL = "http://localhost:20128/v1"
_DEFAULT_MODEL = "auto"


def _is_localhost(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


class OmniRouteProvider(BaseLLMProvider):
    """
    Thin httpx wrapper around any OpenAI-compatible endpoint.
    Designed specifically for the OmniRoute local proxy but works
    with any compatible API (just set OMNIROUTE_BASE_URL).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("OMNIROUTE_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.api_key = api_key or os.getenv("OMNIROUTE_API_KEY", "")
        self.model = model or os.getenv("OMNIROUTE_MODEL", _DEFAULT_MODEL)

        if not _is_localhost(self.base_url):
            logger.warning(
                "OmniRoute base URL '%s' is not localhost - make sure the "
                "remote endpoint is trusted and your API key is secure.",
                self.base_url,
            )

        self._headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        # Always available - works even without a key against localhost
        return True

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"] or ""

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        json_system = (
            (system_instruction or "")
            + "\nRespond with VALID JSON ONLY. Do not include markdown headers or commentary."
        )
        raw = await self.generate_text(
            prompt,
            system_instruction=json_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(
                f"OmniRouteProvider: could not parse JSON from response: {raw[:200]}"
            )
