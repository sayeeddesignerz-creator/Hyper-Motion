"""
Pydantic data models for the Ultimate Content Agent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class SourceType(str, Enum):
    RSS = "rss"
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    MANUAL = "manual"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    DEBUNKED = "debunked"
    UNVERIFIED = "unverified"
    PARTIALLY_TRUE = "partially_true"

class FormatType(str, Enum):
    SHORTS = "shorts"
    LONG_FORM = "long_form"
    TWITTER_THREAD = "twitter_thread"
    NEWSLETTER = "newsletter"

class TrendItem(BaseModel):
    id: str
    title: str
    source: SourceType
    url: Optional[str] = None
    snippet: Optional[str] = None
    search_volume: Optional[str] = None
    trend_score: float = 0.0
    category: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)

class ClaimItem(BaseModel):
    id: str
    claim_text: str
    original_context: Optional[str] = None
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    verdict_explanation: str = ""

class ContentAngle(BaseModel):
    pillar: str
    angle: str
    target_emotion: str = "curiosity"
    hook_premise: str
    format_type: FormatType = FormatType.SHORTS

class ScriptSegment(BaseModel):
    segment_id: int
    duration_seconds: int = 5
    visual_cue: str = ""
    narration: str
    on_screen_text: Optional[str] = None
    sound_effect: Optional[str] = None

class GeneratedScript(BaseModel):
    id: str
    title: str
    format_type: FormatType
    hook: str
    segments: List[ScriptSegment] = Field(default_factory=list)
    call_to_action: str
    word_count: int = 0
    duration_estimate_sec: int = 0
    citations: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

class SEOBundle(BaseModel):
    id: str
    script_id: str
    primary_title: str
    ab_test_titles: List[str] = Field(default_factory=list)
    description: str
    tags: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    discoverability_score: int = 85
    ctr_rationale: str = ""
    created_at: str = Field(default_factory=utc_now)

class AudienceInsight(BaseModel):
    id: str
    topic_or_video: str
    sentiment: str = "neutral"
    extracted_ideas: List[str] = Field(default_factory=list)
    viewer_questions: List[str] = Field(default_factory=list)
    draft_replies: List[Dict[str, str]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

class PipelineRun(BaseModel):
    id: str
    trigger: str = "manual"  # manual or scheduler
    status: str = "pending"  # pending, running, completed, failed
    current_step: str = ""
    trend_count: int = 0
    claims_verified: int = 0
    script_id: Optional[str] = None
    seo_id: Optional[str] = None
    started_at: str = Field(default_factory=utc_now)
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Facebook Integration & Monetization Growth Models
# ============================================================================

class FacebookPostType(str, Enum):
    FEED = "feed"
    STORY = "story"
    REEL = "reel"

class FacebookPostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

class FacebookPageProfile(BaseModel):
    id: str
    name: str
    category: str = "Media / News / Tech"
    followers_count: int = 0
    fan_count: int = 0
    connected: bool = False
    simulation_mode: bool = False
    about: Optional[str] = None
    picture_url: Optional[str] = None
    last_synced: str = Field(default_factory=utc_now)

class FacebookMonetizationStatus(BaseModel):
    page_id: str
    page_name: str
    followers_current: int = 0
    followers_target: int = 5000  # Meta In-stream / Stars benchmark
    minutes_viewed_current: int = 0
    minutes_viewed_target: int = 60000  # 60k eligible minutes in last 60 days
    active_posts_current: int = 0
    active_posts_target: int = 5
    policy_compliance: bool = True
    readiness_percentage: float = 0.0
    eligible_for_monetization: bool = False
    daily_growth_target: str = ""
    actionable_steps: List[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now)

class FacebookStorySlide(BaseModel):
    slide_id: int
    title: str
    overlay_text: str
    interactive_sticker: Optional[str] = None
    visual_description: str = ""
    image_path: Optional[str] = None

class FacebookPostItem(BaseModel):
    id: str
    post_type: FacebookPostType = FacebookPostType.FEED
    title: str
    message: str
    hook: str = ""
    call_to_action: str = ""
    hashtags: List[str] = Field(default_factory=list)
    seo_score: int = 95
    seo_keywords: List[str] = Field(default_factory=list)
    image_path: Optional[str] = None
    image_prompt: Optional[str] = None
    story_slides: List[FacebookStorySlide] = Field(default_factory=list)
    video_script: Optional[str] = None
    status: FacebookPostStatus = FacebookPostStatus.DRAFT
    fb_post_id: Optional[str] = None
    permalink_url: Optional[str] = None
    engagement_likes: int = 0
    engagement_comments: int = 0
    engagement_shares: int = 0
    scheduled_for: Optional[str] = None
    published_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)

class FacebookGrowthReport(BaseModel):
    id: str
    page_id: str
    page_name: str
    analysis_summary: str
    top_performing_angles: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    monetization_gap_analysis: str = ""
    daily_schedule_plan: List[Dict[str, str]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

