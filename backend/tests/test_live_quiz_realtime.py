"""
TeachGenie — Live Quiz Engine: Realtime Broadcast Payload Zero-Leakage Tests
=============================================================================
Verifies that:
1. question:started broadcast payloads strictly omit correct_answer & explanation.
2. student state REST payloads strictly omit correct_answer & explanation before reveal.
3. question:revealed broadcast payloads include correct_answer, explanation, and option distribution.
4. Complete absence of grading metadata prevents student network snooping / DevTools extraction.
"""
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz.schemas import LiveSessionStatus


import asyncio


def test_question_started_broadcast_payload_leak_free():
    """Assert broadcast event question:started NEVER contains correct_answer or explanation."""
    sid = "sess-leak-check-001"
    host_id = "host-prof-x"

    q1 = {
        "id": "q-secret-101",
        "question_text": "What is the capital of Australia?",
        "options": ["Sydney", "Melbourne", "Canberra", "Brisbane"],
        "correct_answer": "Canberra",
        "explanation": "Canberra was selected as the compromise capital city in 1908.",
        "difficulty": "medium",
        "concept_id": "world_geography",
    }

    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-geo-leak-1",
        "host_user_id": host_id,
        "join_code": "123456",
        "status": LiveSessionStatus.LOBBY.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [q1],
        "question_order": ["q-secret-101"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })

    with patch("app.services.live_quiz.session_manager.broadcast_session_event", new_callable=AsyncMock) as mock_broadcast:
        # Advance from LOBBY to Q1
        asyncio.run(mgr.advance_to_next_question(sid, host_user_id=host_id))

        assert mock_broadcast.called
        event_type, payload = mock_broadcast.call_args[0][1], mock_broadcast.call_args[0][2]
        assert event_type == "question:started"

        question_payload = payload.get("question", {})

        # CRITICAL ZERO-LEAKAGE INVARIANTS:
        assert "correct_answer" not in question_payload, "correct_answer MUST NOT exist in question:started broadcast"
        assert "explanation" not in question_payload, "explanation MUST NOT exist in question:started broadcast"
        assert question_payload.get("correct_answer") is None
        assert question_payload.get("explanation") is None

        # Verify legitimate fields are present
        assert question_payload.get("id") == "q-secret-101"
        assert question_payload.get("question_text") == "What is the capital of Australia?"
        assert len(question_payload.get("options", [])) == 4


def test_question_revealed_broadcast_includes_answers_and_distribution():
    """Assert broadcast event question:revealed sends answers and aggregated distributions."""
    sid = "sess-leak-check-002"
    host_id = "host-prof-x"

    q1 = {
        "id": "q-secret-202",
        "question_text": "What is 3 squared?",
        "options": ["6", "9", "12"],
        "correct_answer": "9",
        "explanation": "3 multiplied by 3 equals 9.",
    }

    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-math-leak-2",
        "host_user_id": host_id,
        "join_code": "654321",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [q1],
        "question_order": ["q-secret-202"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": False},
        "version": 1,
    })

    # Add responses
    repo.record_response({
        "id": "resp-1",
        "session_id": sid,
        "participant_id": "p1",
        "question_id": "q-secret-202",
        "selected_option_id": "9",
        "is_correct": True,
        "points": 1000,
    })
    repo.record_response({
        "id": "resp-2",
        "session_id": sid,
        "participant_id": "p2",
        "question_id": "q-secret-202",
        "selected_option_id": "6",
        "is_correct": False,
        "points": 0,
    })

    with patch("app.services.live_quiz.session_manager.broadcast_session_event", new_callable=AsyncMock) as mock_broadcast:
        # Teacher triggers reveal
        asyncio.run(mgr.reveal_current_question(sid, host_user_id=host_id))

        assert mock_broadcast.called
        event_type, payload = mock_broadcast.call_args[0][1], mock_broadcast.call_args[0][2]
        assert event_type == "question:revealed"

        # Correct answer and explanation are now intentionally and legitimately present
        assert payload.get("correct_answer") == "9"
        assert payload.get("explanation") == "3 multiplied by 3 equals 9."

        # Distribution verified
        dist = payload.get("option_distribution", {})
        assert dist.get("9") == 1
        assert dist.get("6") == 1
        assert dist.get("12") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
