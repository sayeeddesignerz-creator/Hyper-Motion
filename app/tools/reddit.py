"""
Reddit topic and discussion scraper tool (uses Reddit public JSON endpoints).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import httpx
from app.tools.cache import Cache

logger = logging.getLogger(__name__)

class RedditTool:
    def __init__(self, cache: Cache | None = None):
        self.cache = cache or Cache()
        self.headers = {"User-Agent": "ultimate-content-agent/1.0 (Mozilla/5.0)"}

    async def get_hot_posts(self, subreddit: str = "technology", limit: int = 15) -> List[Dict[str, Any]]:
        cache_key = f"reddit:{subreddit}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    posts = []
                    for c in children:
                        post_data = c.get("data", {})
                        if post_data.get("stickied"):
                            continue
                        posts.append({
                            "title": post_data.get("title", ""),
                            "url": f"https://reddit.com{post_data.get('permalink', '')}",
                            "score": post_data.get("score", 0),
                            "num_comments": post_data.get("num_comments", 0),
                            "selftext": post_data.get("selftext", "")[:400],
                            "subreddit": subreddit
                        })
                    self.cache.set(cache_key, posts, ttl=1800)
                    return posts
        except Exception as e:
            logger.warning(f"Reddit fetch failed for r/{subreddit}: {e}")
        return []
