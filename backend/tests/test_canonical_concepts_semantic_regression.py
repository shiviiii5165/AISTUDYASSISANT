import re
import pytest
from app.services.lesson_planner.schemas import (
    ProductMode, CanonicalDomain, TeachingIntent, StageStatus, StageArchetype, RoadmapStage, LearningObjective, BloomLevel
)
from app.services.lesson_planner.vnext.compiler import LessonCompiler
from app.services.lesson_planner.vnext.canonical_concepts import CanonicalConceptResolver, CandidateOrigin
from app.services.lesson_planner.vnext.shared_context import LessonContextProvider
from app.services.lesson_resources.intent_profile import IntentProfileBuilder
from app.services.lesson_planner.vnext.resources.trust_engine import ResourceTrustEngine
from app.services.lesson_planner.vnext.resources.coding_engine import CodingResourceEngine


ARCHETYPE_TOKENS = {
    "hook", "mental_model", "demonstration", "guided_practice", "diagnostic_check",
    "concept_intro", "worked_example", "overview", "explanation", "independent_practice",
    "case_study", "discussion", "research_review", "real_world_application"
}


@pytest.mark.anyio
async def test_assertion_a_no_archetype_canonical_concepts():
    """
    Assertion A: Pedagogical archetypes never become canonical domain concepts.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    for stage in roadmap.stages:
        # Check concept_id
        for arch in ARCHETYPE_TOKENS:
            assert not stage.concept_id.endswith(f"_{arch}"), (
                f"Stage '{stage.title}' concept_id '{stage.concept_id}' contains archetype '{arch}'"
            )
        # Check canonical_concept_ids
        for cid in stage.canonical_concept_ids:
            for arch in ARCHETYPE_TOKENS:
                assert not cid.endswith(f"_{arch}"), (
                    f"Stage '{stage.title}' canonical_concept_id '{cid}' contains archetype '{arch}'"
                )


@pytest.mark.anyio
async def test_assertion_b_dp_registered_ontology():
    """
    Assertion B: Dynamic Programming uses only registered cs.algo.dp.* IDs.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    expected_dp_references = [
        ["cs.algo.dp.overlapping_subproblems", "cs.algo.dp.memoization"],
        ["cs.algo.dp.optimal_substructure", "cs.algo.dp.state_definition"],
        ["cs.algo.dp.tabulation", "cs.algo.dp.bottom_up", "cs.algo.dp.recurrence"],
        ["cs.algo.dp.two_dimensional", "cs.algo.dp.grid", "cs.algo.dp.knapsack"],
        ["cs.algo.dp.state_design", "cs.algo.dp.transition_errors", "cs.algo.dp.complexity", "cs.algo.dp.debugging"]
    ]

    assert len(roadmap.stages) == 5
    for i, stage in enumerate(roadmap.stages):
        assert stage.concept_id.startswith("cs.algo.dp."), (
            f"Stage {i} primary concept '{stage.concept_id}' is not in cs.algo.dp.* namespace"
        )
        for cid in stage.canonical_concept_ids:
            assert cid.startswith("cs.algo.dp."), (
                f"Stage {i} concept '{cid}' is not in cs.algo.dp.* namespace"
            )
        # Check matching against expected reference concepts
        expected_subset = expected_dp_references[i]
        for exp_cid in expected_subset:
            assert exp_cid in stage.canonical_concept_ids, (
                f"Stage {i} '{stage.title}' missing expected concept '{exp_cid}' (has {stage.canonical_concept_ids})"
            )


