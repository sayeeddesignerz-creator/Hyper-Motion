"""
Facebook Growth & Monetization Agent.
Analyzes Facebook Page health, historical post performance, audience retention,
and tracks progress toward Facebook Monetization (In-Stream Ads, Stars, Performance Bonus).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models import (
    FacebookPageProfile, FacebookMonetizationStatus,
    FacebookGrowthReport, utc_now
)

logger = logging.getLogger("FacebookGrowthAgent")

GROWTH_AUDIT_PROMPT = """You are a World-Class Meta / Facebook Growth Strategist and Monetization Consultant.
Analyze the following Facebook Page data and past content performance.

PAGE CONTEXT:
Page Name: {page_name}
Category: {category}
About / Description: {about}
Current Followers: {followers_count} / 5,000 (Target for In-Stream Ads & Stars)
Estimated 60-Day Watch Minutes: {minutes_viewed} / 60,000 (Target)
Active Videos Count: {active_videos} / 5 (Target)

CRITICAL INSTRUCTION: Tailor all recommended topics, angles, and strategies SPECIFICALLY to this Page's actual niche, audience, and industry (e.g. if the page is Japanese education, focus on Japanese language and culture; if cooking, focus on recipes). Do NOT suggest generic tech or AI topics unless the page itself is about tech!

RECENT POSTS & ENGAGEMENT:
{posts_summary}

YOUR TASK:
Formulate a comprehensive growth strategy to push this page to 100% Monetization Eligibility.
Facebook algorithm rules to leverage:
1. Comment section depth (provocative yet respectful questions trigger 5x algorithm reach).
2. Shareability quotient (high-utility checklists, debunked myths, and relatable paradigms get shared to Groups).
3. 1+ minute video retention (drives eligible watch minutes).
4. Stories keep daily active audience returning.

