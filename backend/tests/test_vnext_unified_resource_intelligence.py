"""
Unified Resource Intelligence Test Suite for Lesson Planner VNext
==================================================================
Tests:
1. YouTube Transcript Segmentation (semantic blocks, sponsor removal, confidence)
2. YouTube Confidence Policy (<0.70 whole-video fallback, 0.70-0.84 approx, >=0.85 exact)
3. Course Provider Adapters (NPTEL, MIT OCW, Stanford)
4. Deep Course Mapping (Course -> Module / Week -> Lecture -> Exact Objective)
5. Level-Aware Course Routing (School vs UG vs PG)
6. Resource Deduplication & Minimum Effective Resource Set
7. Policy-Driven Resource Visibility (Class 5 vs B.Tech vs PhD)
8. Provider Health Tracking & Circuit Breaker Graceful Degradation
9. Paper Section Intelligence (Section 3 - Method vs whole paper)
10. Outcome Learning Telemetry & Sample-Gated Ranking Adjustment
"""

import pytest
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, CanonicalDomain, TeachingIntent,
    ProductMode, TopicVolatility, UniversalResourceCard, PaperType
)
from app.services.lesson_planner.vnext.resources.contracts import (
    ResourcePurpose, ResourceFeedbackType, ResourceIntent, CourseResource
)
from app.services.lesson_planner.vnext.resources.youtube_router import (
    YouTubeSegmentRouter
)
from app.services.lesson_planner.vnext.resources.course_engine import (
    CourseIntelligenceEngine, VERIFIED_COURSE_CATALOG
)
from app.services.lesson_planner.vnext.resources.academic_engine import (
    AcademicEvidenceEngine
)
from app.services.lesson_planner.vnext.resources.redundancy_detector import (
    RedundancyDetector
)
from app.services.lesson_planner.vnext.resources.registry import (
    ResourceNeedDetector
)
from app.services.lesson_planner.vnext.resources.source_health import (
    SourceHealthTracker
)
from app.services.lesson_planner.vnext.resources.outcome_engine import (
    ResourceOutcomeEngine
)
from app.services.lesson_planner.vnext.resources.trust_engine import (
    ResourceTrustEngine
)
from app.core.config import settings


@pytest.fixture(autouse=True)
def enable_segments_fixture(monkeypatch):
    monkeypatch.setattr(settings, "LESSON_YOUTUBE_SEGMENTS_ENABLED", True)
    ResourceOutcomeEngine.clear_all_signals()


def _make_stage(title: str, archetype: StageArchetype, desc: str = "") -> RoadmapStage:
    return RoadmapStage(
        id=f"st_{title.lower().replace(' ', '_')[:10]}",
        concept_id="c1",
        title=title,
        description=desc or f"Core study of {title}",
        sequence=1,
        duration_minutes=20,
        archetype=archetype
    )


# ---------------------------------------------------------------------------
# 1. YOUTUBE TRANSCRIPT SEGMENTATION & SPONSOR REMOVAL
# ---------------------------------------------------------------------------

def test_youtube_transcript_segmentation_removes_sponsors_and_detects_segment():
    stage = _make_stage("Memoization State Transition", StageArchetype.WORKED_EXAMPLE, "Optimal substructure and memo table")

    # Mock raw transcript with sponsor and fluff blocks
    transcript_raw = [
        {"start": 0, "duration": 20, "text": "Welcome back to the channel, today's video is sponsored by NordVPN."},
        {"start": 20, "duration": 20, "text": "Hit the bell and subscribe to my Patreon for more coding content."},
        {"start": 40, "duration": 30, "text": "Now let us begin memoization state transition for dynamic programming."},
        {"start": 70, "duration": 30, "text": "Notice how the subproblem states memoize previously computed table entries."},
        {"start": 100, "duration": 30, "text": "The memoization state transition avoids recalculating exponential recursive calls."},
        {"start": 130, "duration": 30, "text": "This guarantees polynomial time complexity for optimal substructure."},
        {"start": 160, "duration": 25, "text": "In the next video we will discuss bottom-up tabulation."}
    ]

    res = YouTubeSegmentRouter._segment_transcript(transcript_raw, "Dynamic Programming", stage)
    assert res is not None
    s_start, s_end, s_conf, s_label = res

    # Verified start is after the sponsor block (>40s)
    assert s_start >= 35, f"Expected segment to start after sponsor fluff, got {s_start}"
    assert s_end > s_start
    assert s_conf >= 0.70
    assert "Memoization" in s_label or "Core Explanation" in s_label