@pytest.mark.anyio
async def test_assertion_c_and_d_zero_unresolved_zero_generic():
    """
    Assertions C & D:
    C. UNRESOLVED_CANONICAL_CONCEPT count for known DP topic = 0.
    D. Generic concept_N IDs = 0.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    for stage in roadmap.stages:
        assert stage.concept_id != "UNRESOLVED_CANONICAL_CONCEPT", (
            f"Stage '{stage.title}' has UNRESOLVED_CANONICAL_CONCEPT as primary ID"
        )
        assert "UNRESOLVED_CANONICAL_CONCEPT" not in stage.canonical_concept_ids, (
            f"Stage '{stage.title}' contains UNRESOLVED_CANONICAL_CONCEPT in canonical_concept_ids"
        )
        assert not re.match(r"^concept_\d+$", stage.concept_id), (
            f"Stage '{stage.title}' has generic concept_N as primary ID: {stage.concept_id}"
        )
        for cid in stage.canonical_concept_ids:
            assert not re.match(r"^concept_\d+$", cid), (
                f"Stage '{stage.title}' contains generic concept_N: {cid}"
            )


def test_assertion_e_no_id_truncation_and_collision_safety():
    """
    Assertion E: Canonical IDs are never truncated. Collision tests pass.
    """
    long_name_a = "quantum computing adiabatic state transition protocol in distributed algorithms"
    long_name_b = "quantum computing adiabatic state transition verification in distributed algorithms"

    c_a = CanonicalConceptResolver.resolve_or_create(
        concept_name=long_name_a,
        domain=CanonicalDomain.COMPUTER_SCIENCE
    )
    c_b = CanonicalConceptResolver.resolve_or_create(
        concept_name=long_name_b,
        domain=CanonicalDomain.COMPUTER_SCIENCE
    )

    # Must not be truncated to 32 chars
    assert len(c_a.canonical_id) > 40
    assert len(c_b.canonical_id) > 40
    # Must NOT collide
    assert c_a.canonical_id != c_b.canonical_id
    assert not c_a.canonical_id.endswith("demonstratio")
    assert not c_b.canonical_id.endswith("demonstratio")

    # Origin rejection test
    with pytest.raises(ValueError):
        CanonicalConceptResolver.resolve_or_create(
            concept_name="Dynamic Programming Hook",
            domain=CanonicalDomain.COMPUTER_SCIENCE,
            candidate_origin=CandidateOrigin.PEDAGOGICAL_ARCHETYPE
        )


@pytest.mark.anyio
async def test_assertion_f_and_g_archetype_and_pedagogy_preserved():
    """
    Assertions F & G:
    F. stage_archetype remains unchanged.
    G. pedagogy / instructional role remains unchanged.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    expected_archetypes = [
        StageArchetype.HOOK,
        StageArchetype.MENTAL_MODEL,
        StageArchetype.DEMONSTRATION,
        StageArchetype.GUIDED_PRACTICE,
        StageArchetype.DIAGNOSTIC_CHECK
    ]

    for i, stage in enumerate(roadmap.stages):
        assert stage.archetype == expected_archetypes[i], (
            f"Stage {i} archetype '{stage.archetype}' != expected '{expected_archetypes[i]}'"
        )
        assert stage.teaching_goal != "", f"Stage {i} teaching_goal is empty"
        assert stage.why_this_stage != "", f"Stage {i} why_this_stage is empty"
        assert len(stage.teacher_actions) > 0, f"Stage {i} missing teacher_actions"
        assert len(stage.student_actions) > 0, f"Stage {i} missing student_actions"


@pytest.mark.anyio
@pytest.mark.parametrize("duration", [30, 45, 60, 90])
async def test_assertion_h_duration_variants(duration: int):
    """
    Assertion H: Changing lesson duration/stage count does NOT break semantic resolution.
    Tests: 30-minute, 45-minute, 60-minute, 90-minute DP lessons.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=duration,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    assert len(roadmap.stages) > 0
    total_time = sum(s.duration_minutes for s in roadmap.stages) + roadmap.adaptive_reserve_minutes
    assert total_time == duration, f"Total time {total_time} != requested {duration}"

    for s in roadmap.stages:
        assert s.concept_id.startswith("cs.algo.dp.")
        assert "UNRESOLVED_CANONICAL_CONCEPT" not in s.canonical_concept_ids
        for arch in ARCHETYPE_TOKENS:
            assert not s.concept_id.endswith(f"_{arch}")


def test_assertion_i_stage_reordering_content_driven():
    """
    Assertion I: Teacher-reordered stages still resolve concepts from content rather than stage index.
    """
    # Create Stage 3 (2D DP / Knapsack) placed at index 0
    s_knapsack = RoadmapStage(
        id="stage_custom_1",
        concept_id="temp_id",
        title="Guided Practice: 2D DP, Grid Traversal & Knapsack",
        description="Guided debugging and variations",
        sequence=0,
        duration_minutes=15,
        archetype=StageArchetype.GUIDED_PRACTICE
    )

    resolved_knapsack = CanonicalConceptResolver.resolve_stage_semantics(
        topic="Dynamic Programming",
        stage_title=s_knapsack.title,
        stage_focus="Multi-dimensional DP, grid traversal, and 0/1 knapsack state transitions",
        objectives=[LearningObjective(id="o1", description="Apply 2D DP to grid and knapsack", bloom_level=BloomLevel.APPLY)]
    )

    # Must resolve to 2D/grid/knapsack, NOT memoization/hook
    assert "cs.algo.dp.two_dimensional" in resolved_knapsack
    assert "cs.algo.dp.grid" in resolved_knapsack
    assert "cs.algo.dp.knapsack" in resolved_knapsack
    assert "cs.algo.dp.memoization" not in resolved_knapsack
    assert "cs.algo.dp.overlapping_subproblems" not in resolved_knapsack


@pytest.mark.anyio
async def test_assertion_j_resource_intelligence_receives_true_concepts():
    """
    Assertion J: Resource Intelligence receives true stage concepts and differentiated intent profiles.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    profiles = []
    for stage in roadmap.stages:
        prof = IntentProfileBuilder.build(
            roadmap_id=roadmap.id,
            stage_id=stage.id,
            topic=roadmap.topic,
            stage_title=stage.title,
            stage_description=stage.description,
            archetype=stage.archetype.value,
            canonical_concept_ids=stage.canonical_concept_ids,
            concept_id=stage.concept_id
        )
        profiles.append(prof)
        for arch in ARCHETYPE_TOKENS:
            assert not any(cid.endswith(f"_{arch}") for cid in prof.canonical_concept_ids)

    # Profiles must have differentiated canonical concepts across stages
    assert "cs.algo.dp.overlapping_subproblems" in profiles[0].canonical_concept_ids
    assert "cs.algo.dp.optimal_substructure" in profiles[1].canonical_concept_ids
    assert "cs.algo.dp.tabulation" in profiles[2].canonical_concept_ids
    assert "cs.algo.dp.two_dimensional" in profiles[3].canonical_concept_ids
    assert "cs.algo.dp.state_design" in profiles[4].canonical_concept_ids


