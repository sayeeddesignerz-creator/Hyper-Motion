"""
Google Trends tool using pytrends with RSS fallback.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import feedparser
from app.tools.cache import Cache

logger = logging.getLogger(__name__)

DAILY_TRENDS_RSS = "https://trends.google.com/trending/rss?geo={geo}"

class TrendsTool:
    def __init__(self, cache: Cache | None = None):
        self.cache = cache or Cache()

    async def get_daily_trends(self, geo: str = "US", max_results: int = 20) -> List[Dict[str, Any]]:
        cache_key = f"trends:{geo}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        results = []
        import asyncio
        # Attempt pytrends if available
        try:
            from pytrends.request import TrendReq
            def _fetch_pytrends():
                pytrend = TrendReq(hl="en-US", tz=360)
                return pytrend.trending_searches(pn=geo.lower() if geo.lower() != "us" else "united_states")
            df = await asyncio.to_thread(_fetch_pytrends)
            for idx, row in df.head(max_results).iterrows():
                results.append({
                    "title": str(row[0]),
                    "traffic": "50K+",
                    "source": "Google Trends",
                    "snippet": f"Trending topic on Google ({geo})"
                })
        except Exception as e:
            logger.info(f"pytrends library call fell back to Google Trends RSS: {e}")
            try:
                feed = await asyncio.to_thread(feedparser.parse, DAILY_TRENDS_RSS.format(geo=geo.upper()))
                for entry in feed.entries[:max_results]:
                    results.append({
                        "title": entry.get("title", ""),
                        "traffic": entry.get("ht_approx_traffic", "10K+"),
                        "source": "Google Trends RSS",
                        "snippet": entry.get("description", "")[:300],
                        "news_item": entry.get("ht_news_item_title", "")
                    })
            except Exception as rss_err:
                logger.warning(f"Google Trends RSS failed: {rss_err}")

        self.cache.set(cache_key, results, ttl=3600)
        return results
