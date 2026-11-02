"""
LearnByGenie — Feature 8 Test Suite
====================================
Tests for Step-Grader & Reasoning Diagnostics Engine:
1. Linear equation first-wrong-step detection (§51)
2. Downstream correctness separation (§52)
3. Calculation error vs conceptual error (§53)
4. Physics unit consistency error (§54)
5. Formula error detection (§55)
6. Ambiguous reasoning uncertainty preservation (§56)
7. Resubmission solution versioning & parent tracking (§57)
8. Bounded Socratic Tutor review context (§58)
9. Database idempotency & duplicate submission safety (§34)
10. Cross-user isolation & authorization enforcement (§37)
11. Dynamic new subject adaptation via generic rubric (§41)
12. StepGraderAuditor invariant checks (§49)
"""
import pytest
import uuid
from typing import Dict, Any

from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    OverallOutcome, ErrorType, StepType
)
from app.services.step_grader.service import StepGraderService
from app.services.step_grader.repository import StepGraderRepository
from app.services.step_grader.audit import StepGraderAuditor
from app.services.step_grader.adapters.generic_rubric_adapter import GenericSequenceAdapter
from app.services.mastery.schemas import AssistanceLevel
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.repository import MistakeDNARepository
from app.services.mastery.repository import MasteryRepository

from app.db.supabase_client import supabase

STUDENT_A_ID = "f1c205c6-03b3-479e-b7b8-ef435dd9f595"
STUDENT_B_ID = "84a81abc-66b6-4d79-9ba8-aeadb8d8fef0"


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Cleans in-memory caches and test data before each test."""
    StepGraderRepository.clear_all()
    MistakeDNARepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    if supabase is not None:
        try:
            supabase.table("mistake_events").delete().eq("user_id", STUDENT_A_ID).execute()
            supabase.table("mistake_events").delete().eq("user_id", STUDENT_B_ID).execute()
        except Exception:
            pass
    yield
    StepGraderRepository.clear_all()


# ─── 1. REAL TEST — LINEAR EQUATION (§51, §52) ────────────────────────────────

def test_linear_equation_first_wrong_step_and_downstream_cascade():
    """
    Question: 2x + 4 = 10
    Student:
      1. 2x + 4 = 10
      2. 2x = 10 + 4
      3. x = 7
    Expected:
      Step 1: VALID_STEP
      Step 2: ROOT_ERROR (SIGN_OR_NOTATION or PROCEDURAL)
      Step 3: DOWNSTREAM_ERROR (correctly follows corrupted step 2)
      Exactly ONE Mistake DNA event is logged.
    """
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 + 4
3. x = 7"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    assert res.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res.first_wrong_step == 2
    assert len(res.validated_steps) == 3

    # Step 1: Valid
    s1 = res.validated_steps[0]
    assert s1.validation_status == StepValidationStatus.VALID_STEP
    assert not s1.is_root_error

    # Step 2: Root error
    s2 = res.validated_steps[1]
    assert s2.validation_status == StepValidationStatus.ROOT_ERROR
    assert s2.is_root_error is True
    assert s2.error_type in (ErrorType.SIGN_OR_NOTATION, ErrorType.PROCEDURAL)
    assert "sign" in s2.feedback.lower() or "moving" in s2.feedback.lower()

    # Step 3: Downstream error (7 solves 2x = 14)
    s3 = res.validated_steps[2]
    assert s3.validation_status == StepValidationStatus.DOWNSTREAM_ERROR
    assert s3.is_root_error is False
    assert 3 in res.downstream_steps

    # Check Mistake DNA closed loop: Exactly 1 Mistake event logged
    mistakes = MistakeDNARepository.get_mistake_events(STUDENT_A_ID)
    step_mistakes = [m for m in mistakes if m.source_type == "STEP_GRADER"]
    assert len(step_mistakes) == 1
    assert step_mistakes[0].primary_error_type in (ErrorType.SIGN_OR_NOTATION, ErrorType.PROCEDURAL)


# ─── 2. REAL TEST — CALCULATION ERROR (§53) ───────────────────────────────────

def test_calculation_error_vs_conceptual():
    """
    Question: 2x + 4 = 10
    Student:
      1. 2x + 4 = 10
      2. 2x = 10 - 4
      3. 2x = 5
      4. x = 2.5
    Expected:
      Step 1: VALID_STEP
      Step 2: VALID_STEP
      Step 3: ROOT_ERROR (CALCULATION, not CONCEPTUAL!)
      Step 4: DOWNSTREAM_ERROR
    """
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 - 4
3. 2x = 5
4. x = 2.5"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    assert res.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res.first_wrong_step == 3
    assert res.error_type == ErrorType.CALCULATION

    s3 = res.validated_steps[2]
    assert s3.validation_status == StepValidationStatus.ROOT_ERROR
    assert s3.error_type == ErrorType.CALCULATION
    assert s3.error_subtype == "arithmetic_slip"

    s4 = res.validated_steps[3]
    assert s4.validation_status == StepValidationStatus.DOWNSTREAM_ERROR


# ─── 3. REAL TEST — PHYSICS UNIT ERROR (§54) ──────────────────────────────────

def test_physics_unit_error():
    """
    Question: Calculate force for mass 2 kg with acceleration 5 m/s^2
    Student:
      1. F = m * a
      2. F = 2 * 5
      3. F = 10 J
    Expected:
      Step 1: VALID_STEP
      Step 2: VALID_STEP
      Step 3: ROOT_ERROR (UNIT_OR_DIMENSION, J instead of N)
    """
    raw_sol = """1. F = m * a
