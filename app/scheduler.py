"""
Autonomous Background Scheduler for Ultimate Content Agent.
Periodically sweeps for new trends, fact-checks top breakout stories,
and drafts complete scripts & SEO bundles autonomously.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.config import get_settings
from app.orchestrator import ContentOrchestrator

logger = logging.getLogger("AutonomousScheduler")

class AutonomousScheduler:
    def __init__(self, orchestrator: Optional[ContentOrchestrator] = None):
        self.orchestrator = orchestrator or ContentOrchestrator()
        self.settings = get_settings()
        self._task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        if self._is_running:
            return
        if not self.settings.autonomous_enabled:
            logger.info("Autonomous scheduler is disabled in settings.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Autonomous scheduler started (interval: {self.settings.autonomous_interval_minutes}m).")

    async def stop(self) -> None:
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Autonomous scheduler stopped.")

    async def _loop(self) -> None:
        full_cycle_interval = max(300, self.settings.autonomous_interval_minutes * 60)
        fast_tick_secs = 10  # Check Messenger and comments every 10 seconds for fast replies
        await asyncio.sleep(2)
        last_full_cycle = 0

        while self._is_running:
            # 1. Fast sweep: Auto-reply to new comments and Messenger messages
            try:
                eng = await self.orchestrator.run_engagement_sweep()
                if eng.get("comment_replies", 0) + eng.get("messenger_replies", 0) > 0:
                    logger.info(f"Engagement sweep: {eng['comment_replies']} comment replies, {eng['messenger_replies']} Messenger replies.")
            except Exception as e:
                logger.error(f"Error during engagement sweep: {e}")

            # 2. Process any due scheduled Facebook posts
            try:
                pub_count = await self.orchestrator.process_scheduled_facebook_posts()
                if pub_count > 0:
                    logger.info(f"AutonomousScheduler auto-published {pub_count} scheduled Facebook post(s).")
            except Exception as e:
                logger.error(f"Error checking scheduled Facebook posts: {e}")

            # 3. Check full autonomous content generation cycle interval
            now = asyncio.get_event_loop().time()
            if (now - last_full_cycle) >= full_cycle_interval:
                try:
                    logger.info("Triggering autonomous content cycle...")
                    await self.orchestrator.run_full_pipeline(trigger="autonomous_scheduler")
                    last_full_cycle = now
                    logger.info("Autonomous cycle completed successfully.")
                except Exception as e:
                    logger.error(f"Error during autonomous cycle: {e}")

            await asyncio.sleep(fast_tick_secs)
