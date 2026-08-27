"""
Context Builder & Token Budget Engine (Production Hardened)
===========================================================
Builds the smallest sufficient prompt context package before every model turn.
Strictly eliminates redundant context, long chat dumps, and full document bloating.
"""
from typing import List, Dict, Any, Optional
from ..knowledge.sources import EvidenceItem
from .schemas import LearningState, ConceptSpec, LearningDepth, MisconceptionItem
from .grounding_evaluator import detect_source_conflicts


DEPTH_TOKEN_BUDGETS = {
    LearningDepth.QUICK: 1200,
    LearningDepth.NORMAL: 2200,
    LearningDepth.DEEP: 3800,
    LearningDepth.EXAM: 3000,
}


def build_compact_evidence_prompt(evidence_items: List[EvidenceItem], max_items: int = 4) -> str:
    """Formats top evidence items with clean citation identifiers."""
    if not evidence_items:
        return ""

    formatted_parts = []
    for item in evidence_items[:max_items]:
        badge = item.get_citation_badge()
        text_snippet = item.text.strip()
        if len(text_snippet) > 400:
            text_snippet = text_snippet[:390] + "..."
        formatted_parts.append(f"[{badge}] ({item.source_name}):\n{text_snippet}")

    result = "--- GROUNDED EVIDENCE MATERIAL ---\n" + "\n\n".join(formatted_parts) + "\n----------------------------------"

    # Check for cross-source conflict
    conflict_advisory = detect_source_conflicts(evidence_items)
    if conflict_advisory:
        result += f"\n[SOURCE CONFLICT ALERT]: {conflict_advisory}"

    return result


def build_compact_state_summary(state: LearningState, concept: Optional[ConceptSpec] = None) -> str:
    """Builds a token-dense JSON-like summary of the active student state."""
    concept_name = concept.name if concept else (state.current_concept_id or "General")
    strategy_str = concept.active_strategy.value if (concept and hasattr(concept.active_strategy, "value")) else "formal_explanation"

    lines = [
        f"Topic: {state.topic}",
        f"Active Concept: {concept_name}",
        f"Target Level: {state.level.value if hasattr(state.level, 'value') else state.level}",
        f"Language: {state.language}",
        f"Mode: {state.mode.value if hasattr(state.mode, 'value') else state.mode}",
        f"Depth: {state.depth.value if hasattr(state.depth, 'value') else state.depth}",
        f"Active Strategy: {strategy_str}",
        f"Mastery on Concept: {state.get_current_mastery():.2f}",
        f"Confidence Score: {state.get_current_confidence():.2f}",
    ]

    # Extract unresolved misconceptions for current concept
    active_m_texts = []
    for m in state.misconceptions:
        if isinstance(m, MisconceptionItem):
            if not m.resolved and (not concept or m.concept_id == concept.id):
                active_m_texts.append(m.misconception)
        elif isinstance(m, str):
            active_m_texts.append(m)

    if active_m_texts:
        lines.append(f"Active Misconceptions to Remediate: {', '.join(active_m_texts[-3:])}")
    if state.strategies_used:
        lines.append(f"Previously Attempted Strategies: {', '.join(state.strategies_used[-3:])}")

    return "--- ACTIVE LEARNING STATE ---\n" + "\n".join(lines) + "\n-----------------------------"


def assemble_teaching_context(
    system_prompt: str,
    state: LearningState,
    concept: Optional[ConceptSpec],
    evidence_items: List[EvidenceItem],
    user_message: str,
    include_history_turns: int = 2,
) -> List[Dict[str, str]]:
    """
    Constructs the optimized message array for Teacher / Assessment turns.
    Guarantees that untrusted evidence content remains isolated as reference data.
    """
    messages = [{"role": "system", "content": system_prompt}]

    # 1. State Context
    state_str = build_compact_state_summary(state, concept)
    
    # 2. Evidence Context
    evidence_str = build_compact_evidence_prompt(evidence_items)

    combined_context = state_str
    if evidence_str:
        combined_context += "\n\n" + evidence_str

    # 3. Add context package
    messages.append({
        "role": "user",
        "content": f"[SYSTEM CONTEXT - DO NOT ECHO DIRECTLY]\n{combined_context}"
    })
    messages.append({
        "role": "assistant",
        "content": "Context received. I will tailor my explanation and checkpoint strictly following the active student state and pedagogical strategy."
    })

    # 4. Add minimal recent history turns
    if state.recent_history and include_history_turns > 0:
        recent = state.recent_history[-include_history_turns * 2:]
        for turn in recent:
            messages.append(turn)

    # 5. Latest user prompt
    messages.append({"role": "user", "content": user_message})

    return messages