2. F = 2 * 5
3. F = 10 J"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Physics",
        question_text="Calculate force for mass 2 kg with acceleration 5 m/s^2",
        raw_input=raw_sol,
        skill_id="PHY_NEWTON_LAWS"
    )

    assert res.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res.first_wrong_step == 3
    assert res.error_type == ErrorType.UNIT_OR_DIMENSION

    s3 = res.validated_steps[2]
    assert s3.validation_status == StepValidationStatus.ROOT_ERROR
    assert s3.error_type == ErrorType.UNIT_OR_DIMENSION
    assert "unit mismatch" in s3.feedback.lower()


# ─── 4. REAL TEST — ALL VALID STEPS ───────────────────────────────────────────

def test_all_valid_steps_complete_solution():
    """
    A flawless multi-step solution.
    """
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 - 4
3. 2x = 6
4. x = 3"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    assert res.overall_outcome == OverallOutcome.ALL_STEPS_VALID
    assert res.first_wrong_step is None
    assert all(s.validation_status == StepValidationStatus.VALID_STEP for s in res.validated_steps)
    assert res.confidence == ConfidenceClass.HIGH


# ─── 5. REAL TEST — AMBIGUOUS REASONING (§56) ─────────────────────────────────

def test_ambiguous_reasoning_preserves_uncertainty():
    """
    Ambiguous student reasoning should preserve uncertainty without fake certainty numbers.
    """
    raw_sol = """1. 2x + 4 = 10
2. somehow stuff happens
3. x = 3"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Generic",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    assert res.overall_outcome == OverallOutcome.AMBIGUOUS_REASONING
    assert res.confidence == ConfidenceClass.LOW
    s2 = res.validated_steps[1]
    assert s2.validation_status == StepValidationStatus.UNCERTAIN
    assert s2.error_type == ErrorType.UNKNOWN


# ─── 6. REAL TEST — RESUBMISSION & VERSIONING (§35, §57) ──────────────────────

def test_resubmission_creates_new_attempt_and_preserves_history():
    """
    Student gets feedback on Step 2, fixes it, and resubmits.
    Verifies attempt_sequence increment, parent_attempt_id linking, and history preservation.
    """
    # Attempt 1: Error at Step 2
    raw_sol_1 = """1. 2x + 4 = 10
2. 2x = 10 + 4
3. x = 7"""

    res_1 = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol_1,
        skill_id="MATH_LIN_EQ"
    )
    assert res_1.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res_1.attempt_sequence == 1

    # Attempt 2: Resubmission with Step 2 fixed
    raw_sol_2 = """1. 2x + 4 = 10
