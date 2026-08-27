"""
Assessment Agent — Student Response Evaluator & Diagnostic Engine (Hardened)
=============================================================================
Evaluates student answers, diagnoses conceptual misconceptions, computes
deterministic mastery & confidence updates, resolves misconceptions, and enforces idempotency.
"""
import hashlib
from typing import Dict, Any, Optional
from app.services.ai import router
from .schemas import EvaluationResult, LearningState, CheckpointSpec
from .prompts import ASSESSMENT_SYSTEM_PROMPT
from .mastery import calculate_mastery_update
from .tools import (
    get_learning_state, save_learning_state,
    get_lesson_plan, update_mastery_profile, record_misconception_item,
    resolve_misconception
)


async def evaluate_student_answer(
    session_id: str,
    student_answer: str,
    user_id: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates student response against the active checkpoint and current concept.
    Enforces idempotency to avoid duplicate score bumps on network retries.
    """
    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise ValueError(f"Session {session_id} not found.")

    # Check idempotency hash
    ans_clean = student_answer.strip()
    ans_hash = hashlib.md5(f"{state.current_concept_id}_{ans_clean}_{idempotency_key or ''}".encode()).hexdigest()
    if ans_hash in state.processed_answer_keys:
        prof = state.get_current_profile()
        return {
            "evaluation": {
                "correctness": "correct" if prof.mastery_score >= 0.7 else "partial",
                "score": prof.mastery_score,
                "feedback": "Answer already processed.",
                "idempotent_duplicate": True,
            },
            "new_mastery_score": prof.mastery_score,
            "confidence": prof.confidence,
            "mastery_label": "Mastered" if prof.is_mastered() else "Developing",
            "recommended_action": "continue",
        }

    active_concept = next((c for c in plan.concepts if c.id == state.current_concept_id), None)
    active_checkpoint = state.active_checkpoint

    # If no active checkpoint was recorded, provide default context
    question_text = active_checkpoint.question if active_checkpoint else "Explain the core concept."
    expected_skill = active_checkpoint.expected_skill if active_checkpoint else (active_concept.name if active_concept else state.topic)

    # 1. Build evaluation prompt package
    eval_user_msg = f"""ACTIVE CONCEPT: {active_concept.name if active_concept else state.topic}
CHECKPOINT QUESTION: {question_text}
EXPECTED SKILL / CRITERIA: {expected_skill}

STUDENT ANSWER:
\"\"\"{student_answer}\"\"\"

Evaluate the answer. If incorrect or partial, identify the exact misconception."""

    messages = [
        {"role": "system", "content": ASSESSMENT_SYSTEM_PROMPT},
        {"role": "user", "content": eval_user_msg},
    ]

    # 2. Call ModelRouter for diagnostic analysis
    eval_json = await router.generate_json(
        task="qa",
        messages=messages,
        temperature=0.2,
        max_tokens=1500,
    )

    # 3. Formulate EvaluationResult
    correctness = eval_json.get("correctness", "correct").lower()
    if correctness not in ["correct", "partial", "incorrect"]:
        correctness = "correct" if float(eval_json.get("score", 1.0)) >= 0.7 else "incorrect"

    eval_result = EvaluationResult(
        correctness=correctness,
        score=float(eval_json.get("score", 1.0 if correctness == "correct" else 0.3)),
        misconception=eval_json.get("misconception") if correctness != "correct" else None,
        feedback=eval_json.get("feedback", "Good effort."),
        needs_reteach=(correctness != "correct"),
    )

    # 4. Deterministic Mastery Calculation (Pure Python)
    current_score = state.get_current_mastery()
    attempts = active_concept.attempts_count if active_concept else 1
    difficulty = active_checkpoint.difficulty if active_checkpoint else "medium"
    
    prof = state.get_current_profile()
    active_m_list = list(prof.active_misconceptions)

    new_score, delta, label, decision = calculate_mastery_update(
        current_score=current_score,
        eval_result=eval_result,
        attempt_count=attempts,
        difficulty=difficulty,
        active_misconceptions=active_m_list,
        recent_scores=prof.recent_scores,
    )

    eval_result.mastery_delta = delta
    eval_result.suggested_next_action = decision

    # 5. Persist updates
    if state.current_concept_id:
        update_mastery_profile(
            session_id=session_id,
            concept_id=state.current_concept_id,
            score=new_score,
            delta=delta,
            difficulty=difficulty,
        )
        if eval_result.misconception:
            record_misconception_item(session_id, state.current_concept_id, eval_result.misconception)
        elif correctness == "correct":
            # If student answered correctly, resolve prior active misconceptions on this concept
            resolve_misconception(session_id, state.current_concept_id)

    # Log processed idempotency key
    state.processed_answer_keys.append(ans_hash)
    if len(state.processed_answer_keys) > 20:
        state.processed_answer_keys = state.processed_answer_keys[-20:]

    # Clear active checkpoint once answered
    state.active_checkpoint = None
    save_learning_state(session_id, state)

    return {
        "evaluation": eval_result.dict(),
        "new_mastery_score": new_score,
        "mastery_label": label,
        "recommended_action": decision,
    }
