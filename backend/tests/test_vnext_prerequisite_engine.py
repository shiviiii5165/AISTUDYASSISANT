import pytest
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageReadiness, StageStatus, PrerequisiteMasteryState
)
from app.services.lesson_planner.vnext.shared_context import LearnerStateRepository
from app.services.lesson_planner.vnext.compiler import LessonCompiler


@pytest.mark.anyio
async def test_prerequisite_mastered_allows_progression():
    """When learner state is MASTERED, stage readiness is READY without unnecessary remediation."""
    student_id = "student_prereq_mastered"
    # Seed learner state as MASTERED for quadratic formula
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id="math.algebra.quadratic",
        correctness=True,
        confidence=0.95
    )
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id="math.algebra.quadratic",
        correctness=True,
        confidence=0.95
    )

    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Quadratic Equations",
        grade="Class 10",
        student_id=student_id
    )
    # First stage should be READY and AVAILABLE
    assert roadmap.stages[0].readiness == StageReadiness.READY
    assert roadmap.stages[0].status == StageStatus.AVAILABLE


@pytest.mark.anyio
async def test_prerequisite_weak_recommends_review():
    """When learner state is WEAK, stage readiness is REVIEW_RECOMMENDED and status NEEDS_REVIEW."""
    student_id = "student_prereq_weak"
    # Seed learner state as WEAK for quadratic equations
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id="math.algebra.quadratic",
        correctness=False,
        confidence=0.85
    )
    LearnerStateRepository.update_state(
        student_id=student_id,
        canonical_concept_id="math.algebra.quadratic",
        correctness=False,
        confidence=0.90
    )

    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Quadratic Equations",
        grade="Class 10",
        student_id=student_id
    )
    assert roadmap.stages[0].readiness == StageReadiness.REVIEW_RECOMMENDED
    assert roadmap.stages[0].status == StageStatus.NEEDS_REVIEW


@pytest.mark.anyio
async def test_no_evidence_defaults_to_unknown_not_weak():
    """Learner with NO prior observations must default to UNKNOWN, not WEAK."""
    new_student = "student_completely_new"
    state = LearnerStateRepository.get_state(new_student, "math.core.quadratic_equations_roots")
    assert state.mastery_state == PrerequisiteMasteryState.UNKNOWN
    assert state.evidence_count == 0
