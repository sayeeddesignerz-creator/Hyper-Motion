"""
Script Forge Agent — produces production-grade multi-format narration & visual cue scripts.
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.models import GeneratedScript, ScriptSegment, FormatType, ContentAngle, ClaimItem

SCRIPT_PROMPT = """You are an Award-Winning Scriptwriter for Viral Videos & Educational Tech Essays.
Channel Tone: {tone}
Target Format: {format_type}
Topic: {topic}
Editorial Angle: {angle}
Hook Premise: {hook_premise}
Fact-Checked Claims & Evidence: {claims_text}

Write a complete, high-retention script with timestamped segments.
For EACH segment provide:
- segment_id (1, 2, 3...)
- duration_seconds (e.g. 5)
- visual_cue (b-roll, motion graphic, text overlay, or facial reaction)
- narration (exact spoken text)
- on_screen_text (punchy caption or keyword)
- sound_effect (optional audio cue like [swoosh], [chime], [dramatic riser])

Return JSON:
{{
  "title": "Working Video Title",
  "hook": "Opening 5-second retention hook",
  "call_to_action": "Ending CTA (Subscribe, Comment, Share)",
  "segments": [
    {{
      "segment_id": 1,
      "duration_seconds": 5,
      "visual_cue": "Fast zooms on headline with glowing highlight",
      "narration": "What if everything you were told about this technology was completely wrong?",
      "on_screen_text": "THE BIG LIE",
      "sound_effect": "[dramatic riser]"
    }}
  ]
}}
"""

class ScriptForgeAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("ScriptForge", gateway)

    async def forge_script(
        self,
        topic: str,
        angle: ContentAngle,
        claims: List[ClaimItem]
    ) -> GeneratedScript:
        self.logger.info(f"Forging {angle.format_type.value} script for: '{topic}'")
        
        claims_formatted = "\n".join([f"- Claim: {c.claim_text} | Verdict: {c.status.value} ({c.verdict_explanation})" for c in claims])
        
        prompt = SCRIPT_PROMPT.format(
            tone=self.settings.channel.tone.style,
            format_type=angle.format_type.value,
            topic=topic,
            angle=angle.angle,
            hook_premise=angle.hook_premise,
            claims_text=claims_formatted
        )

        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You write masterclass high-retention scripts.")
            raw_segs = res.get("segments", [])
            segments: List[ScriptSegment] = []
            total_duration = 0
            total_words = 0

            for i, s in enumerate(raw_segs, 1):
                dur = int(s.get("duration_seconds", 5))
                narr = str(s.get("narration", ""))
                words = len(narr.split())
                total_duration += dur
                total_words += words

                segments.append(ScriptSegment(
                    segment_id=i,
                    duration_seconds=dur,
                    visual_cue=s.get("visual_cue", "Dynamic graphic overlay"),
                    narration=narr,
                    on_screen_text=s.get("on_screen_text"),
                    sound_effect=s.get("sound_effect")
                ))

            citations = [f"{c.claim_text}: {c.status.value}" for c in claims]

            return GeneratedScript(
                id=str(uuid.uuid4())[:8],
                title=res.get("title", topic),
                format_type=angle.format_type,
                hook=res.get("hook", angle.hook_premise),
                segments=segments,
                call_to_action=res.get("call_to_action", "Subscribe for more fact-checked breakdowns!"),
                word_count=total_words,
                duration_estimate_sec=total_duration,
                citations=citations
            )
        except Exception as e:
            self.logger.error(f"Script forging failed: {e}. Falling back to template script.")
            fallback_seg = ScriptSegment(
                segment_id=1,
                duration_seconds=10,
                visual_cue="Headline visual with animated facts",
                narration=f"{topic}. Here is what the facts tell us.",
                on_screen_text=topic[:20],
                sound_effect="[chime]"
            )
            return GeneratedScript(
                id=str(uuid.uuid4())[:8],
                title=topic,
                format_type=angle.format_type,
                hook=angle.hook_premise,
                segments=[fallback_seg],
                call_to_action="Subscribe for more daily insights!",
                word_count=15,
                duration_estimate_sec=10,
                citations=[]
            )
