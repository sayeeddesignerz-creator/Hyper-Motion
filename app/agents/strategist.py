"""
Content Strategist Agent — plans channel positioning, hook concepts, and evergreen topic fallbacks.
"""
from __future__ import annotations

import random
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.models import ContentAngle, FormatType

EVERGREEN_TOPICS = [
    "Digital Minimalism: How Top Engineers Reclaim Their Focus",
    "The 5 Artificial Intelligence Myths You Still Believe",
    "How Modern Algorithms Control What You Buy & Think",
    "The Science of Speed Reading & High-Speed Knowledge Retention",
    "Quantum Computing Explained Simply: What Changes by 2030"
]

STRATEGY_PROMPT = """You are an Expert Content Strategist for YouTube and Viral Media.
Channel Context:
Name: {channel_name}
Target Audience: {target_audience}
Niche: {niche}

Topic to Strategize: {topic}
Fact Check Summary: {fact_summary}

Determine the optimal editorial angle, hook premise, target format (shorts vs long_form), and emotional trigger.

Return JSON:
{{
  "pillar": "Pillar Name",
  "angle": "Unique editorial angle for high engagement",
  "target_emotion": "curiosity | surprise | intrigue | urgency",
  "hook_premise": "Compelling first line or opening visual premise",
  "format_type": "shorts" | "long_form"
}}
"""

class StrategistAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("Strategist", gateway)

    async def create_angle(self, topic: str, fact_summary: str = "") -> ContentAngle:
        self.logger.info(f"Formulating strategy for: '{topic}'")
        ch = self.settings.channel
        prompt = STRATEGY_PROMPT.format(
            channel_name=ch.name,
            target_audience=ch.target_audience,
            niche=ch.niche,
            topic=topic,
            fact_summary=fact_summary
        )

        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are a master media strategist.")
            fmt_str = str(res.get("format_type", "shorts")).lower()
            fmt_enum = FormatType.LONG_FORM if "long" in fmt_str else FormatType.SHORTS

            return ContentAngle(
                pillar=res.get("pillar", ch.content_pillars[0] if ch.content_pillars else "Tech Facts"),
                angle=res.get("angle", f"Deep dive analysis into {topic}"),
                target_emotion=res.get("target_emotion", "curiosity"),
                hook_premise=res.get("hook_premise", f"What everyone got wrong about {topic}..."),
                format_type=fmt_enum
            )
        except Exception as e:
            self.logger.warning(f"Strategy generation failed: {e}. Using default angle.")
            return ContentAngle(
                pillar="Tech Breakthroughs",
                angle=f"The truth behind {topic}",
                target_emotion="curiosity",
                hook_premise=f"Here is what you weren't told about {topic}...",
                format_type=FormatType.SHORTS
            )

    def get_evergreen_topic(self) -> str:
        return random.choice(EVERGREEN_TOPICS)
