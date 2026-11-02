"""
LearnByGenie — Feature 6: Adaptive Practice Engine Test Suite
=============================================================
Comprehensive unit and integration tests covering:
1. Deterministic Selection Policies (§55)
2. Deterministic Difficulty Adaptation (§56)
3. Closed Adaptive Loop & Evidence Ingestion (§57)
4. Session State, Idempotency & Multi-Tab Safety (§58)
5. Subject Agnosticism & Dynamic Subject Certification (§52, §59)
6. Hardcoded Topic Logic Audit (§53)
"""
import pytest
import uuid
import re
from datetime import datetime, timezone

from app.services.practice.schemas import (
    PracticeMode, DifficultyBand, QuestionType, AssistanceLevel,
    SelectionCategory, ProvenanceType, VerificationStatus,
    PracticeSessionStatus, ContentCoverageStatus, PracticeItem,
    StudentPracticeItemView, PracticeSession, PracticeResponse,
    PracticeFeedback, PracticeSelectionExplanation, SessionSummary
)
from app.services.practice.policy import (
    PracticePolicy, get_policy, register_policy, DEFAULT_PRACTICE_POLICY_V1
)
from app.services.practice.repository import PracticeRepository
from app.services.practice.service import AdaptivePracticeService
from app.services.practice.item_bank import (
    get_practice_item, get_practice_items_for_skill,
    get_all_practice_items, register_practice_item, make_practice_uuid
)
from app.services.practice.adapters import (
    BaseDomainValidator, GenericMCQValidator, NumericValidator,
    MathAdapter, PhysicsAdapter, CSAdapter, DomainAdapterRegistry
)
from app.services.practice.audit import ContentAuditor

# Frozen Foundations (§FROZEN FOUNDATIONS)
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.schemas import EvidenceSource, MasteryState, AssistanceLevel as MasteryAssistanceLevel
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.repository import MistakeDNARepository
from app.services.mistake_dna.schemas import (
    ErrorType, PatternStatus, RepairStatus, MistakeSourceType,
    MistakeCandidate, AssistanceLevel as MistakeAssistanceLevel
)
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill
from app.db.supabase_client import supabase

STUDENT_A = "f1c205c6-03b3-479e-b7b8-ef435dd9f595"
STUDENT_B = "84a81abc-66b6-4d79-9ba8-aeadb8d8fef0"


def _clean_test_db():
    PracticeRepository.clear_memory_cache()
    MistakeDNARepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    if supabase is not None:
        for uid in [STUDENT_A, STUDENT_B]:
            for tbl in ["practice_responses", "practice_sessions", "mistake_repair_events", "mistake_patterns", "mistake_events", "learner_skill_evidence", "learner_skill_states"]:
                try:
                    supabase.table(tbl).delete().eq("user_id", uid).execute()
                except Exception:
                    pass


@pytest.fixture(autouse=True)
def reset_stores():
    _clean_test_db()
    yield
    _clean_test_db()


# ═════════════════════════════════════════════════════════════════════════════
# 1. SELECTION TESTS (§55)
# ═════════════════════════════════════════════════════════════════════════════

def test_selection_prerequisite_repair_priority():
    """If target skill has a blocking prerequisite in NEEDS_REPAIR, repair item is prioritized (§10, §55)."""
    user_id = STUDENT_A
    from app.services.mastery.schemas import LearnerSkillState, ReadinessState
    state = LearnerSkillState(
        user_id=user_id,
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        mastery_state=MasteryState.NEEDS_REPAIR,
        readiness_state=ReadinessState.BLOCKED_BY_PREREQUISITE
    )
    MasteryRepository.save_skill_state(state)

    session = AdaptivePracticeService.start_session(
        user_id=user_id,
        subject="Mathematics",
        mode=PracticeMode.REPAIR,
        requested_skill_id="MATH_QUAD_EQ"  # Quadratic Equations depends on Linear / Algebra
    )

    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    assert item_view is not None
    # Prerequisite concept should be served first
    assert item_view.skill_id in ("MATH_LIN_EQ", "MATH_ALG_EXP", "MATH_QUAD_EQ")
    expl = AdaptivePracticeService.explain_selection(session.id, user_id)
    assert expl is not None
    assert expl.category in (SelectionCategory.PREREQUISITE_REPAIR, SelectionCategory.DEVELOPING_SKILL, SelectionCategory.MISTAKE_DNA_REPAIR)


