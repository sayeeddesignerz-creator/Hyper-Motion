"""
Abstract Base Class for LLM Providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider credentials exist."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        """Generate plain text from prompt."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Generate structured JSON dict from prompt."""
        pass
