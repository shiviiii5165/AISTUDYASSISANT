import pytest
from app.services.lesson_planner.schemas import CanonicalDomain, PrerequisiteMasteryState
from app.services.lesson_planner.vnext.canonical_concepts import CanonicalConceptResolver
from app.services.lesson_planner.vnext.shared_context import LearnerStateRepository


def test_cross_roadmap_state_reuse():
    """
    Student achieves mastery on 'DP memoization' in Roadmap A.
    When Roadmap B teaches 'Memoization table' or 'top-down dp',
    it must resolve to the same canonical ID and immediately recognize existing mastery!
    """
    concept_a = CanonicalConceptResolver.resolve("DP memoization", CanonicalDomain.COMPUTER_SCIENCE)
    concept_b = CanonicalConceptResolver.resolve("Memoization table", CanonicalDomain.COMPUTER_SCIENCE)

    assert concept_a is not None
    assert concept_b is not None
    assert concept_a.canonical_id == concept_b.canonical_id == "cs.algo.dp.memoization"

    student_id = "student_reuse_42"
    # Earn mastery in roadmap A
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id=concept_a.canonical_id,
        correctness=True,
        confidence=0.90
    )
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id=concept_a.canonical_id,
        correctness=True,
        confidence=0.95
    )

    # In roadmap B, inspect state using concept B
    state_in_roadmap_b = LearnerStateRepository.get_state(student_id, concept_b.canonical_id)
    assert state_in_roadmap_b.mastery_state == PrerequisiteMasteryState.MASTERED
    assert state_in_roadmap_b.success_count == 2


def test_prevention_of_local_stage_id_collisions():
    """
    Passing ephemeral local IDs like 'stage_0_concept' must be sanitized
    and never collide across different stages.
    """
    c1 = CanonicalConceptResolver.resolve_or_create("stage_0_concept", CanonicalDomain.COMPUTER_SCIENCE)
    c2 = CanonicalConceptResolver.resolve_or_create("stage_1_concept", CanonicalDomain.COMPUTER_SCIENCE)

    assert c1.canonical_id != "stage_0_concept"
    assert not c1.canonical_id.startswith("stage_0")


def test_curriculum_version_scoping_separation():
    """
    Same canonical concept across different curriculum scopes or versions
    (e.g., standard v1.0 vs advanced v2.0) must maintain separate persistent state.
    """
    student_id = "student_scope_99"
    cid = "math.algebra.quadratic"

    # Mastery in standard 1.0
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id=cid,
        correctness=True,
        curriculum_scope="standard",
        curriculum_version="1.0"
    )
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id=cid,
        correctness=True,
        curriculum_scope="standard",
        curriculum_version="1.0"
    )

    # In higher ed advanced 2.0, state has no prior observations and defaults to UNKNOWN
    state_adv = LearnerStateRepository.get_state(
        student_id=student_id,
        canonical_concept_id=cid,
        curriculum_scope="advanced",
        curriculum_version="2.0"
    )
    assert state_adv.mastery_state == PrerequisiteMasteryState.UNKNOWN
    assert state_adv.evidence_count == 0


def test_single_error_does_not_flip_mastered_state():
    """
    A student with proven mastery who answers one question incorrectly
    should NOT be instantaneously flipped to WEAK.
    """
    student_id = "student_resilient_1"
    cid = "cs.algo.graph.bfs"

    # Establish mastery with 3 correct answers
    for _ in range(3):
        LearnerStateRepository.update_state(student_id, cid, correctness=True, confidence=0.90)

    state = LearnerStateRepository.get_state(student_id, cid)
    assert state.mastery_state == PrerequisiteMasteryState.MASTERED

    # Single incorrect answer
    updated = LearnerStateRepository.update_state(student_id, cid, correctness=False, confidence=0.70)
    # Success ratio is 3/4 (75%) -> LIKELY_MASTERED, NOT WEAK!
    assert updated.mastery_state in [PrerequisiteMasteryState.MASTERED, PrerequisiteMasteryState.LIKELY_MASTERED]
    assert updated.mastery_state != PrerequisiteMasteryState.WEAK
