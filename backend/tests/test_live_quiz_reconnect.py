"""
LearnByGenie — Live Quiz Engine: Reconnect Mid-Question & Duplicate Scoring Guards
================================================================================
Verifies that:
1. Participant can disconnect mid-question and reconnect seamlessly with JWT token.
2. State restoration: reconnected participant retrieves active question, remaining time,
   and previous submission state without loss of streak or score.
3. Mid-question resubmission / duplicate response attempts are idempotent:
   - Zero duplicate points awarded.
   - Database UNIQUE constraint (session_id, participant_id, question_id) honored.
   - Original response timestamp and choice preserved.
"""
import os
import sys
import pytest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz.schemas import LiveSessionStatus


def test_reconnect_mid_question_preserves_state():
    """Verify participant reconnects mid-question and recovers existing state."""
    sid = "sess-reconnect-1"
    host_id = "host-user-101"
    pid = "part-student-reconnect"

    # 1. Setup active session
    q1 = {
        "id": "q1",
        "question_text": "What is the speed of light in vacuum?",
        "options": ["300,000 km/s", "150,000 km/s", "1,000 km/s", "Sound speed"],
        "correct_answer": "300,000 km/s",
        "explanation": "Approximately 299,792 km/s.",
    }
    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-phys-1",
        "host_user_id": host_id,
        "join_code": "334455",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "current_question_started_at": datetime.now(timezone.utc).isoformat(),
        "current_question_deadline": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
        "total_questions": 1,
        "questions_snapshot": [q1],
        "question_order": ["q1"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": True},
        "settings": {"question_revealed": False},
        "version": 1,
    })

    # 2. Participant joins
    part = repo.create_participant({
        "id": pid,
        "session_id": sid,
        "display_name": "Nova Runner",
        "score": 1000,
        "correct_count": 1,
        "streak": 1,
        "status": "active",
    })
    token = repo.create_participant_token(pid, sid, "Nova Runner")

    # 3. Participant submits answer
    resp_res = mgr.submit_student_response(
        session_id=sid,
        participant_id=pid,
        question_id="q1",
        selected_option_id="300,000 km/s",
        response_time_ms=2100,
    )
    assert resp_res["is_correct"] is True


    # 4. Disconnect happens (simulated)
    repo.update_participant(pid, {"status": "disconnected"})
    disc_part = repo.get_participant(pid)
    assert disc_part["status"] == "disconnected"

    # 5. Participant reconnects using their token
    claims = repo.verify_participant_token(token)
    assert claims["sub"] == pid

    repo.update_participant(pid, {"status": "active"})
    reconnected_state = mgr.get_sanitized_student_state(sid, pid)

    # Asserts state restoration
    assert reconnected_state["has_submitted"] is True
    assert reconnected_state["selected_option_id"] == "300,000 km/s"
    assert reconnected_state["participant"]["score"] >= 2400
    assert reconnected_state["participant"]["streak"] == 2
    assert reconnected_state["is_revealed"] is False


def test_reconnect_duplicate_submission_no_double_scoring():
    """Verify that submitting again after reconnect returns the recorded response without duplicate points."""
    sid = "sess-reconnect-dup"
    host_id = "host-user-102"
    pid = "part-student-dup"

    q = {
        "id": "q1",
        "question_text": "Capital of Japan?",
        "options": ["Tokyo", "Kyoto", "Osaka"],
        "correct_answer": "Tokyo",
    }
    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-geo-1",
        "host_user_id": host_id,
        "join_code": "556677",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [q],
        "question_order": ["q1"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })

    repo.create_participant({
        "id": pid,
        "session_id": sid,
        "display_name": "Echo Student",
        "score": 0,
        "correct_count": 0,
        "streak": 0,
        "status": "active",
    })

    # First submission
    first_res = mgr.submit_student_response(
        session_id=sid,
        participant_id=pid,
        question_id="q1",
        selected_option_id="Tokyo",
        response_time_ms=3000,
    )
    assert first_res["is_correct"] is True
    assert first_res["points"] == 1000

    part_after_first = repo.get_participant(pid)
    assert part_after_first["score"] == 1000

    # Simulate disconnect and reconnect
    repo.update_participant(pid, {"status": "disconnected"})
    repo.update_participant(pid, {"status": "active"})

    # Second submission attempt with DIFFERENT option to test cheating / overwrite prevention
    second_res = mgr.submit_student_response(
        session_id=sid,
        participant_id=pid,
        question_id="q1",
        selected_option_id="Kyoto",
        response_time_ms=5000,
    )

    # Verify duplicate was rejected and original was returned
    assert second_res["id"] == first_res["id"]
    assert second_res["selected_option_id"] == "Tokyo"

    # Verify participant score was NOT incremented again
    part_after_dup = repo.get_participant(pid)
    assert part_after_dup["score"] == 1000, "Score must not double count"
    assert part_after_dup["streak"] == 1, "Streak must not increment twice"

    # Verify only ONE response exists for this question
    responses = repo.get_responses_for_session(sid)
    user_q_responses = [r for r in responses if r["participant_id"] == pid and r["question_id"] == "q1"]
    assert len(user_q_responses) == 1, "Exactly one response must exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
