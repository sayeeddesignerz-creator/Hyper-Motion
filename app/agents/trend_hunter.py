"""
Trend Hunter Agent — scans multi-source signals and finds viral topics.
"""
from __future__ import annotations

import uuid
from typing import List
from rapidfuzz import fuzz

from app.agents.base import BaseAgent
from app.models import TrendItem, SourceType
from app.tools.news import NewsTool
from app.tools.trends import TrendsTool
from app.tools.reddit import RedditTool
from app.tools.youtube_search import YouTubeSearchTool

class TrendHunterAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("TrendHunter", gateway)
        self.news_tool = NewsTool()
        self.trends_tool = TrendsTool()
        self.reddit_tool = RedditTool()
        self.youtube_tool = YouTubeSearchTool()

    async def hunt_trends(self, limit: int = 15) -> List[TrendItem]:
        self.logger.info("Starting multi-source trend sweep...")
        raw_items: List[TrendItem] = []

        keywords = self.settings.channel.niche_keywords
        subreddits = self.settings.channel.subreddits

        # 1. Google Trends
        try:
            gtrends = await self.trends_tool.get_daily_trends(max_results=8)
            for gt in gtrends:
                raw_items.append(TrendItem(
                    id=str(uuid.uuid4())[:8],
                    title=gt.get("title", ""),
                    source=SourceType.GOOGLE_TRENDS,
                    snippet=gt.get("snippet", ""),
                    search_volume=gt.get("traffic", "50K+"),
                    trend_score=90.0,
                    category="Search Momentum"
                ))
        except Exception as e:
            self.logger.warning(f"Error fetching Google Trends: {e}")

        # 2. News RSS
        try:
            for kw in keywords[:3]:
                news = await self.news_tool.search_news(kw, max_results=4)
                for n in news:
                    raw_items.append(TrendItem(
                        id=str(uuid.uuid4())[:8],
                        title=n.get("title", ""),
                        source=SourceType.RSS,
                        url=n.get("link"),
                        snippet=n.get("summary", ""),
                        trend_score=80.0,
                        category="News"
                    ))
        except Exception as e:
            self.logger.warning(f"Error fetching News: {e}")

        # 3. Reddit hot posts
        try:
            for sub in subreddits[:2]:
                rposts = await self.reddit_tool.get_hot_posts(sub, limit=5)
                for rp in rposts:
                    raw_items.append(TrendItem(
                        id=str(uuid.uuid4())[:8],
                        title=rp.get("title", ""),
                        source=SourceType.REDDIT,
                        url=rp.get("url"),
                        snippet=rp.get("selftext", ""),
                        trend_score=float(min(95, 70 + (rp.get("score", 0) // 100))),
                        category=f"r/{sub}"
                    ))
        except Exception as e:
            self.logger.warning(f"Error fetching Reddit: {e}")

        # Deduplicate using fuzzy similarity
        deduped: List[TrendItem] = []
        for item in raw_items:
            is_dup = False
            for existing in deduped:
                if fuzz.token_sort_ratio(item.title.lower(), existing.title.lower()) > 75:
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(item)

        # Sort by trend_score descending
        deduped.sort(key=lambda x: x.trend_score, reverse=True)
        return deduped[:limit]
