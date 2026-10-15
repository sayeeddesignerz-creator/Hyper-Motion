"""
YouTube topic search tool using YouTube Data API v3 or RSS fallback.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import httpx
from app.config import get_settings
from app.tools.cache import Cache

logger = logging.getLogger(__name__)

class YouTubeSearchTool:
    def __init__(self, cache: Cache | None = None):
        self.cache = cache or Cache()
        self.api_key = get_settings().youtube_api_key

    async def search_topics(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        cache_key = f"yt_search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            return []

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": self.api_key,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results,
            "order": "viewCount"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    items = []
                    for item in data.get("items", []):
                        snippet = item.get("snippet", {})
                        items.append({
                            "title": snippet.get("title", ""),
                            "video_id": item.get("id", {}).get("videoId", ""),
                            "channel_title": snippet.get("channelTitle", ""),
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt", "")
                        })
                    self.cache.set(cache_key, items, ttl=3600)
                    return items
        except Exception as e:
            logger.warning(f"YouTube search failed for '{query}': {e}")
        return []
