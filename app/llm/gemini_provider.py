"""
Google Gemini LLM Provider implementation using google-genai SDK.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.llm.base import BaseLLMProvider

logger = logging.getLogger("GeminiProvider")

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        import os
        self.api_key = api_key
        configured_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.model_name = model_name if (model_name and model_name not in ("gemini-2.5-flash", "gemini-2.5-flash-lite")) else configured_model
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")

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
            raise RuntimeError("Gemini provider is not configured")

        contents = prompt
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        config["temperature"] = temperature
        config["max_output_tokens"] = max_tokens

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.8-flash"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_err = None
        for m in candidate_models:
            try:
                response = await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=m,
                    contents=contents,
                    config=config
                )
                if response.text:
                    self.model_name = m
                    return response.text
            except Exception as err:
                last_err = err
                err_str = str(err)
                if "503" in err_str or "404" in err_str or "UNAVAILABLE" in err_str:
                    logger.warning(f"Gemini model {m} unavailable ({err_str[:80]}), falling back to next candidate...")
                    continue
                raise err
        if last_err:
            raise last_err
        return ""

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        json_system = (system_instruction or "") + "\nRespond with VALID JSON ONLY. Do not include markdown headers or commentary."
        raw_text = await self.generate_text(prompt, system_instruction=json_system, temperature=temperature, max_tokens=max_tokens)
        
        # Clean markdown codeblocks and whitespace
        cleaned = raw_text.strip()
        if "```" in cleaned:
            # Extract content within the first code block if present
            code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if code_block_match:
                cleaned = code_block_match.group(1).strip()
            else:
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
        
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            # Fallback greedy regex match for innermost or outermost json object/array
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            raise ValueError(f"Could not parse valid JSON from Gemini output: {raw_text[:200]}")
