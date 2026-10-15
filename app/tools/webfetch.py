"""
Web article text fetcher and summarizer.
"""
from __future__ import annotations

import logging
import re
from typing import Optional
import httpx
from app.tools.cache import Cache

logger = logging.getLogger(__name__)

class WebFetchTool:
    def __init__(self, cache: Cache | None = None):
        self.cache = cache or Cache()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UltimateAgent/1.0"}

    async def fetch_text(self, url: str, max_chars: int = 4000) -> Optional[str]:
        cache_key = f"fetch:{url}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    text = resp.text
                    # Strip basic HTML tags
                    clean = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                    clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
                    clean = re.sub(r"<[^>]+>", " ", clean)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    truncated = clean[:max_chars]
                    self.cache.set(cache_key, truncated, ttl=7200)
                    return truncated
        except Exception as e:
            logger.warning(f"Failed to fetch url '{url}': {e}")
        return None
