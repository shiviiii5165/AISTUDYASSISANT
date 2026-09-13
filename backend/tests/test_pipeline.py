import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.agents.pipeline import handle_student_message, PipelineOutput
from app.agents.orchestrator import OrchestratorOutput
from app.agents.librarian import LibrarianOutput
from app.agents.tutor import TutorTurn
from app.agents.content_creator import ContentCreatorOutput, ContentType


def run(coro):
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: Doubt flow success
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.tutor_turn", new_callable=AsyncMock)
def test_doubt_flow_success(mock_tutor, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="doubt", topic="gravity", confidence=0.9, routed_to="tutor_agent", direct_reply=None
    )
    mock_librarian.return_value = LibrarianOutput(
        context=[], related_context=[], sufficient=True, used_web_fallback=False
    )
    mock_tutor.return_value = TutorTurn(
        message="Here is a hint.", is_topic_complete=False, understanding_level="struggling", concepts_struggled=["gravity"]
    )

    result = run(handle_student_message("user_1", "What is gravity?"))

    assert result.response_type == "tutor_turn"
    assert result.tutor_data is not None
    assert result.tutor_data.message == "Here is a hint."
    assert result.intent == "doubt"
    
    mock_orch.assert_called_once()
    mock_librarian.assert_called_once()
    mock_tutor.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: Content request success
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.create_content", new_callable=AsyncMock)
def test_content_request_success(mock_create, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="content_request", topic="gravity", confidence=0.9, routed_to="content_creator_agent", 
        direct_reply=None, content_subtype="ppt"
    )
    mock_librarian.return_value = LibrarianOutput(
        context=[], related_context=[], sufficient=True, used_web_fallback=False
    )
    mock_create.return_value = ContentCreatorOutput(
        job_id="job123", content_type=ContentType.PPT, status="processing"
    )

    result = run(handle_student_message("user_1", "Make a PPT on gravity"))

    assert result.response_type == "content"
    assert result.content_data is not None
    assert result.content_data.job_id == "job123"
    assert result.intent == "content_request"
    
    mock_orch.assert_called_once()
    mock_librarian.assert_called_once()
    mock_create.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: Progress check
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
def test_progress_check_placeholder(mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="progress_check", topic=None, confidence=0.9, routed_to="study_planner_agent", direct_reply=None
    )

    result = run(handle_student_message("user_1", "How am I doing?"))

    assert result.response_type == "direct_message"
    assert "coming soon" in result.message.lower()
    assert result.intent == "progress_check"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: General chat
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
def test_general_chat(mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="general_chat", topic=None, confidence=0.9, routed_to="direct_reply", direct_reply="Hi there!"
    )

    result = run(handle_student_message("user_1", "Hello"))

    assert result.response_type == "direct_message"
    assert result.message == "Hi there!"
    assert result.intent == "general_chat"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: Clarify
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
def test_clarify(mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="clarify", topic=None, confidence=0.9, routed_to="direct_reply", direct_reply="Can you explain?"
    )

    result = run(handle_student_message("user_1", "help"))

    assert result.response_type == "direct_message"
    assert result.message == "Can you explain?"
    assert result.intent == "clarify"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: Librarian throws exception (fallback to tutor without context)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.tutor_turn", new_callable=AsyncMock)
def test_librarian_exception_does_not_crash(mock_tutor, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="doubt", topic="gravity", confidence=0.9, routed_to="tutor_agent", direct_reply=None
    )
    mock_librarian.side_effect = Exception("DB Timeout")
    mock_tutor.return_value = TutorTurn(
        message="Tutor still works.", is_topic_complete=False, understanding_level="struggling", concepts_struggled=[]
    )

    result = run(handle_student_message("user_1", "What is gravity?"))

    assert result.response_type == "tutor_turn"
    assert result.tutor_data.message == "Tutor still works."
    mock_tutor.assert_called_once()
    
    # Assert the librarian context passed to tutor was empty, not None
    called_kwargs = mock_tutor.call_args.kwargs
    assert called_kwargs["librarian_context"] is not None
    assert called_kwargs["librarian_context"].context == []


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: Tutor throws exception (fallback message)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.tutor_turn", new_callable=AsyncMock)
def test_tutor_exception_does_not_crash(mock_tutor, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="doubt", topic="gravity", confidence=0.9, routed_to="tutor_agent", direct_reply=None
    )
    mock_librarian.return_value = LibrarianOutput(
        context=[], related_context=[], sufficient=True, used_web_fallback=False
    )
    mock_tutor.side_effect = Exception("LLM Timeout")

    result = run(handle_student_message("user_1", "What is gravity?"))

    assert result.response_type == "direct_message"
    assert "issue" in result.message.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: Content Creator throws exception (fallback message)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.create_content", new_callable=AsyncMock)