2. 2x = 10 - 4
3. x = 3"""

    res_2 = StepGraderService.resubmit_solution(
        session_id=res_1.session_id,
        user_id=STUDENT_A_ID,
        updated_raw_input=raw_sol_2
    )

    assert res_2.session_id == res_1.session_id
    assert res_2.attempt_sequence == 2
    assert res_2.overall_outcome == OverallOutcome.ALL_STEPS_VALID
    assert res_2.first_wrong_step is None

    # Verify history in repository
    attempts = StepGraderRepository.get_attempts_for_session(res_1.session_id, STUDENT_A_ID)
    assert len(attempts) == 2
    assert attempts[0].id == res_1.attempt_id
    assert attempts[1].id == res_2.attempt_id
    assert attempts[1].parent_attempt_id == res_1.attempt_id


# ─── 7. REAL TEST — IDEMPOTENCY (§34) ─────────────────────────────────────────

def test_idempotent_duplicate_submission():
    """
    Submitting identical solution with same idempotency key returns cached result
    without creating duplicate records or duplicate Mistake DNA events.
    """
    idem_key = "idemp_test_abc123"
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 + 4
3. x = 7"""

    res_1 = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ",
        idempotency_key=idem_key
    )

    res_2 = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ",
        idempotency_key=idem_key
    )

    assert res_1.attempt_id == res_2.attempt_id
    assert res_1.first_wrong_step == res_2.first_wrong_step

    # Verify no duplicate mistake events
    mistakes = MistakeDNARepository.get_mistake_events(STUDENT_A_ID)
    step_mistakes = [m for m in mistakes if m.source_type == "STEP_GRADER"]
    assert len(step_mistakes) == 1


# ─── 8. BOUNDED TUTOR CONTEXT (§20, §58) ──────────────────────────────────────

def test_bounded_tutor_context():
    """
    Tutor handoff extracts bounded context (step index, raw text, error type, feedback)
    without dumping historical transcripts.
    """
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 + 4
3. x = 7"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    tutor_ctx = StepGraderService.get_tutor_context(res.attempt_id, STUDENT_A_ID)
    assert tutor_ctx.first_wrong_step_index == 2
    assert "2x = 10 + 4" in tutor_ctx.step_raw_text
    assert tutor_ctx.error_type in ("SIGN_OR_NOTATION", "PROCEDURAL")
    assert len(tutor_ctx.feedback) > 0


# ─── 9. CROSS-USER ISOLATION (§37) ───────────────────────────────────────────

def test_cross_user_isolation():
    """
    Student B cannot access or modify Student A's session or attempt.
    """
    raw_sol = "1. 2x + 4 = 10\n2. x = 3"
    res_a = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol
    )

    # Student B attempts to fetch session
    sess_b = StepGraderRepository.get_session(res_a.session_id, STUDENT_B_ID)
    assert sess_b is None

    # Student B attempts to resubmit on Student A's session
    with pytest.raises(ValueError):
        StepGraderService.resubmit_solution(
            session_id=res_a.session_id,
            user_id=STUDENT_B_ID,
            updated_raw_input="1. x = 3"
        )


# ─── 10. DYNAMIC NEW SUBJECT ADAPTATION (§41) ─────────────────────────────────

def test_dynamic_new_subject_adaptation():
    """
    Adds a synthetic structured domain through rubric fixture.
    Core StepGraderService orchestration does not change.
    """
    synthetic_rubric = {
        "required_concepts": ["activation", "transition", "stabilization"],
        "common_errors": {"destabilize": "CONCEPTUAL"},
        "critical_steps": ["step 1: activation", "step 2: transition"]
    }

    raw_sol = """1. system begins activation
2. system enters transition
3. system reaches stabilization"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Synthetic Quantum Mechanics",
        question_text="Explain state stabilization sequence",
        raw_input=raw_sol,
        skill_id="SYNTHETIC_SKILL_001",
        rubric=synthetic_rubric
    )

    assert res.overall_outcome == OverallOutcome.ALL_STEPS_VALID
    assert len(res.validated_steps) == 3


# ─── 11. AUDITOR EXECUTION (§49) ─────────────────────────────────────────────

def test_step_grader_auditor():
    """
    Verifies StepGraderAuditor validates invariants and passes clean attempts.
    """
    raw_sol = """1. 2x + 4 = 10
