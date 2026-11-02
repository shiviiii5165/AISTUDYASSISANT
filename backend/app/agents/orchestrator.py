"""
Orchestrator Agent — Central Intent Classifier & Router
=========================================================
Feature 4 Production Teaching Engine Orchestrator (§2, §3, §4).
Given a raw user message (and optional conversation history/explicit mode):
  1. Classifies intent into canonical categories (§4):
     - QUICK_QA (or 'doubt' alias with QUICK_ASK mode)
     - CONCEPT_LEARNING (or 'doubt' alias with TUTOR mode)
     - DOCUMENT_LEARNING
     - PRACTICE_REQUEST
     - CONTENT_CREATION (or 'content_request' alias)
     - GENERAL_CONVERSATION (or 'general_chat' alias)
  2. Extracts topic and confidence metadata
  3. Supports explicit user mode override (QUICK_ASK vs TUTOR §3)
  4. Returns routing decision: whether Librarian is needed, whether Tutor is needed
"""

import json
import re
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.services.llm_service import call_gemini, safe_json_loads


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

CANONICAL_INTENTS = {
    "quick_qa",
    "concept_learning",
    "document_learning",
    "practice_request",
    "content_creation",
    "general_conversation",
}

VALID_INTENTS = {
    # Feature 4 Canonical
    "quick_qa",
    "concept_learning",
    "document_learning",
    "practice_request",
    "content_creation",
    "general_conversation",
    # Backward compatible aliases
    "doubt",
    "content_request",
    "progress_check",
    "general_chat",
    "clarify",
    "document_summary",
}

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
    "quick_qa": "tutor_agent",
    "concept_learning": "tutor_agent",
    "document_learning": "tutor_agent",
    "practice_request": "tutor_agent",
    "content_creation": "content_creator_agent",
    "general_conversation": "direct_reply",
    # Legacy aliases
    "doubt": "tutor_agent",
    "content_request": "content_creator_agent",
    "progress_check": "study_planner_agent",
    "general_chat": "direct_reply",
    "clarify": "direct_reply",
    "document_summary": "direct_reply",
}


class OrchestratorOutput(BaseModel):
    """Structured output from the Orchestrator's classify-and-route step."""
    intent: str = Field(
        ...,
        description="Canonical intent (quick_qa, concept_learning, content_creation, general_conversation, etc.)",
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
        description="If intent is 'content_request' or 'content_creation', one of: 'ppt', 'video', 'flashcards', or 'unknown'.",
    )
    teaching_mode: Optional[str] = Field(
        None,
        description="'QUICK_ASK' or 'TUTOR'",
    )
    needs_librarian: bool = Field(
        False,
        description="True if document/RAG retrieval is beneficial.",
    )
    needs_tutor: bool = Field(
        False,
        description="True if Socratic or Quick Ask teaching engine should handle it.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC MODE SELECTION (§3: Explicit user choice overrides inference)
# ══════════════════════════════════════════════════════════════════════════════

def determine_teaching_mode(user_input: str, explicit_mode: Optional[str] = None) -> str:
    """
    Deterministic rule-based teaching mode recommendation (§3).
    Explicit user choice always overrides automatic inference.
    """
    if explicit_mode in ("QUICK_ASK", "TUTOR"):
        return explicit_mode

    clean = user_input.strip().lower()

    # Explicit teach me / confusion / step-by-step -> TUTOR
    if re.search(r'\b(teach\s+me|samajh\s+nahi\s+aa\s+raha|basics\s+se\s+sikhao|walk\s+me\s+through|step\s+by\s+step|quiz\s+me)\b', clean):
        return "TUTOR"

    # Short factual lookups or page references -> QUICK_ASK
    if (re.match(r'^(what\s+is|define|definition\s+of|formula\s+for|who\s+discovered)\b', clean) and len(clean.split()) <= 12) or re.search(r'\bpage\s+\d+\b', clean):
        return "QUICK_ASK"

    return "TUTOR"


# ══════════════════════════════════════════════════════════════════════════════
# FEW-SHOT CLASSIFICATION PROMPT
# ══════════════════════════════════════════════════════════════════════════════

CLASSIFICATION_SYSTEM_PROMPT = """You are the Orchestrator for an AI Study Assistant application.
Your ONLY job is to classify a student's message into exactly one intent category and extract metadata.

## Intent Categories (pick exactly one):
1. **doubt** — The student is confused about a concept, asking "why", "how", "what is", requesting an explanation, or saying they don't understand something. Route to: tutor_agent
2. **content_request** — The student explicitly wants a tangible output generated from scratch: flashcards, a PowerPoint/PPT, a video, notes, or a quiz. Route to: content_creator_agent
3. **progress_check** — The student is asking about their own performance, scores, history, study streak, what they've completed, or revision schedule. Route to: study_planner_agent
4. **document_summary** — The student asks for a summary, crux, or overview of the current PDF/document. Route to: direct_reply
5. **general_chat** — Small talk, greetings, thanks, jokes, motivational questions. Route to: direct_reply. You MUST also generate a short, friendly direct_reply.
6. **clarify** — The message is too vague or ambiguous to classify with confidence. Route to: direct_reply. You MUST also generate a short clarifying question as the direct_reply.

## Output Format:
Respond with ONLY a valid JSON object:
{
  "intent": "<one of: doubt, content_request, progress_check, document_summary, general_chat, clarify>",
  "topic": "<detected subject/concept string or null>",
  "confidence": <float 0.0-1.0>,
  "routed_to": "<one of: tutor_agent, content_creator_agent, study_planner_agent, direct_reply>",
  "direct_reply": "<string or null — required only for general_chat and clarify>",
  "content_subtype": "<one of: ppt, video, flashcards, unknown, or null>"
}
"""

STRICT_RETRY_SUFFIX = """
CRITICAL: Respond with ONLY a raw JSON object without markdown or commentary.
"""


def _build_messages(
    user_input: str,
    conversation_history: list[dict] | None = None,
    strict: bool = False,
) -> list[dict]:
    system_prompt = CLASSIFICATION_SYSTEM_PROMPT
    if strict:
        system_prompt += STRICT_RETRY_SUFFIX

    if conversation_history:
        history_text = "\n\n## Recent Conversation History:\n"
        for turn in conversation_history[-4:]:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")
            if role in ("User", "Assistant") and content:
                history_text += f"{role}: {content}\n"
        system_prompt += history_text

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]


