"""
LearnByGenie — Practice Repository Layer (Feature 6, §20, §21, §23, §24, §43, §45, §46)
========================================================================================
Authoritative persistence for:
- practice_sessions (durable session state & optimistic sequence tracking)
- practice_responses (idempotent submission telemetry)
- In-memory fallback cache with strict remote PostgreSQL synchronization
"""
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from app.core.logging import logger
from app.db.supabase_client import supabase
from .schemas import (
    PracticeSession, PracticeResponse, PracticeSessionStatus,
    DifficultyBand, AssistanceLevel, PracticeMode
)


class PracticeRepository:
    """
    Repository for Adaptive Practice sessions and responses.
    """

    _sessions_cache: Dict[str, PracticeSession] = {}
    _responses_cache: Dict[str, PracticeResponse] = {}      # Key: response.id
    _responses_by_session: Dict[str, List[str]] = {}       # Key: session_id -> list of response_ids
    _attempt_idempotency_map: Dict[str, str] = {}           # Key: f"{session_id}:{item_id}:{attempt_seq}" -> resp_id
    _sequence_map: Dict[str, str] = {}                      # Key: f"{session_id}:{question_index}" -> resp_id

    @classmethod
    def clear_memory_cache(cls) -> None:
        cls._sessions_cache.clear()
        cls._responses_cache.clear()
        cls._responses_by_session.clear()
        cls._attempt_idempotency_map.clear()
        cls._sequence_map.clear()

    # ─── 1. PRACTICE SESSIONS ─────────────────────────────────────────────────

    @classmethod
    def save_session(cls, session: PracticeSession) -> PracticeSession:
        """Saves session state to both memory and remote PostgreSQL."""
        session.updated_at = datetime.now(timezone.utc)
        cls._sessions_cache[session.id] = session

        if supabase is not None:
            try:
                row = {
                    "id": session.id,
                    "user_id": session.user_id,
                    "subject": session.subject,
                    "mode": session.mode.value,
                    "curriculum": session.curriculum,
                    "exam_track": session.exam_track,
                    "enrolled_grade": session.enrolled_grade,
                    "grade_band": session.grade_band,
                    "requested_skill_id": session.requested_skill_id,
                    "current_skill_id": session.current_skill_id,
                    "current_item_id": session.current_item_id,
                    "question_index": session.question_index,
                    "question_budget": session.question_budget,
                    "current_difficulty": session.current_difficulty.value,
                    "consecutive_correct": session.consecutive_correct,
                    "consecutive_incorrect": session.consecutive_incorrect,
                    "active_hints_used": session.active_hints_used,
                    "policy_version": session.policy_version,
                    "status": session.status.value,
                    "asked_item_ids": session.asked_item_ids,
                    "skills_practiced": session.skills_practiced,
                    "selection_context": session.selection_context,
                    "started_at": session.started_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                }
                supabase.table("practice_sessions").upsert(row).execute()
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote session upsert notice: {e}")

        return session

    @classmethod
    def get_session(cls, session_id: str) -> Optional[PracticeSession]:
        """Retrieves session from memory cache or remote PostgreSQL."""
        if session_id in cls._sessions_cache:
            return cls._sessions_cache[session_id]

        if supabase is not None:
            try:
                res = supabase.table("practice_sessions").select("*").eq("id", session_id).execute()
                if res and res.data:
                    row = res.data[0]
                    session = PracticeSession(
                        id=row["id"],
                        user_id=row["user_id"],
                        subject=row["subject"],
                        mode=PracticeMode(row["mode"]),
                        curriculum=row.get("curriculum", "CBSE"),
                        exam_track=row.get("exam_track", "Boards"),
                        enrolled_grade=row.get("enrolled_grade", 10),
                        grade_band=row.get("grade_band", "secondary"),
                        requested_skill_id=row.get("requested_skill_id"),
                        current_skill_id=row.get("current_skill_id"),
                        current_item_id=row.get("current_item_id"),
                        question_index=row.get("question_index", 0),
                        question_budget=row.get("question_budget", 10),
                        current_difficulty=DifficultyBand.from_str(row.get("current_difficulty", "STANDARD")),
                        consecutive_correct=row.get("consecutive_correct", 0),
                        consecutive_incorrect=row.get("consecutive_incorrect", 0),
                        active_hints_used=row.get("active_hints_used", 0),
                        policy_version=row.get("policy_version", "1.0.0"),
                        status=PracticeSessionStatus(row.get("status", "IN_PROGRESS")),
                        asked_item_ids=row.get("asked_item_ids", []),
                        skills_practiced=row.get("skills_practiced", []),
                        selection_context=row.get("selection_context", {}),
                        started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(timezone.utc),
                        updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(timezone.utc),
                        completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None
                    )
                    cls._sessions_cache[session.id] = session
                    return session
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote get_session error: {e}")

        return None

    @classmethod
    def get_active_session_for_user(cls, user_id: str, subject: Optional[str] = None) -> Optional[PracticeSession]:
        """Finds any ongoing session for user in progress."""
        for s in cls._sessions_cache.values():
            if s.user_id == user_id and s.status == PracticeSessionStatus.IN_PROGRESS:
                if subject is None or s.subject.lower() == subject.lower():
                    return s

        if supabase is not None:
            try:
                q = supabase.table("practice_sessions").select("*").eq("user_id", user_id).eq("status", "IN_PROGRESS")
                if subject:
                    q = q.eq("subject", subject)
                res = q.order("updated_at", desc=True).limit(1).execute()
                if res and res.data:
                    return cls.get_session(res.data[0]["id"])
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote get_active_session error: {e}")

        return None

    # ─── 2. PRACTICE RESPONSES & IDEMPOTENCY ──────────────────────────────────

    @classmethod
    def record_response(cls, response: PracticeResponse) -> Tuple[PracticeResponse, bool]:
        """
        Idempotently records a practice response (§21, §23, §45, §46).
        Returns (saved_response, is_new).
        If (session_id, item_id, attempt_sequence) was already submitted, returns existing record.
        """
        attempt_key = f"{response.session_id}:{response.item_id}:{response.attempt_sequence}"
        seq_key = f"{response.session_id}:{response.question_index}"

        # 1. Idempotency check: attempt retry
        if attempt_key in cls._attempt_idempotency_map:
            existing_id = cls._attempt_idempotency_map[attempt_key]
            return cls._responses_cache[existing_id], False

        # 2. Concurrency check: duplicate question_index submission (multi-tab race)
        if seq_key in cls._sequence_map:
            existing_id = cls._sequence_map[seq_key]
            return cls._responses_cache[existing_id], False

        # 3. Remote PostgreSQL idempotency check
        if supabase is not None:
            try:
                res = supabase.table("practice_responses").select("*").eq("session_id", response.session_id).eq("item_id", response.item_id).eq("attempt_sequence", response.attempt_sequence).execute()
                if res and res.data:
                    row = res.data[0]
                    existing_resp = cls._row_to_response(row)
                    cls._cache_response(existing_resp)
                    return existing_resp, False
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote check idempotency warning: {e}")

        # 4. Save new response
        cls._cache_response(response)

        if supabase is not None:
            try:
                row = {
                    "id": response.id,
                    "session_id": response.session_id,
                    "user_id": response.user_id,
                    "item_id": response.item_id,
                    "skill_id": response.skill_id,
                    "question_index": response.question_index,
                    "student_response": response.student_response,
                    "correctness": response.correctness,
                    "assistance_level": response.assistance_level.value,
                    "difficulty_band": response.difficulty_band.value,
                    "response_time_ms": response.response_time_ms,
                    "attempt_sequence": response.attempt_sequence,
                    "selection_reason": response.selection_reason,
                    "selection_category": response.selection_category,
                    "hints_requested": response.hints_requested,
                    "provenance": response.provenance,
                    "created_at": response.created_at.isoformat()
                }
                supabase.table("practice_responses").insert(row).execute()
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote insert response notice: {e}")

        return response, True

    @classmethod
    def get_session_responses(cls, session_id: str) -> List[PracticeResponse]:
        """Retrieves all responses for session in chronological sequence."""
        resp_ids = cls._responses_by_session.get(session_id, [])
        if resp_ids:
            return sorted(
                [cls._responses_cache[rid] for rid in resp_ids if rid in cls._responses_cache],
                key=lambda r: r.question_index
            )

        if supabase is not None:
            try:
                res = supabase.table("practice_responses").select("*").eq("session_id", session_id).order("question_index", desc=False).execute()
                if res and res.data:
                    ret = [cls._row_to_response(r) for r in res.data]
                    for r in ret:
                        cls._cache_response(r)
                    return ret
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote get_session_responses error: {e}")

        return []

    @classmethod
    def get_user_recent_responses(cls, user_id: str, limit: int = 50) -> List[PracticeResponse]:
        """Retrieves recent responses across all sessions for learner context / anti-repetition."""
        user_resps = [r for r in cls._responses_cache.values() if r.user_id == user_id]
        if user_resps:
            return sorted(user_resps, key=lambda r: r.created_at, reverse=True)[:limit]

        if supabase is not None:
            try:
                res = supabase.table("practice_responses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
                if res and res.data:
                    return [cls._row_to_response(r) for r in res.data]
            except Exception as e:
                logger.warning(f"[PracticeRepo] Remote get_user_recent_responses error: {e}")

        return []

    # ─── INTERNAL HELPERS ─────────────────────────────────────────────────────

    @classmethod
    def _cache_response(cls, response: PracticeResponse) -> None:
        cls._responses_cache[response.id] = response
        cls._responses_by_session.setdefault(response.session_id, []).append(response.id)
        attempt_key = f"{response.session_id}:{response.item_id}:{response.attempt_sequence}"
        seq_key = f"{response.session_id}:{response.question_index}"
        cls._attempt_idempotency_map[attempt_key] = response.id
        cls._sequence_map[seq_key] = response.id

    @classmethod
    def _row_to_response(cls, row: Dict[str, Any]) -> PracticeResponse:
        return PracticeResponse(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            item_id=row["item_id"],
            skill_id=row["skill_id"],
            question_index=row.get("question_index", 0),
            student_response=row["student_response"],
            correctness=row["correctness"],
            assistance_level=AssistanceLevel(row.get("assistance_level", "INDEPENDENT")),
            difficulty_band=DifficultyBand.from_str(row.get("difficulty_band", "STANDARD")),
            response_time_ms=row.get("response_time_ms", 0),
            attempt_sequence=row.get("attempt_sequence", 1),
            selection_reason=row.get("selection_reason", ""),
            selection_category=row.get("selection_category", ""),
            hints_requested=row.get("hints_requested", 0),
            provenance=row.get("provenance", "CURATED"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc)
        )
