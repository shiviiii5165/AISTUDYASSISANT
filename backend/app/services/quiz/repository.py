"""
Quiz Engine — Persistence & Ownership Layer
===========================================
All DB access for the quiz engine, plus the ownership checks that every
quiz/source access must pass (§38, §39).

Security posture: the backend uses the Supabase service-role key, so RLS does
NOT constrain these queries (see security.md Coverage Notes). Ownership is
therefore enforced HERE, in application code, on every read/write — the same
bug class as security.md #2–#5. A client-supplied quiz_id / source_id is never
trusted without one of these checks.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

from app.db.supabase_client import supabase
from .schemas import Quiz, QuizQuestion, QuizAttempt


class OwnershipError(PermissionError):
    """Raised when the current user does not own the requested resource."""


class NotFoundError(Exception):
    """Raised when a resource does not exist at all."""


# ─── Ownership checks (§38, §39) ─────────────────────────────────────────────

def verify_quiz_owner(quiz_id: str, user_id: str) -> Dict[str, Any]:
    """Return the quiz row iff it exists AND is owned by user_id, else raise."""
    res = supabase.table("quizzes").select("*").eq("id", quiz_id).limit(1).execute()
    rows = res.data or []
    if not rows:
        raise NotFoundError("quiz not found")
    quiz = rows[0]
    if quiz.get("owner_user_id") != user_id:
        # Do not leak existence details beyond "you can't have this".
        raise OwnershipError("not authorized for this quiz")
    return quiz


def verify_source_ownership(source_type: str, source_ids: List[str], user_id: str) -> None:
    """
    Confirm the current user owns every requested source BEFORE any retrieval
    (§39). Topic-only quizzes carry no sources and pass trivially.

    For document sources (pdf/ppt/uploaded material) this checks the `pdfs`
    table's owning user_id — the exact ownership join whose absence caused
    security.md's Critical/High findings. Building generation against an
    unverified client-supplied source_id would reintroduce that leak.
    """
    if source_type in ("topic", "teach_me", "stage") and not source_ids:
        return
    if not source_ids:
        return

    res = supabase.table("pdfs").select("id, user_id").in_("id", source_ids).execute()
    found = {r["id"]: r.get("user_id") for r in (res.data or [])}

    for sid in source_ids:
        if sid not in found:
            raise NotFoundError(f"source not found: {sid}")
        if found[sid] != user_id:
            raise OwnershipError("not authorized for one or more sources")


# ─── Quiz CRUD ───────────────────────────────────────────────────────────────

def create_quiz(quiz: Quiz) -> Dict[str, Any]:
    res = supabase.table("quizzes").insert(quiz.to_db_dict()).execute()
    return (res.data or [None])[0]


def get_quiz_by_idempotency(owner_user_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
    """Support idempotent generation (§55): same key → same quiz."""
    if not idempotency_key:
        return None
    res = (
        supabase.table("quizzes")
        .select("*")
        .eq("owner_user_id", owner_user_id)
        .eq("cache_key", f"idem:{idempotency_key}")
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def list_quizzes(owner_user_id: str) -> List[Dict[str, Any]]:
    res = (
        supabase.table("quizzes")
        .select("*")
        .eq("owner_user_id", owner_user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def update_quiz_status(quiz_id: str, status: str) -> None:
    supabase.table("quizzes").update({"status": status}).eq("id", quiz_id).execute()


def delete_quiz(quiz_id: str) -> None:
    supabase.table("quizzes").delete().eq("id", quiz_id).execute()


# ─── Questions ───────────────────────────────────────────────────────────────

def insert_questions(quiz_id: str, questions: List[QuizQuestion]) -> List[Dict[str, Any]]:
    if not questions:
        return []
    rows = []
    for i, q in enumerate(questions):
        q.quiz_id = quiz_id
        d = q.to_db_dict()
        if not d.get("order_index"):
            d["order_index"] = i
        rows.append(d)
    res = supabase.table("quiz_questions").insert(rows).execute()
    return res.data or []


def get_questions(quiz_id: str) -> List[Dict[str, Any]]:
    res = (
        supabase.table("quiz_questions")
        .select("*")
        .eq("quiz_id", quiz_id)
        .order("order_index")
        .execute()
    )
    return res.data or []


def get_question(question_id: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("quiz_questions").select("*").eq("id", question_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def update_question(question_id: str, fields: Dict[str, Any]) -> None:
    if fields:
        supabase.table("quiz_questions").update(fields).eq("id", question_id).execute()


def delete_question(question_id: str) -> None:
    supabase.table("quiz_questions").delete().eq("id", question_id).execute()


def reorder_questions(quiz_id: str, ordered_ids: List[str]) -> None:
    """Rewrite order_index to match the supplied ordering (§50)."""
    for idx, qid in enumerate(ordered_ids):
        supabase.table("quiz_questions").update({"order_index": idx})\
            .eq("id", qid).eq("quiz_id", quiz_id).execute()


# ─── Attempts ────────────────────────────────────────────────────────────────

def create_attempt(attempt: QuizAttempt) -> Dict[str, Any]:
    row = {
        "quiz_id": attempt.quiz_id,
        "user_id": attempt.user_id,
        "status": attempt.status.value,
        "expires_at": attempt.expires_at.isoformat() if attempt.expires_at else None,
        "total_questions": attempt.total_questions,
        "question_order_seed": attempt.question_order_seed,
        "option_order_seed": attempt.option_order_seed,
        "idempotency_key": attempt.idempotency_key,
    }
    res = supabase.table("quiz_attempts").insert(row).execute()
    return (res.data or [None])[0]


def get_attempt(attempt_id: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("quiz_attempts").select("*").eq("id", attempt_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def get_attempt_by_idempotency(quiz_id: str, user_id: str, key: str) -> Optional[Dict[str, Any]]:
    if not key:
        return None
    res = (
        supabase.table("quiz_attempts")
        .select("*")
        .eq("quiz_id", quiz_id)
        .eq("user_id", user_id)
        .eq("idempotency_key", key)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def finalize_attempt(attempt_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    res = supabase.table("quiz_attempts").update(fields).eq("id", attempt_id).execute()
    return (res.data or [None])[0]
