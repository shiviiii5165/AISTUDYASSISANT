"""
LearnByGenie — Live Quiz Engine: Mastery Engine & Lesson Planner Roadmap Sync Tests
=================================================================================
Verifies that:
1. sync_session_with_mastery_and_roadmap processes real class assessment outcomes.
2. Bayesian mastery calculations update concept scores and confidence based on live results.
3. RoadmapStage mastery synchronization connects properly, flagging NEEDS_REVIEW if accuracy < 70%.
4. Downstream suggested actions (Remedial Lesson, Revision Quiz, Teach Me, PPT) are emitted.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-must-be-at-least-32-chars-long!")

from app.services.live_quiz import repository as repo
from app.services.live_quiz.integrations import sync_session_with_mastery_and_roadmap
from app.services.live_quiz.schemas import LiveSessionStatus


import asyncio


def test_mastery_engine_sync_updates_concepts():
    """Verify live quiz concept accuracies update Bayesian mastery engine profiles."""
    sid = "sess-mastery-sync-1"
    host_id = "teacher-mastery-user"

    q1 = {
        "id": "q1",
        "question_text": "Calculate acceleration given force and mass.",
        "options": ["F/m", "m/F", "F*m", "m^2/F"],
        "correct_answer": "F/m",
        "concept_id": "newtons_second_law",
    }
    q2 = {
        "id": "q2",
        "question_text": "What is kinetic energy?",
        "options": ["1/2 m v^2", "m g h", "F d", "1/2 k x^2"],
        "correct_answer": "1/2 m v^2",
        "concept_id": "kinetic_energy",
    }

    repo.create_live_session({
        "id": sid,
        "quiz_id": "quiz-mastery-1",
        "host_user_id": host_id,
        "join_code": "445566",
        "status": LiveSessionStatus.COMPLETED.value,
        "current_question_index": 1,
        "total_questions": 2,
        "questions_snapshot": [q1, q2],
        "question_order": ["q1", "q2"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": True},
        "version": 2,
    })

    # Record responses:
    # 2 responses on newtons_second_law: both wrong -> 0% accuracy
    repo.record_response({
        "id": "r1",
        "session_id": sid,
        "participant_id": "p1",
        "question_id": "q1",
        "selected_option_id": "m/F",
        "is_correct": False,
        "points": 0,
        "concept_id": "newtons_second_law",
    })
    repo.record_response({
        "id": "r2",
        "session_id": sid,
        "participant_id": "p2",
        "question_id": "q1",
        "selected_option_id": "F*m",
        "is_correct": False,
        "points": 0,
        "concept_id": "newtons_second_law",
    })

    # 2 responses on kinetic_energy: both correct -> 100% accuracy
    repo.record_response({
        "id": "r3",
        "session_id": sid,
        "participant_id": "p1",
        "question_id": "q2",
        "selected_option_id": "1/2 m v^2",
        "is_correct": True,
        "points": 1000,
        "concept_id": "kinetic_energy",
    })
    repo.record_response({
        "id": "r4",
        "session_id": sid,
        "participant_id": "p2",
        "question_id": "q2",
        "selected_option_id": "1/2 m v^2",
        "is_correct": True,
        "points": 1000,
        "concept_id": "kinetic_energy",
    })

    result = asyncio.run(sync_session_with_mastery_and_roadmap(sid))

    assert result["status"] == "synced"
    mastery_updates = result.get("mastery_updates", [])
    assert len(mastery_updates) == 2

    # Check newtons_second_law
    newton = next(m for m in mastery_updates if m["concept_id"] == "newtons_second_law")
    assert newton["accuracy_pct"] == 0.0
    # Score should drop below initial 0.5
    assert newton["new_mastery_score"] < 0.50

    # Check kinetic_energy
    ke = next(m for m in mastery_updates if m["concept_id"] == "kinetic_energy")
    assert ke["accuracy_pct"] == 100.0
    # Score should rise above initial 0.5
    assert ke["new_mastery_score"] > 0.50

    # Check suggested actions
    actions = result.get("suggested_actions", [])
    assert any(a["id"] == "remedial_lesson" for a in actions)
    assert any(a["id"] == "revision_quiz" for a in actions)
    assert any(a["id"] == "teach_me" for a in actions)
    assert any(a["id"] == "presentation" for a in actions)


def test_roadmap_stage_sync_marks_needs_review_when_low_accuracy():
    """Verify low session accuracy triggers NEEDS_REVIEW on associated RoadmapStage."""
    sid = "sess-roadmap-sync-stage"
    host_id = "teacher-roadmap-user"
    quiz_id = "quiz-with-stage-123"

    repo.create_live_session({
        "id": sid,
        "quiz_id": quiz_id,
        "host_user_id": host_id,
        "join_code": "887766",
        "status": LiveSessionStatus.COMPLETED.value,
        "current_question_index": 0,
        "total_questions": 1,
        "questions_snapshot": [{"id": "q1", "correct_answer": "A", "concept_id": "algebra"}],
        "question_order": ["q1"],
        "timer_config": {"enabled": True, "seconds": 30, "speed_bonus": False},
        "settings": {"question_revealed": True},
        "version": 1,
    })

    # Response is incorrect -> 0% overall accuracy
    repo.record_response({
        "id": "r-fail",
        "session_id": sid,
        "participant_id": "p-fail",
        "question_id": "q1",
        "selected_option_id": "B",
        "is_correct": False,
        "points": 0,
        "concept_id": "algebra",
    })

    # Mock stage & roadmap loading
    mock_stage = MagicMock()
    mock_stage.id = "stage-xyz"
    mock_stage.mastery = 0
    mock_stage.status = MagicMock()
    mock_stage.status.value = "needs_review"

    mock_roadmap = MagicMock()
    mock_roadmap.stages = [mock_stage]

    with patch("app.services.quiz.repository.get_quiz_by_idempotency", return_value={"stage_id": "stage-xyz", "roadmap_id": "rm-123"}):
        with patch("app.api.lesson_planner._get_roadmap", return_value=mock_roadmap):
            with patch("app.api.lesson_planner._save_roadmap") as mock_save:
                with patch("app.services.lesson_planner.engine.StateMachineEngine.transition_stage") as mock_trans:
                    result = asyncio.run(sync_session_with_mastery_and_roadmap(sid))

                    assert result["status"] == "synced"
                    assert result["roadmap_sync"] is not None
                    assert result["roadmap_sync"]["new_stage_mastery"] == 0
                    assert mock_trans.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