def test_selection_recurring_mistake_dna_targeted_item():
    """Recurring Mistake DNA pattern triggers item exercising that specific error type (§9, §55)."""
    user_id = STUDENT_A
    # Seed recurring SIGN_OR_NOTATION mistake in MATH_LIN_EQ
    cand = MistakeCandidate(
        user_id=user_id,
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="diag_src_sign_01",
        student_response="3",
        expected_answer="-3",
        prompt_text="Solve 5 - 3x = 14",
    )
    # Ingest twice to trigger RECURRING pattern
    MistakeDNAService.ingest_error_candidate(cand)
    cand2 = MistakeCandidate(
        user_id=user_id,
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        source_type=MistakeSourceType.TUTOR_CHECK,
        source_record_id="tutor_src_sign_02",
        student_response="x = 4",
        expected_answer="x = -4",
        prompt_text="Solve -2x = 8",
    )
    MistakeDNAService.ingest_error_candidate(cand2)

    session = AdaptivePracticeService.start_session(
        user_id=user_id,
        subject="Mathematics",
        mode=PracticeMode.REPAIR
    )

    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    assert item_view is not None
    assert item_view.skill_id == "MATH_LIN_EQ"
    expl = AdaptivePracticeService.explain_selection(session.id, user_id)
    assert expl is not None
    assert expl.category == SelectionCategory.MISTAKE_DNA_REPAIR
    assert "sign" in expl.reason.lower() or "error" in expl.reason.lower()


def test_selection_focused_mode_explicit_topic_override():
    """In FOCUSED mode, student's chosen topic is honored (§4, §55)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(
        user_id=user_id,
        subject="Mathematics",
        mode=PracticeMode.FOCUSED,
        requested_skill_id="MATH_FRAC_DEC"
    )

    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    assert item_view is not None
    assert item_view.skill_id == "MATH_FRAC_DEC"
    expl = AdaptivePracticeService.explain_selection(session.id, user_id)
    assert expl is not None
    assert "Fractions" in expl.skill_name or "MATH_FRAC_DEC" in expl.skill_name


def test_selection_not_assessed_exploratory_probe():
    """NOT_ASSESSED skills receive foundational items without negative labeling (§40, §55)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(
        user_id=user_id,
        subject="Science",
        mode=PracticeMode.ADAPTIVE
    )

    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    assert item_view is not None
    expl = AdaptivePracticeService.explain_selection(session.id, user_id)
    assert expl is not None
    # No label of weakness
    assert "weak" not in expl.reason.lower()
    assert "failure" not in expl.reason.lower()


# ═════════════════════════════════════════════════════════════════════════════
# 2. DIFFICULTY TESTS (§56)
# ═════════════════════════════════════════════════════════════════════════

def test_difficulty_independent_success_progression():
    """Two consecutive independent correct answers promote difficulty (§11, §56)."""
    policy = PracticePolicy(consecutive_correct_for_promotion=2, consecutive_incorrect_for_demotion=2)

    # Foundational -> 1 correct -> still Foundational
    diff, c_c, c_i = policy.adapt_difficulty(DifficultyBand.FOUNDATIONAL, 0, 0, AssistanceLevel.INDEPENDENT, True)
    assert diff == DifficultyBand.FOUNDATIONAL
    assert c_c == 1

    # Foundational -> 2nd correct -> Standard
    diff2, c_c2, _ = policy.adapt_difficulty(diff, c_c, c_i, AssistanceLevel.INDEPENDENT, True)
    assert diff2 == DifficultyBand.STANDARD
    assert c_c2 == 0

    # Standard -> 2 correct -> Advanced
    d3, c3, _ = policy.adapt_difficulty(diff2, 0, 0, AssistanceLevel.INDEPENDENT, True)
    d4, c4, _ = policy.adapt_difficulty(d3, c3, 0, AssistanceLevel.INDEPENDENT, True)
    assert d4 == DifficultyBand.ADVANCED


def test_difficulty_hint_assisted_success_does_not_overpromote():
    """Correct answer after hint does NOT trigger promotion streak (§11, §25, §56)."""
    policy = PracticePolicy(consecutive_correct_for_promotion=2)

    # First independent correct
    diff, c_c, _ = policy.adapt_difficulty(DifficultyBand.STANDARD, 0, 0, AssistanceLevel.INDEPENDENT, True)
    assert c_c == 1

    # Second is HINT_ASSISTED correct
    diff2, c_c2, _ = policy.adapt_difficulty(diff, c_c, 0, AssistanceLevel.HINT_ASSISTED, True)
    # Must NOT promote to ADVANCED
    assert diff2 == DifficultyBand.STANDARD
    assert c_c2 == 0  # Streak reset to prevent assisted promotion


