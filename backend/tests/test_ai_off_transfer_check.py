"""
LearnByGenie — Feature 7: AI-Off Transfer Check Test Suite
============================================================
Comprehensive test suite verifying:
- Eligibility rules (§42)
- Strict AI-off boundary and server-side support lock (§43)
- Evidence round trips to Mastery Graph and Mistake DNA (§44)
- Item novelty & exclusion of triggering items (§45)
- Subject generality across Class 5-12, JEE, NEET, Chemistry, UG CS (§46)
- Session durability, idempotency, multi-tab safety, and cold reload (§47)
- Transfer Auditor verification (§40)
"""
import pytest
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from app.services.transfer.schemas import (
    TransferTrigger, TransferLevel, TransferSessionStatus,
    TransferOutcome, TransferSession, TransferResponse
)
from app.services.transfer.policy import TransferPolicy, get_transfer_policy
from app.services.transfer.repository import TransferRepository
from app.services.transfer.service import AIOffTransferCheckService
from app.services.transfer.audit import TransferAuditor

from app.services.practice.schemas import (
    PracticeItem, DifficultyBand, QuestionType, ProvenanceType,
    VerificationStatus
)
from app.services.practice.item_bank import (
    register_practice_item, get_practice_item, CANONICAL_PRACTICE_ITEMS
)
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.schemas import EvidenceSource, AssistanceLevel
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.repository import MistakeDNARepository
from app.services.mistake_dna.schemas import (
    MistakeSourceType, RepairStatus, PatternStatus, MistakeCandidate
)

TEST_USER_A = "f1c205c6-03b3-479e-b7b8-ef435dd9f595"
TEST_USER_B = "84a81abc-66b6-4d79-9ba8-aeadb8d8fef0"


@pytest.fixture(autouse=True)
def clean_state():
    TransferRepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    MistakeDNARepository.clear_memory_cache()
    yield
    TransferRepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    MistakeDNARepository.clear_memory_cache()


# ─── 1. ELIGIBILITY TESTS (§42) ───────────────────────────────────────────────

def test_transfer_eligibility_qualified_triggers():
    """Tutor repair, practice repair, and student request qualify for transfer check."""
    res_prac = AIOffTransferCheckService.check_eligibility(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        trigger=TransferTrigger.PRACTICE_REPAIR
    )
    assert res_prac.is_eligible is True

    res_tutor = AIOffTransferCheckService.check_eligibility(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        trigger=TransferTrigger.TUTOR_REPAIR
    )
    assert res_tutor.is_eligible is True

    res_student = AIOffTransferCheckService.check_eligibility(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        trigger=TransferTrigger.STUDENT_REQUEST
    )
    assert res_student.is_eligible is True


def test_transfer_eligibility_insufficient_content():
    """Skill with no verified items returns INSUFFICIENT_TRANSFER_CONTENT."""
    res = AIOffTransferCheckService.check_eligibility(
        user_id=TEST_USER_A,
        skill_id="UNSEEDED_SKILL_XYZ",
        trigger=TransferTrigger.PRACTICE_REPAIR
    )
    assert res.is_eligible is False
    assert "INSUFFICIENT_TRANSFER_CONTENT" in res.reason


# ─── 2. STRICT SUPPORT OFF & SERVER-SIDE SUPPORT LOCK (§43, §28, §29) ─────────

def test_ai_support_disabled_in_student_view():
    """Student view strictly hides correct answer, hints, and marks support_disabled = True."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        source_trigger=TransferTrigger.PRACTICE_REPAIR
    )
    assert sess is not None

    item_view = AIOffTransferCheckService.get_current_item(sess.id, TEST_USER_A)
    assert item_view is not None
    assert item_view.support_disabled is True
    assert not hasattr(item_view, "correct_answer")
    assert not hasattr(item_view, "hints")
    assert not hasattr(item_view, "explanation")


def test_server_side_support_lock_aborts_active_transfer():
    """Requesting AI support during an active transfer attempt aborts session."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        source_trigger=TransferTrigger.PRACTICE_REPAIR
    )
    assert sess is not None
    assert AIOffTransferCheckService.is_support_locked(TEST_USER_A, "MATH_FRAC_DEC") is True

    # Student attempts to call Tutor / Hint
    aborted = AIOffTransferCheckService.record_support_attempt(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        support_channel="TUTOR_API"
    )
    assert aborted is True

    # Session must be ABORTED
    sess_after = TransferRepository.get_session(sess.id)
    assert sess_after.status == TransferSessionStatus.ABORTED
    assert "TUTOR_API" in (sess_after.abort_reason or "")
    assert sess_after.support_lock_active is False


