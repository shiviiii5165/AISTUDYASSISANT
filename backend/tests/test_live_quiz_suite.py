"""
LearnByGenie — Live Quiz Engine Unit Test Suite
============================================
Deterministic testing of:
1. Participant JWT issuance and cryptographic verification
2. Real-time deterministic response grading & speed bonuses
3. Server-authoritative state transitions & join code generation
4. Zero-leakage invariant: student state hides correct answers & explanations until revealed
5. Class analytics computation, concept heatmaps, & option distribution aggregation
6. Duplicate submission handling and idempotency

Pure Python, no remote network calls.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_KEY", "x")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-live-secret-key-32-chars-long!")

from datetime import datetime, timezone, timedelta
from app.services.live_quiz import repository as repo
from app.services.live_quiz import scoring
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz.schemas import (
    LiveSessionStatus, LiveEventType, to_student_question_dict
)

_failures = []


def check(name: str, cond: bool):
    if cond:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}")
        _failures.append(name)


# ─── 1. Participant JWT Authentication ───────────────────────────────────────

def test_participant_jwt():
    pid = "part-123"
    sid = "sess-456"
    name = "Curious Owl"

    token = repo.create_participant_token(pid, sid, name)
    check("create_participant_token returns string", isinstance(token, str) and len(token) > 20)

    payload = repo.verify_participant_token(token)
    check("verify_participant_token returns matching sub", payload.get("sub") == pid)
    check("verify_participant_token returns matching session_id", payload.get("session_id") == sid)
    check("verify_participant_token returns matching display_name", payload.get("display_name") == name)
    check("verify_participant_token returns participant role", payload.get("role") == "participant")

    # Tampered token
    tampered = token[:-4] + "abcd"
    try:
        repo.verify_participant_token(tampered)
        check("tampered token should raise ValueError", False)
    except ValueError:
        check("tampered token properly rejected", True)


# ─── 2. Response Grading & Speed Bonus ───────────────────────────────────────

def test_scoring_and_speed_bonus():
    q = {
        "id": "q1",
        "question_text": "What is the powerhouse of the cell?",
        "options": ["Mitochondria", "Nucleus", "Ribosome", "Golgi"],
        "correct_answer": "Mitochondria",
    }

    # Correct without speed bonus
    cfg_no_bonus = {"enabled": True, "seconds": 30, "speed_bonus": False}
    is_corr, pts = scoring.grade_live_response(q, "Mitochondria", 5000, cfg_no_bonus)
    check("correct answer scores True", is_corr is True)
    check("standard base points awarded (1000)", pts == 1000)

    # Case insensitivity & whitespace tolerance
    is_corr_ci, pts_ci = scoring.grade_live_response(q, "  mitochondria  ", 5000, cfg_no_bonus)
    check("case-insensitive and trimmed answer graded correct", is_corr_ci is True and pts_ci == 1000)

    # Wrong answer
    is_wrong, pts_wrong = scoring.grade_live_response(q, "Nucleus", 2000, cfg_no_bonus)
    check("wrong answer scores False", is_wrong is False)
    check("wrong answer gets 0 points", pts_wrong == 0)

    # Empty answer
    is_empty, pts_empty = scoring.grade_live_response(q, None, 2000, cfg_no_bonus)
    check("null answer gets 0 points", is_empty is False and pts_empty == 0)

    # Speed bonus enabled
    cfg_bonus = {"enabled": True, "seconds": 30, "speed_bonus": True}
    # Instant answer (< 1s out of 30s) -> nearly full 500 bonus points
    _, pts_fast = scoring.grade_live_response(q, "Mitochondria", 500, cfg_bonus)
    check("fast response gets speed bonus (> 1450 pts)", pts_fast >= 1480)

    # Late response (at 29s out of 30s) -> tiny bonus
    _, pts_slow = scoring.grade_live_response(q, "Mitochondria", 29000, cfg_bonus)
    check("slow response gets reduced speed bonus (< 1050 pts)", 1000 <= pts_slow < 1050)


# ─── 3. State Machine Transitions & Code Generation ──────────────────────────

def test_state_transitions():
    code = mgr.generate_join_code()
    check("join code is 6 digits", len(code) == 6 and code.isdigit())

    # Legal transitions
    try:
        mgr.assert_legal_transition(LiveSessionStatus.CREATED.value, LiveSessionStatus.LOBBY.value)
        mgr.assert_legal_transition(LiveSessionStatus.LOBBY.value, LiveSessionStatus.LIVE.value)
        mgr.assert_legal_transition(LiveSessionStatus.LIVE.value, LiveSessionStatus.PAUSED.value)
        mgr.assert_legal_transition(LiveSessionStatus.PAUSED.value, LiveSessionStatus.LIVE.value)
        mgr.assert_legal_transition(LiveSessionStatus.LIVE.value, LiveSessionStatus.COMPLETED.value)
        check("legal state transitions pass validation", True)
    except Exception as e:
        check(f"legal state transition failed: {e}", False)

    # Illegal transitions
    try:
        mgr.assert_legal_transition(LiveSessionStatus.CREATED.value, LiveSessionStatus.LIVE.value)
        check("illegal transition CREATED -> LIVE should fail", False)
    except repo.StateTransitionError:
        check("illegal transition CREATED -> LIVE successfully blocked", True)

    try:
        mgr.assert_legal_transition(LiveSessionStatus.COMPLETED.value, LiveSessionStatus.LIVE.value)
        check("illegal transition COMPLETED -> LIVE should fail", False)
    except repo.StateTransitionError:
        check("illegal transition COMPLETED -> LIVE successfully blocked", True)


# ─── 4. Zero-Leakage Invariant ───────────────────────────────────────────────

def test_zero_leakage_student_state():
    q_dict = {
        "id": "q-top-secret",
        "question_text": "What is 2 + 2?",
        "options": ["3", "4", "5", "22"],
        "correct_answer": "4",
        "explanation": "Elementary arithmetic: two plus two equals four.",
        "difficulty": "easy",
        "concept_id": "math_addition",
    }

    sanitized = to_student_question_dict(q_dict)
    check("sanitized dict preserves question_text", sanitized["question_text"] == "What is 2 + 2?")
    check("sanitized dict preserves options", sanitized["options"] == ["3", "4", "5", "22"])
    check("sanitized dict OMITS correct_answer", "correct_answer" not in sanitized)
    check("sanitized dict OMITS explanation", "explanation" not in sanitized)


# ─── 5. Memory Session & Analytics Verification ─────────────────────────────

def test_session_lifecycle_and_analytics():
    sid = "sess-mock-001"
    host_id = "teacher-101"
    pid1 = "student-1"
    pid2 = "student-2"

    q1 = {
        "id": "q1",
        "question_text": "Capital of France?",
        "options": ["Paris", "Berlin", "Rome", "Madrid"],
        "correct_answer": "Paris",
        "concept_id": "geography_capitals",
    }
    q2 = {
        "id": "q2",
        "question_text": "7 * 8 = ?",
        "options": ["54", "56", "64", "48"],
        "correct_answer": "56",
        "concept_id": "math_multiplication",
    }

    sess_data = {
        "id": sid,
        "quiz_id": "quiz-mock-999",
        "host_user_id": host_id,
        "join_code": "888999",
        "status": LiveSessionStatus.LIVE.value,
        "mode": "teacher_led",
        "current_question_index": 0,
        "current_question_started_at": datetime.now(timezone.utc).isoformat(),
        "current_question_deadline": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
        "total_questions": 2,
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False, "show_correctness_immediately": True},
        "questions_snapshot": [q1, q2],
        "question_order": ["q1", "q2"],
        "version": 1,
    }
    repo.create_live_session(sess_data)

    # Add participants
    repo.create_participant({"id": pid1, "session_id": sid, "display_name": "Alice", "score": 0, "status": "active"})
    repo.create_participant({"id": pid2, "session_id": sid, "display_name": "Bob", "score": 0, "status": "active"})

    # Record responses for Q1: Alice correct, Bob wrong
    repo.record_response({
        "id": "resp-1",
        "session_id": sid,
        "participant_id": pid1,
        "question_id": "q1",
        "selected_option_id": "Paris",
        "is_correct": True,
        "points": 1000,
        "response_time_ms": 3500,
        "concept_id": "geography_capitals",
    })
    repo.record_response({
        "id": "resp-2",
        "session_id": sid,
        "participant_id": pid2,
        "question_id": "q1",
        "selected_option_id": "Berlin",
        "is_correct": False,
        "points": 0,
        "response_time_ms": 6000,
        "concept_id": "geography_capitals",
    })

    analytics = scoring.compute_session_analytics(sid)
    check("analytics reports 2 participants", analytics.get("total_participants") == 2)
    check("analytics reports 2 total responses", analytics.get("total_responses") == 2)
    check("overall accuracy is 50%", analytics.get("overall_accuracy") == 50.0)

    heatmap = analytics.get("concept_heatmap", [])
    geo_item = next((h for h in heatmap if h.get("concept_id") == "geography_capitals"), None)
    check("concept heatmap contains geography_capitals", geo_item is not None)
    if geo_item:
        check("geography_capitals accuracy is 50.0%", geo_item.get("accuracy_pct") == 50.0)

    # Student sanitized view for Alice while Q1 is unrevealed
    alice_state = mgr.get_sanitized_student_state(sid, pid1)
    check("alice sees is_revealed False", alice_state["is_revealed"] is False)
    check("alice question does not contain correct_answer", "correct_answer" not in (alice_state["question"] or {}))
    check("alice has_submitted is True", alice_state["has_submitted"] is True)
    check("alice selected_option_id is Paris", alice_state["selected_option_id"] == "Paris")

    # Duplicate response submission guard
    dup_resp = {
        "id": "resp-1-dup",
        "session_id": sid,
        "participant_id": pid1,
        "question_id": "q1",
        "selected_option_id": "Rome",
        "is_correct": False,
        "points": 0,
    }
    saved_dup = repo.record_response(dup_resp)
    check("duplicate response returns previously recorded response", saved_dup.get("id") == "resp-1")


def run_all():
    print("================================================================================")
    print("LEARNBYGENIE — LIVE QUIZ ENGINE UNIT TESTS")
    print("================================================================================")
    test_participant_jwt()
    test_scoring_and_speed_bonus()
    test_state_transitions()
    test_zero_leakage_student_state()
    test_session_lifecycle_and_analytics()

    print("================================================================================")
    if _failures:
        print(f"FAILED: {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL LIVE QUIZ TESTS PASSED (100% OK)")
        print("================================================================================")


if __name__ == "__main__":
    run_all()
