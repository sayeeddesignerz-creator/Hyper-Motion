"""
End-to-end Multi-Agent Orchestrator for Ultimate Content Agent.
"""
from __future__ import annotations

import logging
import uuid
from typing import Dict, Any, List, Optional

from app.db import Database
from app.events import events
from app.llm.gateway import LLMGateway
from app.models import (
    PipelineRun, GeneratedScript, SEOBundle, TrendItem, ClaimItem, utc_now,
    FacebookPageProfile, FacebookMonetizationStatus, FacebookGrowthReport,
    FacebookPostItem, FacebookPostStatus
)
from app.agents.trend_hunter import TrendHunterAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.strategist import StrategistAgent
from app.agents.script_forge import ScriptForgeAgent
from app.agents.seo_optimizer import SEOOptimizerAgent
from app.agents.audience_miner import AudienceMinerAgent
from app.agents.learner import LearnerAgent
from app.agents.facebook_growth_agent import FacebookGrowthAgent
from app.agents.facebook_content_agent import FacebookContentAgent
from app.agents.engagement_agent import EngagementAgent
from app.tools.facebook import FacebookClient

logger = logging.getLogger("Orchestrator")

class ContentOrchestrator:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.gateway = LLMGateway()

        # Core Agents
        self.trend_hunter = TrendHunterAgent(self.gateway)
        self.fact_checker = FactCheckerAgent(self.gateway)
        self.strategist = StrategistAgent(self.gateway)
        self.script_forge = ScriptForgeAgent(self.gateway)
        self.seo_optimizer = SEOOptimizerAgent(self.gateway)
        self.audience_miner = AudienceMinerAgent(self.gateway)
        self.learner = LearnerAgent(self.gateway)

        # Facebook & Monetization Growth Engine
        self.facebook_client = FacebookClient()
        self.facebook_growth = FacebookGrowthAgent(self.gateway)
        self.facebook_content = FacebookContentAgent(self.gateway)
        self.engagement_agent = EngagementAgent(self.gateway)
        self._replied_comment_ids: set = set()  # in-memory dedup per session

    async def initialize(self) -> None:
        await self.db.initialize()
        logger.info("ContentOrchestrator database initialized.")

    async def run_discovery(self, limit: int = 15) -> List[TrendItem]:
        await events.broadcast("pipeline_progress", {"step": "trend_discovery", "status": "running"})
        trends = await self.trend_hunter.hunt_trends(limit=limit)
        await self.db.save_trends(trends)
        await events.broadcast("pipeline_progress", {"step": "trend_discovery", "status": "completed", "count": len(trends)})
        return trends

    async def run_fact_check(self, topic: str, snippet: str = "") -> List[ClaimItem]:
        await events.broadcast("pipeline_progress", {"step": "fact_check", "status": "running", "topic": topic})
        claims = await self.fact_checker.verify_topic(topic, snippet)
        await self.db.save_claims(claims)
        await events.broadcast("pipeline_progress", {"step": "fact_check", "status": "completed", "claims_count": len(claims)})
        return claims

    async def run_full_pipeline(self, target_topic: Optional[str] = None, trigger: str = "manual") -> Dict[str, Any]:
        run_id = str(uuid.uuid4())[:8]
        run = PipelineRun(id=run_id, trigger=trigger, status="running", current_step="start")
        await self.db.save_pipeline_run(run)
        await events.broadcast("pipeline_started", {"run_id": run_id, "trigger": trigger})

        try:
            # 1. Topic Selection
            topic = target_topic
            topic_snippet = ""
            if not topic:
                run.current_step = "hunting_trends"
                await self.db.save_pipeline_run(run)
                trends = await self.run_discovery(limit=10)
                run.trend_count = len(trends)
                if trends:
                    top_trend = trends[0]
                    topic = top_trend.title
                    topic_snippet = top_trend.snippet or ""
                else:
                    topic = self.strategist.get_evergreen_topic()
                    topic_snippet = "Evergreen high-performing tech pillar"

            # 2. Fact-Checking
            run.current_step = "fact_checking"
            await self.db.save_pipeline_run(run)
            claims = await self.run_fact_check(topic, topic_snippet)
            run.claims_verified = len(claims)

            # 3. Strategy Formulation
            run.current_step = "strategy_formulation"
            await self.db.save_pipeline_run(run)
            await events.broadcast("pipeline_progress", {"step": "strategy", "status": "running", "topic": topic})
            fact_summary = "; ".join([f"{c.claim_text} ({c.status.value})" for c in claims])
            angle = await self.strategist.create_angle(topic, fact_summary)
            await events.broadcast("pipeline_progress", {"step": "strategy", "status": "completed", "angle": angle.angle})

            # 4. Script Forging
            run.current_step = "script_forging"
            await self.db.save_pipeline_run(run)
            await events.broadcast("pipeline_progress", {"step": "script_forging", "status": "running"})
            script = await self.script_forge.forge_script(topic, angle, claims)
            await self.db.save_script(script)
            run.script_id = script.id
            await events.broadcast("pipeline_progress", {"step": "script_forging", "status": "completed", "script_id": script.id})

            # 5. SEO Optimization
            run.current_step = "seo_optimization"
            await self.db.save_pipeline_run(run)
            await events.broadcast("pipeline_progress", {"step": "seo_optimization", "status": "running"})
            seo_bundle = await self.seo_optimizer.optimize(script)
            await self.db.save_seo_bundle(seo_bundle)
            run.seo_id = seo_bundle.id
            await events.broadcast("pipeline_progress", {"step": "seo_optimization", "status": "completed", "seo_id": seo_bundle.id})

            # Finalize run
            run.status = "completed"
            run.current_step = "done"
            run.completed_at = utc_now()
            await self.db.save_pipeline_run(run)

            result = {
                "run_id": run_id,
                "topic": topic,
                "angle": angle.model_dump(),
                "claims": [c.model_dump() for c in claims],
                "script": script.model_dump(),
                "seo": seo_bundle.model_dump()
            }
            await events.broadcast("pipeline_completed", {"run_id": run_id, "script_id": script.id})
            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            run.status = "failed"
            run.error = str(e)
            run.completed_at = utc_now()
            await self.db.save_pipeline_run(run)
            await events.broadcast("pipeline_failed", {"run_id": run_id, "error": str(e)})
            raise

    # =========================================================================
    # Facebook Page Growth & Publishing Automation
    # =========================================================================

    def refresh_facebook_client(self, page_id: Optional[str] = None, access_token: Optional[str] = None) -> FacebookClient:
        """Reload Facebook client when settings or tokens are updated."""
        self.facebook_client = FacebookClient(page_id=page_id, access_token=access_token)
        logger.info("FacebookClient re-initialized.")
        return self.facebook_client

    async def run_facebook_audit(self) -> Dict[str, Any]:
        """Perform full page health audit, monetization progress calculation, and growth roadmap."""
        await events.broadcast("facebook_audit_progress", {"step": "fetching_page", "status": "running"})
        
        # 1. Fetch live or simulated page profile, posts, insights
        raw_profile = await self.facebook_client.get_page_profile()
        profile = FacebookPageProfile(
            id=raw_profile.get("id", "sim_page"),
            name=raw_profile.get("name", "Facebook Creator Page"),
            category=raw_profile.get("category", "Media / News"),
            followers_count=raw_profile.get("followers_count", 0),
            fan_count=raw_profile.get("fan_count", 0),
            connected=raw_profile.get("connected", False),
            simulation_mode=raw_profile.get("simulation_mode", True),
            about=raw_profile.get("about"),
            picture_url=raw_profile.get("picture_url"),
            last_synced=utc_now()
        )
        await self.db.save_facebook_page_profile(profile)

        posts = await self.facebook_client.get_page_posts(limit=10)
        insights = await self.facebook_client.get_page_insights()

        await events.broadcast("facebook_audit_progress", {"step": "analyzing_growth", "status": "running"})

        # 2. Run growth & monetization auditor
        monetization_status, growth_report = await self.facebook_growth.analyze_page(profile, posts, insights)
        await self.db.save_facebook_monetization(monetization_status)
        await self.db.save_facebook_growth_report(growth_report)

        await events.broadcast("facebook_audit_completed", {
            "page_id": profile.id,
            "readiness_percentage": monetization_status.readiness_percentage,
            "followers": monetization_status.followers_current
        })

        return {
            "profile": profile.model_dump(),
            "monetization": monetization_status.model_dump(),
            "growth_report": growth_report.model_dump(),
            "recent_posts": posts
        }

    async def run_facebook_content_pipeline(
        self,
        target_topic: Optional[str] = None,
        auto_publish: bool = False,
        generate_images: bool = True,
        image_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete viral Facebook Growth package:
        - Hook-driven Feed Post + AI Image
        - Interactive 3-slide Story Sequence + Vertical AI Image
        - 45-60s Reel Retention Script
        Optionally publishes directly to the Page via Meta Graph API.
        """
        await events.broadcast("facebook_content_progress", {"step": "topic_selection", "status": "running"})

        # 1. Topic Selection (Use provided, or pick from recent growth report or trending news)
        topic = target_topic
        if not topic:
            recent_reports = await self.db.get_recent_facebook_growth_reports(limit=1)
            if recent_reports and recent_reports[0].get("recommended_topics"):
                topic = recent_reports[0]["recommended_topics"][0]
            else:
                trends = await self.run_discovery(limit=5)
                topic = trends[0].title if trends else self.strategist.get_evergreen_topic()

        # 2. Fact Check context
        await events.broadcast("facebook_content_progress", {"step": "fact_checking", "status": "running", "topic": topic})
        claims = await self.fact_checker.verify_topic(topic)

        # 3. Angle Formulation
        angle = await self.strategist.create_angle(topic, "; ".join([c.claim_text for c in claims[:3]]))

        # 4. Generate Content Bundle (Feed Post, Story, Reel, Images)
        await events.broadcast("facebook_content_progress", {"step": "generating_content_and_images", "status": "running"})
        content_bundle = await self.facebook_content.generate_facebook_package(
            topic=topic,
            angle=angle,
            claims=claims,
            generate_images=generate_images,
            image_provider=image_provider
        )

        feed_post: FacebookPostItem = content_bundle["feed_post"]
        story_post: FacebookPostItem = content_bundle["story"]
        reel_post: FacebookPostItem = content_bundle["reel"]

        # 5. Full SEO Optimization for Facebook Post (Meta Search + Suggested Algorithm)
        await events.broadcast("facebook_content_progress", {"step": "optimizing_seo", "status": "running", "topic": topic})
        try:
            seo_data = await self.seo_optimizer.optimize_facebook_post(
                topic=topic,
                raw_message=feed_post.message,
                hook=feed_post.hook
            )
            feed_post.message = seo_data.get("message", feed_post.message)
            feed_post.hashtags = seo_data.get("hashtags", feed_post.hashtags)
            feed_post.seo_keywords = seo_data.get("seo_keywords", [])
            feed_post.seo_score = seo_data.get("seo_score", 95)
        except Exception as e:
            self.logger.warning(f"Failed to apply SEO pass to Facebook post: {e}")

        # 6. Save items to DB
        await self.db.save_facebook_post(feed_post)
        await self.db.save_facebook_post(story_post)
        await self.db.save_facebook_post(reel_post)

        # 7. Optional Auto-Publish (Published with full SEO optimization)
        publish_results = {}
        if auto_publish:
            await events.broadcast("facebook_content_progress", {"step": "publishing_to_facebook", "status": "running"})
            pub_res = await self.publish_facebook_item(feed_post.id)
            publish_results["feed_post"] = pub_res

        await events.broadcast("facebook_content_completed", {
            "topic": topic,
            "feed_post_id": feed_post.id,
            "story_id": story_post.id,
            "reel_id": reel_post.id
        })

        return {
            "topic": topic,
            "feed_post": (await self.db.get_facebook_post(feed_post.id)),
            "story": (await self.db.get_facebook_post(story_post.id)),
            "reel": (await self.db.get_facebook_post(reel_post.id)),
            "published": publish_results
        }

    async def publish_facebook_item(self, post_id: str) -> Dict[str, Any]:
        """Publish a specific draft or scheduled item to Facebook."""
        post_data = await self.db.get_facebook_post(post_id)
        if not post_data:
            return {"success": False, "error": f"Post with ID '{post_id}' not found"}

        post_type = post_data.get("post_type", "feed")
        caption = post_data.get("message", "")
        img_path = post_data.get("image_path")
        hashtags = post_data.get("hashtags", [])

        # If caption does not have hashtags, append them automatically before publishing
        if hashtags and "#" not in caption:
            tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in hashtags])
            caption = f"{caption.strip()}\n\n{tag_str}"

        result = {"success": False}
        if post_type == "story":
            result = await self.facebook_client.publish_story(image_path=img_path)
        elif img_path:
            result = await self.facebook_client.publish_photo_post(caption=caption, image_path=img_path)
        else:
            result = await self.facebook_client.publish_feed_post(message=caption)

        if result.get("success"):
            fb_id = result.get("id")
            permalink = result.get("permalink_url") or f"https://facebook.com/{fb_id}"
            await self.db.update_facebook_post_status(
                post_id=post_id,
                status="published",
                fb_post_id=fb_id,
                permalink_url=permalink,
                published_at=utc_now()
            )
            await events.broadcast("facebook_item_published", {
                "post_id": post_id,
                "fb_post_id": fb_id,
                "permalink": permalink,
                "simulated": result.get("simulated", False)
            })
        else:
            err = result.get("error", "Unknown publishing error")
            await self.db.update_facebook_post_status(
                post_id=post_id,
                status="failed",
                error_message=str(err)
            )

        return result

    async def process_scheduled_facebook_posts(self) -> int:
        """Find any posts due for publishing and publish them automatically."""
        now_iso = utc_now()
        due_posts = await self.db.get_due_scheduled_facebook_posts(now_iso)
        published_count = 0
        for p in due_posts:
            logger.info(f"Auto-publishing scheduled Facebook item: {p['id']}")
            res = await self.publish_facebook_item(p["id"])
            if res.get("success"):
                published_count += 1
        return published_count

    async def run_engagement_sweep(self) -> Dict[str, Any]:
        """Sweep page posts for new comments and Messenger inbox for unread messages, then auto-reply with AI."""
        comment_replies = 0
        messenger_replies = 0
        errors = []

        if not self.facebook_client.is_configured:
            logger.info("Engagement sweep skipped — Facebook not configured.")
            return {"comment_replies": 0, "messenger_replies": 0, "skipped": True}

        # --- 1. Reply to Messenger inbox messages (Checked first for near-instant messaging) ---
        try:
            import datetime as _dt
            inbox = await self.facebook_client.get_inbox_messages(limit=15)
            for msg_item in inbox:
                sender_id   = msg_item.get("sender_id", "")
                msg_text    = msg_item.get("message", "").strip()
                sender_name = msg_item.get("sender_name", "there")
                msg_id      = msg_item.get("message_id", "")
                created_at  = msg_item.get("created_time", "")

                if not sender_id or not msg_text or msg_id in self._replied_comment_ids:
                    continue

                # ── Guard: skip messages outside the 24-h reply window ─────────
                # Facebook's Messenger policy only allows RESPONSE-type messages
                # within 24 hours of the user's last message. Attempting to send
                # after that always fails with error_subcode 2018278.
                if created_at:
                    try:
                        msg_time  = _dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        age_hours = (_dt.datetime.now(_dt.timezone.utc) - msg_time).total_seconds() / 3600
                        if age_hours > 23.5:          # 30-min safety margin
                            self._replied_comment_ids.add(msg_id)   # don't retry
                            logger.debug(
                                f"Skipping Messenger reply to {sender_name} — "
                                f"message is {age_hours:.1f}h old (24-h window closed)."
                            )
                            continue
                    except Exception:
                        pass  # unparseable timestamp → attempt the reply anyway
                # ──────────────────────────────────────────────────────────────

                reply_text = await self.engagement_agent.generate_messenger_reply(
                    message_text=msg_text,
                    sender_name=sender_name,
                )
                result = await self.facebook_client.send_messenger_message(sender_id, reply_text)

                if result.get("message_id"):
                    # Success
                    self._replied_comment_ids.add(msg_id)
                    messenger_replies += 1
                    logger.info(f"Replied to Messenger from {sender_name} ({sender_id})")
                elif result.get("window_expired"):
                    # Policy window closed — mark handled, not an error
                    self._replied_comment_ids.add(msg_id)
                    logger.debug(f"Messenger window expired for {sender_name} — marked handled.")
                else:
                    errors.append(f"Messenger reply failed for {sender_name}: {result.get('error', 'unknown')}")
        except Exception as e:
            logger.error(f"Error during Messenger sweep: {e}")
            errors.append(str(e))


        # --- 2. Reply to post comments ---
        try:
            # Get recent live posts from the page feed
            live_posts = await self.facebook_client.get_page_posts(limit=15)
            for post in live_posts:
                post_id = post.get("id", "")
                if not post_id:
                    continue
                comments = await self.facebook_client.get_post_comments(post_id, limit=10)
                post_context = post.get("message", "")[:200]
                for comment in comments:
                    comment_id = comment.get("id", "")
                    if not comment_id or comment_id in self._replied_comment_ids:
                        continue
                    commenter_id = str(comment.get("from", {}).get("id", ""))
                    # Don't reply to page's own comments
                    if commenter_id == str(self.facebook_client.page_id):
                        continue
                    # Don't reply if page already replied to this comment
                    existing_replies = comment.get("comments", {}).get("data", [])
                    has_page_reply = any(str(r.get("from", {}).get("id", "")) == str(self.facebook_client.page_id) for r in existing_replies)
                    if has_page_reply:
                        self._replied_comment_ids.add(comment_id)
                        continue
                    comment_text = comment.get("message", "").strip()
                    commenter = comment.get("from", {}).get("name", "there")
                    if not comment_text:
                        continue
                    # Generate and post reply
                    reply_text = await self.engagement_agent.generate_comment_reply(
                        comment_text=comment_text,
                        post_context=post_context,
                        commenter_name=commenter,
                    )
                    result = await self.facebook_client.reply_to_comment(
                        comment_id=comment_id,
                        message=reply_text,
                        user_id=commenter_id if commenter_id and commenter_id != "None" else None
                    )
                    if result.get("id") and not result.get("error"):
                        self._replied_comment_ids.add(comment_id)
                        comment_replies += 1
                        logger.info(f"✅ Replied to comment {comment_id} by {commenter}")
                    else:
                        errors.append(f"Comment reply failed: {result.get('error', 'unknown')}")
        except Exception as e:
            logger.error(f"Error during comment sweep: {e}")
            errors.append(str(e))

        await events.broadcast("engagement_sweep_completed", {
            "comment_replies": comment_replies,
            "messenger_replies": messenger_replies,
            "errors": errors,
        })
        logger.info(f"Engagement sweep done — {comment_replies} comment replies, {messenger_replies} Messenger replies.")
        return {"comment_replies": comment_replies, "messenger_replies": messenger_replies, "errors": errors}

