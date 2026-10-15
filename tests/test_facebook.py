"""
Unit and integration tests for Facebook Integration & Monetization Growth Engine.
"""
import pytest
from app.db import Database
from app.models import (
    FacebookPostItem, FacebookPostType, FacebookPostStatus,
    FacebookPageProfile, FacebookMonetizationStatus, FacebookGrowthReport,
    FacebookStorySlide
)
from app.tools.facebook import FacebookClient
from app.tools.image_generator import MediaGenerator
from app.agents.facebook_growth_agent import FacebookGrowthAgent
from app.agents.facebook_content_agent import FacebookContentAgent

@pytest.mark.asyncio
async def test_facebook_client_simulation():
    client = FacebookClient(page_id="test_page", access_token="")
    profile = await client.get_page_profile()
    assert profile["simulation_mode"] is True
    assert profile["followers_count"] > 1000

    posts = await client.get_page_posts(limit=5)
    assert len(posts) > 0
    assert "likes" in posts[0]

    insights = await client.get_page_insights()
    assert "minutes_viewed_60d" in insights

    # Test simulated publishing
    pub_res = await client.publish_feed_post("Test post")
    assert pub_res["success"] is True
    assert pub_res["simulated"] is True
    assert "id" in pub_res

@pytest.mark.asyncio
async def test_media_generator_fallback():
    gen = MediaGenerator()
    # Test generation of post visual and story visual
    post_img = await gen.generate_post_image(
        prompt="Quantum artificial intelligence breakthrough chip glowing in emerald light",
        title="Room Temperature Quantum Computing Debunked"
    )
    assert post_img is not None
    assert str(post_img).endswith((".jpg", ".svg", ".png"))

    story_img = await gen.generate_story_image(
        prompt="Cyberpunk aesthetic neural grid vertical wallpaper",
        overlay_text="Swipe up to vote"
    )
    assert story_img is not None

@pytest.mark.asyncio
async def test_facebook_db_operations(tmp_path):
    db_file = tmp_path / "test_fb.db"
    db = Database(db_file)
    await db.initialize()

    # Save page profile
    prof = FacebookPageProfile(
        id="fb_123",
        name="Viral Tech Page",
        category="Tech Creator",
        followers_count=3200,
        fan_count=3100,
        connected=True,
        simulation_mode=False
    )
    await db.save_facebook_page_profile(prof)
    fetched_prof = await db.get_facebook_page_profile()
    assert fetched_prof is not None
    assert fetched_prof["name"] == "Viral Tech Page"
    assert fetched_prof["followers_count"] == 3200

    # Save monetization status
    mon = FacebookMonetizationStatus(
        page_id="fb_123",
        page_name="Viral Tech Page",
        followers_current=3200,
        followers_target=5000,
        minutes_viewed_current=45000,
        minutes_viewed_target=60000,
        active_posts_current=12,
        active_posts_target=5,
        policy_compliance=True,
        readiness_percentage=75.5,
        eligible_for_monetization=False,
        daily_growth_target="Post 1 Reel + 1 Post daily",
        actionable_steps=["Pin top comments", "Post 60s Reels"]
    )
    await db.save_facebook_monetization(mon)
    fetched_mon = await db.get_facebook_monetization("fb_123")
    assert fetched_mon is not None
    assert fetched_mon["readiness_percentage"] == 75.5
    assert len(fetched_mon["actionable_steps"]) == 2

    # Save post item
    post = FacebookPostItem(
        id="post_1",
        post_type=FacebookPostType.FEED,
        title="Why Compound AI Beats Single LLMs",
        message="Full breakdown of AI systems in 2026...",
        hook="Stop relying on single prompts.",
        call_to_action="Comment below!",
        hashtags=["#AI", "#Tech"],
        status=FacebookPostStatus.DRAFT
    )
    await db.save_facebook_post(post)
    posts = await db.get_facebook_posts()
    assert len(posts) == 1
    assert posts[0]["title"] == "Why Compound AI Beats Single LLMs"

    # Update status to scheduled
    await db.update_facebook_post_status("post_1", "scheduled", scheduled_for="2026-10-12T10:00:00Z")
    updated = await db.get_facebook_post("post_1")
    assert updated["status"] == "scheduled"

    # Stats check
    stats = await db.get_stats()
    assert stats["facebook_posts"] == 1

@pytest.mark.asyncio
async def test_facebook_growth_agent_calculation():
    agent = FacebookGrowthAgent()
    profile = FacebookPageProfile(
        id="p1",
        name="Tech Pulse",
        followers_count=3500
    )
    posts = [{"message": "Test post", "likes": 50, "comments": 10, "shares": 5}]
    insights = {"minutes_viewed_60d": 42000, "active_videos_count": 6}

    mon_status, report = await agent.analyze_page(profile, posts, insights)
    assert mon_status.page_id == "p1"
    assert mon_status.followers_current == 3500
    assert mon_status.readiness_percentage > 50.0
    assert report.page_name == "Tech Pulse"
    assert len(report.recommended_topics) > 0

@pytest.mark.asyncio
async def test_facebook_content_agent():
    agent = FacebookContentAgent()
    package = await agent.generate_facebook_package(
        topic="The Future of Autonomous Agents",
        generate_images=False  # speed up test
    )
    assert "feed_post" in package
    assert "story" in package
    assert "reel" in package
    feed_post = package["feed_post"]
    assert len(feed_post.message) > 50
    assert len(feed_post.hashtags) > 0
    assert package["story"].post_type == FacebookPostType.STORY
    assert package["reel"].post_type == FacebookPostType.REEL
