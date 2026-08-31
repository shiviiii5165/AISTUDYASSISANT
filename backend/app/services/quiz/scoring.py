"""
Quiz Engine — Deterministic Scoring, Shuffling & Timing (§10, §37, §38, §41, §43, §63)
======================================================================================
Pure-Python. NO LLM calls, NO client-trusted values.

  * Scoring grades a submission against the stored `correct_answer` only. A
    client-supplied score or is_correct is never read (§10, §38) — closing the
    same trust-boundary gap security.md #13 left for this implementation.
  * Shuffling is seeded (§41). Storing the seed lets the server reconstruct the
    exact order the student saw, so grading and review align (§63).
  * Timing is server-enforced (§43): elapsed is derived from stored timestamps,
    never from a client-reported elapsed value.
"""
from __future__ import annotations
import random
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from .schemas import QuizQuestion, QuestionType, PerQuestionResult


# ─── Shuffle (seeded, reconstructable) ───────────────────────────────────────

def make_seed() -> int:
    """A fresh 63-bit seed per attempt. Stored so the order can be replayed."""
    return random.getrandbits(63)


def shuffled_question_order(question_ids: List[str], seed: int) -> List[str]:
    """Deterministic question order for a given seed (§41, §63)."""
    order = list(question_ids)
    random.Random(seed).shuffle(order)
    return order


def shuffled_option_order(question_id: str, options: List[str], seed: int) -> List[str]:
    """
    Deterministic per-question option order. Deriving each question's RNG from
    (seed, question_id) means one stored seed reproduces every question's option
    order, and adding/removing a question doesn't disturb the others.
    """
    order = list(options)
    # Combine the attempt seed with a stable hash of the question id.
    qhash = int.from_bytes(question_id.encode("utf-8"), "little", signed=False) if question_id else 0
    random.Random(seed ^ (qhash & ((1 << 63) - 1))).shuffle(order)
    return order


# ─── Timing (server-enforced) ────────────────────────────────────────────────

def compute_expires_at(started_at: datetime, timer_seconds: Optional[int]) -> Optional[datetime]:
    if not timer_seconds or timer_seconds <= 0:
        return None
    return started_at + timedelta(seconds=timer_seconds)


def is_expired(expires_at: Optional[datetime], now: Optional[datetime] = None) -> bool:
    if expires_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    return now > expires_at


def server_time_spent(started_at: datetime, submitted_at: datetime) -> int:
    """Elapsed seconds from stored timestamps — never a client-reported value."""
    delta = (submitted_at - started_at).total_seconds()
    return max(0, int(delta))


# ─── Answer normalization & grading ──────────────────────────────────────────

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _as_list(v: Union[str, List[str], None]) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def grade_question(q: QuizQuestion, given: Union[str, List[str], None]) -> Tuple[bool, float]:
    """
    Grade one answer against the stored correct_answer.
    Returns (is_correct, partial_credit 0.0–1.0). Deterministic; no LLM.

    short_answer awards partial credit by accepted-keyword overlap; a semantic
    judgment call for genuinely open responses is delegated to the QA/judge path
    (Phase 3) and is out of scope for this deterministic grader.
    """
    correct = [_normalize(c) for c in _as_list(q.correct_answer) if _normalize(c)]
    given_norm = [_normalize(g) for g in _as_list(given) if _normalize(g)]

    if not given_norm:
        return False, 0.0

    if q.type in (QuestionType.MCQ, QuestionType.TRUE_FALSE):
        # Exact membership: the selected option must be an accepted answer.
        ok = bool(given_norm) and all(g in correct for g in given_norm) and \
            len(given_norm) == len([c for c in correct])
        # For single-select, treat first given as the choice.
        single_ok = given_norm[0] in correct
        is_correct = single_ok if len(correct) == 1 else ok
        return is_correct, (1.0 if is_correct else 0.0)

    if q.type == QuestionType.FILL_BLANK:
        is_correct = given_norm[0] in correct
        return is_correct, (1.0 if is_correct else 0.0)

    if q.type == QuestionType.SHORT_ANSWER:
        g = given_norm[0]
        # Full credit on exact/accepted match.
        if g in correct:
            return True, 1.0
        # Partial credit: overlap of accepted keywords appearing in the answer.
        accepted_terms = set()
        for c in correct:
            accepted_terms |= {t for t in re.findall(r"[a-z0-9]+", c) if len(t) > 2}
        if not accepted_terms:
            return False, 0.0
        hit = sum(1 for t in accepted_terms if t in g)
        partial = round(hit / len(accepted_terms), 2)
        return (partial >= 0.99), partial

    return False, 0.0


def score_attempt(
    questions: List[QuizQuestion],
    answers: Dict[str, Union[str, List[str], None]],
) -> Dict[str, Any]:
    """
    Grade a full attempt server-side (§10, §38).

    `answers` maps question_id -> given answer. Unanswered questions score 0.
    Returns score (0–100), correct_count, per-question results, and per-concept
    rollup for the mastery feed (§30).
    """
    per_results: List[PerQuestionResult] = []
    total = len(questions)
    correct_count = 0
    weighted_sum = 0.0
    concept_agg: Dict[str, Dict[str, float]] = {}

    for q in questions:
        qid = q.id or ""
        given = answers.get(qid)
        is_correct, partial = grade_question(q, given)
        if is_correct:
            correct_count += 1
        weighted_sum += partial

        per_results.append(PerQuestionResult(
            question_id=qid,
            concept_id=q.concept_id,
            given_answer=given,
            is_correct=is_correct,
            partial=partial,
            correct_answer=q.correct_answer,
        ))

        if q.concept_id:
            agg = concept_agg.setdefault(q.concept_id, {"correct": 0.0, "total": 0.0})
            agg["total"] += 1.0
            agg["correct"] += partial

    concept_performance = {
        cid: {
            "correct": round(v["correct"], 2),
            "total": int(v["total"]),
            "accuracy": round(v["correct"] / v["total"], 2) if v["total"] else 0.0,
        }
        for cid, v in concept_agg.items()
    }

    score = round((weighted_sum / total) * 100, 2) if total else 0.0

    return {
        "score": score,
        "correct_count": correct_count,
        "total_questions": total,
        "per_question_results": [r.dict() for r in per_results],
        "concept_performance": concept_performance,
    }