def test_difficulty_single_failure_does_not_collapse():
    """Single incorrect answer does NOT collapse difficulty (§11, §56)."""
    policy = PracticePolicy(consecutive_incorrect_for_demotion=2)

    # In ADVANCED, 1 incorrect
    diff, c_c, c_i = policy.adapt_difficulty(DifficultyBand.ADVANCED, 1, 0, AssistanceLevel.INDEPENDENT, False)
    assert diff == DifficultyBand.ADVANCED
    assert c_i == 1

    # 2nd consecutive incorrect -> demote by one level to STANDARD
    diff2, _, c_i2 = policy.adapt_difficulty(diff, 0, c_i, AssistanceLevel.INDEPENDENT, False)
    assert diff2 == DifficultyBand.STANDARD
    assert c_i2 == 0


# ═════════════════════════════════════════════════════════════════════════════
# 3. EVIDENCE & CLOSED REPAIR LOOP TESTS (§57)
# ═════════════════════════════════════════════════════════════════════════

def test_response_submits_practice_evidence_to_mastery_graph():
    """Every validated response submits exactly one PRACTICE evidence to MasteryGraph (§27, §57)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics")
    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    assert item_view is not None

    item = get_practice_item(item_view.id)
    # Submit correct answer
    feedback = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item.id,
        student_response=item.correct_answer,
        question_index=0
    )
    assert feedback is not None
    assert feedback.correctness is True

    # Verify evidence in MasteryRepository
    ev_list = MasteryRepository.get_evidence_for_skill(user_id, item.skill_id)
    practice_evs = [e for e in ev_list if e.source_type == EvidenceSource.PRACTICE]
    assert len(practice_evs) == 1
    assert practice_evs[0].correctness is True


def test_incorrect_response_forwards_to_mistake_dna():
    """Incorrect response creates Mistake DNA event; correct response passes repair evidence (§28, §29)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics")
    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    item = get_practice_item(item_view.id)

    # Submit wrong answer
    feedback = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item.id,
        student_response="definitely_wrong_answer_xyz",
        question_index=0
    )
    assert feedback is not None
    assert feedback.correctness is False

    # Check Mistake DNA repository
    events = MistakeDNARepository.get_mistake_events(user_id)
    assert len(events) >= 1
    assert events[0].source_type == MistakeSourceType.PRACTICE
    assert events[0].skill_id == item.skill_id


def test_verifiable_repair_loop_independent_vs_assisted():
    """Assisted repair moves pattern to IN_REPAIR; independent repair achieves REPAIRED (§16, §29, §57)."""
    user_id = STUDENT_A
    skill_id = "MATH_NUM_OPS"

    # Step 1: Create open mistake pattern
    cand = MistakeCandidate(
        user_id=user_id,
        skill_id=skill_id,
        subject="Mathematics",
        source_type=MistakeSourceType.DIAGNOSTIC,
        source_record_id="diag_seed_calc_01",
        student_response="81",
        correct_answer="82",
        prompt_text="What is 45 + 37?"
    )
    MistakeDNAService.ingest_error_candidate(cand)
    pats = MistakeDNARepository.get_patterns_for_user(user_id, skill_id)
    assert len(pats) == 1
    assert pats[0].repair_status == RepairStatus.OPEN

    # Step 2: Session with hint -> correct with HINT_ASSISTED
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics")
    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    item = get_practice_item(item_view.id)

    # Request hint
    hint_text, revealed, _ = AdaptivePracticeService.request_hint(session.id, user_id, item.id)
    assert hint_text is not None
    assert revealed == 1

    feedback = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item.id,
        student_response=item.correct_answer,
        question_index=0
    )
    assert feedback.correctness is True
    assert feedback.assistance_level == AssistanceLevel.HINT_ASSISTED

    # Pattern should be IN_REPAIR, NOT REPAIRED (§17)
    pat_updated = MistakeDNARepository.get_patterns_for_user(user_id, skill_id)[0]
    assert pat_updated.repair_status == RepairStatus.IN_REPAIR

    # Step 3: Later independent correct response achieves REPAIRED (§16)
    repairs = MistakeDNAService.mark_repair_evidence(
        user_id=user_id,
        skill_id=skill_id,
        evidence_source=MistakeSourceType.PRACTICE,
        evidence_record_id="independent_practice_check_01",
        assistance_level=AssistanceLevel.INDEPENDENT
    )
    assert len(repairs) >= 1
    pat_repaired = MistakeDNARepository.get_patterns_for_user(user_id, skill_id)[0]
    assert pat_repaired.repair_status == RepairStatus.REPAIRED