def test_youtube_confidence_policy_and_zero_hallucination():
    stage = _make_stage("Quantum Superposition", StageArchetype.DEMONSTRATION)

    # Candidate with zero transcript and zero chapters
    class MockNoTranscriptVideo:
        title = "Quantum Superposition in 5 Minutes"
        url = "https://youtube.com/watch?v=quantum12345"
        channel = "Science Channel"
        chapters = []
        transcript = None

    card = YouTubeSegmentRouter._score_and_segment(
        item=MockNoTranscriptVideo(),
        stage=stage,
        topic="Quantum Superposition",
        learner_level="B.Tech",
        volatility=TopicVolatility.LOW
    )

    # Must fall back cleanly to whole video with ZERO hallucinated timestamps
    assert card.timestamp_source == "whole_video"
    assert card.timestamp_start is None
    assert card.timestamp_end is None
    assert card.type == "video"
    assert "t=" not in card.url


# ---------------------------------------------------------------------------
# 2. COURSE INTELLIGENCE ENGINE & NPTEL / MIT OCW MAPPING
# ---------------------------------------------------------------------------

def test_course_intelligence_deep_mapping_nptel():
    stage = _make_stage("Massive MIMO Channel Estimation", StageArchetype.WORKED_EXAMPLE)

    cards = CourseIntelligenceEngine.get_course_recommendations(
        topic="Massive MIMO",
        stage=stage,
        learner_level="B.Tech",
        domain=CanonicalDomain.ECE
    )

    assert len(cards) >= 1
    c = cards[0]
    assert "NPTEL" in c.title or "NPTEL" in c.source_authority
    assert "IIT Kanpur" in c.source_authority or "IIT" in c.source_authority
    assert c.course_metadata is not None
    cm = c.course_metadata
    assert "Module 4" in cm["module_title"] or "Massive MIMO" in cm["course_title"]
    assert "Lecture 38" in cm["lecture_title"]
    assert cm["estimated_duration"] == 22
    assert "open" in cm["access_type"]
    assert c.quality_score >= 90


def test_course_intelligence_mit_ocw_mapping():
    stage = _make_stage("Dynamic Programming Memoization", StageArchetype.CONCEPT_INTRO)

    cards = CourseIntelligenceEngine.get_course_recommendations(
        topic="Dynamic Programming",
        stage=stage,
        learner_level="B.Tech",
        domain=CanonicalDomain.COMPUTER_SCIENCE
    )

    assert len(cards) >= 1
    mit_card = next((c for c in cards if "MIT OCW" in c.title or "MIT" in c.source_authority), cards[0])
    assert "MIT" in mit_card.source_authority
    assert "6.006" in mit_card.title or "Algorithms" in mit_card.title
    assert mit_card.quality_score >= 90


def test_course_routing_level_appropriateness():
    # 1. School level MUST route to school foundational courses (SWAYAM / NCERT), never large univ courses
    stage_school = _make_stage("Quadratic Equations Formula", StageArchetype.EXPLANATION)
    school_cards = CourseIntelligenceEngine.get_course_recommendations(
        topic="Quadratic Equations",
        stage=stage_school,
        learner_level="Class 10",
        domain=CanonicalDomain.MATHEMATICS
    )
    assert len(school_cards) >= 1
    assert any("SWAYAM" in c.title or "NCERT" in c.source_authority for c in school_cards)
    assert not any("6.006" in c.title or "MIT OCW" in c.title for c in school_cards)

    # 2. PG level gets graduate level courses
    stage_pg = _make_stage("Raft Distributed Consensus", StageArchetype.EXTENSION)
    pg_cards = CourseIntelligenceEngine.get_course_recommendations(
        topic="Distributed Consensus",
        stage=stage_pg,
        learner_level="M.Tech",
        domain=CanonicalDomain.COMPUTER_SCIENCE
    )
    assert len(pg_cards) >= 1
    assert any("MIT" in c.source_authority or "6.824" in c.title for c in pg_cards)


# ---------------------------------------------------------------------------
# 3. REDUNDANCY DETECTION & MINIMUM EFFECTIVE RESOURCE SET
# ---------------------------------------------------------------------------

