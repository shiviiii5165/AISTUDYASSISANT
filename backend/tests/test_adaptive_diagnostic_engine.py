"""
LearnByGenie — Feature 2 Test Suite: Adaptive Diagnostic & Actual-Level Detection Engine
========================================================================================
Comprehensive deterministic verification:
- Diagnostic start & LearnerContextService integration
- Anchor question selection (Class 3 vs Class 11 JEE)
- Weak-student prerequisite branching & confirmation logic
- Single wrong answer cannot label a gap (confirmation requirement)
- Strong-student progression
- Question budget & stopping rules
- Interruption and resume
- Answer-key isolation & zero leakage
- Idempotency & duplicate submission safety
- Cross-user isolation & teacher role restriction
- JEE and NEET prerequisite probing (no rank/AIR prediction)
- UG coursework extensibility (Computer Science)
- Feature 3 output contract schema integrity
- No global intelligence score, no rank prediction, no gamification
- Item bank content quality audit tooling
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.diagnostic.service import DiagnosticService
from app.services.diagnostic.repository import DiagnosticRepository
from app.services.diagnostic.schemas import (
    DiagnosticStage, DiagnosticState, ConfidenceClass, OverallReadiness,
    DiagnosticSession, DiagnosticResponse, AnswerSubmissionRequest
)
from app.services.diagnostic.adaptive_engine import (
    AdaptiveDecisionEngine, get_default_budget_for_grade
)
from app.services.diagnostic.item_bank import get_item, get_items_for_skill
from app.services.diagnostic.curriculum_blueprint import get_skill
from app.services.diagnostic.audit import audit_entire_item_bank
from app.services.learner_context.schemas import (
    LearnerContext, EducationContext, GoalsContext, PreferencesContext,
    ProfileCompleteness, LearningActivitySummary
)
from app.services.learner_context.service import LearnerContextService

client = TestClient(app)

STUDENT_A_ID = "a56da972-0f19-418d-b0f7-de91ff114190"
STUDENT_B_ID = "d7007dd2-57dd-477c-9429-629d620cd616"


def make_mock_context(grade_level="Class 10", board="CBSE", exam="Boards", lang="english"):
    return LearnerContext(
        student_id=STUDENT_A_ID,
        role="student",
        profile_version=1,
        education=EducationContext(
            level=grade_level,
            level_id=grade_level.lower().replace(" ", "_"),
            stage="SECONDARY",
            board=board,
            stream="general",
            exam_tracks=[exam] if exam else [],
        ),
        goals=GoalsContext(primary=exam),
        subjects=["Mathematics", "Physics"],
        preferences=PreferencesContext(
            preferred_language=lang,
            explanation_language=lang,
            content_difficulty="standard",
            preferred_session_minutes=30,
        ),
        profile_completeness=ProfileCompleteness(
            is_complete=True,
            status="Profile ready",
            completion_percentage=100,
            missing_fields=[]
        ),
        learning_activity_summary=LearningActivitySummary(),
    )


class MockUser:
    def __init__(self, uid: str, role: str = "student"):
        self.id = uid
        self.role = role


from app.db.supabase_client import supabase


@pytest.fixture(autouse=True)
def clean_diagnostic_state():
    DiagnosticRepository.clear_memory_cache()
    if supabase is not None:
        try:
            supabase.table("diagnostic_sessions").delete().in_("user_id", [STUDENT_A_ID, STUDENT_B_ID]).execute()
        except Exception:
            pass
    yield
    DiagnosticRepository.clear_memory_cache()
    if supabase is not None:
        try:
            supabase.table("diagnostic_sessions").delete().in_("user_id", [STUDENT_A_ID, STUDENT_B_ID]).execute()
        except Exception:
            pass


# ─── 1. Diagnostic Start & LearnerContext Integration ─────────────────────────

def test_diagnostic_start_consumes_learner_context():
    """Verify diagnostic session consumes canonical LearnerContext without direct DB leakage."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(
            user_id=STUDENT_A_ID,
            subject="Mathematics",
            retake=False
        )

        assert res.session is not None
        assert res.session.subject == "Mathematics"
        assert res.session.enrolled_grade == 10
        assert res.session.exam_track == "Boards"
        assert res.session.question_budget == 10
        assert res.session.status == "IN_PROGRESS"
        assert res.current_question is not None
        assert res.current_question.sequence_number == 1
        assert res.is_completed is False


