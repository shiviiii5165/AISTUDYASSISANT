"""
Quiz Engine — Attempt Lifecycle & Server-Side Scoring (Phase 4)
==============================================================
Deterministic. Starts attempts, enforces the timer server-side (§43), grades
against stored answers only (§10, §38), and makes submission idempotent so a
duplicate submit never double-scores (§55, §56). Attempt state lives in the DB,
so it survives a mid-attempt refresh (§57).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

from . import repository as repo
from .schemas import QuizQuestion, QuizAttempt, AttemptStatus, QuestionType
from . import scoring


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _row_to_question(r: Dict[str, Any]) -> QuizQuestion:
    ca = r.get("correct_answer")
    if isinstance(ca, list) and len(ca) == 1:
        ca = ca[0]
    return QuizQuestion(
        id=r.get("id"),
        quiz_id=r.get("quiz_id"),
        question_text=r.get("question_text", ""),
        type=QuestionType(r.get("type", "mcq")),
        options=r.get("options") or [],
        correct_answer=ca if ca is not None else "",
        concept_id=r.get("concept_id"),
        difficulty=r.get("difficulty", "medium"),
        order_index=r.get("order_index", 0),
    )


def start_attempt(quiz_id: str, user_id: str, quiz_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new attempt with stored shuffle seeds and a server-computed
    deadline, then return the student-facing question payload in shuffled order.
    Correct answers are NOT included in the returned payload.
    """
    question_rows = repo.get_questions(quiz_id)
    questions = [_row_to_question(r) for r in question_rows]

    config = quiz_row.get("config") or {}
    timer_seconds = config.get("timer_seconds")
    shuffle_q = config.get("shuffle_questions", True)
    shuffle_o = config.get("shuffle_options", True)

    started_at = datetime.now(timezone.utc)
    q_seed = scoring.make_seed()
    o_seed = scoring.make_seed()
    expires_at = scoring.compute_expires_at(started_at, timer_seconds)

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=started_at,
        expires_at=expires_at,
        total_questions=len(questions),
        question_order_seed=q_seed,
        option_order_seed=o_seed,
    )
    row = repo.create_attempt(attempt)

    payload = _render_questions(questions, q_seed, o_seed, shuffle_q, shuffle_o)
    return {
        "attempt_id": row["id"],
        "quiz_id": quiz_id,
        "started_at": started_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "timer_seconds": timer_seconds,
        "questions": payload,
    }


def _render_questions(
    questions: List[QuizQuestion], q_seed: int, o_seed: int,
    shuffle_q: bool, shuffle_o: bool,
) -> List[Dict[str, Any]]:
    by_id = {q.id: q for q in questions}
    ids = [q.id for q in questions]
    if shuffle_q:
        ids = scoring.shuffled_question_order(ids, q_seed)

    out = []
    for qid in ids:
        q = by_id[qid]
        d = q.to_student_dict()
        if shuffle_o and q.options:
            d["options"] = scoring.shuffled_option_order(qid, q.options, o_seed)
        out.append(d)
    return out


def submit_attempt(
    attempt_id: str,
    user_id: str,
    answers: Dict[str, Union[str, List[str], None]],
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Grade and finalize an attempt server-side. Idempotent (§55, §56): a repeated
    submit of an already-submitted attempt returns the stored result rather than
    re-grading.
    """
    attempt = repo.get_attempt(attempt_id)
    if not attempt:
        raise repo.NotFoundError("attempt not found")
    # Attempts are per-user; only the owner may submit (§38).
    if attempt.get("user_id") != user_id:
        raise repo.OwnershipError("not authorized for this attempt")

    # Already finalized → return stored result (idempotency).
    if attempt.get("status") in (AttemptStatus.SUBMITTED.value, AttemptStatus.EXPIRED.value):
        return _result_view(attempt, already="already_submitted")

    started_at = _parse_dt(attempt.get("started_at")) or datetime.now(timezone.utc)
    expires_at = _parse_dt(attempt.get("expires_at"))
    now = datetime.now(timezone.utc)

    question_rows = repo.get_questions(attempt["quiz_id"])
    questions = [_row_to_question(r) for r in question_rows]

    result = scoring.score_attempt(questions, answers)

    # Server-enforced timeout (§43): late submissions are marked expired; we
    # still record what was answered, but flag it.
    timed_out = scoring.is_expired(expires_at, now)
    status = AttemptStatus.EXPIRED.value if timed_out else AttemptStatus.SUBMITTED.value

    fields = {
        "status": status,
        "submitted_at": now.isoformat(),
        "time_spent_seconds": scoring.server_time_spent(started_at, now),
        "score": result["score"],
        "correct_count": result["correct_count"],
        "total_questions": result["total_questions"],
        "per_question_results": result["per_question_results"],
        "concept_performance": result["concept_performance"],
        "idempotency_key": idempotency_key or attempt.get("idempotency_key"),
    }
    updated = repo.finalize_attempt(attempt_id, fields)
    return _result_view(updated or {**attempt, **fields}, timed_out=timed_out)


def _result_view(attempt: Dict[str, Any], already: str = "", timed_out: bool = False) -> Dict[str, Any]:
    return {
        "attempt_id": attempt.get("id"),
        "quiz_id": attempt.get("quiz_id"),
        "status": attempt.get("status"),
        "score": attempt.get("score"),
        "correct_count": attempt.get("correct_count"),
        "total_questions": attempt.get("total_questions"),
        "time_spent_seconds": attempt.get("time_spent_seconds"),
        "per_question_results": attempt.get("per_question_results", []),
        "concept_performance": attempt.get("concept_performance", {}),
        "timed_out": timed_out or attempt.get("status") == AttemptStatus.EXPIRED.value,
        "note": already,
    }
