"""
News tool — fetch breaking news and trends via RSS feeds.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

import feedparser
from app.tools.cache import Cache

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

class NewsTool:
    def __init__(self, cache: Cache | None = None):
        self.cache = cache or Cache()

    async def search_news(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        cache_key = f"news:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            import asyncio
            url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
            feed = await asyncio.to_thread(feedparser.parse, url)
            articles = []
            for entry in feed.entries[:max_results]:
                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:500],
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "Google News",
                })
            self.cache.set(cache_key, articles, ttl=1800)
            return articles
        except Exception as e:
            logger.warning(f"Google News RSS fetch failed for '{query}': {e}")
            return []