# ─── 2. Answer-Key Isolation (Security Boundary) ──────────────────────────────

def test_answer_key_isolation_in_student_payload():
    """Verify correct_answer and explanation are NEVER sent to the student before grading."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(
            user_id=STUDENT_A_ID,
            subject="Mathematics"
        )
        q = res.current_question
        assert q is not None
        q_dict = q.dict()
        assert "correct_answer" not in q_dict
        assert "explanation" not in q_dict
        assert "branch_logic" not in q_dict
        assert q.prompt != ""
        assert len(q.options) >= 2


# ─── 3. Grade-Stage Budgets & Anchor Selection ───────────────────────────────

def test_grade_stage_budgets_and_anchor_class_3_vs_class_11():
    """Primary (Class 3) receives short budget (6) and foundational probes."""
    assert get_default_budget_for_grade(3) == 6
    assert get_default_budget_for_grade(7) == 8
    assert get_default_budget_for_grade(10) == 10
    assert get_default_budget_for_grade(11) == 10

    # Class 3 Student
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 3", "CBSE", "Foundation", "english")
        res3 = DiagnosticService.start_diagnostic(
            user_id=STUDENT_A_ID,
            subject="Mathematics"
        )
        assert res3.session.question_budget == 6
        assert res3.current_question.grade_band == "primary"
        assert res3.current_question.skill_id == "MATH_NUM_OPS"


# ─── 4. Confirmation Logic: One Wrong Answer Cannot Label a Gap ──────────────

def test_single_wrong_answer_cannot_label_gap():
    """A single wrong answer must NOT classify a skill as NEEDS_REPAIR."""
    skill = get_skill("MATH_QUAD_EQ")
    stats = {"attempts": 1, "correct": 0, "incorrect": 1}
    state, conf, action, is_rec = AdaptiveDecisionEngine.classify_skill_result(skill, stats)

    assert state == DiagnosticState.DEVELOPING
    assert state != DiagnosticState.NEEDS_REPAIR
    assert conf == ConfidenceClass.LOW_EVIDENCE
    assert is_rec is False


def test_confirmed_gap_classification_requires_two_failures():
    """Only upon confirmed repeated failure (>= 2 incorrect) does a skill classify as NEEDS_REPAIR."""
    skill = get_skill("MATH_QUAD_EQ")
    stats = {"attempts": 2, "correct": 0, "incorrect": 2}
    state, conf, action, is_rec = AdaptiveDecisionEngine.classify_skill_result(skill, stats)

    assert state == DiagnosticState.NEEDS_REPAIR
    assert conf == ConfidenceClass.MODERATE_EVIDENCE
    assert is_rec is True
    assert "Prerequisite gap detected" in action


# ─── 5. Weak-Student Prerequisite Branching ───────────────────────────────────

def test_weak_student_prerequisite_branching():
    """When a student struggles on secondary quadratic equations, system branches to prerequisites."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id

        # Submit wrong answer to question 1
        sub1 = AnswerSubmissionRequest(item_id=res.current_question.id, student_response="WRONG_ANSWER")
        res2 = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub1)
        assert not res2.is_completed
        assert res2.session.current_stage == DiagnosticStage.CONFIRMATION.value


# ─── 6. Strong-Student Progression ────────────────────────────────────────────

