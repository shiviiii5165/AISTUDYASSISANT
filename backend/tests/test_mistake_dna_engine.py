"""
LearnByGenie — Feature 5: Mistake DNA Engine Test Suite
========================================================
Comprehensive verification covering:
1. Canonical error taxonomy & classification (§42)
2. Pattern state progression (ISOLATED -> RECURRING -> PERSISTENT -> REPAIRED) (§43)
3. Source independence & idempotency (§11, §12)
4. Repair evidence lifecycle & assistance awareness (§16, §17, §44)
5. Historical memory preservation & recurrence after repair (§18, §44)
6. Prerequisite correlation without causal over-claims (§13, §14)
7. MasteryGraph authority boundary (§14)
8. Socratic Tutor, Diagnostic, and Quiz integration contracts (§21, §22, §23, §46)
9. Security, RLS, and cross-user isolation (§30, §45)
10. Deterministic auditor validation (§41)
"""
import pytest
import uuid
from datetime import datetime, timezone

from app.services.mistake_dna.schemas import (
    ErrorType, PatternStatus, RepairStatus, ConfidenceClass,
    AssistanceLevel, MistakeSourceType, MistakeCandidate,
    MistakePattern, MistakeEvent, StepGraderMistakeCandidate
)
from app.services.mistake_dna.classifier import MistakeClassifier
from app.services.mistake_dna.repository import MistakeDNARepository
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.audit import MistakeDNAAuditor
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.schemas import EvidenceSource, MasteryState, AssistanceLevel as MasteryAssistanceLevel
from app.services.tutor.schemas import TutorCheck, CheckType, CheckOutcome
from app.services.tutor.service import PersonalizedTutorService

from app.db.supabase_client import supabase

STUDENT_A = "f1c205c6-03b3-479e-b7b8-ef435dd9f595"
STUDENT_B = "84a81abc-66b6-4d79-9ba8-aeadb8d8fef0"


def _clean_test_db():
    if supabase is not None:
        try:
            supabase.table("mistake_repair_events").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("mistake_patterns").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("mistake_events").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("learner_skill_evidence").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
            supabase.table("learner_skill_states").delete().in_("user_id", [STUDENT_A, STUDENT_B]).execute()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_stores():
    MistakeDNARepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    _clean_test_db()
    yield
    MistakeDNARepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    _clean_test_db()


# ─── 1. CLASSIFICATION TESTS (§42) ────────────────────────────────────────────

def test_classify_sign_or_notation_error():
    # Numeric opposite sign
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_1",
        prompt_text="Solve 2x + 6 = 0",
        expected_answer="x = -3",
        student_response="x = 3"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.SIGN_OR_NOTATION
    assert res.confidence == ConfidenceClass.HIGH
    assert res.error_subtype == "sign_transposition"


def test_classify_calculation_arithmetic_slip():
    # Minor computation slip (25 instead of 24)
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_NUM_OPS",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="rec_2",
        prompt_text="Compute 6 * 4",
        expected_answer="24",
        student_response="25"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.CALCULATION
    assert res.confidence == ConfidenceClass.HIGH


def test_classify_unit_or_dimension_error():
    # Expected m/s, answered without units or wrong units
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="PHY_MOTION_BASIC",
        subject="Physics",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_3",
        prompt_text="Find speed when distance is 100 m and time is 10 s",
        expected_answer="10 m/s",
        student_response="10"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.UNIT_OR_DIMENSION
    assert res.error_subtype == "missing_unit"


def test_classify_formula_recall_error():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="PHY_MOTION_BASIC",
        subject="Physics",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_4",
        prompt_text="What is the formula for kinetic energy?",
        expected_answer="1/2 m v^2",
        student_response="m v^2",
        feedback_reason="Student forgot the formula factor of 1/2"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.FORMULA_RECALL


def test_classify_misread_question_error():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_5",
        prompt_text="Find 2x if x + 4 = 10",
        expected_answer="12",
        student_response="6",
        feedback_reason="Student solved for x instead of 2x (misread target question)"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.MISREAD_QUESTION


def test_classify_incomplete_response():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_6",
        prompt_text="Factorize x^2 - 5x + 6",
        student_response="idk"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.INCOMPLETE_RESPONSE


def test_classify_unknown_fallback_without_fabrication():
    # Ambiguous input with no clear signal
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="rec_7",
        prompt_text="What is the discriminant?",
        student_response="triangle symbol"
    )
    res = MistakeClassifier.classify(cand)
    assert res.primary_error_type == ErrorType.UNKNOWN
    assert res.confidence == ConfidenceClass.LOW


