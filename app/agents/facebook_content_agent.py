"""
Facebook Content Forge Agent.
Generates viral Feed Posts, interactive Story sequences, high-retention Reel scripts,
and automatically generates matching AI visuals for Facebook Pages.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models import (
    FacebookPostItem, FacebookPostType, FacebookPostStatus,
    FacebookStorySlide, ClaimItem, ContentAngle, utc_now
)
from app.tools.image_generator import MediaGenerator

logger = logging.getLogger("FacebookContentAgent")

FB_CONTENT_PROMPT = """You are a Master Facebook Content Creator, Viral Copywriter & Meta SEO Strategist.
Create a high-growth Facebook content package engineered for MAXIMUM algorithmic distribution, search discovery, comments, shares, and watch time.

TARGET TOPIC: {topic}
EDITORIAL ANGLE: {angle}
VERIFIED FACTS & CONTEXT:
{facts_summary}

REQUIREMENTS:
1. FEED POST (FULL SEO OPTIMIZED):
   - Hook: Irresistible 1-line pattern interrupt that stops mindless feed scrolling.
   - Body Structure: Clean, spaced lines with micro-paragraphs. High utility/intellectual value.
   - SEO Keywords: Naturally integrate high-volume search terms related to the topic so the post ranks on Facebook Search and in "Suggested For You" feeds.
   - Engagement Catalyst: End with an open-ended debate question that triggers comments (key algorithmic multiplier).
   - SEO Hashtag Suite: 5 high-converting, topic-specific and discovery hashtags placed cleanly at the end.
   - Visual Prompt: Detailed, rich prompt to generate a 1:1 photorealistic or graphic asset.

2. STORIES SEQUENCE (3 Slides):
   - Slide 1 (Hook): Grabs attention in 1 second.
   - Slide 2 (Core Revelation): The surprising takeaway or fact.
   - Slide 3 (Interactive): Poll or Question sticker prompt (e.g. "Did you know this? [Yes / Mind blown]").
   - Detailed visual prompt for generating a vertical 9:16 story graphic.

3. REEL / VIDEO SCRIPT (45-60s):
   - Hook (0-3s): Punchy visual interrupt and bold opening line.
   - Retention Body (3-45s): Fast-paced, concise script with visual cues in brackets.
   - Climax & CTA (45-60s): Call to action to follow the page for daily breakthroughs.