def test_strong_student_progression():
    """Strong student answering correctly proceeds steadily without unnecessary prerequisite probes."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id

        item = get_item(res.current_question.id)
        sub = AnswerSubmissionRequest(item_id=item.id, student_response=item.correct_answer)
        res2 = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub)

        assert not res2.is_completed
        assert res2.session.questions_answered == 1


# ─── 7. Stopping Rules and Question Budget Enforcement ────────────────────────

def test_stopping_rule_and_budget_enforcement():
    """Diagnostic terminates when budget is reached and compiles final report."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 3", "CBSE", "Foundation", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id

        curr = res
        while not curr.is_completed:
            it = get_item(curr.current_question.id)
            sub = AnswerSubmissionRequest(item_id=it.id, student_response=it.correct_answer)
            curr = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub)

        assert curr.is_completed is True
        assert curr.current_question is None
        assert curr.result is not None
        assert curr.result.total_items_answered <= 6
        assert curr.session.status == "COMPLETED"


# ─── 8. Interruption and Safe Resume ───────────────────────────────────────────

def test_interruption_and_safe_resume():
    """Browser refresh or network drop resumes at current question without restarting."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id
        first_q_id = res.current_question.id

        resumed = DiagnosticService.get_session_state(user_id=STUDENT_A_ID, session_id=sess_id)
        assert resumed.session.id == sess_id
        assert resumed.current_question.id == first_q_id
        assert resumed.session.questions_answered == 0


# ─── 9. Idempotency & Duplicate Submission Safety ─────────────────────────────

def test_duplicate_submission_is_idempotent():
    """Submitting the same item twice must not double-count answers or modify evidence."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE", "Boards", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id
        item = get_item(res.current_question.id)

        sub = AnswerSubmissionRequest(item_id=item.id, student_response=item.correct_answer)
        res1 = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub)
        ans_count_1 = res1.session.questions_answered

        # Resubmit exact same answer
        res2 = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub)
        ans_count_2 = res2.session.questions_answered

        assert ans_count_1 == ans_count_2 == 1


# ─── 10. Cross-User Isolation & Role Protection ───────────────────────────────

def test_cross_user_isolation_denies_unauthorized_access():
    """Student B cannot view or submit answers to Student A's diagnostic session."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id

        with pytest.raises(Exception) as excinfo:
            DiagnosticService.get_session_state(user_id=STUDENT_B_ID, session_id=sess_id)
        assert "403" in str(excinfo.value)


def test_api_cross_user_and_teacher_rejection():
    """FastAPI endpoints verify token identity and reject teachers from student diagnostic routes."""
    from app.core.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: MockUser(STUDENT_A_ID, "teacher")

    resp = client.post("/api/diagnostic/start", json={"subject": "Mathematics"})
    assert resp.status_code == 403
    assert "student accounts" in resp.json()["detail"].lower()

    app.dependency_overrides.clear()


# ─── 11. JEE Prerequisite Probing (No Rank / AIR Prediction) ─────────────────

def test_jee_diagnostic_prerequisite_probing_no_rank_prediction():
    """JEE Physics probes vectors & kinematics foundation without generating rank or AIR predictions."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 12", "CBSE", "JEE", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Physics")
        assert res.session.exam_track == "JEE"

        curr = res
        while not curr.is_completed:
            it = get_item(curr.current_question.id)
            sub = AnswerSubmissionRequest(item_id=it.id, student_response="WRONG")
            curr = DiagnosticService.submit_answer(STUDENT_A_ID, res.session.id, sub)

        report = curr.result
        assert report is not None
        report_str = report.json().lower()
        assert "rank" not in report_str
        assert "air " not in report_str
        assert "percentile" not in report_str
        assert "genius" not in report_str
        assert "iq" not in report_str


# ─── 12. NEET Biology Prerequisite Probing ───────────────────────────────────

