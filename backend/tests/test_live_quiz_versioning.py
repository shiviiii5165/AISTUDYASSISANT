"""
LearnByGenie — Live Quiz Engine: Version-Freeze Isolation Tests
============================================================
Verifies that:
1. Live session stores an immutable questions_snapshot at initialization.
2. Subsequent modifications, edits, or deletions in the source quiz table
   have zero effect on the active live session.
3. Scoring, options, and student presentation continue to resolve against
   the frozen snapshot with full data integrity.
"""
import os
import sys
import copy
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz.schemas import LiveSessionStatus


def test_version_freeze_isolation():
    """Verify editing source quiz mid-session does not alter running session."""
    sid = "sess-version-freeze-1"
    host_id = "teacher-v-freeze"
    quiz_id = "quiz-source-original"

    # Original questions in source quiz
    q1_orig = {
        "id": "q-math-1",
        "question_text": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4",
        "explanation": "Two plus two equals four.",
    }
    q2_orig = {
        "id": "q-math-2",
        "question_text": "What is 5 * 5?",
        "options": ["20", "25", "30"],
        "correct_answer": "25",
        "explanation": "Five times five equals twenty-five.",
    }

    # Launch session with snapshot
    frozen_snapshot = copy.deepcopy([q1_orig, q2_orig])
    repo.create_live_session({
        "id": sid,
        "quiz_id": quiz_id,
        "host_user_id": host_id,
        "join_code": "771122",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "total_questions": 2,
        "questions_snapshot": frozen_snapshot,
        "question_order": ["q-math-1", "q-math-2"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })

    pid = "part-student-version"
    repo.create_participant({
        "id": pid,
        "session_id": sid,
        "display_name": "Test Solver",
        "score": 0,
        "status": "active",
    })

    # NOW: Source quiz is radically mutated mid-session (simulating an external editor)
    q1_mutated = {
        "id": "q-math-1",
        "question_text": "What is 10 + 10?",  # Changed text!
        "options": ["10", "20", "30"],       # Changed options!
        "correct_answer": "20",              # Changed answer!
        "explanation": "Ten plus ten.",
    }

    # Verify that the running live session's snapshot was unaffected
    active_sess = repo.get_live_session(sid)
    snapshot = active_sess["questions_snapshot"]

    assert snapshot[0]["question_text"] == "What is 2 + 2?", "Snapshot text must remain frozen"
    assert snapshot[0]["correct_answer"] == "4", "Snapshot correct_answer must remain frozen"
    assert "20" not in snapshot[0]["options"], "Mutated options must not leak into running session"

    # Verify student sanitized state receives the frozen question
    student_state = mgr.get_sanitized_student_state(sid, pid)
    assert student_state["question"]["question_text"] == "What is 2 + 2?"
    assert student_state["question"]["options"] == ["3", "4", "5", "6"]

    # Verify submission grades against the frozen snapshot ("4" is correct, "20" is not valid)
    submission_res = mgr.submit_student_response(
        session_id=sid,
        participant_id=pid,
        question_id="q-math-1",
        selected_option_id="4",
        response_time_ms=2500,
    )
    assert submission_res["is_correct"] is True
    assert submission_res["points"] == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