2. 2x = 10 + 4
3. x = 7"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    audit_res = StepGraderAuditor.run_system_audit(STUDENT_A_ID)
    assert audit_res["overall_status"] == "PASS"
    assert audit_res["failed_count"] == 0


# ─── 12. CHEMISTRY STOICHIOMETRY NUMERICAL (§13) ──────────────────────────────

def test_chemistry_stoichiometry_calculation_error():
    """
    Chemistry numerical with calculation slip and downstream tracking.
    """
    raw_sol = """1. n = mass / molar mass
2. n = 36 / 18 = 3 moles
3. mass = 3 * 18 = 54 grams"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Chemistry",
        question_text="Calculate moles for 36 grams of H2O (molar mass = 18)",
        raw_input=raw_sol,
        skill_id="CHEM_STOICHIOMETRY"
    )

    assert res.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res.first_wrong_step == 2
    assert res.error_type == ErrorType.CALCULATION
    s2 = res.validated_steps[1]
    assert s2.validation_status == StepValidationStatus.ROOT_ERROR
    s3 = res.validated_steps[2]
    assert s3.validation_status == StepValidationStatus.DOWNSTREAM_ERROR


# ─── 13. COMPUTER SCIENCE ALGORITHM TRACE (§14) ───────────────────────────────

def test_cs_reasoning_off_by_one_condition():
    """
    Computer science condition check detects loop boundary issues.
    """
    raw_sol = """1. initialize i = 0
2. while i <= n
3. process element"""

    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Computer Science",
        question_text="Iterate over 0-indexed list of size n",
        raw_input=raw_sol,
        skill_id="CS_DATA_STRUCT"
    )

    assert res.overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED
    assert res.first_wrong_step == 2
    assert res.error_type == ErrorType.REASONING
    assert res.validated_steps[1].error_subtype == "off_by_one"


# ─── 14. COLD RESTART RECOVERY (§31, §36) ─────────────────────────────────────

def test_cold_restart_persistence_recovery():
    """
    Purging process memory cache should still allow retrieving session, attempt, and steps.
    """
    raw_sol = "1. 2x + 4 = 10\n2. 2x = 6\n3. x = 3"
    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ"
    )

    # Purge volatile memory cache
    StepGraderRepository.clear_memory_cache()

    # Retrieve from repository
    recovered_sess = StepGraderRepository.get_session(res.session_id, STUDENT_A_ID)
    assert recovered_sess is not None
    assert recovered_sess.id == res.session_id

    recovered_att = StepGraderRepository.get_attempt(res.attempt_id, STUDENT_A_ID)
    assert recovered_att is not None
    assert recovered_att.overall_outcome == OverallOutcome.ALL_STEPS_VALID

    recovered_steps = StepGraderRepository.get_steps_for_attempt(res.attempt_id, STUDENT_A_ID)
    assert len(recovered_steps) == 3


# ─── 15. ASSISTANCE LEVEL TRACKING (§25) ──────────────────────────────────────

def test_assistance_level_tracking():
    """
    Grading tracks assistance level accurately without granting independent transfer claim.
    """
    raw_sol = "1. 2x + 4 = 10\n2. 2x = 6\n3. x = 3"
    res = StepGraderService.grade_solution(
        user_id=STUDENT_A_ID,
        subject="Mathematics",
        question_text="2x + 4 = 10",
        raw_input=raw_sol,
        skill_id="MATH_LIN_EQ",
        assistance_level=AssistanceLevel.HINT_ASSISTED
    )

    attempt = StepGraderRepository.get_attempt(res.attempt_id, STUDENT_A_ID)
    assert attempt.assistance_level == AssistanceLevel.HINT_ASSISTED