def test_redundancy_detector_prunes_duplicates():
    card1 = UniversalResourceCard(
        id="c1",
        title="Dynamic Programming Tutorial: Memoization Explained",
        type="video",
        why_recommended="Primary explanation",
        what_it_covers="DP concepts",
        learner_level="B.Tech",
        source_authority="Tech Channel A",
        quality_score=94,
        url="https://youtube.com/watch?v=test1"
    )
    card2 = UniversalResourceCard(
        id="c2",
        title="Dynamic Programming Tutorial: Memoization Explained Step by Step",
        type="video",
        why_recommended="Duplicate video",
        what_it_covers="DP concepts",
        learner_level="B.Tech",
        source_authority="Tech Channel A",
        quality_score=82,
        url="https://youtube.com/watch?v=test1_dup"
    )

    sim = RedundancyDetector.compute_similarity(card1, card2)
    assert sim >= 0.65, f"Expected high similarity between duplicates, got {sim}"

    selected, pruned = RedundancyDetector.optimize_resource_set([card1, card2], max_total=5)
    assert pruned == 1
    assert len(selected) == 1
    assert selected[0].id == "c1"  # Retained higher quality card


def test_minimum_effective_resource_set_role_capping():
    # Create 8 diverse cards
    cards = [
        UniversalResourceCard(id=f"v{i}", title=f"Video Explanation {i}", type="video", why_recommended="Why", what_it_covers="Cov", learner_level="UG", quality_score=95 - i, url=f"http://v{i}") for i in range(4)
    ] + [
        UniversalResourceCard(id=f"p{i}", title=f"Practice Problem {i}", type="coding_problem", why_recommended="Why", what_it_covers="Cov", learner_level="UG", quality_score=90 - i, url=f"http://p{i}") for i in range(2)
    ] + [
        UniversalResourceCard(id="doc1", title="Official Docs Reference", type="official_docs", why_recommended="Why", what_it_covers="Cov", learner_level="UG", quality_score=98, url="http://docs")
    ]

    selected, pruned = RedundancyDetector.optimize_resource_set(cards, max_total=4)
    assert len(selected) <= 4
    assert pruned >= 3


# ---------------------------------------------------------------------------
# 4. POLICY-DRIVEN RESOURCE VISIBILITY
# ---------------------------------------------------------------------------

def test_class_5_photosynthesis_strict_policy():
    stage = _make_stage("Chloroplast and Light Absorption", StageArchetype.CONCEPT_INTRO)

    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.BIOLOGY,
        intent=TeachingIntent.UNDERSTAND,
        learner_level="Class 5",
        mode=ProductMode.TEACHER_CLASSROOM
    )

    assert "youtube" in needs
    assert "research" not in needs, "Class 5 must never be shown research papers"
    assert "coding" not in needs


# ---------------------------------------------------------------------------
# 5. SOURCE HEALTH & CIRCUIT BREAKER
# ---------------------------------------------------------------------------

def test_source_health_tracker_and_circuit_breaker():
    provider = "external_nptel_probe"

    # 1. Successful call records latency and high success rate
    t0 = SourceHealthTracker.start_call(provider)
    SourceHealthTracker.record_success(provider, t0)
    health = SourceHealthTracker.get_health(provider)
    assert health.success_count == 1
    assert health.success_rate == 1.0
    assert SourceHealthTracker.is_healthy(provider)

    # 2. Repeated failures trigger circuit breaker
    for _ in range(6):
        t = SourceHealthTracker.start_call(provider)
        SourceHealthTracker.record_failure(provider, t, "HTTP 503 Service Unavailable")

    assert not SourceHealthTracker.is_healthy(provider)
    assert health.rate_limit_status == "circuit_broken"


# ---------------------------------------------------------------------------
# 6. PAPER SECTION INTELLIGENCE
# ---------------------------------------------------------------------------

def test_paper_section_intelligence():
    stage_algo = _make_stage("Transformer Self-Attention Algorithm", StageArchetype.WORKED_EXAMPLE)
    sec_algo = AcademicEvidenceEngine._determine_paper_section(stage_algo, PaperType.CONFERENCE_PAPER, is_survey=False)
    assert "Methodology" in sec_algo or "Architecture" in sec_algo

    stage_eval = _make_stage("Benchmark Evaluation and Accuracy", StageArchetype.SUMMARY)
    sec_eval = AcademicEvidenceEngine._determine_paper_section(stage_eval, PaperType.CONFERENCE_PAPER, is_survey=False)
    assert "Experimental Results" in sec_eval or "Empirical" in sec_eval

    stage_survey = _make_stage("Survey of Reinforcement Learning", StageArchetype.CONCEPT_INTRO)
    sec_survey = AcademicEvidenceEngine._determine_paper_section(stage_survey, PaperType.SURVEY, is_survey=True)
    assert "Taxonomy" in sec_survey