@pytest.mark.anyio
async def test_assertion_k_cross_feature_context_preserves_canonical_ids():
    """
    Assertion K: Cross-feature SharedLessonContext preserves identical canonical IDs.
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    shared_ctx = LessonContextProvider.get_shared_context(roadmap)
    assert len(shared_ctx.canonical_concepts) > 0

    shared_cids = [c["canonical_id"] for c in shared_ctx.canonical_concepts]
    assert "cs.algo.dp.overlapping_subproblems" in shared_cids
    assert "cs.algo.dp.memoization" in shared_cids
    assert "cs.algo.dp.optimal_substructure" in shared_cids
    assert "cs.algo.dp.tabulation" in shared_cids

    for cid in shared_cids:
        for arch in ARCHETYPE_TOKENS:
            assert not cid.endswith(f"_{arch}")


def test_assertion_l_bst_substring_regression():
    """
    Assertion L: BST substring regression remains PASS.
    """
    # Negative cases: must NOT match BST
    negatives = [
        "optimal substructure",
        "abstract data type",
        "obstacle grid",
        "substitution",
        "substantive analysis"
    ]
    for text in negatives:
        assert not CodingResourceEngine._matches_bst(text), f"'{text}' falsely matched BST!"

    # Positive cases: MUST match BST
    positives = ["BST", "bst", "Search in BST", "BST Insertion"]
    for text in positives:
        assert CodingResourceEngine._matches_bst(text), f"'{text}' failed to match BST!"


@pytest.mark.anyio
async def test_assertion_m_and_section_14_resource_acceptance():
    """
    Assertion M & Section 14 Resource Acceptance:
    For a fresh standard DP lesson, verify resources follow stage semantics:
    memoization -> memoization resources
    optimal substructure -> state/substructure resources
    tabulation -> bottom-up/tabulation resources
    2D / knapsack -> grid/knapsack resources
    diagnostic -> state/debugging/complexity resources
    """
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Dynamic Programming",
        grade="B.Tech",
        subject="Algorithms",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )

    stage_cards = []
    for stage in roadmap.stages:
        cards = await ResourceTrustEngine.aggregate_stage_resources(
            topic=roadmap.topic,
            stage=stage,
            domain=roadmap.domain,
            intent=roadmap.intent,
            learner_level=roadmap.level,
            mode=roadmap.mode,
            volatility=roadmap.volatility
        )
        stage_cards.append(cards)
        assert len(cards) > 0, f"Stage '{stage.title}' received 0 resources"

    # Stage 0 (Memoization / Overlapping Subproblems)
    s0_text = " ".join([f"{c.title} {c.what_it_covers}" for c in stage_cards[0]]).lower()
    assert any(k in s0_text for k in ["memoization", "dynamic programming", "subproblem", "recursion"])

    # Stage 1 (Optimal Substructure)
    s1_text = " ".join([f"{c.title} {c.what_it_covers}" for c in stage_cards[1]]).lower()
    assert any(k in s1_text for k in ["optimal substructure", "substructure", "dynamic programming"])
    assert not any("binary search tree" in c.title.lower() for c in stage_cards[1])

    # Stage 2 (Tabulation / Bottom-Up)
    s2_text = " ".join([f"{c.title} {c.what_it_covers}" for c in stage_cards[2]]).lower()
    assert any(k in s2_text for k in ["tabulation", "bottom-up", "bottom up", "recurrence", "dynamic programming"])

    # Stage 3 (2D / Knapsack)
    s3_text = " ".join([f"{c.title} {c.what_it_covers}" for c in stage_cards[3]]).lower()
    assert any(k in s3_text for k in ["knapsack", "grid", "2d", "multidimensional", "dynamic programming"])

    # Stage 4 (Diagnostic / Complexity)
    s4_text = " ".join([f"{c.title} {c.what_it_covers}" for c in stage_cards[4]]).lower()
    assert any(k in s4_text for k in ["complexity", "debugging", "pitfall", "space", "dynamic programming"])
