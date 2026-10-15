"""
Engagement Agent — auto-replies to Facebook post comments and Messenger inbox messages.
Uses the LLM Gateway to generate contextual, on-brand replies.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.llm.gateway import LLMGateway
from app.config import get_settings

logger = logging.getLogger("Agent.Engagement")

REPLY_SYSTEM_PROMPT = """You are the social media manager for a Facebook Page.
Your job is to craft short, warm, and engaging replies to comments and Messenger messages.

Rules:
- Keep replies under 3 sentences.
- Sound human, conversational, and positive — never robotic.
- If a comment is a question, answer it helpfully.
- If it's praise, thank them genuinely and encourage engagement (follow, share, etc).
- If it's criticism, respond calmly and professionally.
- Match the language of the commenter (if they write in another language, reply in that language).
- Never mention that you are an AI.
- End with a soft CTA when relevant (e.g. "Stay tuned for more!" or "Drop your thoughts below 👇").

Page context:
- Page Name: {page_name}
- Page Niche: {niche}
- Tone: {tone}
"""


class EngagementAgent(BaseAgent):
    def __init__(self, gateway: Optional[LLMGateway] = None):
        super().__init__("Engagement", gateway)
        self.settings = get_settings()

    async def generate_comment_reply(
        self,
        comment_text: str,
        post_context: str = "",
        commenter_name: str = "there",
    ) -> str:
        """Generate an AI reply to a Facebook comment."""
        channel = self.settings.channel
        system = REPLY_SYSTEM_PROMPT.format(
            page_name=channel.name,
            niche=channel.niche,
            tone=channel.tone.style,
        )
        user_prompt = (
            f"Post context: {post_context[:200] if post_context else 'General page post'}\n"
            f"Commenter ({commenter_name}) wrote: \"{comment_text}\"\n\n"
            "Write a concise, friendly reply to this comment."
        )
        try:
            reply = await self.gateway.generate_text(
                prompt=user_prompt,
                system_instruction=system,
                temperature=0.7,
                max_tokens=300,
                agent_name="engagement",
            )
            logger.info(f"Generated comment reply for: {comment_text[:60]!r}")
            raw_reply = reply.strip().strip('"')
            # If the reply does not start with the commenter's name, prefix it so Facebook triggers a push notification
            if commenter_name and commenter_name.lower() not in ("there", "someone", "unknown", ""):
                if not raw_reply.lower().startswith(f"@{commenter_name.lower()}") and not raw_reply.lower().startswith(commenter_name.lower()):
                    return f"@{commenter_name} {raw_reply}"
            return raw_reply
        except Exception as e:
            logger.error(f"Failed to generate comment reply: {e}")
            prefix = f"@{commenter_name} " if commenter_name and commenter_name.lower() not in ("there", "someone") else ""
            return f"{prefix}Thanks for your comment! Keep practicing and stay tuned for more! 🚀"

    async def generate_messenger_reply(
        self,
        message_text: str,
        sender_name: str = "there",
    ) -> str:
        """Generate an AI reply to a Messenger inbox message."""
        channel = self.settings.channel
        system = REPLY_SYSTEM_PROMPT.format(
            page_name=channel.name,
            niche=channel.niche,
            tone=channel.tone.style,
        )
        user_prompt = (
            f"Messenger message from {sender_name}: \"{message_text}\"\n\n"
            "Write a helpful, friendly reply to this message."
        )
        try:
            reply = await self.gateway.generate_text(
                prompt=user_prompt,
                system_instruction=system,
                temperature=0.7,
                max_tokens=300,
                agent_name="engagement",
            )
            logger.info(f"Generated Messenger reply for: {message_text[:60]!r}")
            return reply.strip().strip('"')
        except Exception as e:
            logger.error(f"Failed to generate Messenger reply: {e}")
            return f"Hi {sender_name}! Thanks for reaching out. We will get back to you shortly!"
