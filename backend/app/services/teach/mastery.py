"""
Deterministic Multi-Factor Mastery & Confidence Engine (Pure Python — 0 Token Cost)
=====================================================================================
Calculates Bayesian-inspired student mastery scores (0.00 to 1.00) and observation
confidence (0.00 to 1.00), tracking evidence consistency, difficulty weights, and
misconception blockers.
"""
import math
from typing import Dict, Any, Tuple, Optional, List
from .schemas import EvaluationResult, ConceptStatus, ConceptMasteryProfile


MASTERY_THRESHOLDS = {
    "weak": (0.00, 0.39),
    "developing": (0.40, 0.69),
    "strong": (0.70, 0.89),
    "mastered": (0.90, 1.00),
}

DIFFICULTY_WEIGHTS = {
    "easy": 0.75,
    "medium": 1.0,
    "hard": 1.35,
    "explain_back": 1.5,
    "own_words": 1.5,
}


def get_mastery_level_label(score: float, confidence: float = 1.0) -> str:
    """Returns human-readable mastery level label."""
    if score >= 0.85 and confidence >= 0.50:
        return "Mastered"
    elif score >= 0.70:
        return "Strong"
    elif score >= 0.40:
        return "Developing"
    return "Weak"


def calculate_confidence_score(evidence_count: int, recent_scores: List[float]) -> float:
    """
    Computes statistical confidence based on observation volume and variance.
    1 observation -> ~0.35 confidence
    2 observations -> ~0.60 confidence
    3+ observations -> ~0.75 to 0.95 confidence
    """
    if evidence_count <= 0:
        return 0.0

    # Base asymptotic confidence curve: 1 - e^(-0.45 * N)
    base_conf = 1.0 - math.exp(-0.48 * evidence_count)

    # Consistency adjustment
    if len(recent_scores) >= 2:
        variance = sum((s - (sum(recent_scores) / len(recent_scores))) ** 2 for s in recent_scores) / len(recent_scores)
        penalty = min(0.20, variance * 0.5)
        base_conf = max(0.1, base_conf - penalty)

    return round(min(0.99, max(0.05, base_conf)), 2)


def calculate_mastery_update(
    current_score: float,
    eval_result: EvaluationResult,
    attempt_count: int = 1,
    difficulty: str = "medium",
    active_misconceptions: Optional[List[str]] = None,
    recent_scores: Optional[List[float]] = None,
) -> Tuple[float, float, str, str]:
    """
    Backward-compatible core function returning:
    (new_score, delta, mastery_label, recommended_decision)
    """
    scores_list = list(recent_scores or [])
    scores_list.append(eval_result.score)
    evidence_count = attempt_count + 1

    diff_mult = DIFFICULTY_WEIGHTS.get(difficulty.lower(), 1.0)
    delta = 0.0

    if eval_result.correctness == "correct":
        # First-attempt or hard question boost
        base_boost = 0.32 if attempt_count <= 1 else 0.22
        delta = base_boost * diff_mult * max(0.6, eval_result.score)
    elif eval_result.correctness == "partial":
        delta = 0.10 * diff_mult * eval_result.score
    else:
        # Incorrect answer
        penalty = 0.16
        if eval_result.misconception:
            penalty = 0.22
        delta = -penalty

    # New raw score
    raw_new_score = current_score + delta

    # If active blocking misconceptions exist, cap score below 0.80
    has_blocking_misconception = bool(active_misconceptions and len(active_misconceptions) > 0)
    if has_blocking_misconception:
        raw_new_score = min(0.79, raw_new_score)

    new_score = round(max(0.0, min(1.0, raw_new_score)), 2)
    confidence = calculate_confidence_score(evidence_count, scores_list)
    label = get_mastery_level_label(new_score, confidence)

    # ── Deterministic Learning Decision Engine ──
    if new_score >= 0.85 and confidence >= 0.50 and not has_blocking_misconception:
        decision = "advance_next_concept"
    elif new_score >= 0.70 and difficulty != "explain_back":
        decision = "explain_it_back"  # Request self-explanation in student's own words for gold-standard mastery
    elif new_score >= 0.50:
        decision = "reinforce_with_example"
    elif eval_result.misconception or attempt_count >= 2:
        decision = "switch_strategy_reteach"
    else:
        decision = "simpler_check"

    # P3 Production Integration: Emit Standard Learning Evidence
    try:
        from app.services.lesson_planner.vnext.shared_context import LearningEvidenceService
        from app.services.lesson_planner.schemas import LearningEvidenceRecord
        rec = LearningEvidenceRecord(
            student_id="student_teach_me",
            concept_id=getattr(eval_result, "concept_id", "teach_me_concept") or "teach_me_concept",
            source_type="teach_me",
            source_id="session_auto",
            question_id=f"eval_{difficulty}",
            correctness=(eval_result.correctness == "correct"),
            confidence=round(max(0.1, eval_result.score), 2),
            misconception_candidate=eval_result.misconception
        )
        LearningEvidenceService.record_evidence(rec)
    except Exception:
        pass

    return new_score, delta, label, decision
