"""
SEO Optimizer Agent — generates high-CTR titles, A/B testing variants, rich descriptions, and tag suites.
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.models import SEOBundle, GeneratedScript

SEO_PROMPT = """You are a YouTube & Viral Algorithm SEO Expert.
Script Title: {script_title}
Hook: {hook}
Target Audience: {target_audience}
Content Summary: {summary}

Generate an ultra-optimized SEO bundle:
1. "primary_title": Maximum CTR title under 65 chars (compelling, curiosity-inducing, zero cheap clickbait).
2. "ab_test_titles": Exactly 4 alternative high-converting title angles for A/B testing:
   - Intrigue/Mystery angle
   - Question angle
   - Numbered/Statistic angle
   - Contrarian/Shock angle
3. "description": Rich 200+ word YouTube description with:
   - First 2 lines hook
   - Key takeaway bullets
   - Chapter breakdown timestamps
   - Call to action
4. "tags": 15 high-volume, low-competition tags.
5. "hashtags": 5 relevant hashtags (e.g. #Tech #AI #FactCheck).
6. "discoverability_score": Integer 80 to 98.
7. "ctr_rationale": 2 sentences explaining why these titles maximize click-through rate.

Return JSON:
{{
  "primary_title": "...",
  "ab_test_titles": ["...", "...", "...", "..."],
  "description": "...",
  "tags": ["...", "..."],
  "hashtags": ["...", "..."],
  "discoverability_score": 92,
  "ctr_rationale": "..."
}}
"""

class SEOOptimizerAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("SEOOptimizer", gateway)

    async def optimize(self, script: GeneratedScript) -> SEOBundle:
        self.logger.info(f"Optimizing SEO for script: '{script.title}'")
        
        narrations = " ".join([s.narration for s in script.segments[:5]])
        prompt = SEO_PROMPT.format(
            script_title=script.title,
            hook=script.hook,
            target_audience=self.settings.channel.target_audience,
            summary=narrations[:400]
        )

        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are a senior YouTube SEO strategist.")
            return SEOBundle(
                id=str(uuid.uuid4())[:8],
                script_id=script.id,
                primary_title=res.get("primary_title", script.title),
                ab_test_titles=res.get("ab_test_titles", [
                    f"Why Everyone Is Wrong About {script.title}",
                    f"The Truth Behind {script.title}",
                    f"What Happens If {script.title}?",
                    f"How {script.title} Actually Works"
                ]),
                description=res.get("description", f"In this video we breakdown {script.title}."),
                tags=res.get("tags", ["Tech", "Facts", "Breakthrough"]),
                hashtags=res.get("hashtags", ["#Tech", "#AI", "#Facts"]),
                discoverability_score=int(res.get("discoverability_score", 88)),
                ctr_rationale=res.get("ctr_rationale", "High emotional curiosity combined with high-volume search keywords.")
            )
        except Exception as e:
            self.logger.warning(f"SEO generation failed: {e}. Falling back to default bundle.")
            return SEOBundle(
                id=str(uuid.uuid4())[:8],
                script_id=script.id,
                primary_title=script.title,
                ab_test_titles=[
                    f"The Real Truth About {script.title}",
                    f"What They Don't Tell You About {script.title}"
                ],
                description=f"Deep dive fact check and reaction to {script.title}.",
                tags=["Tech", "News", "Facts"],
                hashtags=["#Facts", "#Tech"],
                discoverability_score=80,
                ctr_rationale="Solid search keyword match."
            )

    async def optimize_facebook_post(self, topic: str, raw_message: str, hook: str) -> Dict[str, Any]:
        """
        Produce algorithmic Meta Graph & Facebook Search SEO optimization:
        - High-volume search keywords & discovery tags
        - Engagement-optimized hashtags (broad + niche + trending)
        - SEO-enriched message formatting with natural keyword injection
        """
        self.logger.info(f"Generating Facebook Algorithm & Search SEO for: '{topic}'")
        prompt = f"""You are a Meta Graph & Facebook Search Algorithm Optimization (SEO) Master.
Topic: {topic}
Hook: {hook}
Draft Message:
{raw_message}

Your goal: Maximize organic reach, Facebook Search discoverability, Suggested Feed placements, and algorithmic ranking.

Requirements:
1. "optimized_message": Refine the post to naturally weave in high-volume search intent keywords while maintaining a viral, punchy, human tone. Ensure the hook stops scrolling, spaced bullets for readability, a compelling engagement question, and relevant hashtags at the bottom.
2. "hashtags": 5 to 7 precision hashtags (mix of high-volume broad tags and topic-specific search tags, e.g. #TechNews #ArtificialIntelligence #FutureTech).
3. "seo_keywords": 8-12 high-intent search keywords that users type into Facebook Search.
4. "seo_score": Estimated algorithmic discoverability score (integer 90 to 99).
5. "search_intent": 1 short sentence summarizing what user search queries this post answers.

Return pure JSON:
{{
  "optimized_message": "...",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "seo_keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "seo_score": 96,
  "search_intent": "..."
}}
"""
        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are Facebook's principal search & viral algorithm engineer.")
            return {
                "message": res.get("optimized_message", raw_message),
                "hashtags": res.get("hashtags", ["#TechNews", "#Innovation", "#Breakthrough", "#FactCheck"]),
                "seo_keywords": res.get("seo_keywords", [topic, "tech updates", "viral news"]),
                "seo_score": int(res.get("seo_score", 95)),
                "search_intent": res.get("search_intent", f"Latest insights and truth about {topic}")
            }
        except Exception as e:
            self.logger.warning(f"Facebook SEO enhancement failed: {e}. Keeping original with curated SEO tags.")
            return {
                "message": raw_message,
                "hashtags": ["#TechNews", "#Innovation", "#Breakthrough", "#FactCheck", "#TrendingNow"],
                "seo_keywords": [topic, "technology", "news update", "insights"],
                "seo_score": 90,
                "search_intent": f"Understanding {topic}"
            }

