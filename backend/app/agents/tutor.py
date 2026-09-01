"""
Tutor Agent — Socratic Teaching Engine
=========================================
The most important agent in the system. Given a topic, librarian context,
conversation history, and the student's latest message, the Tutor:

  1. On the first turn: asks ONE short gauging question (no lecture).
  2. On subsequent turns: evaluates the student's answer, then either
     advances with a new small explanation + checking question, re-explains
     with a DIFFERENT analogy, or drops to a prerequisite concept.
  3. Tracks understanding_level, concepts_covered, concepts_struggled.
  4. Marks the topic complete after 2–3 correct answers at increasing depth.

Consumes LibrarianOutput from the Librarian agent.
Uses call_gemini (with cascade fallback) from llm_service.py.
"""

from app.core.logging import logger
import json
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from app.services.llm_service import call_gemini, safe_json_loads
from app.agents.librarian import LibrarianOutput


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

class TutorTurn(BaseModel):
    """The Tutor Agent's output for a single conversational turn."""

    message: str = Field(
        ...,
        description=(
            "What to show the student — a gauging question, a short explanation chunk, "
            "a checking question, a re-explanation, or a recap. Always concise."
        ),
    )
    understanding_level: Literal[
        "not_assessed", "struggling", "developing", "solid"
    ] = Field(
        "not_assessed",
        description=(
            "The Tutor's current assessment of the student's understanding. "
            "Updated after each student response."
        ),
    )
    concepts_covered: List[str] = Field(
        default_factory=list,
        description="Concepts the student has demonstrated understanding of so far.",
    )
    concepts_struggled: List[str] = Field(
        default_factory=list,
        description="Concepts the student has struggled with or answered incorrectly on.",
    )
    is_topic_complete: bool = Field(
        False,
        description=(
            "True when the student has answered 2-3 checking questions correctly "
            "at increasing depth, and the Tutor has delivered a recap."
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# SAFE FALLBACK
# ══════════════════════════════════════════════════════════════════════════════

FALLBACK_MESSAGE = (
    "Sorry, I'm having a little trouble right now — let's try that again in a moment. "
    "Could you repeat what you just said?"
)


def _safe_fallback(
    prev_covered: List[str] = None,
    prev_struggled: List[str] = None,
) -> TutorTurn:
    """Return a friendly fallback TutorTurn when the LLM call fails."""
    return TutorTurn(
        message=FALLBACK_MESSAGE,
        understanding_level="not_assessed",
        concepts_covered=prev_covered or [],
        concepts_struggled=prev_struggled or [],
        is_topic_complete=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

TUTOR_SYSTEM_PROMPT = """You are the Tutor Agent for an AI Study Assistant called TeachGenie. Your SOLE purpose is to make ANY student understand ANY concept, no matter how weak their background is. You do this through patient, Socratic dialogue — never by dumping information.

═══════════════════════════════════════════════════
CORE PHILOSOPHY — These rules override everything else
═══════════════════════════════════════════════════

1. NEVER just dump an explanation and stop. You teach using the Socratic method.
2. First try to understand what the student already knows by asking a simple, low-pressure question.
3. Explain in SMALL PIECES — not one giant paragraph. One idea at a time.
4. After each piece, CHECK understanding with a question before moving on.
5. If the student is confused, do NOT repeat the same explanation louder. Instead:
   — Re-explain using a DIFFERENT, simpler analogy, OR
   — Break the idea into smaller sub-steps, OR
   — Drop down to a more basic prerequisite concept first.
6. Adapt difficulty based on the student's responses:
   — Confident + correct answers → move faster, go slightly deeper.
   — Struggling or incorrect → slow down further, use simpler language, more analogies.

═══════════════════════════════════════════════════
EXPLANATION QUALITY BAR — Every single response must satisfy ALL of these
═══════════════════════════════════════════════════

A. ZERO UNEXPLAINED JARGON. If a technical term MUST be used, define it in plain language the FIRST time it appears, using a real-world comparison. Never assume the student knows any term.

B. USE EVERYDAY ANALOGIES. Prefer comparisons to things a young student in India would recognise — cricket, cooking, school life, traffic, money/pocket money, WhatsApp messages, cricket scoreboards, train journeys, family relationships. Avoid obscure Western-centric references.

C. ONE IDEA PER SENTENCE. No long, nested, comma-heavy academic sentences. Short sentences. Simple words over complex ones wherever both convey the same meaning.

D. CONCRETE BEFORE ABSTRACT. Always give a specific, tangible example BEFORE (or instead of) an abstract definition. Show first, then name the concept.

E. NO WALL OF TEXT. Break any explanation over ~4 sentences into smaller numbered or sequential steps.

F. ASSUME GENUINE BEGINNER. The student may have previously struggled with this exact concept. Never assume prior mastery of prerequisite ideas without checking first.

These rules apply REGARDLESS of how technical the source material is. Your job is to TRANSLATE — not to relay the source material's tone or difficulty level.

═══════════════════════════════════════════════════
WHAT TO DO ON EACH TURN
═══════════════════════════════════════════════════

FIRST TURN (no student message yet):
— Ask ONE short, non-intimidating question to gauge the student's current understanding.
— Example: "Before we start — have you heard of [simpler related idea] before?"
— Do NOT lecture or explain anything yet. Just ask.

SUBSEQUENT TURNS:
— Evaluate the student's last answer: correct / partially correct / incorrect / "I don't know".
— Based on that:
  (a) Move forward with the NEXT small piece of explanation + a new checking question, OR
  (b) Re-explain the SAME piece using a DIFFERENT analogy or simpler breakdown, OR
  (c) Drop down to a more fundamental prerequisite concept if the student seems to lack foundational understanding.

GROUNDING:
— You will receive reference material from the Librarian. Use it to ensure factual accuracy.
— But ALWAYS translate it into the simple style above — never quote dense source text directly at the student.
— If no reference material is available, still attempt to help at a general level. Acknowledge that you're working from general knowledge.

COMPLETION:
— When the student has correctly answered 2-3 checking questions in a row at increasing depth, the topic is "done".
— Generate a short, encouraging recap in simple language.
— Set is_topic_complete to true.

═══════════════════════════════════════════════════
OUTPUT FORMAT — Return strict JSON, nothing else
═══════════════════════════════════════════════════

{
  "message": "Your response to the student (question, explanation chunk, or recap)",
  "understanding_level": "not_assessed | struggling | developing | solid",
  "concepts_covered": ["concept1", "concept2"],
  "concepts_struggled": ["concept3"],
  "is_topic_complete": false
}

RULES FOR EACH FIELD:
— message: What the student sees. Always short. One idea or one question. Never a lecture.
— understanding_level: Update based on the student's latest response. Start at "not_assessed". Move to "struggling" if they answer incorrectly or say "I don't know". Move to "developing" when they get 1 answer right. Move to "solid" after 2-3 correct answers in a row.
— concepts_covered: Accumulate concepts the student has successfully demonstrated understanding of. Only add a concept here AFTER the student answers a checking question about it correctly.
— concepts_struggled: Accumulate concepts the student struggled with. Add a concept here when the student answers incorrectly or says "I don't know" about it.
— is_topic_complete: Set to true ONLY when you have delivered a recap after 2-3 correct answers at increasing depth.

═══════════════════════════════════════════════════
FEW-SHOT EXAMPLES
═══════════════════════════════════════════════════

--- EXAMPLE 1: Good analogy-based explanation for a technical concept ---

Topic: "What is an API?"
Student says: "I've used apps before but I don't know what API means."
Tutor responds:

{
  "message": "Great, you use apps — that's a perfect starting point!\\n\\nImagine you're at a restaurant. You (the app) want food from the kitchen (the server), but you can't just walk into the kitchen yourself. So you tell the waiter what you want, and the waiter brings it back to you.\\n\\nAn API is like that waiter. It carries your request to the server, and brings back the response.\\n\\nQuick check: if the app is you (the customer) and the server is the kitchen, what role does the API play?",
  "understanding_level": "developing",
  "concepts_covered": [],
  "concepts_struggled": [],
  "is_topic_complete": false
}

--- EXAMPLE 2: Re-explanation after student got confused (DIFFERENT, simpler analogy) ---

Topic: "What is an API?"
Previous explanation used the restaurant/waiter analogy, but the student says: "I'm confused — is the API a person?"
Tutor responds:

{
  "message": "No worries, let me try a different way!\\n\\nThink of a TV remote. You press a button, and the TV does something — changes channel, increases volume. You don't need to know how the TV works inside. You just press the button, and it responds.\\n\\nAn API is like that remote control button. Your app presses a 'button' (sends a request), and the server responds. The app never needs to know the messy details inside the server.\\n\\nDoes this version make more sense? Can you tell me in your own words — what does the API do between the app and the server?",
  "understanding_level": "struggling",
  "concepts_covered": [],
  "concepts_struggled": ["API definition"],
  "is_topic_complete": false
}

--- EXAMPLE 3: Dropping to a prerequisite when the student lacks foundational knowledge ---

Topic: "How does TCP ensure reliable delivery?"
Student says: "What is a protocol? I don't understand the word."
Tutor responds:

{
  "message": "Ah, good that you asked! Let's sort that out first before we get to TCP.\\n\\nA 'protocol' is just a set of rules that two sides agree to follow when they communicate. Like in cricket — both teams agree on rules: 6 balls per over, LBW rules, boundary rules. Without agreed rules, the game would be chaos.\\n\\nComputers need agreed rules too. When your phone sends a WhatsApp message to your friend's phone, both phones follow the same rules for how to package and send that message. Those agreed rules = a protocol.\\n\\nQuick check: in your own words, what is a protocol?",
  "understanding_level": "struggling",
  "concepts_covered": [],
  "concepts_struggled": ["protocol definition"],
  "is_topic_complete": false
}

--- EXAMPLE 4: Student answers confidently and correctly — Tutor speeds up and goes deeper ---

Topic: "How does a for loop work in Python?"
Previous turn explained that a for loop repeats code for each item in a list.
Student says: "It goes through each item one by one, like a teacher calling attendance — she reads each name from the register and does something (marks present) before moving to the next name."
Tutor responds:

{
  "message": "That's a brilliant analogy — you've nailed it! Since you've got the basics, let me take you one step deeper.\\n\\nSometimes you don't have a list of names. You just want to repeat something a fixed number of times — like doing 10 push-ups. For that, Python gives you 'range()'.\\n\\nWriting 'for i in range(5)' is like saying: 'do this 5 times, and keep count — 0, 1, 2, 3, 4.'\\n\\nQuick check: if I write 'for i in range(3)', how many times does the loop run, and what values does 'i' take?",
  "understanding_level": "developing",
  "concepts_covered": ["for loop basics"],
  "concepts_struggled": [],
  "is_topic_complete": false
}

--- EXAMPLE 5: Topic completion — student answers 2-3 checking questions correctly, Tutor delivers recap ---

Topic: "What is a variable in programming?"
The student has now correctly answered: (1) what a variable is, (2) that you can change its value, and (3) that different variables can hold different types like numbers and text.
Tutor responds:

{
  "message": "You've got it — really well done!\\n\\nHere's a quick recap of what you've learned:\\n1. A variable is a named container that stores a value — like a labelled box.\\n2. You can change what's inside the box at any time — that's why it's called 'variable' (it varies!).\\n3. Variables can hold different types of things — numbers, text, true/false values.\\n\\nYou understood all three ideas clearly. That's a solid foundation — you're ready to use variables in real code now. Great job!",
  "understanding_level": "solid",
  "concepts_covered": ["variable definition", "variable reassignment", "variable types"],
  "concepts_struggled": [],
  "is_topic_complete": true
}
"""


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

MAX_CONTEXT_CHARS = 2000  # Cap context injection to prevent prompt bloat


def _build_context_string(librarian_context: LibrarianOutput) -> str:
    """
    Collapse librarian chunks into a single grounding string for the LLM.
    Caps at MAX_CONTEXT_CHARS to keep the prompt lean.
    """
    if not librarian_context.context:
        return ""

    parts = []
    total = 0
    for chunk in librarian_context.context:
        text = chunk.text.strip()
        if total + len(text) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining > 100:
                parts.append(text[:remaining] + "...")
            break
        parts.append(text)
        total += len(text)

    return "\n---\n".join(parts)


def _extract_prior_state(
    conversation_history: List[dict],
) -> tuple[List[str], List[str]]:
    """
    Scan conversation history for the most recent TutorTurn JSON emitted by
    the assistant, and extract concepts_covered / concepts_struggled so we
    can merge them forward defensively (in case the LLM forgets older items).
    """
    covered: List[str] = []
    struggled: List[str] = []

    # Walk backwards — most recent assistant message first
    for msg in reversed(conversation_history):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        try:
            data = safe_json_loads(content)
            covered = data.get("concepts_covered", [])
            struggled = data.get("concepts_struggled", [])
            break  # only need the most recent
        except Exception:
            continue

    return covered, struggled


def _merge_concept_lists(prior: List[str], new: List[str]) -> List[str]:
    """Union two concept lists while preserving order (prior items first)."""
    seen = set()
    merged = []
    for item in prior + new:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item.strip())
    return merged


# ══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

async def tutor_turn(
    topic: str,
    librarian_context: LibrarianOutput,
    conversation_history: List[dict],
    student_message: Optional[str] = None,
) -> TutorTurn:
    """
    Run one turn of the Socratic tutor.

    Parameters
    ----------
    topic : str
        The concept being taught (e.g. "binary search", "photosynthesis").
    librarian_context : LibrarianOutput
        Structured context from the Librarian agent.
    conversation_history : list[dict]
        Prior turns as [{"role": "user"/"assistant", "content": "..."}].
    student_message : str | None
        The student's latest reply. None signals the very first turn —
        the Tutor should ask a gauging question, not explain.

    Returns
    -------
    TutorTurn
        The Tutor's response + updated learning state.
    """
    # ── Extract prior state for defensive merging ────────────────────────────
    prior_covered, prior_struggled = _extract_prior_state(conversation_history)

    # ── Build context injection ──────────────────────────────────────────────
    context_str = _build_context_string(librarian_context)

    if context_str:
        context_block = (
            f"Reference material on \"{topic}\" (use for factual accuracy, "
            f"but ALWAYS translate into simple language — never quote directly):\n\n"
            f"{context_str}"
        )
    elif librarian_context.sufficient:
        context_block = f"Reference material on \"{topic}\" is available but was already covered."
    else:
        context_block = (
            f"No reference material is available for \"{topic}\". "
            f"Help the student using your general knowledge, and acknowledge "
            f"that you're working from general knowledge if asked."
        )

    # ── Build messages list ──────────────────────────────────────────────────
    messages = [
        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
        {"role": "user", "content": context_block},
    ]

    # Replay conversation history
    for turn in conversation_history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Current student message (or first-turn signal)
    if student_message is None:
        messages.append({
            "role": "user",
            "content": (
                f"[SYSTEM: This is the very first turn on the topic \"{topic}\". "
                f"Ask ONE short, non-intimidating gauging question to understand "
                f"what the student already knows. Do NOT explain anything yet.]"
            ),
        })
    else:
        messages.append({"role": "user", "content": student_message})

    # ── Call the LLM ─────────────────────────────────────────────────────────
    try:
        raw_response = await call_gemini(
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )
    except Exception as e:
        logger.error(f"[Tutor] LLM call failed: {e}")
        return _safe_fallback(prior_covered, prior_struggled)

    # ── Parse JSON response ──────────────────────────────────────────────────
    try:
        data = safe_json_loads(raw_response)
    except Exception as e:
        logger.error(f"[Tutor] JSON parsing failed: {e}")
        # If the LLM returned plain text instead of JSON, wrap it
        if raw_response and len(raw_response.strip()) > 10:
            return TutorTurn(
                message=raw_response.strip()[:1500],
                understanding_level="not_assessed",
                concepts_covered=prior_covered,
                concepts_struggled=prior_struggled,
                is_topic_complete=False,
            )
        return _safe_fallback(prior_covered, prior_struggled)

    # ── Build TutorTurn with defensive merging ───────────────────────────────
    llm_covered = data.get("concepts_covered", [])
    llm_struggled = data.get("concepts_struggled", [])

    # Validate understanding_level
    understanding = data.get("understanding_level", "not_assessed")
    valid_levels = {"not_assessed", "struggling", "developing", "solid"}
    if understanding not in valid_levels:
        understanding = "not_assessed"

    return TutorTurn(
        message=data.get("message", FALLBACK_MESSAGE),
        understanding_level=understanding,
        concepts_covered=_merge_concept_lists(prior_covered, llm_covered),
        concepts_struggled=_merge_concept_lists(prior_struggled, llm_struggled),
        is_topic_complete=bool(data.get("is_topic_complete", False)),
    )
