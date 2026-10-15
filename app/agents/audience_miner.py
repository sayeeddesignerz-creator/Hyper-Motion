"""
Audience Miner Agent — mines viewer comments, extracts content ideas, and drafts high-engagement responses.
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.models import AudienceInsight

AUDIENCE_PROMPT = """You are an Audience Intelligence & Community Management Specialist.
Topic / Video: {topic}
Comments Sample:
{comments_sample}

Analyze the audience reaction:
1. Overall sentiment ("positive", "skeptical", "inquisitive", "mixed")
2. Extract top 3 new video/content ideas suggested by viewers
3. Extract top 3 recurring viewer questions or confusions
4. Draft 2 thoughtful, engaging creator replies that spark further conversation.

Return JSON:
{{
  "sentiment": "mixed",
  "extracted_ideas": ["Topic idea 1", "Topic idea 2", "Topic idea 3"],
  "viewer_questions": ["Question 1?", "Question 2?", "Question 3?"],
  "draft_replies": [
    {{"comment": "Is this actually viable?", "reply": "Great question! While the early tests are promising..."}},
    {{"comment": "Wait, did they test this on humans?", "reply": "Currently still in peer-reviewed trials, but..."}}
  ]
}}
"""

class AudienceMinerAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("AudienceMiner", gateway)

    async def analyze_community(self, topic: str, comments: List[str]) -> AudienceInsight:
        self.logger.info(f"Mining audience insights for: '{topic}'")
        sample_text = "\n".join([f"- {c}" for c in comments[:10]]) if comments else "- What happens next with this tech?\n- Is this actually real or just marketing hype?"

        prompt = AUDIENCE_PROMPT.format(topic=topic, comments_sample=sample_text)
        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are an audience engagement expert.")
            return AudienceInsight(
                id=str(uuid.uuid4())[:8],
                topic_or_video=topic,
                sentiment=res.get("sentiment", "inquisitive"),
                extracted_ideas=res.get("extracted_ideas", [f"Future implications of {topic}"]),
                viewer_questions=res.get("viewer_questions", ["How soon will this be available?"]),
                draft_replies=res.get("draft_replies", [])
            )
        except Exception as e:
            self.logger.warning(f"Audience mining failed: {e}")
            return AudienceInsight(
                id=str(uuid.uuid4())[:8],
                topic_or_video=topic,
                sentiment="inquisitive",
                extracted_ideas=[f"Part 2: Deep dive into {topic}"],
                viewer_questions=["What is the real timeline?"],
                draft_replies=[]
            )