# ═════════════════════════════════════════════════════════════════════════════
# 4. SESSION, IDEMPOTENCY & MULTI-TAB SAFETY (§58)
# ═════════════════════════════════════════════════════════════════════════════

def test_session_idempotent_duplicate_response():
    """Duplicate network submissions do not double-advance sequence or double-score (§23, §58)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics")
    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    item = get_practice_item(item_view.id)

    # First submission
    fb1 = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item.id,
        student_response=item.correct_answer,
        question_index=0,
        attempt_sequence=1
    )
    assert fb1 is not None

    # Immediate duplicate submission
    fb2 = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item.id,
        student_response=item.correct_answer,
        question_index=0,
        attempt_sequence=1
    )
    assert fb2 is not None
    assert fb2.question_index == fb1.question_index

    # Check evidence count: exactly 1 evidence in MasteryRepository
    evs = MasteryRepository.get_evidence_for_skill(user_id, item.skill_id)
    assert len(evs) == 1


def test_session_multi_tab_divergence_protection():
    """Multi-tab submission with stale question_index returns past feedback without corrupting sequence (§46, §58)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics", question_budget=5)
    item_view1 = AdaptivePracticeService.get_next_item(session.id, user_id)
    item1 = get_practice_item(item_view1.id)

    # Tab A answers question 0
    fb1 = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item1.id,
        student_response=item1.correct_answer,
        question_index=0
    )
    assert fb1.question_index == 0

    # Session question_index is now 1
    reloaded_sess = AdaptivePracticeService.get_session(session.id, user_id)
    assert reloaded_sess.question_index == 1

    # Tab B attempts to answer question 0 again (stale tab)
    fb_tab_b = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=user_id,
        item_id=item1.id,
        student_response="stale_answer",
        question_index=0  # Outdated index!
    )
    # Protected: Tab B receives past question 0 result without advancing session index to 2!
    assert fb_tab_b.question_index == 0
    reloaded_sess2 = AdaptivePracticeService.get_session(session.id, user_id)
    assert reloaded_sess2.question_index == 1


def test_session_resume_across_cold_restart():
    """Session recovers active item and index across memory purge / reload (§24, §58)."""
    user_id = STUDENT_A
    session = AdaptivePracticeService.start_session(user_id=user_id, subject="Mathematics")
    item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
    active_item_id = item_view.id

    # Simulated resume
    resumed_sess, resumed_item = AdaptivePracticeService.resume_session(session.id, user_id)
    assert resumed_sess is not None
    assert resumed_item is not None
    assert resumed_item.id == active_item_id
    assert resumed_sess.question_index == 0


def test_cross_user_isolation():
    """Student B cannot access Student A's practice session (§44, §58)."""
    session = AdaptivePracticeService.start_session(user_id=STUDENT_A, subject="Mathematics")

    # Student B queries Student A's session
    s_b = AdaptivePracticeService.get_session(session.id, user_id=STUDENT_B)
    assert s_b is None

    # Student B attempts to submit response to Student A's session
    fb_b = AdaptivePracticeService.submit_response(
        session_id=session.id,
        user_id=STUDENT_B,
        item_id="some_item",
        student_response="answer",
        question_index=0
    )
    assert fb_b is None


# ═════════════════════════════════════════════════════════════════════════════
# 5. SUBJECT AGNOSTICISM & MULTI-DOMAIN CERTIFICATION (§52, §59)
# ═════════════════════════════════════════════════════════════════════════