Return JSON in this EXACT structure:
{{
  "feed_post": {{
    "title": "Short title or headline",
    "hook": "Opening 1-line hook",
    "message": "Full post text formatted with proper line breaks, emojis, bullet points, call-to-action question, and hashtags at the bottom.",
    "call_to_action": "Specific engagement prompt",
    "hashtags": ["#TechTrends", "#Innovation", "#FactCheck", "#SearchTerm"],
    "seo_keywords": ["keyword 1", "keyword 2", "keyword 3"],
    "image_prompt": "Photorealistic or stylized visual prompt for 1080x1080 square graphic"
  }},
  "story_sequence": {{
    "slides": [
      {{
        "slide_id": 1,
        "title": "Hook Slide",
        "overlay_text": "Text for slide 1",
        "interactive_sticker": null,
        "visual_description": "Bold visual description"
      }},
      {{
        "slide_id": 2,
        "title": "Revelation Slide",
        "overlay_text": "Text for slide 2",
        "interactive_sticker": null,
        "visual_description": "Data or infographic visual"
      }},
      {{
        "slide_id": 3,
        "title": "Interactive CTA Slide",
        "overlay_text": "Text for slide 3",
        "interactive_sticker": "Poll: [Option A] vs [Option B]",
        "visual_description": "Call to action visual"
      }}
    ],
    "story_image_prompt": "Vertical 9:16 aesthetic visual prompt for story background"
  }},
  "reel_script": {{
    "title": "Reel Title",
    "hook": "0-3s opening line",
    "script_content": "Full video script with [Visual Cues] and (Audio cues)",
    "call_to_action": "Follow for daily breakthroughs"
  }}
}}
"""

class FacebookContentAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("FacebookContent", gateway)
        self.media_gen = MediaGenerator()

    async def generate_facebook_package(
        self,
        topic: str,
        angle: Optional[ContentAngle] = None,
        claims: Optional[List[ClaimItem]] = None,
        generate_images: bool = True,
        image_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete Facebook growth bundle:
        - Feed Post with generated 1:1 image
        - Story sequence with generated 9:16 vertical image
        - Viral Reel script
        """
        self.logger.info(f"Crafting Facebook growth content package for: '{topic}'")

        facts_text = ""
        if claims:
            facts_text = "\n".join([f"- {c.claim_text} ({c.status.value}): {c.verdict_explanation}" for c in claims[:4]])
        if not facts_text:
            facts_text = f"Top industry breakthrough and analytical perspective on {topic}."

        angle_str = angle.angle if angle else f"The untold truth and strategic impact of {topic}"

        prompt = FB_CONTENT_PROMPT.format(
            topic=topic,
            angle=angle_str,
            facts_summary=facts_text
        )

        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are Facebook's #1 viral content strategist.")
        except Exception as e:
            self.logger.warning(f"LLM content generation failed: {e}. Generating structured template.")
            res = self._fallback_package(topic)

        feed_data = res.get("feed_post", {})
        story_data = res.get("story_sequence", {})
        reel_data = res.get("reel_script", {})

        # Generate Real AI Visuals if requested
        post_img_path = None
        story_img_path = None
        if generate_images:
            try:
                img_prompt = feed_data.get("image_prompt", f"High tech futuristic concept representing {topic}")
                post_img_path = await self.media_gen.generate_post_image(
                    prompt=img_prompt,
                    title=feed_data.get("hook", topic),
                    provider=image_provider
                )
            except Exception as e:
                self.logger.error(f"Error generating feed image: {e}")

            try:
                story_prompt = story_data.get("story_image_prompt", f"Vertical wallpaper aesthetic for {topic}")
                story_img_path = await self.media_gen.generate_story_image(
                    prompt=story_prompt,
                    overlay_text=feed_data.get("hook", topic),
                    provider=image_provider
                )
            except Exception as e:
                self.logger.error(f"Error generating story image: {e}")

        # Construct Feed Post Item
        post_id = f"fb_{uuid.uuid4().hex[:8]}"
        feed_post_item = FacebookPostItem(
            id=post_id,
            post_type=FacebookPostType.FEED,
            title=feed_data.get("title", f"The Truth About {topic}"),
            message=feed_data.get("message", f"Breaking down {topic}...\n\nWhat are your thoughts on this?"),
            hook=feed_data.get("hook", f"Here is what everyone gets wrong about {topic}:"),
            call_to_action=feed_data.get("call_to_action", "Drop your opinion below!"),
            hashtags=feed_data.get("hashtags", ["#Tech", "#Innovation", "#Breakthrough"]),
            seo_keywords=feed_data.get("seo_keywords", [topic, "technology", "news"]),
            seo_score=95,
            image_path=post_img_path,
            image_prompt=feed_data.get("image_prompt"),
            status=FacebookPostStatus.DRAFT,
            created_at=utc_now()
        )

        # Construct Story Item
        story_id = f"fbstory_{uuid.uuid4().hex[:8]}"
        raw_slides = story_data.get("slides", [])
        slides = [
            FacebookStorySlide(
                slide_id=s.get("slide_id", i),
                title=s.get("title", f"Slide {i}"),
                overlay_text=s.get("overlay_text", ""),
                interactive_sticker=s.get("interactive_sticker"),
                visual_description=s.get("visual_description", ""),
                image_path=story_img_path
            )
            for i, s in enumerate(raw_slides, 1)
        ]

        story_post_item = FacebookPostItem(
            id=story_id,
            post_type=FacebookPostType.STORY,
            title=f"Story: {topic}",
            message=slides[0].overlay_text if slides else f"Did you know about {topic}?",
            hook=slides[0].overlay_text if slides else "",
            call_to_action=slides[-1].interactive_sticker if slides else "Tap to vote",
            image_path=story_img_path,
            image_prompt=story_data.get("story_image_prompt"),
            story_slides=slides,
            status=FacebookPostStatus.DRAFT,
            created_at=utc_now()
        )

        # Construct Reel Item
        reel_id = f"fbreel_{uuid.uuid4().hex[:8]}"
        reel_post_item = FacebookPostItem(
            id=reel_id,
            post_type=FacebookPostType.REEL,
            title=reel_data.get("title", f"Reel: {topic}"),
            message=reel_data.get("script_content", f"[0-3s Hook] Stop scrolling if you follow {topic}..."),
            hook=reel_data.get("hook", f"Stop scrolling if you follow {topic}!"),
            call_to_action=reel_data.get("call_to_action", "Follow for daily breakthroughs"),
            video_script=reel_data.get("script_content"),
            hashtags=["#Reels", "#Viral", "#TechReels"],
            status=FacebookPostStatus.DRAFT,
            created_at=utc_now()
        )

        return {
            "feed_post": feed_post_item,
            "story": story_post_item,
            "reel": reel_post_item,
            "topic": topic
        }

    def _fallback_package(self, topic: str) -> Dict[str, Any]:
        return {
            "feed_post": {
                "title": f"The Real Impact of {topic}",
                "hook": f"🚨 Most people completely misunderstand what's happening with {topic} right now.",
                "message": (
                    f"🚨 Most people completely misunderstand what's happening with {topic} right now.\n\n"
                    f"Behind the viral headlines, three key shifts are fundamentally reshaping this space:\n\n"
                    f"1️⃣ The mainstream narrative focuses on hype, ignoring the actual architecture.\n"
                    f"2️⃣ Real-world testing proves the most shared claims are exaggerated.\n"
                    f"3️⃣ Early adopters who understand the mechanics are quietly reaping the rewards.\n\n"
                    f"👉 Have you noticed this shift yet, or do you think the hype is justified? Let me know your take in the comments!\n\n"
                    f"#Technology #Innovation #TechNews #FactCheck #FutureTech"
                ),
                "call_to_action": "Let me know your take in the comments below!",
                "hashtags": ["#Technology", "#Innovation", "#FactCheck", "#FutureTech"],
                "image_prompt": f"Minimalist modern tech infographic explaining {topic}, emerald green and deep dark slate palette, 8k crisp details"
            },
            "story_sequence": {
                "slides": [
                    {
                        "slide_id": 1,
                        "title": "Shocking Truth",
                        "overlay_text": f"Wait... did you believe the viral rumors about {topic}?",
                        "interactive_sticker": None,
                        "visual_description": "Dramatic dark background with illuminated question icon"
                    },
                    {
                        "slide_id": 2,
                        "title": "The Verified Fact",
                        "overlay_text": f"Here is what the evidence actually proves. (Swipe to see)",
                        "interactive_sticker": None,
                        "visual_description": "Clean data graphic with emerald verified seal"
                    },
                    {
                        "slide_id": 3,
                        "title": "Vote Now",
                        "overlay_text": f"Did this change your perspective on {topic}?",
                        "interactive_sticker": "Poll: [Totally!] vs [Still skeptical]",
                        "visual_description": "Interactive voting card format"
                    }
                ],
                "story_image_prompt": f"Vertical phone wallpaper aesthetic showing illuminated neural grid and data streams, deep emerald green accents, 9:16 ratio"
            },
            "reel_script": {
                "title": f"Why Everyone is Wrong About {topic}",
                "hook": f"[0-3s] Don't make this mistake when looking at {topic}!",
                "script_content": (
                    f"[0-3s Fast zoom] Don't make this mistake when looking at {topic}!\n\n"
                    f"[3-15s On-screen text: THE MYTH] Everyone is sharing this headline claiming miraculous results overnight.\n\n"
                    f"[15-35s B-roll illustration] But when you look at the technical whitepaper, here is the catch they aren't telling you.\n\n"
                    f"[35-50s Green highlight overlay] The real breakthrough isn't the scale—it's how the models orchestrate together.\n\n"
                    f"[50-60s Host to camera] If you want verified facts before the crowd catches on, tap follow right now!"
                ),
                "call_to_action": "Tap follow for verified daily tech breakdowns!"
            }
        }