def test_content_creator_exception_does_not_crash(mock_create, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="content_request", topic="gravity", confidence=0.9, routed_to="content_creator_agent", 
        direct_reply=None, content_subtype="ppt"
    )
    mock_librarian.return_value = LibrarianOutput(
        context=[], related_context=[], sufficient=True, used_web_fallback=False
    )
    mock_create.side_effect = Exception("Service unavailable")

    result = run(handle_student_message("user_1", "Make a PPT"))

    assert result.response_type == "direct_message"
    assert "problem" in result.message.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: Orchestrator throws exception (fallback message)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
def test_orchestrator_exception_does_not_crash(mock_orch):
    mock_orch.side_effect = Exception("Out of memory")

    result = run(handle_student_message("user_1", "Hello"))

    assert result.response_type == "direct_message"
    assert "trouble understanding" in result.message.lower()
    assert result.intent == "error"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: Content-type sub-classification correctly drives flow
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.create_content", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
def test_content_subtype_drives_flow(mock_librarian, mock_create, mock_orch):
    # Test ambiguous unknown subtype
    mock_orch.return_value = OrchestratorOutput(
        intent="content_request", topic="gravity", confidence=0.9, routed_to="content_creator_agent", 
        direct_reply=None, content_subtype="unknown"
    )

    result = run(handle_student_message("user_1", "Create material"))

    assert result.response_type == "direct_message"
    assert "Which format" in result.message
    mock_create.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: Librarian returns empty context (flows correctly to Tutor)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.pipeline.classify_and_route", new_callable=AsyncMock)
@patch("app.agents.pipeline.retrieve_context", new_callable=AsyncMock)
@patch("app.agents.pipeline.tutor_turn", new_callable=AsyncMock)
def test_librarian_empty_context_flows_to_tutor(mock_tutor, mock_librarian, mock_orch):
    mock_orch.return_value = OrchestratorOutput(
        intent="doubt", topic="gravity", confidence=0.9, routed_to="tutor_agent", direct_reply=None
    )
    # Librarian returns sufficient=False and empty context
    mock_librarian.return_value = LibrarianOutput(
        context=[], related_context=[], sufficient=False, used_web_fallback=False
    )
    mock_tutor.return_value = TutorTurn(
        message="Let's learn.", is_topic_complete=False, understanding_level="struggling", concepts_struggled=[]
    )

    result = run(handle_student_message("user_1", "gravity"))

    assert result.response_type == "tutor_turn"
    mock_tutor.assert_called_once()
    called_kwargs = mock_tutor.call_args.kwargs
    assert called_kwargs["librarian_context"].sufficient is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12: End-to-end integration-style test (mocked at LLM boundary)
# ══════════════════════════════════════════════════════════════════════════════
@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
@patch("app.agents.librarian._get_user_document_ids", new_callable=AsyncMock)
@patch("app.agents.librarian.perform_web_search", new_callable=AsyncMock)
def test_end_to_end_doubt_flow(mock_web, mock_get_docs, mock_tutor_llm, mock_orch_llm):
    import json
    # Mock Orchestrator LLM
    mock_orch_llm.return_value = json.dumps({
        "intent": "doubt", "topic": "momentum", "confidence": 0.95, 
        "routed_to": "tutor_agent", "direct_reply": None, "content_subtype": None
    })
    
    # Return empty lists to skip DB/web calls
    mock_get_docs.return_value = []
    mock_web.return_value = []
    
    # Mock Tutor LLM
    mock_tutor_llm.return_value = json.dumps({
        "message": "What is the formula for momentum?", 
        "is_topic_complete": False,
        "understanding_level": "struggling", 
        "concepts_struggled": ["momentum formula"]
    })

    result = run(handle_student_message("user_1", "I don't get momentum."))

    assert result.response_type == "tutor_turn"
    assert result.intent == "doubt"
    assert result.tutor_data.message == "What is the formula for momentum?"
    assert result.tutor_data.understanding_level == "struggling"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