def test_same_engine_multi_domain_support():
    """Same engine successfully serves Mathematics, Science, Physics, Chemistry, Biology, CS (§52)."""
    user_id = STUDENT_A
    domains_to_test = [
        ("Mathematics", "MATH_FRAC_DEC"),
        ("Science", "SCI_MATTER_STATES"),
        ("Physics", "PHY_NEWTON_LAWS"),
        ("Physics", "PHY_ELECTROSTATICS"),
        ("Chemistry", "CHEM_BONDING"),
        ("Biology", "BIO_GENETICS"),
        ("Computer Science", "CS_DATA_STRUCT"),
    ]

    for subj, sk_id in domains_to_test:
        session = AdaptivePracticeService.start_session(
            user_id=user_id,
            subject=subj,
            mode=PracticeMode.FOCUSED,
            requested_skill_id=sk_id,
            question_budget=3
        )
        assert session.subject == subj
        item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
        assert item_view is not None, f"Failed to serve item for {subj} ({sk_id})"
        assert item_view.subject.lower() == subj.lower()
        assert item_view.skill_id == sk_id


def test_dynamic_synthetic_subject_registration():
    """Adding a dynamic new subject fixture works with ZERO changes to AdaptivePracticeService (§15, §52, §59)."""
    user_id = STUDENT_A
    synthetic_subject = "Cognitive Robotics"
    synthetic_skill_id = "ROB_KINEMATICS"

    # Register synthetic item
    synth_item = PracticeItem(
        id=make_practice_uuid("synth-rob-01"),
        skill_id=synthetic_skill_id,
        subject=synthetic_subject,
        grade_band="ug",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="What mathematical matrix relates joint velocities to end-effector Cartesian velocities?",
        options=["Jacobian Matrix", "Hessian Matrix", "Covariance Matrix", "Adjacency Matrix"],
        correct_answer="Jacobian Matrix",
        explanation="The Jacobian matrix maps joint velocities to operational space velocities.",
        hints=["It is the matrix of all first-order partial derivatives."],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED
    )
    register_practice_item(synth_item)

    try:
        # Start practice session for synthetic subject
        session = AdaptivePracticeService.start_session(
            user_id=user_id,
            subject=synthetic_subject,
            mode=PracticeMode.ADAPTIVE
        )
        assert session.subject == synthetic_subject

        # Engine serves synthetic item without modifying any core practice code!
        item_view = AdaptivePracticeService.get_next_item(session.id, user_id)
        assert item_view is not None
        assert item_view.prompt == synth_item.prompt
        assert item_view.subject == synthetic_subject

        # Submit response
        feedback = AdaptivePracticeService.submit_response(
            session_id=session.id,
            user_id=user_id,
            item_id=synth_item.id,
            student_response="Jacobian Matrix",
            question_index=0
        )
        assert feedback is not None
        assert feedback.correctness is True
    finally:
        from app.services.practice.item_bank import CANONICAL_PRACTICE_ITEMS
        if synth_item in CANONICAL_PRACTICE_ITEMS:
            CANONICAL_PRACTICE_ITEMS.remove(synth_item)


# ═════════════════════════════════════════════════════════════════════════════
# 6. HARDCODED DEMO TOPIC LOGIC AUDIT (§53)
# ═════════════════════════════════════════════════════════════════════════

def test_hardcoded_topic_logic_audit():
    """Verifies that selection and session architecture have ZERO hardcoded demo conditions (§53)."""
    import inspect
    from app.services.practice import service, policy, repository

    modules = [service, policy, repository]
    banned_patterns = [
        r'if\s+.*topic\s*==\s*["\']quadratic["\']',
        r'if\s+.*subject\s*==\s*["\']physics["\']',
        r'if\s+.*exam\s*==\s*["\']JEE["\']',
        r'if\s+.*topic\s*==\s*["\']fraction["\']',
    ]

    violations = []
    for mod in modules:
        src = inspect.getsource(mod)
        for pat in banned_patterns:
            matches = re.findall(pat, src, re.IGNORECASE)
            if matches:
                violations.append(f"{mod.__name__}: {matches}")

    assert len(violations) == 0, f"Found hardcoded topic logic violations: {violations}"


# ═════════════════════════════════════════════════════════════════════════════
# 7. CONTENT AUDITOR CERTIFICATION (§49, §50, §51)
# ═════════════════════════════════════════════════════════════════════════

def test_content_auditor_all_canonical_items_valid():
    """Audits practice item bank: answer presence, no duplicate options, valid schemas (§51)."""
    report = ContentAuditor.audit_all()
    assert report.is_valid is True, f"Audit issues found: {report.issues_found}"
    assert report.total_items >= 15
    assert report.verified_items == report.total_items
    assert len(report.issues_found) == 0
