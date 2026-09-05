"""
Orchestrator Agent — Test Suite
=================================
8 test cases covering:
  - All 4 intent categories (doubt, content_request, progress_check, general_chat)
  - Ambiguous/clarify intent (low confidence threshold)
  - Retry-then-fallback on malformed LLM JSON
  - Retry-then-fallback on LLM exception (call_gemini raises)
  - Routing correctness (routed_to matches intent)

All tests mock `call_gemini` so they run offline without API keys.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.agents.orchestrator import (
    classify_and_route,
    OrchestratorOutput,
    _parse_and_validate,
    _fallback_clarify,
    VALID_INTENTS,
    VALID_ROUTES,
    INTENT_ROUTE_MAP,
)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER — run async tests
# ══════════════════════════════════════════════════════════════════════════════

def run(coro):
    """Run an async coroutine synchronously for pytest."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: doubt intent → routed_to tutor_agent
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_doubt_intent(mock_llm):
    """A clear conceptual question should classify as 'doubt' and route to tutor_agent."""
    mock_llm.return_value = json.dumps({
        "intent": "doubt",
        "topic": "TCP three-way handshake",
        "confidence": 0.95,
        "routed_to": "tutor_agent",
        "direct_reply": None,
        "content_subtype": None,
    })

    result = run(classify_and_route("I don't understand how TCP three-way handshake works"))

    assert isinstance(result, OrchestratorOutput)
    assert result.intent == "doubt"
    assert result.topic == "TCP three-way handshake"
    assert result.confidence >= 0.5
    assert result.routed_to == "tutor_agent"
    assert result.direct_reply is None
    mock_llm.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: content_request intent → routed_to content_creator_agent
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_content_request_intent(mock_llm):
    """An explicit request for PPT/summary/flashcards should classify as 'content_request'."""
    mock_llm.return_value = json.dumps({
        "intent": "content_request",
        "topic": "database normalization",
        "confidence": 0.97,
        "routed_to": "content_creator_agent",
        "direct_reply": None,
        "content_subtype": "ppt",
    })

    result = run(classify_and_route("Make me a 10-slide PPT on database normalization"))

    assert result.intent == "content_request"
    assert result.topic == "database normalization"
    assert result.routed_to == "content_creator_agent"
    assert result.confidence >= 0.5
    assert result.content_subtype == "ppt"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: progress_check intent → routed_to study_planner_agent (label only)
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_progress_check_intent(mock_llm):
    """A performance/history question should classify as 'progress_check'.
    routed_to must be 'study_planner_agent' as a STRING LABEL only —
    no actual import or call to any study planner module should exist."""
    mock_llm.return_value = json.dumps({
        "intent": "progress_check",
        "topic": None,
        "confidence": 0.92,
        "routed_to": "study_planner_agent",
        "direct_reply": None,
        "content_subtype": None,
    })

    result = run(classify_and_route("How many questions did I answer correctly this week?"))

    assert result.intent == "progress_check"
    assert result.routed_to == "study_planner_agent"
    # Verify it's just a string — no module reference, no callable
    assert isinstance(result.routed_to, str)
    assert result.direct_reply is None


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: general_chat intent → routed_to direct_reply with a reply
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_general_chat_intent(mock_llm):
    """Greetings/small talk should classify as 'general_chat' with a direct_reply."""
    mock_llm.return_value = json.dumps({
        "intent": "general_chat",
        "topic": None,
        "confidence": 0.98,
        "routed_to": "direct_reply",
        "direct_reply": "Good morning! Ready to help you study today!",
        "content_subtype": None,
    })

    result = run(classify_and_route("Hey, good morning! How are you?"))

    assert result.intent == "general_chat"
    assert result.routed_to == "direct_reply"
    assert result.direct_reply is not None
    assert len(result.direct_reply) > 0


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: Ambiguous message → clarify intent (low confidence triggers threshold)
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_ambiguous_triggers_clarify(mock_llm):
    """When the LLM returns low confidence (< 0.5), the orchestrator should
    override the intent to 'clarify' regardless of what the LLM picked."""
    mock_llm.return_value = json.dumps({
        "intent": "doubt",  # LLM guessed doubt, but confidence is too low
        "topic": None,
        "confidence": 0.35,
        "routed_to": "tutor_agent",
        "direct_reply": None,
        "content_subtype": None,
    })

    result = run(classify_and_route("Can you help me with that thing we discussed?"))

    assert result.intent == "clarify", "Low confidence should force intent to 'clarify'"
    assert result.routed_to == "direct_reply"
    assert result.direct_reply is not None
    assert result.confidence < 0.5


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: Malformed LLM JSON on attempt 1, valid on attempt 2 (retry path)
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_malformed_json_retry_succeeds(mock_llm):
    """If the LLM returns invalid JSON on the first attempt, the orchestrator
    should retry with a stricter prompt. If attempt 2 succeeds, use that result."""
    # First call: garbled output (not valid JSON at all)
    # Second call: valid JSON
    mock_llm.side_effect = [
        "Sure! I think the intent is doubt about TCP... here is my analysis:",  # NOT JSON
        json.dumps({
            "intent": "doubt",
            "topic": "TCP",
            "confidence": 0.88,
            "routed_to": "tutor_agent",
            "direct_reply": None,
            "content_subtype": None,
        }),
    ]

    result = run(classify_and_route("Explain TCP to me"))

    assert result.intent == "doubt"
    assert result.routed_to == "tutor_agent"
    assert mock_llm.call_count == 2, "Should have retried after first failure"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: LLM raises exception on BOTH attempts → fallback to clarify
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_llm_exception_fallback_to_clarify(mock_llm):
    """If call_gemini raises an exception on BOTH the standard and strict
    attempts, the orchestrator must NOT crash — it should return a safe
    'clarify' fallback response."""
    mock_llm.side_effect = Exception("Connection timeout while contacting LLM service")

    result = run(classify_and_route("What is polymorphism in Java?"))

    assert isinstance(result, OrchestratorOutput)
    assert result.intent == "clarify"
    assert result.routed_to == "direct_reply"
    assert result.confidence == 0.0
    assert result.direct_reply is not None
    assert mock_llm.call_count == 2, "Should have attempted both standard and strict calls"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: Malformed JSON on BOTH attempts → fallback to clarify (not crash)
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_double_malformed_json_fallback(mock_llm):
    """If the LLM returns unparseable garbage on BOTH attempts, the
    orchestrator must gracefully fall back to clarify — not raise an exception."""
    mock_llm.side_effect = [
        "I am not sure what JSON format you want, here is my best guess <broken>",
        "```\nstill not valid json {{{{\n```",
    ]

    result = run(classify_and_route("help"))

    assert isinstance(result, OrchestratorOutput)
    assert result.intent == "clarify"
    assert result.routed_to == "direct_reply"
    assert result.confidence == 0.0
    assert result.direct_reply is not None


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 (bonus): Verify INTENT_ROUTE_MAP covers all valid intents
# ══════════════════════════════════════════════════════════════════════════════