def test_neet_diagnostic_prerequisite_probing():
    """NEET Biology probes genetics and cellular unit readiness."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 11", "CBSE", "NEET", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Biology")
        assert res.session.exam_track == "NEET"
        assert res.current_question.subject == "Biology"


# ─── 13. UG Coursework Extensibility (Computer Science) ───────────────────────

def test_ug_coursework_diagnostic_extensibility():
    """UG Data Structures & Logic diagnostic runs without schema redesign."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("UG", "Autonomous", "Semester Exam", "english")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Computer Science")
        assert res.session.enrolled_grade == 14
        assert res.current_question.subject == "Computer Science"
        assert res.current_question.grade_band == "ug"


# ─── 14. Feature 3 Ingestion Contract Schema Integrity ─────────────────────────

def test_feature_3_output_contract_integrity():
    """Result must contain valid Feature 3 ingestion contract payload."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")
        sess_id = res.session.id

        curr = res
        while not curr.is_completed:
            it = get_item(curr.current_question.id)
            sub = AnswerSubmissionRequest(item_id=it.id, student_response=it.correct_answer)
            curr = DiagnosticService.submit_answer(STUDENT_A_ID, sess_id, sub)

        result = curr.result
        assert result is not None
        assert len(result.feature3_contract_payload) > 0

        for f3 in result.feature3_contract_payload:
            assert f3.skill_id != ""
            assert f3.diagnostic_state in ("SECURE", "DEVELOPING", "NEEDS_REPAIR", "NOT_ASSESSED", "FRAGILE")
            assert f3.evidence_count >= 1
            assert f3.confidence in ("LOW_EVIDENCE", "MODERATE_EVIDENCE", "HIGH_EVIDENCE")
            assert f3.source == "DIAGNOSTIC"
            assert f3.diagnostic_session_id == sess_id
            assert f3.timestamp != ""
            assert f3.recommended_action != ""


# ─── 15. No Global Intelligence Label & Operating Band Form ──────────────────

def test_no_global_student_label_and_operating_band_form():
    """The system must NOT declare 'You are a Class 8 student.' Enrolled grade is preserved."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE")
        res = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Mathematics")

        curr = res
        while not curr.is_completed:
            it = get_item(curr.current_question.id)
            sub = AnswerSubmissionRequest(item_id=it.id, student_response="INCORRECT")
            curr = DiagnosticService.submit_answer(STUDENT_A_ID, res.session.id, sub)

        result = curr.result
        assert result.enrolled_grade == 10
        assert "you are a class" not in result.operating_level_band.lower()
        assert "recommended starting point" in result.operating_level_band.lower()


# ─── 16. Historical Diagnostics Retention ─────────────────────────────────────

def test_historical_diagnostics_retention():
    """Historical diagnostic reports are persisted and listed via get_history()."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE")

        res1 = DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Science")
        curr = res1
        while not curr.is_completed:
            it = get_item(curr.current_question.id)
            curr = DiagnosticService.submit_answer(STUDENT_A_ID, res1.session.id, AnswerSubmissionRequest(item_id=it.id, student_response=it.correct_answer))

        history = DiagnosticService.get_history(STUDENT_A_ID)
        assert len(history) >= 1
        assert any(h.subject == "Science" for h in history)


# ─── 17. Content Quality Audit Tooling ─────────────────────────────────────────

def test_item_bank_content_quality_audit():
    """Audits entire canonical item bank for completeness, valid options, and correct answers."""
    report = audit_entire_item_bank()
    assert report.total_items_audited >= 15
    assert report.is_healthy is True
    assert len(report.issues) == 0
    assert report.passed_items_count == report.total_items_audited


# ─── 18. Unsupported Subject Rejection ────────────────────────────────────────

def test_unsupported_subject_rejection():
    """Requesting an unconfigured subject raises 400 Bad Request."""
    with patch.object(LearnerContextService, "get_learner_context") as mock_ctx:
        mock_ctx.return_value = make_mock_context("Class 10", "CBSE")
        with pytest.raises(Exception) as exc:
            DiagnosticService.start_diagnostic(user_id=STUDENT_A_ID, subject="Acrobatics")
        assert "400" in str(exc.value)
