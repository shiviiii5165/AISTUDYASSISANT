import pytest
from app.services.lesson_planner.schemas import LearningEvidenceRecord
from app.services.lesson_planner.vnext.shared_context import LearningEvidenceService


def test_same_event_id_retried_is_duplicate():
    """Submitting the exact same event_id must return is_duplicate=True without updating state."""
    rec1 = LearningEvidenceRecord(
        student_id="student_101",
        concept_id="dp_memoization",
        source_type="checkpoint",
        event_id="evt_unique_101",
        correctness=True,
        confidence=0.90
    )
    rec2 = LearningEvidenceRecord(
        student_id="student_101",
        concept_id="dp_memoization",
        source_type="checkpoint",
        event_id="evt_unique_101",
        correctness=True,
        confidence=0.90
    )

    _, is_dup1 = LearningEvidenceService.record_evidence(rec1)
    assert is_dup1 is False

    _, is_dup2 = LearningEvidenceService.record_evidence(rec2)
    assert is_dup2 is True


def test_deterministic_fallback_retry_is_duplicate():
    """When event_id is omitted, deterministic hash must catch retried identical evidence."""
    rec1 = LearningEvidenceRecord(
        student_id="student_102",
        roadmap_id="plan_a",
        concept_id="graph_bfs",
        source_type="quiz",
        source_id="quiz_42",
        question_id="q1",
        attempt=1,
        correctness=False,
        confidence=0.80
    )
    rec2 = LearningEvidenceRecord(
        student_id="student_102",
        roadmap_id="plan_a",
        concept_id="graph_bfs",
        source_type="quiz",
        source_id="quiz_42",
        question_id="q1",
        attempt=1,
        correctness=False,
        confidence=0.80
    )

    _, is_dup1 = LearningEvidenceService.record_evidence(rec1)
    assert is_dup1 is False

    _, is_dup2 = LearningEvidenceService.record_evidence(rec2)
    assert is_dup2 is True


def test_genuinely_different_attempts_recorded():
    """Attempt 1 and Attempt 2 for same student/question are both legitimately recorded."""
    rec_att1 = LearningEvidenceRecord(
        student_id="student_103",
        roadmap_id="plan_b",
        concept_id="sorting",
        source_type="quiz",
        question_id="q2",
        attempt=1,
        correctness=False,
        confidence=0.70
    )
    rec_att2 = LearningEvidenceRecord(
        student_id="student_103",
        roadmap_id="plan_b",
        concept_id="sorting",
        source_type="quiz",
        question_id="q2",
        attempt=2,
        correctness=True,
        confidence=0.95
    )

    _, is_dup1 = LearningEvidenceService.record_evidence(rec_att1)
    assert is_dup1 is False

    _, is_dup2 = LearningEvidenceService.record_evidence(rec_att2)
    assert is_dup2 is False


def test_same_question_across_different_roadmaps():
    """The same question answered in Roadmap A vs Roadmap B must not be falsely flagged as duplicate."""
    rec_road1 = LearningEvidenceRecord(
        student_id="student_104",
        roadmap_id="plan_x",
        concept_id="react_hooks",
        source_type="quiz",
        question_id="q_hooks_1",
        attempt=1,
        correctness=True
    )
    rec_road2 = LearningEvidenceRecord(
        student_id="student_104",
        roadmap_id="plan_y",
        concept_id="react_hooks",
        source_type="quiz",
        question_id="q_hooks_1",
        attempt=1,
        correctness=True
    )

    _, is_dup1 = LearningEvidenceService.record_evidence(rec_road1)
    assert is_dup1 is False

    _, is_dup2 = LearningEvidenceService.record_evidence(rec_road2)
    assert is_dup2 is False


def test_evidence_failure_atomicity_rolls_back():
    """If learner state update fails after evidence insert, idempotency keys must roll back."""
    rec = LearningEvidenceRecord(
        student_id="student_atomic",
        concept_id="sql_joins",
        source_type="checkpoint",
        event_id="evt_atomic_fail",
        correctness=True
    )

    with pytest.raises(RuntimeError) as exc_info:
        LearningEvidenceService.record_evidence(rec, simulate_failure_after_insert=True)
    assert "TRANSACTION_FAILED" in str(exc_info.value)

    # After simulated rollback, submitting the event_id again MUST succeed (not falsely locked as duplicate)
    _, is_dup = LearningEvidenceService.record_evidence(rec, simulate_failure_after_insert=False)
    assert is_dup is False