Return JSON in this EXACT structure:
{{
  "analysis_summary": "2-3 sentences diagnosing the page's current state and biggest viral opportunities.",
  "monetization_readiness_score": 75,
  "monetization_gap_analysis": "Exact gap breakdown for Followers and Watch Time with velocity estimate.",
  "top_performing_angles": [
    "Angle 1: Debunking viral tech myths with proof",
    "Angle 2: Counter-intuitive workflow secrets",
    "Angle 3: Behind-the-scenes engineering breakdowns"
  ],
  "recommended_topics": [
    "Topic 1 for rapid viral reach",
    "Topic 2 for high comment discussion",
    "Topic 3 for group shares"
  ],
  "daily_schedule_plan": [
    {{"time": "09:00 AM", "type": "Story", "action": "Interactive Poll / Hook"}},
    {{"time": "01:00 PM", "type": "Feed Post", "action": "High-Value Infographic or Debunk Post"}},
    {{"time": "07:30 PM", "type": "Reel / Video", "action": "Retention-focused 60s Breakdown"}}
  ],
  "actionable_steps": [
    "Step 1 to accelerate followers",
    "Step 2 to boost watch minutes",
    "Step 3 for policy safety"
  ]
}}
"""

class FacebookGrowthAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("FacebookGrowth", gateway)

    async def analyze_page(
        self,
        profile: FacebookPageProfile,
        recent_posts: List[Dict[str, Any]],
        insights: Dict[str, Any]
    ) -> tuple[FacebookMonetizationStatus, FacebookGrowthReport]:
        """Audit page and generate monetization progress + growth action report."""
        self.logger.info(f"Auditing page '{profile.name}' for monetization growth...")

        # Calculate base metrics from real live data
        followers_curr = profile.followers_count
        followers_target = 5000
        minutes_curr = insights.get("minutes_viewed_60d", 0)
        minutes_target = 60000
        active_posts = len(recent_posts)

        # Posts summary for LLM prompt
        posts_str = ""
        for i, p in enumerate(recent_posts[:5], 1):
            posts_str += f"{i}. \"{p.get('message', '')[:100]}...\" (Likes: {p.get('likes', 0)}, Comments: {p.get('comments', 0)}, Shares: {p.get('shares', 0)})\n"

        prompt = GROWTH_AUDIT_PROMPT.format(
            page_name=profile.name,
            category=profile.category,
            about=profile.about or "General",
            followers_count=followers_curr,
            minutes_viewed=minutes_curr,
            active_videos=active_posts,
            posts_summary=posts_str or "No historical posts fetched yet."
        )

        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are Meta's top content growth architect.")
        except Exception as e:
            self.logger.warning(f"LLM growth audit failed: {e}. Falling back to heuristic audit.")
            res = self._heuristic_audit(profile, followers_curr, minutes_curr, active_posts)

        # Compute readiness percentage
        fol_pct = min(1.0, followers_curr / max(1, followers_target)) * 40
        min_pct = min(1.0, minutes_curr / max(1, minutes_target)) * 40
        act_pct = min(1.0, active_posts / 5) * 20
        calculated_readiness = round(fol_pct + min_pct + act_pct, 1)

        readiness_score = float(res.get("monetization_readiness_score", calculated_readiness))
        eligible = (followers_curr >= followers_target) and (minutes_curr >= minutes_target) and (active_posts >= 5)

        monetization_status = FacebookMonetizationStatus(
            page_id=profile.id,
            page_name=profile.name,
            followers_current=followers_curr,
            followers_target=followers_target,
            minutes_viewed_current=minutes_curr,
            minutes_viewed_target=minutes_target,
            active_posts_current=active_posts,
            active_posts_target=5,
            policy_compliance=True,
            readiness_percentage=readiness_score,
            eligible_for_monetization=eligible,
            daily_growth_target="Post 1 High-Retention Reel + 1 Value Post + 2 Stories daily to reach 5k followers in ~18 days",
            actionable_steps=res.get("actionable_steps", [
                "Post 60s retention Reels with immediate 2-second visual pattern interrupts",
                "Pin top comments with a follow-up controversy question to double comment count",
                "Share verified fact-checks to targeted niche Facebook Groups"
            ]),
            updated_at=utc_now()
        )

        growth_report = FacebookGrowthReport(
            id=f"rep_{utc_now()[:10].replace('-', '')}_{profile.id[:6]}",
            page_id=profile.id,
            page_name=profile.name,
            analysis_summary=res.get("analysis_summary", "Page has strong initial engagement momentum. Key gap is reaching 5,000 follower threshold and consistent 60-day watch time."),
            top_performing_angles=res.get("top_performing_angles", [
                "Debunking Viral Myths with Proof Citations",
                "Speed breakdowns of complex technical concepts",
                "Counter-intuitive career & tech revelations"
            ]),
            recommended_topics=res.get("recommended_topics", [
                "Why AI Models Are Hitting A Wall: The Compound AI Revolution",
                "The 3 Tech Habits Killing Your Productivity",
                "Fact Check: The Truth Behind Room Temperature Quantum Computing"
            ]),
            monetization_gap_analysis=res.get("monetization_gap_analysis", f"Remaining: {max(0, followers_target - followers_curr)} followers and {max(0, minutes_target - minutes_curr)} watch minutes."),
            daily_schedule_plan=res.get("daily_schedule_plan", [
                {"time": "09:00 AM", "type": "Story", "action": "Curiosity Question Sticker"},
                {"time": "01:30 PM", "type": "Feed Post", "action": "Infographic or Fact-Check Post"},
                {"time": "08:00 PM", "type": "Reel", "action": "60s Video Script with Visual Cues"}
            ]),
            created_at=utc_now()
        )

        return monetization_status, growth_report

    def _heuristic_audit(self, profile, followers, minutes, active_posts) -> Dict[str, Any]:
        fol_pct = min(1.0, followers / 5000) * 40
        min_pct = min(1.0, minutes / 60000) * 40
        act_pct = min(1.0, active_posts / 5) * 20
        calculated_readiness = round(fol_pct + min_pct + act_pct, 1)

        is_japanese = "nihongo" in profile.name.lower() or "japanese" in (profile.about or "").lower()
        if is_japanese:
            angles = [
                "Japanese Language Nuances & Common Beginner Mistakes",
                "JLPT Grammar Hacks & Mnemonics for Fast Retention",
                "Cultural Context Behind Everyday Japanese Expressions"
            ]
            topics = [
                "Why Textbook Japanese Fails in Real Conversations in Tokyo",
                "5 Kanji Tricks to Learn 100 Characters in 7 Days",
                "Common Mistakes Foreigners Make When Speaking Polite Keigo"
            ]
        else:
            angles = [
                "High-Value Educational Breakdowns",
                "Quick-Lesson Reels with 3-Second Retention Hooks",
                "Interactive Quizzes and Daily Practice Prompts"
            ]
            topics = [
                f"Essential Tips for {profile.name} Audience",
                "Top 5 Mistakes Beginners Make and How to Avoid Them",
                "Daily Quick Challenge for Followers"
            ]

        return {
            "analysis_summary": f"Page '{profile.name}' is actively connected with {followers} followers and {active_posts} posts. Growth strategy is calibrated for monetization.",
            "monetization_readiness_score": calculated_readiness,
            "monetization_gap_analysis": f"Remaining to monetize: {max(0, 5000 - followers)} followers, {max(0, 60000 - minutes)} watch minutes, and {max(0, 5 - active_posts)} eligible posts.",
            "top_performing_angles": angles,
            "recommended_topics": topics,
            "daily_schedule_plan": [
                {"time": "09:00 AM", "type": "Story", "action": "Morning Poll / Trend Hook"},
                {"time": "01:00 PM", "type": "Feed Post", "action": "In-depth Fact Check / Graphic Post"},
                {"time": "07:30 PM", "type": "Reel", "action": "Viral 60s Reel with punchy audio"}
            ],
            "actionable_steps": [
                "Use high-contrast hook banners in all image graphics",
                "End every post with an open question to provoke comments",
                "Maintain 100% original content to avoid Meta Partner Monetization demonetization"
            ]
        }
