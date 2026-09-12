import pytest
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, CanonicalDomain, TeachingIntent,
    ProductMode, TopicVolatility
)
from app.services.lesson_planner.vnext.resources.registry import (
    ResourceNeedDetector, BUILTIN_SOURCE_REGISTRY
)
from app.services.lesson_planner.vnext.resources.youtube_router import (
    YouTubeSegmentRouter
)
from app.services.lesson_planner.vnext.resources.academic_engine import (
    AcademicEvidenceEngine
)
from app.services.lesson_planner.vnext.resources.coding_engine import (
    CodingResourceEngine
)
from app.services.lesson_planner.vnext.resources.docs_engine import (
    OfficialDocsEngine
)
from app.services.lesson_planner.vnext.resources.trust_engine import (
    ResourceTrustEngine
)


def test_resource_need_detector_visibility_rules():
    stage_visual = RoadmapStage(
        id="s1",
        concept_id="c1",
        title="Visualizing Recursion",
        description="Stack frame tree diagram",
        duration_minutes=15,
        archetype=StageArchetype.MENTAL_MODEL
    )

    # 1. School level should NOT have research papers by default
    school_needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage_visual,
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        intent=TeachingIntent.TEACH,
        learner_level="Grade 8",
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert "youtube" in school_needs
    assert "research" not in school_needs, "Research papers must be hidden from Grade 8"

    # 2. Research Mode MUST have research papers
    research_needs = ResourceNeedDetector.evaluate_stage_needs(
        stage=stage_visual,
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        intent=TeachingIntent.RESEARCH,
        learner_level="Ph.D",
        mode=ProductMode.RESEARCH_ADVANCED
    )
    assert "research" in research_needs

    # 3. Coding should be active for CS implement intent
    assert "coding" in school_needs or "coding" in ResourceNeedDetector.evaluate_stage_needs(
        stage=stage_visual,
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        intent=TeachingIntent.IMPLEMENT,
        learner_level="B.Tech",
        mode=ProductMode.TEACHER_CLASSROOM
    )


def test_coding_resource_engine():
    stage = RoadmapStage(
        id="s2",
        concept_id="c2",
        title="Binary Tree Inorder Traversal",
        description="Traverse tree iteratively and recursively",
        duration_minutes=20,
        archetype=StageArchetype.CODING
    )

    cards = CodingResourceEngine.get_coding_resources(
        topic="Binary Tree Inorder Traversal",
        stage=stage,
        learner_proficiency="developing"
    )

    types = [c.type for c in cards]
    assert "coding_reference" in types  # GeeksforGeeks
    assert "coding_problem" in types    # LeetCode

    # GFG card verification
    gfg = next(c for c in cards if c.type == "coding_reference")
    assert "geeksforgeeks.org" in gfg.url
    assert gfg.quality_score >= 90

    # LeetCode progression verification
    lc_cards = [c for c in cards if c.type == "coding_problem"]
    assert len(lc_cards) >= 3
    assert any("Easy" in c.title for c in lc_cards)
    assert any("Medium" in c.title for c in lc_cards)


def test_official_docs_engine():
    stage = RoadmapStage(
        id="s3",
        concept_id="c3",
        title="React Hooks and Effects",
        description="Lifecycle and state management",
        duration_minutes=15,
        archetype=StageArchetype.DEMONSTRATION
    )

    docs = OfficialDocsEngine.get_official_docs(
        topic="React Hooks",
        stage=stage,
        learner_level="B.Tech"
    )

    assert len(docs) >= 1
    assert "react.dev" in docs[0].url
    assert docs[0].quality_score >= 95
    assert docs[0].confidence >= 0.95


@pytest.mark.anyio
async def test_youtube_segment_router_live():
    stage = RoadmapStage(
        id="s4",
        concept_id="c4",
        title="Functional Dependency",
        description="Understand normalization anomalies and Armstrong axioms",
        duration_minutes=15,
        archetype=StageArchetype.MENTAL_MODEL
    )

    cards = await YouTubeSegmentRouter.route_segments(
        topic="DBMS Normalization",
        stage=stage,
        learner_level="B.Tech",
        volatility=TopicVolatility.LOW
    )

    assert len(cards) <= 3, "Diversity selection must enforce max 3 items"
    if len(cards) > 0:
        c = cards[0]
        assert c.type in ["video_segment", "video"]
        if c.type == "video_segment":
            assert c.timestamp_start is not None
        else:
            assert c.timestamp_source == "whole_video"
        assert c.quality_score >= 70
        assert c.score_breakdown.concept_match > 0
        assert "youtube.com" in c.url


@pytest.mark.anyio
async def test_resource_trust_engine_aggregation():
    stage = RoadmapStage(
        id="s5",
        concept_id="c5",
        title="React State Management",
        description="Using hooks and context API",
        duration_minutes=20,
        archetype=StageArchetype.CODING
    )

    all_cards = await ResourceTrustEngine.aggregate_stage_resources(
        topic="React Hooks",
        stage=stage,
        domain=CanonicalDomain.SOFTWARE_ENGINEERING,
        intent=TeachingIntent.IMPLEMENT,
        learner_level="B.Tech",
        mode=ProductMode.TEACHER_CLASSROOM
    )

    card_types = [c.type for c in all_cards]
    assert "official_docs" in card_types
    assert "coding_reference" in card_types
    assert len(stage.universal_resources) == len(all_cards)
