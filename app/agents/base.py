"""
Base Agent class for Ultimate Content Agent.
"""
from __future__ import annotations

import logging
from typing import Optional
from app.llm.gateway import LLMGateway
from app.config import get_settings

class BaseAgent:
    def __init__(self, name: str, gateway: Optional[LLMGateway] = None):
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
        self.gateway = gateway or LLMGateway()
        self.settings = get_settings()