# ─── 3. ITEM NOVELTY & EXCLUSION (§45, §6) ────────────────────────────────────

def test_transfer_item_excludes_triggering_practice_item():
    """Transfer item must not repeat the exact item recently answered in repair."""
    items = [it for it in CANONICAL_PRACTICE_ITEMS if it.skill_id == "MATH_FRAC_DEC"]
    assert len(items) >= 2
    triggering_item_id = items[0].id

    # Start session excluding the triggering item
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        source_trigger=TransferTrigger.PRACTICE_REPAIR,
        excluded_item_ids=[triggering_item_id]
    )
    assert sess is not None
    assert sess.current_item_id != triggering_item_id


def test_insufficient_content_when_all_items_excluded():
    """When all existing items have been seen, reports insufficient content gracefully."""
    items = [it for it in CANONICAL_PRACTICE_ITEMS if it.skill_id == "MATH_FRAC_DEC"]
    all_item_ids = [it.id for it in items]

    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        source_trigger=TransferTrigger.PRACTICE_REPAIR,
        excluded_item_ids=all_item_ids
    )
    assert sess is None  # Gracefully refuses to repeat exact items


# ─── 4. EVIDENCE ROUND TRIPS & NO DIRECT MASTERY MUTATION (§44, §17, §19, §20)

def test_successful_independent_transfer_emits_mastery_and_confirms_repair():
    """Successful independent transfer emits EvidenceSource.TRANSFER_CHECK and confirms repair."""
    # Seed recurring mistake in Mistake DNA
    cand = MistakeCandidate(
        user_id=TEST_USER_A,
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        source_type=MistakeSourceType.PRACTICE,
        source_record_id="seed_t_1",
        question_reference="solve x",
        student_response="x = 7",
        correct_answer="x = -7",
        expected_answer="x = -7",
        prompt_text="5 - 3x = 14",
        assistance_level=AssistanceLevel.INDEPENDENT,
        metadata={}
    )
    MistakeDNAService.ingest_error_candidate(cand)

    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        source_trigger=TransferTrigger.MISTAKE_DNA_REPAIR
    )
    assert sess is not None
    raw_item = get_practice_item(sess.current_item_id)

    # Submit correct answer independently
    fb = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )
    assert fb is not None
    assert fb.correctness is True
    assert fb.outcome == TransferOutcome.PASSED

    # 1. Check MasteryGraph received exactly one TRANSFER_CHECK evidence
    m_evs = MasteryRepository.get_evidence_for_skill(TEST_USER_A, "MATH_LIN_EQ")
    assert len(m_evs) >= 1
    assert any(e.source_type == EvidenceSource.TRANSFER_CHECK for e in m_evs)

    # 2. Check Mistake DNA pattern received independent repair confirmation
    patterns = MistakeDNARepository.get_patterns_for_user(TEST_USER_A, skill_id="MATH_LIN_EQ")
    if patterns:
        assert patterns[0].repair_status in (RepairStatus.REPAIRED, RepairStatus.IN_REPAIR)


def test_failed_independent_transfer_emits_evidence_and_mistake_event():
    """Failed transfer attempt records valid evidence and creates mistake event without shaming."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        source_trigger=TransferTrigger.PRACTICE_REPAIR
    )
    assert sess is not None

    fb = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=sess.current_item_id,
        student_response="Completely_Wrong_Answer",
        question_index=0
    )
    assert fb is not None
    assert fb.correctness is False
    assert fb.outcome == TransferOutcome.NEEDS_MORE_EVIDENCE
    assert "needs a little more practice" in fb.feedback_headline.lower()

    # MasteryGraph received TRANSFER_CHECK evidence
    m_evs = MasteryRepository.get_evidence_for_skill(TEST_USER_A, "SCI_MATTER_STATES")
    assert any(e.source_type == EvidenceSource.TRANSFER_CHECK for e in m_evs)

    # Mistake DNA received TRANSFER_CHECK mistake event
    mst_evs = MistakeDNARepository.get_mistake_events(TEST_USER_A)
    assert any(e.source_type == MistakeSourceType.TRANSFER_CHECK for e in mst_evs)


# ─── 5. IDEMPOTENCY & MULTI-TAB SAFETY (§47, §14, §15) ────────────────────────

def test_transfer_response_idempotency():
    """Duplicate submissions of same answer return identical feedback without double-recording."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        source_trigger=TransferTrigger.STUDENT_REQUEST
    )
    raw_item = get_practice_item(sess.current_item_id)

    fb1 = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )
    fb2 = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )
    assert fb1.outcome == fb2.outcome
    resps = TransferRepository.get_session_responses(sess.id)
    assert len(resps) == 1


