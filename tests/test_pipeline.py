"""
Tests for Ultimate Content Agent pipeline and components.
"""
import pytest
import asyncio
from app.db import Database
from app.models import TrendItem, SourceType, ClaimItem, VerificationStatus, GeneratedScript, ScriptSegment, FormatType, SEOBundle
from app.agents.trend_hunter import TrendHunterAgent
from app.agents.strategist import StrategistAgent

@pytest.mark.asyncio
async def test_database_crud(tmp_path):
    db_file = tmp_path / "test_ultimate.db"
    db = Database(db_file)
    await db.initialize()

    # Save trends
    t = TrendItem(
        id="t1",
        title="AI Breakthrough 2026",
        source=SourceType.GOOGLE_TRENDS,
        trend_score=95.0
    )
    await db.save_trends([t])
    trends = await db.get_recent_trends()
    assert len(trends) == 1
    assert trends[0]["title"] == "AI Breakthrough 2026"

    # Save claims
    c = ClaimItem(
        id="c1",
        claim_text="Quantum chips run at room temp",
        status=VerificationStatus.DEBUNKED,
        confidence=90.0,
        evidence=["Tested in cryo conditions only"],
        sources=["Nature 2026"],
        verdict_explanation="Still requires liquid helium"
    )
    await db.save_claims([c])
    claims = await db.get_recent_claims()
    assert len(claims) == 1
    assert claims[0]["status"] == "debunked"
    assert claims[0]["evidence"] == ["Tested in cryo conditions only"]

    # Save script
    seg = ScriptSegment(segment_id=1, duration_seconds=5, visual_cue="Zoom in", narration="Look at this chip.")
    script = GeneratedScript(
        id="s1",
        title="The Truth About Quantum",
        format_type=FormatType.SHORTS,
        hook="Stop believing quantum hype",
        segments=[seg],
        call_to_action="Follow for more",
        word_count=5,
        duration_estimate_sec=5
    )
    await db.save_script(script)
    fetched_script = await db.get_script("s1")
    assert fetched_script is not None
    assert fetched_script["hook"] == "Stop believing quantum hype"

    # Save SEO
    seo = SEOBundle(
        id="seo1",
        script_id="s1",
        primary_title="The Truth About Quantum Computing",
        ab_test_titles=["Why Quantum is Not Ready", "Quantum Secrets Revealed"],
        description="Full breakdown of quantum limits.",
        tags=["quantum", "tech"],
        hashtags=["#quantum", "#tech"]
    )
    await db.save_seo_bundle(seo)
    fetched_seo = await db.get_seo_for_script("s1")
    assert fetched_seo is not None
    assert fetched_seo["primary_title"] == "The Truth About Quantum Computing"

    # Verify stats
    stats = await db.get_stats()
    assert stats["trends"] == 1
    assert stats["claims"] == 1
    assert stats["scripts"] == 1
    assert stats["seo_bundles"] == 1

def test_strategist_evergreen_topics():
    strat = StrategistAgent()
    topic = strat.get_evergreen_topic()
    assert isinstance(topic, str)
    assert len(topic) > 10

@pytest.mark.asyncio
async def test_omnirouter_resilience():
    from app.llm.omnirouter import OmniRouter
    router = OmniRouter()
    assert router.is_available() is True
    
    # Test JSON synthesis and fallback guarantee
    # generate_json always returns a dict; key names vary by model/prompt
    res = await router.generate_json("You are an expert fact-checking system. Extract claims for AI.")
    assert isinstance(res, dict), f"Expected dict, got {type(res)}"
    assert len(res) > 0, "Response dict should not be empty"
