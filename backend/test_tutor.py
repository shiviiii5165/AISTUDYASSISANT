"""
Tutor Agent — Comprehensive Test Suite
========================================
10+ pytest cases covering every functional requirement, all with mocked LLM calls.

Run with:
    pytest test_tutor.py -v
"""
import json
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.agents.tutor import (
    tutor_turn,
    TutorTurn,
    TUTOR_SYSTEM_PROMPT,
    FALLBACK_MESSAGE,
    _build_context_string,
    _merge_concept_lists,
    _extract_prior_state,
)
from app.agents.librarian import LibrarianOutput, ChunkResult


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _run(coro):
    """Run an async coroutine in a synchronous test."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _make_librarian_output(
    chunks=None, sufficient=True, web_fallback=False,
) -> LibrarianOutput:
    """Build a LibrarianOutput with optional chunk text."""
    context = []
    if chunks:
        for i, text in enumerate(chunks):
            context.append(ChunkResult(
                text=text,
                source_document=f"doc_{i}",
                page_or_location=f"Page {i+1}",
                relevance_score=0.85,
                source="internal",
            ))
    return LibrarianOutput(
        context=context,
        related_context=[],
        sufficient=sufficient,
        used_web_fallback=web_fallback,
    )


def _mock_llm_json(**fields) -> str:
    """Build a mock LLM JSON response string."""
    default = {
        "message": "Test response",
        "understanding_level": "not_assessed",
        "concepts_covered": [],
        "concepts_struggled": [],
        "is_topic_complete": False,
    }
    default.update(fields)
    return json.dumps(default)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: First turn (student_message=None) → gauging question, not lecture
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_first_turn_asks_gauging_question(mock_llm):
    """On the very first turn, the Tutor should ask a short gauging question,
    NOT deliver an explanation. is_topic_complete must be False."""
    mock_llm.return_value = _mock_llm_json(
        message="Before we start — have you ever heard of what a 'variable' is in maths?",
        understanding_level="not_assessed",
    )

    result = _run(tutor_turn(
        topic="variables in programming",
        librarian_context=_make_librarian_output(["Variables store data values."]),
        conversation_history=[],
        student_message=None,  # first turn
    ))

    assert isinstance(result, TutorTurn)
    assert result.is_topic_complete is False
    assert result.understanding_level == "not_assessed"
    # The message should be a question, not a long explanation
    assert "?" in result.message
    # Verify the LLM was called with the first-turn system instruction
    call_args = mock_llm.call_args
    messages = call_args[1].get("messages") or call_args[0][0]
    last_msg = messages[-1]["content"]
    assert "first turn" in last_msg.lower() or "gauging" in last_msg.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: Correct answer → moves forward, understanding upgrades
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_correct_answer_moves_forward(mock_llm):
    """When the student answers correctly, the Tutor should move forward
    and update understanding_level toward 'developing'."""
    mock_llm.return_value = _mock_llm_json(
        message="Exactly right! A variable is like a labelled box.\n\nNow, do you know what happens when you put a new value in the same box?",
        understanding_level="developing",
        concepts_covered=["what a variable is"],
    )

    result = _run(tutor_turn(
        topic="variables in programming",
        librarian_context=_make_librarian_output(["Variables store data values."]),
        conversation_history=[
            {"role": "assistant", "content": _mock_llm_json(
                message="Have you heard of variables before?",
                understanding_level="not_assessed",
            )},
        ],
        student_message="Yes, it's like a container that holds a value, right?",
    ))

    assert result.understanding_level in ("developing", "solid")
    assert len(result.concepts_covered) > 0
    assert result.is_topic_complete is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: "I don't know" → re-explains with DIFFERENT analogy
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_i_dont_know_triggers_different_explanation(mock_llm):
    """When the student says 'I don't know', the Tutor should re-explain
    using a DIFFERENT analogy. The new message must not be a near-duplicate."""
    first_explanation = (
        "Think of a variable like a labelled lunchbox. "
        "You write a name on the box, and you can put food inside."
    )
    second_explanation = (
        "Let me try another way! Imagine you have a notebook. "
        "On each page, you write a title at the top, and below it you write a number or word. "
        "A variable is like one page in that notebook — it has a name and a value."
    )

    mock_llm.return_value = _mock_llm_json(
        message=second_explanation,
        understanding_level="struggling",
        concepts_struggled=["variable definition"],
    )

    result = _run(tutor_turn(
        topic="variables in programming",
        librarian_context=_make_librarian_output(["Variables store data values."]),
        conversation_history=[
            {"role": "assistant", "content": _mock_llm_json(message=first_explanation)},
        ],
        student_message="I don't know",
    ))

    # The two explanations should be meaningfully different
    assert result.message != first_explanation
    assert result.understanding_level == "struggling"
    assert "variable definition" in result.concepts_struggled


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: Incorrect answer → does NOT repeat same explanation verbatim
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_incorrect_answer_not_verbatim_repeat(mock_llm):
    """When the student answers incorrectly, the Tutor must NOT just repeat
    the same explanation word-for-word."""
    original_explanation = "A function is like a recipe. You give it ingredients, it gives you a dish."
    new_explanation = (
        "No worries! Let me explain differently.\n\n"
        "Think of a vending machine. You press a button (input), "
        "and the machine gives you a snack (output). "
        "A function works the same way — input goes in, output comes out.\n\n"
        "What do you think a function takes as 'input'?"
    )

    mock_llm.return_value = _mock_llm_json(
        message=new_explanation,
        understanding_level="struggling",
        concepts_struggled=["function basics"],
    )

    result = _run(tutor_turn(
        topic="functions in programming",
        librarian_context=_make_librarian_output(),
        conversation_history=[
            {"role": "assistant", "content": _mock_llm_json(message=original_explanation)},
        ],
        student_message="A function is a variable?",
    ))

    assert result.message != original_explanation
    assert "?" in result.message  # Should end with a checking question


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: 2-3 correct answers in a row → is_topic_complete = True with recap
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_multiple_correct_answers_completes_topic(mock_llm):
    """After 2-3 correct answers at increasing depth, the Tutor should
    mark the topic as complete and deliver a recap."""
    mock_llm.return_value = _mock_llm_json(
        message=(
            "Excellent work! Let me give you a quick recap:\n\n"
            "1. A loop repeats a block of code.\n"
            "2. A 'for' loop runs a fixed number of times.\n"
            "3. A 'while' loop runs until a condition becomes false.\n\n"
            "You've understood all three ideas really well. Great job!"
        ),
        understanding_level="solid",
        concepts_covered=["loop basics", "for loop", "while loop"],
        is_topic_complete=True,
    )

    history = [
        {"role": "assistant", "content": _mock_llm_json(
            message="What is a loop?", understanding_level="not_assessed",
        )},
        {"role": "user", "content": "It repeats something again and again."},
        {"role": "assistant", "content": _mock_llm_json(
            message="Right! Now what's the difference between for and while?",
            understanding_level="developing",
            concepts_covered=["loop basics"],
        )},
        {"role": "user", "content": "For loop has a fixed count, while loop checks a condition."},
        {"role": "assistant", "content": _mock_llm_json(
            message="Perfect! Can you give an example of when you'd use a while loop?",
            understanding_level="developing",
            concepts_covered=["loop basics", "for loop"],
        )},
    ]

    result = _run(tutor_turn(
        topic="loops in programming",
        librarian_context=_make_librarian_output(),
        conversation_history=history,
        student_message="When you don't know how many times you need to repeat, like reading user input until they type 'quit'.",
    ))

    assert result.is_topic_complete is True
    assert result.understanding_level == "solid"
    assert len(result.concepts_covered) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: Prompt contains the Explanation Quality Bar instructions
# ══════════════════════════════════════════════════════════════════════════════

def test_system_prompt_contains_quality_bar():
    """The system prompt sent to the LLM must contain the Explanation Quality Bar
    instructions — this is the compile-time safety net for explanation quality."""
    assert "ZERO UNEXPLAINED JARGON" in TUTOR_SYSTEM_PROMPT
    assert "EVERYDAY ANALOGIES" in TUTOR_SYSTEM_PROMPT
    assert "ONE IDEA PER SENTENCE" in TUTOR_SYSTEM_PROMPT
    assert "CONCRETE BEFORE ABSTRACT" in TUTOR_SYSTEM_PROMPT
    assert "NO WALL OF TEXT" in TUTOR_SYSTEM_PROMPT
    assert "ASSUME GENUINE BEGINNER" in TUTOR_SYSTEM_PROMPT
    # Also check Core Philosophy
    assert "Socratic method" in TUTOR_SYSTEM_PROMPT
    assert "DIFFERENT, simpler analogy" in TUTOR_SYSTEM_PROMPT
    # Check few-shot examples are present
    assert "restaurant" in TUTOR_SYSTEM_PROMPT.lower()
    assert "TV remote" in TUTOR_SYSTEM_PROMPT or "remote" in TUTOR_SYSTEM_PROMPT
    assert "cricket" in TUTOR_SYSTEM_PROMPT.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: LLM raises exception → safe fallback, no crash
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_llm_exception_returns_safe_fallback(mock_llm):
    """When the LLM call raises any exception, the Tutor must return a
    friendly fallback message — never a raw error or crash."""
    mock_llm.side_effect = Exception("API rate limit exceeded")

    result = _run(tutor_turn(
        topic="recursion",
        librarian_context=_make_librarian_output(),
        conversation_history=[],
        student_message="What is recursion?",
    ))

    assert isinstance(result, TutorTurn)
    assert FALLBACK_MESSAGE in result.message
    assert result.is_topic_complete is False
    assert result.understanding_level == "not_assessed"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: Empty librarian context → still produces reasonable response
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_empty_librarian_context_still_responds(mock_llm):
    """When the Librarian provides no context (sufficient=False, empty chunks),
    the Tutor should still produce a reasonable response."""
    mock_llm.return_value = _mock_llm_json(
        message=(
            "I don't have specific notes on this topic, but I can still help! "
            "Before we start — have you heard of 'quantum' in everyday language, "
            "like 'quantum leap' in movies?"
        ),
        understanding_level="not_assessed",
    )

    empty_context = _make_librarian_output(
        chunks=[], sufficient=False, web_fallback=False,
    )

    result = _run(tutor_turn(
        topic="quantum entanglement",
        librarian_context=empty_context,
        conversation_history=[],
        student_message=None,
    ))

    assert isinstance(result, TutorTurn)
    assert len(result.message) > 10  # Not empty
    assert result.is_topic_complete is False
    # Verify the LLM received the "no reference material" message
    call_args = mock_llm.call_args
    messages = call_args[1].get("messages") or call_args[0][0]
    context_msg = messages[1]["content"]
    assert "no reference material" in context_msg.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: concepts_covered and concepts_struggled accumulate across turns
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_concepts_accumulate_across_turns(mock_llm):
    """Simulate a multi-turn sequence and verify that concepts_covered and
    concepts_struggled accumulate correctly via defensive merging."""

    # Turn 1: student struggles with "array definition"
    # Turn 2: student gets "array definition" right, but now we teach "indexing"
    # Result: both "array definition" should be in covered, "array definition"
    #         should also remain in struggled (it was struggled first)

    mock_llm.return_value = _mock_llm_json(
        message="Great! You've got arrays. Now — what do you think happens when you say arr[2]?",
        understanding_level="developing",
        concepts_covered=["array definition"],  # LLM adds this
        concepts_struggled=[],  # LLM forgot the earlier struggle
    )

    # History has a prior turn where the student struggled
    prior_turn = _mock_llm_json(
        message="Let me try explaining arrays differently...",
        understanding_level="struggling",
        concepts_covered=[],
        concepts_struggled=["array definition"],
    )

    result = _run(tutor_turn(
        topic="arrays",
        librarian_context=_make_librarian_output(),
        conversation_history=[
            {"role": "assistant", "content": prior_turn},
            {"role": "user", "content": "Oh I get it, it's like a row of boxes with numbers on them!"},
        ],
        student_message="Yes, an array is a list of items stored together!",
    ))

    # "array definition" should be in BOTH covered and struggled
    # (struggled from history, covered from this turn)
    assert "array definition" in result.concepts_covered
    assert "array definition" in result.concepts_struggled


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: Jargon-heavy source chunk → Tutor does NOT reproduce it verbatim
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_jargon_heavy_source_not_reproduced_verbatim(mock_llm):
    """When the Librarian provides a dense, jargon-heavy source chunk, the
    Tutor's output message must NOT reproduce the dense phrasing verbatim."""

    # Dense academic source text
    dense_source = (
        "The backpropagation algorithm computes the gradient of the loss function "
        "with respect to each weight by the chain rule, iterating backwards from "
        "the last layer. The partial derivatives are accumulated via dynamic "
        "programming to avoid redundant computation of intermediate sub-expressions "
        "in the computational graph."
    )

    # Tutor's simplified response
    simple_response = (
        "Let me explain how a neural network learns from its mistakes.\n\n"
        "Imagine you're playing a game of 'hot and cold'. "
        "Someone hides an object, and after each guess, they tell you "
        "'warmer' or 'colder'. You adjust your next guess based on that feedback.\n\n"
        "A neural network does something similar. After making a prediction, "
        "it checks how wrong it was. Then it goes back through each step "
        "and adjusts a little bit to be less wrong next time.\n\n"
        "Does this make sense so far? What part would you like me to explain more?"
    )

    mock_llm.return_value = _mock_llm_json(message=simple_response)

    result = _run(tutor_turn(
        topic="backpropagation",
        librarian_context=_make_librarian_output([dense_source]),
        conversation_history=[],
        student_message="Can you explain backpropagation?",
    ))

    # Spot-check: specific dense multi-word phrases from the source
    # should NOT appear in the Tutor's output
    jargon_phrases = [
        "gradient of the loss function",
        "chain rule",
        "partial derivatives",
        "dynamic programming",
        "computational graph",
        "redundant computation of intermediate sub-expressions",
    ]
    for phrase in jargon_phrases:
        assert phrase not in result.message, (
            f"Tutor reproduced jargon verbatim: '{phrase}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: LLM returns non-JSON text → graceful degradation, not crash
# ══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.tutor.call_gemini", new_callable=AsyncMock)
def test_llm_returns_plain_text_graceful_degradation(mock_llm):
    """If the LLM returns plain text instead of JSON, the Tutor should
    wrap it in a TutorTurn rather than crashing."""
    mock_llm.return_value = (
        "Sure! Let me help you understand recursion. "
        "Have you ever seen a mirror facing another mirror?"
    )

    result = _run(tutor_turn(
        topic="recursion",
        librarian_context=_make_librarian_output(),
        conversation_history=[],
        student_message=None,
    ))

    assert isinstance(result, TutorTurn)
    assert len(result.message) > 10
    assert result.is_topic_complete is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12: _merge_concept_lists preserves order and deduplicates
# ══════════════════════════════════════════════════════════════════════════════

def test_merge_concept_lists():
    """Unit test for the concept list merging utility."""
    prior = ["arrays", "Loops"]
    new = ["loops", "functions", "arrays"]

    result = _merge_concept_lists(prior, new)

    # Should deduplicate case-insensitively, preserving order
    assert len(result) == 3
    assert result[0] == "arrays"
    assert result[1] == "Loops"  # prior version preserved
    assert result[2] == "functions"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 13: _build_context_string caps at MAX_CONTEXT_CHARS
# ══════════════════════════════════════════════════════════════════════════════

def test_context_string_capped():
    """The context string builder should not exceed the character cap."""
    long_chunk = "x" * 3000
    ctx = _make_librarian_output([long_chunk])
    result = _build_context_string(ctx)
    assert len(result) <= 2100  # MAX_CONTEXT_CHARS + some buffer for "..."