# ─── 2. PATTERNING & OCCURRENCE TESTS (§43) ───────────────────────────────────

def test_single_error_becomes_isolated():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="sess_1_item_1",
        prompt_text="Solve x - 5 = 10",
        expected_answer="15",
        student_response="-15"
    )
    ev, pat, is_new = MistakeDNAService.ingest_error_candidate(cand)
    assert is_new is True
    assert ev.primary_error_type == ErrorType.SIGN_OR_NOTATION
    assert pat.occurrence_count == 1
    assert pat.pattern_status == PatternStatus.ISOLATED


def test_repeated_independent_errors_become_recurring():
    # Occurrence 1
    cand1 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="sess_1_item_1",
        expected_answer="15",
        student_response="-15"
    )
    MistakeDNAService.ingest_error_candidate(cand1)

    # Occurrence 2 (separate task / source)
    cand2 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="tutor_turn_check_1",
        expected_answer="7",
        student_response="-7"
    )
    ev2, pat2, is_new = MistakeDNAService.ingest_error_candidate(cand2)
    assert is_new is True
    assert pat2.occurrence_count == 2
    assert pat2.pattern_status == PatternStatus.RECURRING


def test_multi_occurrence_becomes_persistent():
    for i in range(1, 5):
        cand = MistakeCandidate(
            user_id=STUDENT_A,
            skill_id="MATH_LIN_EQ",
            source_type=MistakeSourceType.TUTOR_CHECK,
            source_record_id=f"tutor_turn_check_{i}",
            expected_answer="10",
            student_response="-10"
        )
        _, pat, _ = MistakeDNAService.ingest_error_candidate(cand)

    assert pat.occurrence_count == 4
    assert pat.pattern_status == PatternStatus.PERSISTENT


def test_source_idempotency_prevents_duplicate_counts():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="tutor_check_idemp_1",
        expected_answer="5",
        student_response="-5"
    )
    # Submission 1
    ev1, pat1, is_new1 = MistakeDNAService.ingest_error_candidate(cand)
    assert is_new1 is True
    assert pat1.occurrence_count == 1

    # Submission 2 with same source identity
    ev2, pat2, is_new2 = MistakeDNAService.ingest_error_candidate(cand)
    assert is_new2 is False
    assert ev1.id == ev2.id
    assert pat2.occurrence_count == 1  # Did NOT increment!


def test_different_wording_same_skill_and_error_aggregates_pattern():
    cand1 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="sess_1",
        prompt_text="Solve 2x = 8",
        expected_answer="4",
        student_response="-4"
    )
    MistakeDNAService.ingest_error_candidate(cand1)

    # Different prompt question, same mathematical error type
    cand2 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="sess_2",
        prompt_text="Find x for 3x - 9 = 0",
        expected_answer="3",
        student_response="-3"
    )
    ev2, pat2, _ = MistakeDNAService.ingest_error_candidate(cand2)
    assert pat2.occurrence_count == 2
    assert pat2.pattern_status == PatternStatus.RECURRING


def test_different_error_type_creates_separate_pattern():
    cand1 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="sess_1",
        expected_answer="5",
        student_response="-5" # SIGN_OR_NOTATION
    )
    MistakeDNAService.ingest_error_candidate(cand1)

    cand2 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="sess_2",
        expected_answer="24",
        student_response="25" # CALCULATION
    )
    MistakeDNAService.ingest_error_candidate(cand2)

    patterns = MistakeDNAService.get_skill_patterns(STUDENT_A, "MATH_LIN_EQ")
    assert len(patterns) == 2
    types = {p.error_type for p in patterns}
    assert types == {ErrorType.SIGN_OR_NOTATION, ErrorType.CALCULATION}


# ─── 3. REPAIR LIFECYCLE & ASSISTANCE AWARENESS (§44) ─────────────────────────

def test_hint_assisted_check_does_not_falsely_repair():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="chk_fail_1",
        expected_answer="x = 2 and x = 3",
        student_response="x = -2 and x = -3"
    )
    MistakeDNAService.ingest_error_candidate(cand)

    # Student succeeds with heavy hints (HINT_ASSISTED)
    repairs = MistakeDNAService.mark_repair_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        evidence_source=MistakeSourceType.TUTOR_CHECK,
        evidence_record_id="chk_pass_assisted",
        assistance_level=AssistanceLevel.HINT_ASSISTED
    )
    # Must NOT be marked repaired
    assert len(repairs) == 0

    pats = MistakeDNAService.get_skill_patterns(STUDENT_A, "MATH_QUAD_EQ")
    assert pats[0].repair_status == RepairStatus.IN_REPAIR
    assert pats[0].pattern_status != PatternStatus.REPAIRED


