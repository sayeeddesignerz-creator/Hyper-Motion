"""
Configuration loader — reads YAML channel config & .env secrets.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

_cfg_logger = logging.getLogger("Config")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = PROJECT_ROOT / ".cache"
DATA_DIR = PROJECT_ROOT / "data"
MEDIA_DIR = OUTPUT_DIR / "facebook_media"

for path in (CONFIG_DIR, OUTPUT_DIR, CACHE_DIR, DATA_DIR, MEDIA_DIR):
    path.mkdir(parents=True, exist_ok=True)

def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

_load_dotenv()

class ChannelTone(BaseModel):
    style: str = "Analytical, Punchy, High-Energy, Fact-Based"
    voice: str = "Authoritative yet accessible storyteller"
    pacing: str = "Fast-paced with clear visual transitions"

class FormatConfig(BaseModel):
    length_seconds: List[int] = Field(default_factory=lambda: [30, 60, 180, 600])
    word_range: List[int] = Field(default_factory=lambda: [100, 1200])
    max_sentences: int = 50

class ChannelConfig(BaseModel):
    name: str = Field(default_factory=lambda: os.getenv("CHANNEL_NAME", "Ultimate Tech & Facts"))
    niche: str = "Tech, Science, Viral Facts & Strategic Analysis"
    language: str = "en"
    audience_region: str = "US"
    target_audience: str = Field(default_factory=lambda: os.getenv("TARGET_AUDIENCE", "Tech Enthusiasts & Curiosity Seekers"))
    youtube_category_ids: List[int] = Field(default_factory=lambda: [27, 28, 24])
    content_pillars: List[str] = Field(default_factory=lambda: [
        "Tech Breakthroughs & AI Innovations",
        "Fact Check vs Viral Myths",
        "Deep Dive Strategic Analysis",
        "Future Tech Trends"
    ])
    tone: ChannelTone = Field(default_factory=ChannelTone)
    format_config: FormatConfig = Field(default_factory=FormatConfig)
    banned_topics: List[str] = Field(default_factory=list)
    trusted_sources: List[str] = Field(default_factory=lambda: [
        "reuters.com", "apnews.com", "nature.com", "arxiv.org", "techcrunch.com", "bbc.com", "theverge.com"
    ])
    subreddits: List[str] = Field(default_factory=lambda: ["technology", "futrology", "todayilearned", "science"])
    niche_keywords: List[str] = Field(default_factory=lambda: ["AI", "Tech", "Science", "Breakthrough", "Fact Check", "Future"])

class AgentLLMConfig(BaseModel):
    provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini"))
    model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    temperature: float = 0.3
    max_output_tokens: int = 4096

class Settings(BaseModel):
    # API Keys
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openrouter_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    youtube_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY"))

    # OmniRoute local proxy settings
    omniroute_base_url: str = Field(
        default_factory=lambda: os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
    )
    omniroute_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OMNIROUTE_API_KEY")
    )
    omniroute_model: str = Field(
        default_factory=lambda: os.getenv("OMNIROUTE_MODEL", "auto")
    )

    # Default Provider Settings
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    image_generation_provider: str = Field(
        default_factory=lambda: os.getenv("IMAGE_GENERATION_PROVIDER", "openai")
    )
    openai_image_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
    )

    # Server settings
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    dashboard_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("DASHBOARD_API_KEY"))

    # Autonomous scheduler
    autonomous_enabled: bool = Field(default_factory=lambda: os.getenv("AUTONOMOUS_ENABLED", "true").lower() == "true")
    autonomous_interval_minutes: int = Field(default_factory=lambda: int(os.getenv("AUTONOMOUS_INTERVAL_MINUTES", "60")))

    # Facebook Meta Graph API Configuration
    facebook_page_access_token: Optional[str] = Field(default_factory=lambda: os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"))
    facebook_page_id: Optional[str] = Field(default_factory=lambda: os.getenv("FACEBOOK_PAGE_ID"))
    facebook_app_id: Optional[str] = Field(default_factory=lambda: os.getenv("FACEBOOK_APP_ID"))
    facebook_app_secret: Optional[str] = Field(default_factory=lambda: os.getenv("FACEBOOK_APP_SECRET"))
    facebook_graph_version: str = Field(default_factory=lambda: os.getenv("FACEBOOK_GRAPH_VERSION", "v21.0"))
    facebook_simulation_mode: bool = Field(default_factory=lambda: os.getenv("FACEBOOK_SIMULATION_MODE", "false").lower() == "true")
    facebook_webhook_verify_token: str = Field(default_factory=lambda: os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "hypermotion_webhook_secret"))

    # Channel configuration
    channel: ChannelConfig = Field(default_factory=ChannelConfig)

_settings_instance: Optional[Settings] = None


def _warn_omniroute_url(url: str) -> None:
    """Log a startup warning when OmniRoute is pointed at a non-localhost URL."""
    host = urlparse(url).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        _cfg_logger.warning(
            "OMNIROUTE_BASE_URL '%s' is not localhost — ensure the remote endpoint "
            "is trusted and OMNIROUTE_API_KEY is kept secure.",
            url,
        )


def reload_settings() -> Settings:
    global _settings_instance
    _load_dotenv()
    _settings_instance = Settings()
    return _settings_instance

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
        _warn_omniroute_url(_settings_instance.omniroute_base_url)
    return _settings_instance