# ---------------------------------------------------------------------------
# 7. OUTCOME LEARNING TELEMETRY & ADAPTIVE RANKING
# ---------------------------------------------------------------------------

def test_outcome_learning_sample_gating():
    card = UniversalResourceCard(
        id="res_outcome_test",
        title="Interactive Recursion Visualizer",
        type="simulation",
        why_recommended="Visual demo",
        what_it_covers="Recursion",
        learner_level="B.Tech",
        quality_score=85,
        url="https://example.com/visualizer"
    )

    # 1. Fewer than 10 samples -> score NOT modified (sample gating)
    for _ in range(5):
        ResourceOutcomeEngine.record_outcome_signal(
            resource_id="res_outcome_test",
            concept_id="c_recursion",
            learner_level="B.Tech",
            pre_state="misconception",
            post_state="mastered",
            time_spent_seconds=300,
            teacher_feedback=ResourceFeedbackType.EXCELLENT_EXPLANATION
        )

    cards_unmodified = ResourceOutcomeEngine.apply_outcome_aware_ranking([card])
    assert cards_unmodified[0].quality_score == 85

    # 2. Add 7 more samples (total 12 >= 10) -> score is blended upward
    for _ in range(7):
        ResourceOutcomeEngine.record_outcome_signal(
            resource_id="res_outcome_test",
            concept_id="c_recursion",
            learner_level="B.Tech",
            pre_state="misconception",
            post_state="mastered",
            time_spent_seconds=300,
            teacher_feedback=ResourceFeedbackType.EXCELLENT_EXPLANATION
        )

    cards_boosted = ResourceOutcomeEngine.apply_outcome_aware_ranking([card])
    assert cards_boosted[0].quality_score > 85, "Expected proven outcome effectiveness to boost score"
    assert cards_boosted[0].outcome_effectiveness is not None


# ---------------------------------------------------------------------------
# 8. NEGATIVE ROUTING & DOMAIN LEAKAGE AUDIT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_negative_routing_react_framework_no_leetcode():
    """
    React Server Components must prioritize React official docs and framework material;
    LeetCode must NOT appear unless a genuine algorithmic practice objective exists.
    """
    stage = _make_stage("React 19 Server Components", StageArchetype.CODING, "Server-side rendering and streaming components")

    cards = await ResourceTrustEngine.aggregate_stage_resources(
        topic="React 19 Server Components",
        stage=stage,
        domain=CanonicalDomain.SOFTWARE_ENGINEERING,
        intent=TeachingIntent.IMPLEMENT,
        learner_level="Professional",
        mode=ProductMode.TEACHER_CLASSROOM
    )

    types = [c.type for c in cards]
    titles = [c.title for c in cards]

    # Official docs must be present
    assert any("official_docs" in t or "react.dev" in c.url for c, t in zip(cards, types)), "React official docs must be present"

    # LeetCode must NOT appear
    assert not any("leetcode" in c.url.lower() or "leetcode" in t.lower() for c, t in zip(cards, titles)), "LeetCode must not leak into React framework lessons"


def test_negative_routing_school_lessons_no_research():
    """
    School lessons must NOT receive research-heavy resources, Q1 journals, or conference tiers.
    """
    stage = _make_stage("Cell Structure and Nucleus", StageArchetype.CONCEPT_INTRO, "Basic cellular components for Class 6")

    needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage,
        domain=CanonicalDomain.BIOLOGY,
        intent=TeachingIntent.UNDERSTAND,
        learner_level="Class 6",
        mode=ProductMode.TEACHER_CLASSROOM
    )

    assert "research" not in needs, "Research papers must be strictly hidden from school lessons"
    assert "academic" not in needs


def test_negative_routing_phd_research_no_beginner_spam():
    """
    Research lessons must NOT receive beginner tutorial spam (e.g. 'in 5 minutes', 'for dummies', 'scratch').
    """
    title_beginner = "Quantum Error Correction for Beginners in 5 Minutes"
    title_advanced = "Surface Codes and Fault-Tolerant Quantum Computation"

    assert YouTubeSegmentRouter._fails_hard_filters(title_beginner, 20, learner_level="Ph.D") is True, "Beginner tutorial spam must be rejected for PhD level"
    assert YouTubeSegmentRouter._fails_hard_filters(title_advanced, 20, learner_level="Ph.D") is False, "Rigorous research tutorial must pass hard filters"