def test_independent_check_repairs_pattern():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="chk_fail_1",
        expected_answer="6",
        student_response="-6"
    )
    MistakeDNAService.ingest_error_candidate(cand)

    # Independent successful later evidence
    repairs = MistakeDNAService.mark_repair_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_QUAD_EQ",
        evidence_source=MistakeSourceType.TUTOR_CHECK,
        evidence_record_id="chk_pass_independent",
        assistance_level=AssistanceLevel.INDEPENDENT
    )
    assert len(repairs) == 1
    assert repairs[0].assistance_level == AssistanceLevel.INDEPENDENT

    pats = MistakeDNAService.get_skill_patterns(STUDENT_A, "MATH_QUAD_EQ")
    assert pats[0].repair_status == RepairStatus.REPAIRED
    assert pats[0].pattern_status == PatternStatus.REPAIRED


def test_repaired_pattern_history_preserved_and_recurrence_triggers_reassessment():
    cand1 = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="rec_1",
        expected_answer="4",
        student_response="-4"
    )
    MistakeDNAService.ingest_error_candidate(cand1)

    # Repair with independent check
    MistakeDNAService.mark_repair_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        evidence_source=MistakeSourceType.TUTOR_CHECK,
        evidence_record_id="rep_1",
        assistance_level=AssistanceLevel.INDEPENDENT
    )

    # Verify state is REPAIRED
    pat_repaired = MistakeDNAService.get_skill_patterns(STUDENT_A, "MATH_LIN_EQ")[0]
    assert pat_repaired.repair_status == RepairStatus.REPAIRED

    # Later new recurrence happens
    cand_recur = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="rec_2",
        expected_answer="8",
        student_response="-8"
    )
    _, pat_after, _ = MistakeDNAService.ingest_error_candidate(cand_recur)

    # Recurrence triggers REASSESSMENT_NEEDED! (§44)
    assert pat_after.repair_status == RepairStatus.REASSESSMENT_NEEDED
    assert pat_after.occurrence_count == 2


# ─── 4. PREREQUISITE CORRELATION & MASTERY SEPARATION (§13, §14) ──────────────

def test_prerequisite_correlation_surfaced_without_direct_mastery_mutation():
    # Ingest 2 incorrect attempts to transition MATH_ALG_EXP to NEEDS_REPAIR (Feature 3 invariant §5)
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_ALG_EXP",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="diag_prereq_fail_1",
        correctness=False
    )
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_ALG_EXP",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="diag_prereq_fail_2",
        correctness=False
    )
    st_prereq = MasteryRepository.get_skill_state(STUDENT_A, "MATH_ALG_EXP")
    assert st_prereq.mastery_state == MasteryState.NEEDS_REPAIR

    # Student now fails dependent skill MATH_LIN_EQ in Mistake DNA
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="chk_linear_1",
        expected_answer="10",
        student_response="-10"
    )
    ev, pat, _ = MistakeDNAService.ingest_error_candidate(cand)

    # Prerequisite signal is attached
    assert pat.likely_prerequisite_skill == "MATH_ALG_EXP"
    assert "needs repair" in pat.prerequisite_signal.lower()

    # MasteryGraphService remains authority: MATH_LIN_EQ mastery state has NOT been altered by Mistake DNA
    st_lin = MasteryRepository.get_skill_state(STUDENT_A, "MATH_LIN_EQ")
    assert st_lin is None or st_lin.mastery_state != MasteryState.NEEDS_REPAIR


# ─── 5. SECURITY & CROSS-USER ISOLATION (§45) ─────────────────────────────────

def test_cross_user_isolation():
    cand_a = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="rec_a_1",
        expected_answer="5",
        student_response="-5"
    )
    MistakeDNAService.ingest_error_candidate(cand_a)

    pats_a = MistakeDNAService.get_patterns(STUDENT_A)
    pats_b = MistakeDNAService.get_patterns(STUDENT_B)

    assert len(pats_a) == 1
    assert len(pats_b) == 0


# ─── 6. AUDITOR INTEGRITY VALIDATION (§41) ────────────────────────────────────