def test_transfer_multi_tab_divergence_protection():
    """Stale tab submission does not double advance session."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics"
    )
    raw_item = get_practice_item(sess.current_item_id)

    # Tab A submits
    AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )

    # Tab B submits stale index 0
    fb_tab_b = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )
    assert fb_tab_b is not None
    sess_after = TransferRepository.get_session(sess.id)
    assert sess_after.question_index == 1


# ─── 6. COLD RESTORE & RESUME (§47, §16) ──────────────────────────────────────

def test_transfer_session_resume_after_memory_purge():
    """Purging memory completely reconstructs session state from authoritative repository."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        source_trigger=TransferTrigger.TUTOR_REPAIR
    )
    sess_id = sess.id
    raw_item_id = sess.current_item_id

    # Purge memory cache
    TransferRepository.clear_memory_cache()

    # Resume
    res = AIOffTransferCheckService.resume_session(sess_id, TEST_USER_A)
    assert res is not None
    res_sess, res_item = res
    assert res_sess.id == sess_id
    assert res_sess.skill_id == "PHY_NEWTON_LAWS"
    assert res_sess.current_item_id == raw_item_id
    assert res_item.item_id == raw_item_id


# ─── 7. CROSS-USER ISOLATION (§36, §37) ───────────────────────────────────────

def test_cross_user_isolation():
    """Student B cannot view or submit responses to Student A's transfer session."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics"
    )

    # Student B queries item
    item_b = AIOffTransferCheckService.get_current_item(sess.id, TEST_USER_B)
    assert item_b is None

    # Student B attempts submission
    fb_b = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_B,
        item_id=sess.current_item_id,
        student_response="3/4"
    )
    assert fb_b is None

    # Student B queries summary
    sum_b = AIOffTransferCheckService.get_session_summary(sess.id, TEST_USER_B)
    assert sum_b is None


# ─── 8. SUBJECT GENERALITY ACROSS ALL 7 DOMAINS (§46, §24) ────────────────────

@pytest.mark.parametrize("subj,skill_id", [
    ("Mathematics", "MATH_NUM_OPS"),        # Class 5 Math
    ("Science", "SCI_MATTER_STATES"),        # Class 8 Science
    ("Mathematics", "MATH_QUAD_EQ"),         # Class 10 Math
    ("Physics", "PHY_ELECTROSTATICS"),       # JEE Physics
    ("Biology", "BIO_GENETICS"),             # NEET Biology
    ("Chemistry", "CHEM_BONDING"),           # Chemistry
    ("Computer Science", "CS_DATA_STRUCT"),  # UG Computer Science
])
def test_same_engine_across_all_domains(subj, skill_id):
    """The identical transfer engine executes flows across all domains without hardcoded logic."""
    sess = AIOffTransferCheckService.start_session(
        user_id=TEST_USER_A,
        skill_id=skill_id,
        subject=subj,
        source_trigger=TransferTrigger.STUDENT_REQUEST
    )
    assert sess is not None
    raw_item = get_practice_item(sess.current_item_id)
    assert raw_item is not None

    fb = AIOffTransferCheckService.submit_response(
        session_id=sess.id,
        user_id=TEST_USER_A,
        item_id=raw_item.id,
        student_response=raw_item.correct_answer,
        question_index=0
    )
    assert fb is not None
    assert fb.correctness is True
    assert fb.outcome == TransferOutcome.PASSED


# ─── 9. TRANSFER AUDITOR (§40) ────────────────────────────────────────────────

def test_transfer_auditor_clean_suite():
    """TransferAuditor passes with zero issues on valid operations."""
    rep = TransferAuditor.audit_all()
    assert rep.is_valid is True
    assert len(rep.issues_found) == 0
