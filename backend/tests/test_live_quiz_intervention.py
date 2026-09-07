"""
TeachGenie — Live Quiz Engine: Deterministic-Visual-First Remedial Intervention Tests
=====================================================================================
Verifies that:
1. 'visual' intervention is 100% deterministic (0 token cost, ZERO LLM calls).
2. Generates SVG flowchart markup and concept contrast card directly.
3. LLM calls DO NOT fire automatically on low accuracy or question reveal.
4. LLM only fires when teacher explicitly calls action_type in ['explain', 'example', 'followup'].
5. Scoped LLM prompt receives the class's most selected wrong distractor to dispel specific misconception.
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
from app.services.live_quiz import intervention as interv_svc
from app.services.live_quiz.schemas import LiveSessionStatus, LiveEventType


@pytest.fixture
def session_with_misconception():
    sid = "sess-interv-test-1"
    host_id = "teacher-jane"

    q = {
        "id": "q-photo",
        "question_text": "What is the primary product of photosynthesis?",
        "options": ["Glucose", "Carbon Dioxide", "Nitrogen", "Methane"],
        "correct_answer": "Glucose",
        "explanation": "Photosynthesis converts light energy into chemical energy stored in glucose.",
        "concept_id": "photosynthesis",
    }
    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-bio-1",
        "host_user_id": host_id,
        "join_code": "665544",
        "status": LiveSessionStatus.LIVE.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [q],
        "question_order": ["q-photo"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": True},
        "version": 1,
    })

    # Record responses: 1 correct (Glucose), 3 wrong on Carbon Dioxide (top distractor)
    repo.record_response({
        "id": "r1",
        "session_id": sid,
        "participant_id": "p1",
        "question_id": "q-photo",
        "selected_option_id": "Glucose",
        "is_correct": True,
        "points": 1000,
    })
    repo.record_response({
        "id": "r2",
        "session_id": sid,
        "participant_id": "p2",
        "question_id": "q-photo",
        "selected_option_id": "Carbon Dioxide",
        "is_correct": False,
        "points": 0,
    })
    repo.record_response({
        "id": "r3",
        "session_id": sid,
        "participant_id": "p3",
        "question_id": "q-photo",
        "selected_option_id": "Carbon Dioxide",
        "is_correct": False,
        "points": 0,
    })
    repo.record_response({
        "id": "r4",
        "session_id": sid,
        "participant_id": "p4",
        "question_id": "q-photo",
        "selected_option_id": "Carbon Dioxide",
        "is_correct": False,
        "points": 0,
    })
    return sid


import asyncio


def test_visual_intervention_zero_tokens_zero_llm(session_with_misconception):
    """Assert visual intervention generates SVG flowchart with 0 tokens and NO LLM call."""
    sid = session_with_misconception

    with patch("app.services.live_quiz.intervention.ai_router.generate_text", new_callable=AsyncMock) as mock_llm:
        res = asyncio.run(interv_svc.generate_live_intervention(
            session_id=sid,
            action_type="visual",
            question_id="q-photo",
        ))

        # 1. LLM was NEVER called
        mock_llm.assert_not_called()

        # 2. Token cost is explicitly 0
        assert res["token_cost"] == 0
        assert res["type"] == "visual"
        assert res["concept"] == "photosynthesis"

        # 3. SVG is generated
        assert "<svg" in res["svg"]
        assert "</svg>" in res["svg"]

        # 4. Comparison card captures concept contrast & top misconception distractor
        comp = res["comparison"]
        assert comp["correct_concept"]["text"] == "Glucose"
        assert comp["common_misconception"]["text"] == "Carbon Dioxide"


def test_llm_fires_only_on_explicit_teacher_action(session_with_misconception):
    """Verify LLM is only called when teacher explicitly chooses 'explain', with distractor injected."""
    sid = session_with_misconception

    mock_llm_return = AsyncMock()
    mock_llm_return.text = "Photosynthesis creates glucose as food. Carbon dioxide is an input, not a product!"
    mock_llm_return.tokens_prompt = 45
    mock_llm_return.tokens_completion = 22

    with patch("app.services.live_quiz.intervention.ai_router.generate_text", new_callable=AsyncMock, return_value=mock_llm_return) as mock_llm:
        res = asyncio.run(interv_svc.generate_live_intervention(
            session_id=sid,
            action_type="explain",
            question_id="q-photo",
        ))

        # 1. Exactly one LLM call occurred
        assert mock_llm.call_count == 1

        # 2. Distractor was injected into prompt
        call_kwargs = mock_llm.call_args[1]
        user_msg = call_kwargs["messages"][1]["content"]
        assert "Carbon Dioxide" in user_msg, "Top wrong distractor must be present in prompt"
        assert "Glucose" in user_msg, "Correct answer must be present in prompt"

        # 3. Return payload structure
        assert res["type"] == "explain"
        assert res["token_cost"] == 67
        assert "Carbon dioxide is an input" in res["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