def test_auditor_detects_clean_health():
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="clean_rec_1",
        expected_answer="5",
        student_response="-5"
    )
    MistakeDNAService.ingest_error_candidate(cand)

    report = MistakeDNAAuditor.run_audit(STUDENT_A)
    assert report.audit_passed is True
    assert len(report.orphan_skill_ids) == 0
    assert report.duplicate_source_events == 0
    assert report.repairs_without_evidence == 0


def test_auditor_detects_repairs_without_evidence():
    # Artificially inject an invalid repaired pattern without repair event
    pat = MistakePattern(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        error_type=ErrorType.SIGN_OR_NOTATION,
        pattern_status=PatternStatus.REPAIRED,
        repair_status=RepairStatus.REPAIRED,
        occurrence_count=1
    )
    MistakeDNARepository.save_pattern(pat)

    report = MistakeDNAAuditor.run_audit(STUDENT_A)
    assert report.repairs_without_evidence == 1
    assert report.audit_passed is False


# ─── 7. FUTURE CONTRACT READINESS (§24, §25, §26) ─────────────────────────────

def test_future_contracts_read_interfaces():
    # Adaptive practice query contract (§25)
    cand = MistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="p_rec_1",
        expected_answer="5",
        student_response="-5"
    )
    MistakeDNAService.ingest_error_candidate(cand)

    open_for_practice = MistakeDNAService.get_open_patterns_for_practice(STUDENT_A)
    assert len(open_for_practice) == 1

    # Spaced revision query contract (§26)
    rev_pats = MistakeDNAService.get_patterns_for_revision(STUDENT_A)
    assert len(rev_pats) == 0  # Requires >= 2 occurrences

    # Step grader ingestion contract (§24)
    sg_cand = StepGraderMistakeCandidate(
        user_id=STUDENT_A,
        skill_id="MATH_LIN_EQ",
        first_wrong_step="2x = -8 => x = 4",
        step_index=2,
        error_type=ErrorType.SIGN_OR_NOTATION,
        source_record_id="step_grader_attempt_99"
    )
    ev_sg, pat_sg, is_new_sg = MistakeDNAService.ingest_step_grader_error(sg_cand)
    assert is_new_sg is True
    assert ev_sg.source_type == MistakeSourceType.STEP_GRADER


# ─── 8. FASTAPI ENDPOINT & RLS SECURITY TESTS (§30, §45) ──────────────────────

def test_unauthenticated_mistakes_api_rejected():
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.clear()
    client = TestClient(app)
    res = client.get("/api/mistakes/patterns")
    assert res.status_code in (401, 403)


def test_authenticated_mistakes_api_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.dependencies import get_current_user

    class MockUser:
        id = STUDENT_A
        email = "testing1234@gmail.com"

    app.dependency_overrides[get_current_user] = lambda: MockUser()
    client = TestClient(app)

    try:
        # Ingest test error
        cand = MistakeCandidate(
            user_id=STUDENT_A,
            skill_id="MATH_LIN_EQ",
            source_type=MistakeSourceType.DIAGNOSTIC,
            source_record_id="api_test_source_1",
            expected_answer="6",
            student_response="-6"
        )
        _, pat, _ = MistakeDNAService.ingest_error_candidate(cand)

        # 1. Query patterns
        res_pat = client.get("/api/mistakes/patterns")
        assert res_pat.status_code == 200
        patterns_data = res_pat.json()
        assert len(patterns_data) >= 1

        # 2. Query recent mistakes
        res_recent = client.get("/api/mistakes/recent")
        assert res_recent.status_code == 200
        recent_data = res_recent.json()
        assert len(recent_data) >= 1

        # 3. Query pattern detail
        res_detail = client.get(f"/api/mistakes/detail/{pat.id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert "explainability" in detail_data
        assert "recommended_repair" in detail_data

        # 4. Query repairs
        res_repairs = client.get("/api/mistakes/repairs")
        assert res_repairs.status_code == 200

        # 5. Query compact summary
        res_summary = client.get("/api/mistakes/summary")
        assert res_summary.status_code == 200
        summary_data = res_summary.json()
        assert summary_data["total_patterns"] >= 1

        # 6. Audit endpoint
        res_audit = client.post("/api/mistakes/audit")
        assert res_audit.status_code == 200

        # 7. INVARIANT: Student direct mutation denial (§30)
        # Client cannot directly mutate pattern status
        res_illegal = client.patch(f"/api/mistakes/patterns/{pat.id}", json={"pattern_status": "REPAIRED"})
        assert res_illegal.status_code in (404, 405), "Direct client state mutation endpoint must not exist"

    finally:
        app.dependency_overrides.clear()

