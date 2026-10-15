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

from app.tools.conversation_library import ConversationSkills

logger = logging.getLogger("Agent.Engagement")


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
        """Generate an authentic, human, friendly reply to a Facebook comment."""
        channel = self.settings.channel
        page_name = channel.name or "Hyper Motion"
        if "ultimate" in page_name.lower():
            page_name = page_name.replace("Ultimate", "").replace("ultimate", "").strip() or "Hyper Motion"

        prompt = ConversationSkills.build_system_prompt(
            page_name=page_name,
            niche=channel.niche,
            user_message=f"{comment_text} (Context: {post_context[:160]})" if post_context else comment_text,
            is_comment=True,
            user_name=commenter_name
        )

        try:
            reply = await self.gateway.generate_text(
                prompt=prompt,
                temperature=0.75,
                max_tokens=220,
                agent_name="engagement",
            )
            logger.info(f"Generated human comment reply for: {comment_text[:60]!r}")
            raw_reply = reply.strip().strip('"')

            # Clean any leftover assistant / page prefixes
            for pfx in [f"{page_name}:", "Assistant:", "Reply:", "Kenji:"]:
                if raw_reply.lower().startswith(pfx.lower()):
                    raw_reply = raw_reply[len(pfx):].strip()

            if commenter_name and commenter_name.lower() not in ("there", "someone", "unknown", ""):
                if not raw_reply.lower().startswith(f"@{commenter_name.lower()}") and not raw_reply.lower().startswith(commenter_name.lower()):
                    return f"@{commenter_name} {raw_reply}"
            return raw_reply
        except Exception as e:
            logger.error(f"Failed to generate comment reply: {e}")
            prefix = f"@{commenter_name} " if commenter_name and commenter_name.lower() not in ("there", "someone") else ""
            return f"{prefix}Appreciate you stopping by and sharing your thoughts! Always glad to have you here. ✨"

    async def generate_messenger_reply(
        self,
        message_text: str,
        sender_name: str = "there",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a warm, friendly Messenger reply using active conversational skills & formality awareness."""
        channel = self.settings.channel
        page_name = channel.name or "Hyper Motion"
        if "ultimate" in page_name.lower():
            page_name = page_name.replace("Ultimate", "").replace("ultimate", "").strip() or "Hyper Motion"

        prompt = ConversationSkills.build_system_prompt(
            page_name=page_name,
            niche=channel.niche,
            user_message=message_text,
            conversation_history=history,
            is_comment=False,
            user_name=sender_name
        )

        try:
            reply = await self.gateway.generate_text(
                prompt=prompt,
                temperature=0.75,
                max_tokens=250,
                agent_name="engagement",
            )
            logger.info(f"Generated Messenger reply for: {message_text[:60]!r}")
            raw_reply = reply.strip().strip('"')

            for pfx in [f"{page_name}:", "Assistant:", "Reply:", "Kenji:"]:
                if raw_reply.lower().startswith(pfx.lower()):
                    raw_reply = raw_reply[len(pfx):].strip()

            return raw_reply
        except Exception as e:
            logger.error(f"Failed to generate Messenger reply: {e}")
            return f"Hey {sender_name}! Thanks for reaching out. We're glad to connect with you — how can I help you today?"

