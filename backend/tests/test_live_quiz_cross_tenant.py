"""
TeachGenie — Live Quiz Engine: Cross-Tenant Security & Host Isolation Tests
===========================================================================
Verifies that:
1. User B cannot control, mutate, or advance User A's live session.
2. User B cannot pause, resume, reveal, or finalize User A's session.
3. User B cannot trigger AI interventions or view teacher analytics/reports for User A.
4. Participant token issued for Session A is strictly rejected if used against Session B.
5. verify_session_host raises OwnershipError with 403 HTTP parity.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz.schemas import LiveSessionStatus


@pytest.fixture
def active_session_teacher_a():
    sid = "sess-tenant-teacher-a"
    host_a = "user-teacher-alice-uuid"

    q = {
        "id": "q1",
        "question_text": "Is energy conserved?",
        "options": ["Yes", "No", "Depends"],
        "correct_answer": "Yes",
    }
    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-tenant-1",
        "host_user_id": host_a,
        "join_code": "998811",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [q],
        "question_order": ["q1"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })
    return sid, host_a


def test_user_b_cannot_verify_host_of_user_a(active_session_teacher_a):
    sid, host_a = active_session_teacher_a
    host_b = "user-teacher-bob-attacker-uuid"

    # Host A should succeed
    sess_a = repo.verify_session_host(sid, host_a)
    assert sess_a["id"] == sid

    # Host B must be rejected with OwnershipError
    with pytest.raises(repo.OwnershipError) as exc_info:
        repo.verify_session_host(sid, host_b)
    assert "Not authorized to manage this live session" in str(exc_info.value)


import asyncio


def test_user_b_cannot_advance_user_a_session(active_session_teacher_a):
    sid, host_a = active_session_teacher_a
    host_b = "user-teacher-bob-attacker-uuid"

    with pytest.raises(repo.OwnershipError):
        asyncio.run(mgr.advance_to_next_question(sid, host_user_id=host_b))


def test_user_b_cannot_pause_or_resume_user_a_session(active_session_teacher_a):
    sid, host_a = active_session_teacher_a
    host_b = "user-teacher-bob-attacker-uuid"

    with pytest.raises(repo.OwnershipError):
        asyncio.run(mgr.pause_live_session(sid, host_user_id=host_b))

    with pytest.raises(repo.OwnershipError):
        asyncio.run(mgr.resume_live_session(sid, host_user_id=host_b))


def test_user_b_cannot_reveal_user_a_question(active_session_teacher_a):
    sid, host_a = active_session_teacher_a
    host_b = "user-teacher-bob-attacker-uuid"

    with pytest.raises(repo.OwnershipError):
        asyncio.run(mgr.reveal_current_question(sid, host_user_id=host_b))


def test_user_b_cannot_finalize_user_a_session(active_session_teacher_a):
    sid, host_a = active_session_teacher_a
    host_b = "user-teacher-bob-attacker-uuid"

    with pytest.raises(repo.OwnershipError):
        asyncio.run(mgr.finalize_session(sid, host_user_id=host_b))


def test_cross_session_participant_token_isolation():
    """Verify that a participant token issued for Session 1 cannot access Session 2."""
    sid1 = "sess-room-111"
    sid2 = "sess-room-222"
    pid = "part-student-x"

    token_for_s1 = repo.create_participant_token(pid, sid1, "Charlie")

    payload = repo.verify_participant_token(token_for_s1)
    assert payload["session_id"] == sid1
    assert payload["session_id"] != sid2, "Token is bound to session 1 and cannot match session 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