def _parse_and_validate(raw_text: str, user_input: str = "", explicit_mode: Optional[str] = None) -> OrchestratorOutput:
    data = safe_json_loads(raw_text)

    intent = str(data.get("intent", "")).strip().lower()
    if intent not in VALID_INTENTS:
        raise ValueError(f"Invalid intent '{intent}', expected one of {VALID_INTENTS}")

    try:
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence < 0.5 and intent != "clarify":
        intent = "clarify"
        data["direct_reply"] = data.get("direct_reply") or (
            "I'm not quite sure what you need. Could you rephrase or provide more details?"
        )

    routed_to = INTENT_ROUTE_MAP.get(intent, "direct_reply")
    direct_reply = data.get("direct_reply")
    if intent in ("general_chat", "clarify") and not direct_reply:
        direct_reply = "Could you clarify what you'd like help with?" if intent == "clarify" else "Hey there! What would you like to study today?"

    topic = data.get("topic")
    if isinstance(topic, str):
        topic = topic.strip() or None

    content_subtype = None
    if intent in ("content_request", "content_creation"):
        raw_subtype = str(data.get("content_subtype", "")).strip().lower()
        content_subtype = raw_subtype if raw_subtype in ("ppt", "video", "flashcards") else "unknown"

    teaching_mode = determine_teaching_mode(user_input, explicit_mode)

    return OrchestratorOutput(
        intent=intent,
        topic=topic,
        confidence=round(confidence, 2),
        routed_to=routed_to,
        direct_reply=direct_reply,
        content_subtype=content_subtype,
        teaching_mode=teaching_mode,
        needs_librarian=bool(topic and routed_to == "tutor_agent"),
        needs_tutor=routed_to == "tutor_agent"
    )


def _fallback_clarify() -> OrchestratorOutput:
    return OrchestratorOutput(
        intent="clarify",
        topic=None,
        confidence=0.0,
        routed_to="direct_reply",
        direct_reply="I'm having a little trouble understanding your request right now. Could you rephrase it?",
        content_subtype=None,
        teaching_mode=None,
        needs_librarian=False,
        needs_tutor=False
    )


async def classify_and_route(
    user_input: str,
    conversation_history: list[dict] | None = None,
    explicit_mode: Optional[str] = None,
) -> OrchestratorOutput:
    """
    Main entry point. Classifies user intent and determines routing.
    Honors explicit_mode override (§3).
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return _fallback_clarify()

    # 1. LLM Attempt 1
    try:
        messages = _build_messages(user_input, conversation_history, strict=False)
        raw_text = await call_gemini(messages, temperature=0.1, max_tokens=512)
        return _parse_and_validate(raw_text, user_input, explicit_mode)
    except Exception as e:
        err_msg = str(e)
        if "API calls failed" in err_msg or "Embedding generation failed" in err_msg:
            return OrchestratorOutput(
                intent="clarify",
                topic=None,
                confidence=0.0,
                routed_to="direct_reply",
                direct_reply="The AI is currently overloaded. Please try again in a few moments.",
                content_subtype=None,
            )

    # 2. LLM Attempt 2 (Strict)
    try:
        messages = _build_messages(user_input, conversation_history, strict=True)
        raw_text = await call_gemini(messages, temperature=0.0, max_tokens=512)
        return _parse_and_validate(raw_text, user_input, explicit_mode)
    except Exception:
        pass

    return _fallback_clarify()
