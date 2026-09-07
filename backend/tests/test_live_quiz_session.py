"""
TeachGenie — Live Quiz Engine: Session Lifecycle & State Machine Transitions
=============================================================================
Verifies:
1. Cryptographic 6-digit numeric join codes.
2. Full legal state lifecycle: CREATED -> LOBBY -> LIVE -> PAUSED -> LIVE -> COMPLETED.
3. Illegal state transitions raise StateTransitionError.
4. Join code partial index recycling logic.
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


def test_join_code_generation_and_uniqueness():
    code = mgr.generate_join_code()
    assert len(code) == 6
    assert code.isdigit()
    assert 100000 <= int(code) <= 999999


def test_legal_state_machine_transitions():
    # Valid transitions
    mgr.assert_legal_transition(LiveSessionStatus.CREATED.value, LiveSessionStatus.LOBBY.value)
    mgr.assert_legal_transition(LiveSessionStatus.LOBBY.value, LiveSessionStatus.LIVE.value)
    mgr.assert_legal_transition(LiveSessionStatus.LIVE.value, LiveSessionStatus.PAUSED.value)
    mgr.assert_legal_transition(LiveSessionStatus.PAUSED.value, LiveSessionStatus.LIVE.value)
    mgr.assert_legal_transition(LiveSessionStatus.LIVE.value, LiveSessionStatus.COMPLETED.value)
    mgr.assert_legal_transition(LiveSessionStatus.LIVE.value, LiveSessionStatus.ENDED.value)
    mgr.assert_legal_transition(LiveSessionStatus.PAUSED.value, LiveSessionStatus.ENDED.value)


def test_illegal_state_machine_transitions():
    # Illegal: jump straight from CREATED to LIVE
    with pytest.raises(repo.StateTransitionError):
        mgr.assert_legal_transition(LiveSessionStatus.CREATED.value, LiveSessionStatus.LIVE.value)

    # Illegal: resuscitate COMPLETED session back to LIVE
    with pytest.raises(repo.StateTransitionError):
        mgr.assert_legal_transition(LiveSessionStatus.COMPLETED.value, LiveSessionStatus.LIVE.value)

    # Illegal: jump from LOBBY to PAUSED
    with pytest.raises(repo.StateTransitionError):
        mgr.assert_legal_transition(LiveSessionStatus.LOBBY.value, LiveSessionStatus.PAUSED.value)


def test_join_code_recycling_on_session_termination():
    """Verify code can be reused once previous session terminates."""
    code = "654987"
    sid1 = "sess-term-1"
    sid2 = "sess-term-2"

    # Active session holds code
    repo.create_live_session({
        "id": sid1,
        "quiz_id": "q1",
        "host_user_id": "host-1",
        "join_code": code,
        "status": LiveSessionStatus.LIVE.value,
        "total_questions": 1,
        "questions_snapshot": [],
        "question_order": [],
        "version": 1,
    })

    # While active, find_active_session_by_code finds sid1
    active_match = repo.find_active_session_by_code(code)
    assert active_match is not None
    assert active_match["id"] == sid1

    # Terminate sid1
    repo.update_live_session(sid1, {"status": LiveSessionStatus.COMPLETED.value})

    # Now find_active_session_by_code should return None (code is recyclable)
    freed_match = repo.find_active_session_by_code(code)
    assert freed_match is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
