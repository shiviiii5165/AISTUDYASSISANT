"""
Orchestrator Agent — Central Intent Classifier & Router
=========================================================
Given a raw user message (and optional conversation history), this module:
  1. Classifies intent into: doubt, content_request, progress_check, general_chat, clarify
  2. Extracts topic and confidence metadata
  3. Returns a routing decision (which downstream agent should handle it)
  4. For general_chat and clarify intents, generates a direct reply via the LLM

Uses the existing `call_gemini` cascade from llm_service.py for all LLM calls.
No dependency on any downstream agent module — routing targets are string labels only.
"""

import json
from typing import Optional
from pydantic import BaseModel, Field

from app.services.llm_service import call_gemini, safe_json_loads


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

VALID_INTENTS = {"doubt", "content_request", "progress_check", "general_chat", "clarify", "document_summary"}
VALID_ROUTES = {
    "tutor_agent",
    "librarian_agent",
    "content_creator_agent",
    "study_planner_agent",
    "direct_reply",
    "none",
}

# Intent → default routing target
INTENT_ROUTE_MAP = {
    "doubt": "tutor_agent",
    "content_request": "content_creator_agent",
    "progress_check": "study_planner_agent",
    "general_chat": "direct_reply",
    "clarify": "direct_reply",
    "document_summary": "direct_reply", # Handled via V1 RAG pipeline which returns direct_reply
}


class OrchestratorOutput(BaseModel):
    """Structured output from the Orchestrator's classify-and-route step."""
    intent: str = Field(
        ...,
        description="One of: 'doubt', 'content_request', 'progress_check', 'general_chat', 'clarify'",
    )
    topic: Optional[str] = Field(
        None,
        description="The primary subject/concept the user is talking about, or null if unclear.",
    )
    confidence: float = Field(
        ...,
        description="Float between 0.0 and 1.0 indicating classification confidence.",
    )
    routed_to: str = Field(
        ...,
        description="One of: 'tutor_agent', 'librarian_agent', 'content_creator_agent', 'study_planner_agent', 'direct_reply', 'none'",
    )
    direct_reply: Optional[str] = Field(
        None,
        description="If intent is 'general_chat' or 'clarify', a short reply to the user.",
    )
    content_subtype: Optional[str] = Field(
        None,
        description="If intent is 'content_request', one of: 'ppt', 'video', 'flashcards', or 'unknown'.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# FEW-SHOT CLASSIFICATION PROMPT
# ══════════════════════════════════════════════════════════════════════════════

CLASSIFICATION_SYSTEM_PROMPT = """You are the Orchestrator for an AI Study Assistant application.
Your ONLY job is to classify a student's message into exactly one intent category and extract metadata.

## Intent Categories (pick exactly one):
1. **doubt** — The student is confused about a concept, asking "why", "how", "what is", requesting an explanation, or saying they don't understand something. Route to: tutor_agent
2. **content_request** — The student explicitly wants a tangible output generated from scratch: flashcards, a PowerPoint/PPT, a video, notes, or a quiz. Route to: content_creator_agent
3. **progress_check** — The student is asking about their own performance, scores, history, study streak, what they've completed, or revision schedule. Route to: study_planner_agent
4. **document_summary** — The student asks for a summary, crux, or overview of the current PDF/document (e.g. "syllabus summary", "summarize the chapter"). Route to: direct_reply
5. **general_chat** — Small talk, greetings, thanks, jokes, motivational questions, or anything that doesn't fit the above categories. Route to: direct_reply. You MUST also generate a short, friendly direct_reply.
6. **clarify** — The message is too vague or ambiguous to classify with confidence. Route to: direct_reply. You MUST also generate a short clarifying question as the direct_reply.

## Confidence Rules:
- If you are highly confident in the classification, set confidence to 0.8–1.0.
- If the message could belong to multiple categories, pick the most likely one but set confidence to 0.5–0.7.
- If you genuinely cannot determine the intent, set intent to "clarify" and confidence to 0.3–0.5.

## Output Format:
Respond with ONLY a valid JSON object (no markdown, no extra text):
{
  "intent": "<one of: doubt, content_request, progress_check, document_summary, general_chat, clarify>",
  "topic": "<detected subject/concept string or null>",
  "confidence": <float 0.0-1.0>,
  "routed_to": "<one of: tutor_agent, content_creator_agent, study_planner_agent, direct_reply>",
  "direct_reply": "<string or null — required only for general_chat and clarify>",
  "content_subtype": "<one of: ppt, video, flashcards, unknown, or null>"
}

## Few-Shot Examples:

User: "I don't understand how TCP three-way handshake works"
Output: {"intent": "doubt", "topic": "TCP three-way handshake", "confidence": 0.95, "routed_to": "tutor_agent", "direct_reply": null, "content_subtype": null}

User: "Make me a 10-slide PPT on database normalization"
Output: {"intent": "content_request", "topic": "database normalization", "confidence": 0.97, "routed_to": "content_creator_agent", "direct_reply": null, "content_subtype": "ppt"}

User: "How many questions did I answer correctly this week?"
Output: {"intent": "progress_check", "topic": null, "confidence": 0.92, "routed_to": "study_planner_agent", "direct_reply": null, "content_subtype": null}

User: "Hey, good morning! How are you doing?"
Output: {"intent": "general_chat", "topic": null, "confidence": 0.98, "routed_to": "direct_reply", "direct_reply": "Good morning! I'm doing great and ready to help you study. What would you like to learn today?", "content_subtype": null}

User: "Can you help me with that thing we discussed?"
Output: {"intent": "clarify", "topic": null, "confidence": 0.35, "routed_to": "direct_reply", "direct_reply": "I'd love to help! Could you tell me which topic or concept you're referring to so I can assist you better?", "content_subtype": null}

User: "Generate flashcards for operating system deadlocks"
Output: {"intent": "content_request", "topic": "operating system deadlocks", "confidence": 0.96, "routed_to": "content_creator_agent", "direct_reply": null, "content_subtype": "flashcards"}

Now classify the following student message."""


STRICT_RETRY_SUFFIX = """

CRITICAL: Your previous response was not valid JSON. You MUST respond with ONLY a raw JSON object.
Do NOT include markdown code fences, explanation text, or anything outside the JSON.
Example of the EXACT format required:
{"intent": "doubt", "topic": "example", "confidence": 0.9, "routed_to": "tutor_agent", "direct_reply": null, "content_subtype": null}
"""


# ══════════════════════════════════════════════════════════════════════════════
# CORE CLASSIFY-AND-ROUTE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def _build_messages(
    user_input: str,
    conversation_history: list[dict] | None = None,
    strict: bool = False,
) -> list[dict]:
    """Build the messages array for the LLM call."""
    system_prompt = CLASSIFICATION_SYSTEM_PROMPT
    if strict:
        system_prompt += STRICT_RETRY_SUFFIX

    # Format recent conversation history as context string (last 4 turns max)
    if conversation_history:
        history_text = "\n\n## Recent Conversation History:\n"
        for turn in conversation_history[-4:]:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")
            if role in ("User", "Assistant") and content:
                history_text += f"{role}: {content}\n"
        system_prompt += history_text

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_input})
    return messages


