"""
Async SQLite Database for Ultimate Content Agent.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite

from app.config import DATA_DIR
from app.models import (
    TrendItem, ClaimItem, GeneratedScript, SEOBundle, 
    AudienceInsight, PipelineRun, utc_now,
    FacebookPostItem, FacebookPostType, FacebookPostStatus,
    FacebookPageProfile, FacebookMonetizationStatus, FacebookGrowthReport, FacebookStorySlide
)

DB_PATH = DATA_DIR / "ultimate.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create tables if they do not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trends (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT,
                    snippet TEXT,
                    search_volume TEXT,
                    trend_score REAL DEFAULT 0.0,
                    category TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    claim_text TEXT NOT NULL,
                    original_context TEXT,
                    status TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    evidence TEXT,
                    sources TEXT,
                    verdict_explanation TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    format_type TEXT NOT NULL,
                    hook TEXT,
                    segments TEXT NOT NULL,
                    call_to_action TEXT,
                    word_count INTEGER DEFAULT 0,
                    duration_estimate_sec INTEGER DEFAULT 0,
                    citations TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS seo_bundles (
                    id TEXT PRIMARY KEY,
                    script_id TEXT NOT NULL,
                    primary_title TEXT NOT NULL,
                    ab_test_titles TEXT,
                    description TEXT NOT NULL,
                    tags TEXT,
                    hashtags TEXT,
                    discoverability_score INTEGER DEFAULT 85,
                    ctr_rationale TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS audience_insights (
                    id TEXT PRIMARY KEY,
                    topic_or_video TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    extracted_ideas TEXT,
                    viewer_questions TEXT,
                    draft_replies TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id TEXT PRIMARY KEY,
                    trigger TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    trend_count INTEGER DEFAULT 0,
                    claims_verified INTEGER DEFAULT 0,
                    script_id TEXT,
                    seo_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS omni_providers (
                    id TEXT PRIMARY KEY,
                    provider_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    api_key TEXT,
                    base_url TEXT,
                    models TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS omni_routes (
                    route_name TEXT PRIMARY KEY,
                    primary_provider_id TEXT NOT NULL,
                    primary_model TEXT NOT NULL,
                    fallback_chain TEXT NOT NULL,
                    cooldown_seconds INTEGER DEFAULT 300,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS omni_engines (
                    id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(provider_id, model)
                )
            """)

            # Facebook Integration Tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS facebook_posts (
                    id TEXT PRIMARY KEY,
                    post_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    hook TEXT,
                    call_to_action TEXT,
                    hashtags TEXT,
                    image_path TEXT,
                    image_prompt TEXT,
                    story_slides TEXT,
                    video_script TEXT,
                    status TEXT NOT NULL,
                    fb_post_id TEXT,
                    permalink_url TEXT,
                    engagement_likes INTEGER DEFAULT 0,
                    engagement_comments INTEGER DEFAULT 0,
                    engagement_shares INTEGER DEFAULT 0,
                    scheduled_for TEXT,
                    published_at TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS facebook_page_profile (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    followers_count INTEGER DEFAULT 0,
                    fan_count INTEGER DEFAULT 0,
                    connected INTEGER DEFAULT 0,
                    simulation_mode INTEGER DEFAULT 0,
                    about TEXT,
                    picture_url TEXT,
                    last_synced TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS facebook_monetization (
                    page_id TEXT PRIMARY KEY,
                    page_name TEXT NOT NULL,
                    followers_current INTEGER DEFAULT 0,
                    followers_target INTEGER DEFAULT 5000,
                    minutes_viewed_current INTEGER DEFAULT 0,
                    minutes_viewed_target INTEGER DEFAULT 60000,
                    active_posts_current INTEGER DEFAULT 0,
                    active_posts_target INTEGER DEFAULT 5,
                    policy_compliance INTEGER DEFAULT 1,
                    readiness_percentage REAL DEFAULT 0.0,
                    eligible_for_monetization INTEGER DEFAULT 0,
                    daily_growth_target TEXT,
                    actionable_steps TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS facebook_growth_reports (
                    id TEXT PRIMARY KEY,
                    page_id TEXT NOT NULL,
                    page_name TEXT NOT NULL,
                    analysis_summary TEXT NOT NULL,
                    top_performing_angles TEXT,
                    recommended_topics TEXT,
                    monetization_gap_analysis TEXT,
                    daily_schedule_plan TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS messenger_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            await db.commit()

    async def save_trends(self, trends: List[TrendItem]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            for t in trends:
                await db.execute("""
                    INSERT OR REPLACE INTO trends (id, title, source, url, snippet, search_volume, trend_score, category, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (t.id, t.title, t.source.value, t.url, t.snippet, t.search_volume, t.trend_score, t.category, t.created_at))
            await db.commit()

    async def get_recent_trends(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM trends ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def save_claims(self, claims: List[ClaimItem]) -> None:
        now = utc_now()
        async with aiosqlite.connect(self.db_path) as db:
            for c in claims:
                await db.execute("""
                    INSERT OR REPLACE INTO claims (id, claim_text, original_context, status, confidence, evidence, sources, verdict_explanation, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (c.id, c.claim_text, c.original_context, c.status.value, c.confidence, 
                      json.dumps(c.evidence), json.dumps(c.sources), c.verdict_explanation, now))
            await db.commit()

    async def get_recent_claims(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM claims ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["evidence"] = json.loads(d.get("evidence") or "[]")
                d["sources"] = json.loads(d.get("sources") or "[]")
                result.append(d)
            return result

    async def save_script(self, script: GeneratedScript) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            segments_json = json.dumps([s.model_dump() for s in script.segments])
            citations_json = json.dumps(script.citations)
            await db.execute("""
                INSERT OR REPLACE INTO scripts (id, title, format_type, hook, segments, call_to_action, word_count, duration_estimate_sec, citations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (script.id, script.title, script.format_type.value, script.hook, segments_json, script.call_to_action, script.word_count, script.duration_estimate_sec, citations_json, script.created_at))
            await db.commit()

    async def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["segments"] = json.loads(d.get("segments") or "[]")
            d["citations"] = json.loads(d.get("citations") or "[]")
            return d

    async def get_recent_scripts(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM scripts ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["segments"] = json.loads(d.get("segments") or "[]")
                d["citations"] = json.loads(d.get("citations") or "[]")
                res.append(d)
            return res

    async def save_seo_bundle(self, seo: SEOBundle) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO seo_bundles (id, script_id, primary_title, ab_test_titles, description, tags, hashtags, discoverability_score, ctr_rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (seo.id, seo.script_id, seo.primary_title, json.dumps(seo.ab_test_titles), seo.description, json.dumps(seo.tags), json.dumps(seo.hashtags), seo.discoverability_score, seo.ctr_rationale, seo.created_at))
            await db.commit()

    async def get_seo_for_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM seo_bundles WHERE script_id = ?", (script_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["ab_test_titles"] = json.loads(d.get("ab_test_titles") or "[]")
            d["tags"] = json.loads(d.get("tags") or "[]")
            d["hashtags"] = json.loads(d.get("hashtags") or "[]")
            return d

    async def get_recent_seo_bundles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Recent SEO bundles joined with their script titles (SEO Matrix view)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT b.*, s.title AS script_title
                FROM seo_bundles b
                LEFT JOIN scripts s ON s.id = b.script_id
                ORDER BY b.created_at DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["ab_test_titles"] = json.loads(d.get("ab_test_titles") or "[]")
                d["tags"] = json.loads(d.get("tags") or "[]")
                d["hashtags"] = json.loads(d.get("hashtags") or "[]")
                res.append(d)
            return res

    async def save_audience_insight(self, insight: AudienceInsight) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO audience_insights (id, topic_or_video, sentiment, extracted_ideas, viewer_questions, draft_replies, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (insight.id, insight.topic_or_video, insight.sentiment, json.dumps(insight.extracted_ideas), json.dumps(insight.viewer_questions), json.dumps(insight.draft_replies), insight.created_at))
            await db.commit()

    async def get_recent_audience_insights(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM audience_insights ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["extracted_ideas"] = json.loads(d.get("extracted_ideas") or "[]")
                d["viewer_questions"] = json.loads(d.get("viewer_questions") or "[]")
                d["draft_replies"] = json.loads(d.get("draft_replies") or "[]")
                res.append(d)
            return res

    async def save_pipeline_run(self, run: PipelineRun) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO pipeline_runs (id, trigger, status, current_step, trend_count, claims_verified, script_id, seo_id, started_at, completed_at, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run.id, run.trigger, run.status, run.current_step, run.trend_count, run.claims_verified, run.script_id, run.seo_id, run.started_at, run.completed_at, run.error))
            await db.commit()

    async def get_recent_runs(self, limit: int = 15) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            trends_count = (await (await db.execute("SELECT count(*) FROM trends")).fetchone())[0]
            claims_count = (await (await db.execute("SELECT count(*) FROM claims")).fetchone())[0]
            scripts_count = (await (await db.execute("SELECT count(*) FROM scripts")).fetchone())[0]
            seo_count = (await (await db.execute("SELECT count(*) FROM seo_bundles")).fetchone())[0]
            ideas_count = (await (await db.execute("SELECT count(*) FROM audience_insights")).fetchone())[0]
            runs_count = (await (await db.execute("SELECT count(*) FROM pipeline_runs")).fetchone())[0]
            fb_posts_count = (await (await db.execute("SELECT count(*) FROM facebook_posts")).fetchone())[0]
            return {
                "trends": trends_count,
                "claims": claims_count,
                "scripts": scripts_count,
                "seo_bundles": seo_count,
                "audience_insights": ideas_count,
                "total_runs": runs_count,
                "facebook_posts": fb_posts_count
            }

    async def save_omni_provider(
        self,
        provider_id: str,
        provider_type: str,
        name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        models: Optional[List[str]] = None,
        enabled: bool = True
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            models_json = json.dumps(models or [])
            await db.execute("""
                INSERT OR REPLACE INTO omni_providers (id, provider_type, name, api_key, base_url, models, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (provider_id, provider_type, name, api_key or "", base_url or "", models_json, 1 if enabled else 0, utc_now()))
            await db.commit()

    async def get_omni_providers(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM omni_providers ORDER BY created_at ASC")
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["models"] = json.loads(d.get("models") or "[]")
                d["enabled"] = bool(d.get("enabled"))
                # mask api key for security
                raw_key = d.get("api_key") or ""
                d["has_key"] = bool(raw_key)
                d["key_masked"] = (raw_key[:4] + "••••" + raw_key[-4:]) if len(raw_key) > 8 else ("••••" if raw_key else "None")
                res.append(d)
            return res

    async def delete_omni_provider(self, provider_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM omni_providers WHERE id = ?", (provider_id,))
            # Cascade: engine nodes belonging to this provider are removed too
            await db.execute("DELETE FROM omni_engines WHERE provider_id = ?", (provider_id,))
            await db.commit()

    async def get_omni_provider_raw(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Unmasked provider row — internal use only (key preservation, ping tests)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM omni_providers WHERE id = ?", (provider_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["models"] = json.loads(d.get("models") or "[]")
            d["enabled"] = bool(d.get("enabled"))
            return d

    async def save_omni_route(
        self,
        route_name: str,
        primary_provider_id: str,
        primary_model: str,
        fallback_chain: List[Dict[str, str]],
        cooldown_seconds: int = 300,
        max_retries: int = 3
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            chain_json = json.dumps(fallback_chain or [])
            await db.execute("""
                INSERT OR REPLACE INTO omni_routes (route_name, primary_provider_id, primary_model, fallback_chain, cooldown_seconds, max_retries, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (route_name, primary_provider_id, primary_model, chain_json, cooldown_seconds, max_retries, utc_now()))
            await db.commit()

    async def get_omni_routes(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM omni_routes ORDER BY created_at ASC")
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["fallback_chain"] = json.loads(d.get("fallback_chain") or "[]")
                res.append(d)
            return res

    async def delete_omni_route(self, route_name: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM omni_routes WHERE route_name = ?", (route_name,))
            await db.commit()

    # --- Engine nodes (provider + model pairs used by the node graph) ---

    async def save_omni_engine(self, engine_id: str, provider_id: str, model: str, name: str = "") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO omni_engines (id, provider_id, model, name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (engine_id, provider_id, model, name or model, utc_now()))
            await db.commit()

    async def get_omni_engines(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM omni_engines ORDER BY created_at ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def delete_omni_engine(self, engine_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM omni_engines WHERE id = ?", (engine_id,))
            await db.commit()

    # =========================================================================
    # Facebook Operations
    # =========================================================================

    async def save_facebook_post(self, post: FacebookPostItem) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            hashtags_json = json.dumps(post.hashtags or [])
            slides_json = json.dumps([s.model_dump() for s in (post.story_slides or [])])
            await db.execute("""
                INSERT OR REPLACE INTO facebook_posts (
                    id, post_type, title, message, hook, call_to_action, hashtags,
                    image_path, image_prompt, story_slides, video_script, status,
                    fb_post_id, permalink_url, engagement_likes, engagement_comments,
                    engagement_shares, scheduled_for, published_at, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post.id, post.post_type.value, post.title, post.message, post.hook,
                post.call_to_action, hashtags_json, post.image_path, post.image_prompt,
                slides_json, post.video_script, post.status.value, post.fb_post_id,
                post.permalink_url, post.engagement_likes, post.engagement_comments,
                post.engagement_shares, post.scheduled_for, post.published_at,
                post.error_message, post.created_at
            ))
            await db.commit()

    async def get_facebook_posts(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute("SELECT * FROM facebook_posts WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cursor = await db.execute("SELECT * FROM facebook_posts ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["hashtags"] = json.loads(d.get("hashtags") or "[]")
                d["story_slides"] = json.loads(d.get("story_slides") or "[]")
                res.append(d)
            return res

    async def get_facebook_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM facebook_posts WHERE id = ?", (post_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["hashtags"] = json.loads(d.get("hashtags") or "[]")
            d["story_slides"] = json.loads(d.get("story_slides") or "[]")
            return d

    async def update_facebook_post_status(
        self,
        post_id: str,
        status: str,
        fb_post_id: Optional[str] = None,
        permalink_url: Optional[str] = None,
        error_message: Optional[str] = None,
        published_at: Optional[str] = None,
        scheduled_for: Optional[str] = None
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE facebook_posts 
                SET status = ?, 
                    fb_post_id = COALESCE(?, fb_post_id),
                    permalink_url = COALESCE(?, permalink_url),
                    error_message = ?,
                    published_at = COALESCE(?, published_at),
                    scheduled_for = COALESCE(?, scheduled_for)
                WHERE id = ?
            """, (status, fb_post_id, permalink_url, error_message, published_at, scheduled_for, post_id))
            await db.commit()

    async def delete_facebook_post(self, post_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM facebook_posts WHERE id = ?", (post_id,))
            await db.commit()

    async def get_due_scheduled_facebook_posts(self, now_iso: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM facebook_posts 
                WHERE status = 'scheduled' AND scheduled_for IS NOT NULL AND scheduled_for <= ?
                ORDER BY scheduled_for ASC
            """, (now_iso,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["hashtags"] = json.loads(d.get("hashtags") or "[]")
                d["story_slides"] = json.loads(d.get("story_slides") or "[]")
                res.append(d)
            return res

    async def save_facebook_page_profile(self, profile: FacebookPageProfile) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO facebook_page_profile (
                    id, name, category, followers_count, fan_count, connected,
                    simulation_mode, about, picture_url, last_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.id, profile.name, profile.category, profile.followers_count,
                profile.fan_count, 1 if profile.connected else 0,
                1 if profile.simulation_mode else 0, profile.about,
                profile.picture_url, profile.last_synced
            ))
            await db.commit()

    async def get_facebook_page_profile(self) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM facebook_page_profile ORDER BY last_synced DESC LIMIT 1")
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["connected"] = bool(d.get("connected"))
            d["simulation_mode"] = bool(d.get("simulation_mode"))
            return d

    async def save_facebook_monetization(self, mon: FacebookMonetizationStatus) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            steps_json = json.dumps(mon.actionable_steps or [])
            await db.execute("""
                INSERT OR REPLACE INTO facebook_monetization (
                    page_id, page_name, followers_current, followers_target,
                    minutes_viewed_current, minutes_viewed_target, active_posts_current,
                    active_posts_target, policy_compliance, readiness_percentage,
                    eligible_for_monetization, daily_growth_target, actionable_steps, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mon.page_id, mon.page_name, mon.followers_current, mon.followers_target,
                mon.minutes_viewed_current, mon.minutes_viewed_target, mon.active_posts_current,
                mon.active_posts_target, 1 if mon.policy_compliance else 0, mon.readiness_percentage,
                1 if mon.eligible_for_monetization else 0, mon.daily_growth_target,
                steps_json, mon.updated_at
            ))
            await db.commit()

    async def get_facebook_monetization(self, page_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if page_id:
                cursor = await db.execute("SELECT * FROM facebook_monetization WHERE page_id = ?", (page_id,))
            else:
                cursor = await db.execute("SELECT * FROM facebook_monetization ORDER BY updated_at DESC LIMIT 1")
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["policy_compliance"] = bool(d.get("policy_compliance"))
            d["eligible_for_monetization"] = bool(d.get("eligible_for_monetization"))
            d["actionable_steps"] = json.loads(d.get("actionable_steps") or "[]")
            return d

    async def save_facebook_growth_report(self, report: FacebookGrowthReport) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            angles_json = json.dumps(report.top_performing_angles or [])
            topics_json = json.dumps(report.recommended_topics or [])
            schedule_json = json.dumps(report.daily_schedule_plan or [])
            await db.execute("""
                INSERT OR REPLACE INTO facebook_growth_reports (
                    id, page_id, page_name, analysis_summary, top_performing_angles,
                    recommended_topics, monetization_gap_analysis, daily_schedule_plan, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.id, report.page_id, report.page_name, report.analysis_summary,
                angles_json, topics_json, report.monetization_gap_analysis,
                schedule_json, report.created_at
            ))
            await db.commit()

    async def get_recent_facebook_growth_reports(self, limit: int = 5) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM facebook_growth_reports ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["top_performing_angles"] = json.loads(d.get("top_performing_angles") or "[]")
                d["recommended_topics"] = json.loads(d.get("recommended_topics") or "[]")
                d["daily_schedule_plan"] = json.loads(d.get("daily_schedule_plan") or "[]")
                res.append(d)
            return res

    async def clear_all_data(self) -> Dict[str, int]:
        """Delete all content data from every table. Returns row counts deleted per table."""
        tables = [
            "trends", "claims", "scripts", "seo_bundles",
            "audience_insights", "pipeline_runs",
            "facebook_posts", "facebook_page_profiles",
            "facebook_monetization_status", "facebook_growth_reports",
        ]
        deleted: Dict[str, int] = {}
        async with aiosqlite.connect(self.db_path) as db:
            for t in tables:
                try:
                    cur = await db.execute(f"SELECT COUNT(*) FROM {t}")
                    row = await cur.fetchone()
                    count = row[0] if row else 0
                    await db.execute(f"DELETE FROM {t}")
                    deleted[t] = count
                except Exception:
                    deleted[t] = 0
            await db.commit()
        return deleted

    async def save_messenger_message(self, sender_id: str, role: str, content: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messenger_conversations (sender_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (sender_id, role, content, utc_now())
            )
            await db.commit()

    async def get_recent_messenger_messages(self, sender_id: str, limit: int = 6) -> List[Dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content FROM messenger_conversations WHERE sender_id = ? ORDER BY id DESC LIMIT ?",
                (sender_id, limit)
            )
            rows = await cursor.fetchall()
            messages = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
            return messages

    async def get_all_recent_messenger_messages(self, limit: int = 30) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, sender_id, role, content, created_at FROM messenger_conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


