"""
OpenAI & OpenRouter LLM Provider implementation using openai SDK.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from app.llm.base import BaseLLMProvider

logger = logging.getLogger("OpenAIProvider")

class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model_name: str = "gpt-4o-mini",
        base_url: Optional[str] = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self._client = None
        if self.api_key:
            try:
                from openai import AsyncOpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider is not configured")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        json_system = (system_instruction or "") + "\nRespond with VALID JSON ONLY. Do not include markdown headers or commentary."
        raw_text = await self.generate_text(prompt, system_instruction=json_system, temperature=temperature, max_tokens=max_tokens)

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Could not parse valid JSON from OpenAI output: {raw_text[:200]}")