def _parse_and_validate(raw_text: str) -> OrchestratorOutput:
    """
    Parse raw LLM text into a validated OrchestratorOutput.
    Raises ValueError if parsing or validation fails.
    """
    data = safe_json_loads(raw_text)

    # Normalise intent
    intent = str(data.get("intent", "")).strip().lower()
    if intent not in VALID_INTENTS:
        raise ValueError(f"Invalid intent '{intent}', expected one of {VALID_INTENTS}")

    # Normalise confidence
    try:
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    # Apply ambiguity threshold: if confidence < 0.5, force clarify
    if confidence < 0.5 and intent != "clarify":
        intent = "clarify"
        data["direct_reply"] = data.get("direct_reply") or (
            "I'm not quite sure what you need. Could you rephrase or provide more details?"
        )

    # Determine routing
    routed_to = INTENT_ROUTE_MAP.get(intent, "direct_reply")

    # Ensure direct_reply exists for intents that require it
    direct_reply = data.get("direct_reply")
    if intent in ("general_chat", "clarify") and not direct_reply:
        if intent == "clarify":
            direct_reply = "Could you clarify what you'd like help with? I want to make sure I assist you correctly."
        else:
            direct_reply = "Hey there! What would you like to study today?"

    topic = data.get("topic")
    if isinstance(topic, str):
        topic = topic.strip() or None

    content_subtype = None
    if intent == "content_request":
        raw_subtype = str(data.get("content_subtype", "")).strip().lower()
        if raw_subtype in ("ppt", "video", "flashcards"):
            content_subtype = raw_subtype
        else:
            content_subtype = "unknown"

    return OrchestratorOutput(
        intent=intent,
        topic=topic,
        confidence=round(confidence, 2),
        routed_to=routed_to,
        direct_reply=direct_reply,
        content_subtype=content_subtype,
    )


def _fallback_clarify() -> OrchestratorOutput:
    """Safe fallback when all LLM attempts fail."""
    return OrchestratorOutput(
        intent="clarify",
        topic=None,
        confidence=0.0,
        routed_to="direct_reply",
        direct_reply="I'm having a little trouble understanding your request right now. Could you rephrase it?",
        content_subtype=None,
    )


async def classify_and_route(
    user_input: str,
    conversation_history: list[dict] | None = None,
) -> OrchestratorOutput:
    """
    Main entry point. Classifies user intent and determines routing.

    Retry strategy:
      - Attempt 1: Standard prompt → parse JSON
      - Attempt 2: Strict prompt (if attempt 1 fails to parse) → parse JSON
      - Fallback: Return intent="clarify" safely rather than crashing
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return _fallback_clarify()

    # ── Attempt 1: Standard prompt ──────────────────────────────────────────
    try:
        messages = _build_messages(user_input, conversation_history, strict=False)
        raw_text = await call_gemini(
            messages=messages,
            temperature=0.1,
            max_tokens=512,
        )
        return _parse_and_validate(raw_text)
    except Exception as e:
        err_msg = str(e)
        print(f"[Orchestrator] Attempt 1 failed: {e}")
        if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
            return OrchestratorOutput(
                intent="clarify",
                topic=None,
                confidence=0.0,
                routed_to="direct_reply",
                direct_reply="The AI is currently overloaded. Please try again in a few moments.",
                content_subtype=None,
            )

    # ── Attempt 2: Strict prompt (retry) ────────────────────────────────────
    try:
        messages = _build_messages(user_input, conversation_history, strict=True)
        raw_text = await call_gemini(
            messages=messages,
            temperature=0.0,
            max_tokens=512,
        )
        return _parse_and_validate(raw_text)
    except Exception as e:
        err_msg = str(e)
        print(f"[Orchestrator] Attempt 2 (strict) failed: {e}")
        if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
            return OrchestratorOutput(
                intent="clarify",
                topic=None,
                confidence=0.0,
                routed_to="direct_reply",
                direct_reply="The AI is currently overloaded. Please try again in a few moments.",
                content_subtype=None,
            )

    # ── Fallback: safe clarify ──────────────────────────────────────────────
    return _fallback_clarify()