def test_route_map_coverage():
    """Every valid intent must have a corresponding routing target in INTENT_ROUTE_MAP."""
    for intent in VALID_INTENTS:
        assert intent in INTENT_ROUTE_MAP, f"Missing route mapping for intent '{intent}'"
        assert INTENT_ROUTE_MAP[intent] in VALID_ROUTES, f"Invalid route for intent '{intent}'"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10 (bonus): Empty input returns clarify without calling LLM
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_empty_input_returns_clarify(mock_llm):
    """An empty or whitespace-only input should return clarify immediately
    without even calling the LLM."""
    result = run(classify_and_route("   "))

    assert result.intent == "clarify"
    assert result.routed_to == "direct_reply"
    mock_llm.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: content_request intent with explicit video subtype
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_content_request_video(mock_llm):
    """Explicit request for a video should set content_subtype='video'."""
    mock_llm.return_value = json.dumps({
        "intent": "content_request",
        "topic": "photosynthesis",
        "confidence": 0.95,
        "routed_to": "content_creator_agent",
        "direct_reply": None,
        "content_subtype": "video",
    })

    result = run(classify_and_route("make me a video on photosynthesis"))

    assert result.intent == "content_request"
    assert result.content_subtype == "video"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12: content_request intent with explicit flashcards subtype
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_content_request_flashcards(mock_llm):
    """Explicit request for flashcards should set content_subtype='flashcards'."""
    mock_llm.return_value = json.dumps({
        "intent": "content_request",
        "topic": "history of rome",
        "confidence": 0.95,
        "routed_to": "content_creator_agent",
        "direct_reply": None,
        "content_subtype": "flashcards",
    })

    result = run(classify_and_route("give me flashcards for history of rome"))

    assert result.intent == "content_request"
    assert result.content_subtype == "flashcards"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 13: content_request intent with ambiguous format defaults to unknown
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_content_request_ambiguous_format(mock_llm):
    """Ambiguous format should result in content_subtype='unknown'."""
    mock_llm.return_value = json.dumps({
        "intent": "content_request",
        "topic": "history of rome",
        "confidence": 0.95,
        "routed_to": "content_creator_agent",
        "direct_reply": None,
        "content_subtype": "unknown",
    })

    result = run(classify_and_route("create some study material on history of rome"))

    assert result.intent == "content_request"
    assert result.content_subtype == "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 14: invalid content_subtype normalizes to unknown
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.orchestrator.call_gemini", new_callable=AsyncMock)
def test_content_request_invalid_subtype(mock_llm):
    """If the LLM hallucinates a subtype like 'pdf', it should normalize to 'unknown'."""
    mock_llm.return_value = json.dumps({
        "intent": "content_request",
        "topic": "history of rome",
        "confidence": 0.95,
        "routed_to": "content_creator_agent",
        "direct_reply": None,
        "content_subtype": "pdf",
    })

    result = run(classify_and_route("generate a pdf on history of rome"))

    assert result.intent == "content_request"
    assert result.content_subtype == "unknown"



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
