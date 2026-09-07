"""
Live Quiz Engine — Persistence & Participant Auth Layer
=======================================================
Handles all DB access for live quiz sessions, participant JWT issuance &
verification, response storage with duplicate prevention, and audit event logs.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from jose import jwt, JWTError

from app.db.supabase_client import supabase
from app.core.config import settings
from app.core.logging import logger
from .schemas import (
    LiveSessionStatus, ACTIVE_SESSION_STATUSES, LiveParticipantStatus
)


class OwnershipError(PermissionError):
    """Raised when host does not own the requested live session."""


class NotFoundError(Exception):
    """Raised when resource does not exist."""


class StateTransitionError(ValueError):
    """Raised on illegal state machine transition."""


class DatabaseWriteError(RuntimeError):
    """Raised when a persistent database write to Supabase fails."""


# In-memory store fallback for testing or when Supabase is disconnected
_MEM_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MEM_PARTICIPANTS: Dict[str, Dict[str, Any]] = {}
_MEM_RESPONSES: Dict[str, Dict[str, Any]] = {}  # key: (session_id, participant_id, question_id)
_MEM_EVENTS: List[Dict[str, Any]] = []

# Persistence toggle: True by default; can be disabled for isolated in-memory unit tests
_PERSISTENCE_ENABLED: bool = True

def set_persistence_enabled(enabled: bool) -> None:
    """Explicitly enable or disable Supabase persistence."""
    global _PERSISTENCE_ENABLED
    _PERSISTENCE_ENABLED = enabled

def is_persistence_enabled() -> bool:
    """Check if Supabase persistence is active and configured."""
    return _PERSISTENCE_ENABLED and (supabase is not None)

_JWT_SECRET = getattr(settings, "SUPABASE_JWT_SECRET", "") or "teachgenie-live-secret-key-default-2026"
_JWT_ALGORITHM = "HS256"


# ─── Participant JWT Token Helpers ──────────────────────────────────────────

def create_participant_token(participant_id: str, session_id: str, display_name: str) -> str:
    """Issue a cryptographically signed HMAC-SHA256 Participant JWT."""
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {
        "sub": participant_id,
        "session_id": session_id,
        "display_name": display_name,
        "role": "participant",
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def verify_participant_token(token: str) -> Dict[str, Any]:
    """Verify and decode participant JWT. Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("role") != "participant":
            raise ValueError("Invalid token role")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid participant token: {e}") from e


# ─── Session Persistence & Ownership ─────────────────────────────────────────

def create_live_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist a new live quiz session to Supabase.
    Raises DatabaseWriteError if Supabase persistence is enabled and write fails.
    """
    sid = session_data.get("id")

    if is_persistence_enabled():
        try:
            res = supabase.table("live_quiz_sessions").insert(session_data).execute()
            if res.data:
                _MEM_SESSIONS[sid] = res.data[0]
                return res.data[0]
            raise DatabaseWriteError(f"Supabase returned empty response on session insert for {sid}")
        except Exception as e:
            _MEM_SESSIONS.pop(sid, None)
            logger.error(f"[LiveQuizRepo] Supabase insert failed: {e}")
            raise DatabaseWriteError(f"Failed to persist live quiz session {sid}: {e}") from e

    _MEM_SESSIONS[sid] = dict(session_data)
    return session_data


def get_live_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session by ID."""
    if session_id in _MEM_SESSIONS:
        return _MEM_SESSIONS[session_id]

    if supabase:
        try:
            res = supabase.table("live_quiz_sessions").select("*").eq("id", session_id).limit(1).execute()
            rows = res.data or []
            if rows:
                _MEM_SESSIONS[session_id] = rows[0]
                return rows[0]
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase get session failed: {e}")

    return None


def verify_session_host(session_id: str, host_user_id: str) -> Dict[str, Any]:
    """Verify that host_user_id owns this session."""
    sess = get_live_session(session_id)
    if not sess:
        raise NotFoundError(f"Live session {session_id} not found")
    if sess.get("host_user_id") != host_user_id:
        raise OwnershipError("Not authorized to manage this live session")
    return sess


def find_active_session_by_code(join_code: str) -> Optional[Dict[str, Any]]:
    """
    Look up an active session by its 6-digit code.
    Matches partial unique index: status IN ('CREATED', 'LOBBY', 'LIVE', 'PAUSED').
    """
    clean_code = str(join_code).strip()

    # Check memory first
    for s in _MEM_SESSIONS.values():
        if s.get("join_code") == clean_code and s.get("status") in [
            st.value for st in ACTIVE_SESSION_STATUSES
        ]:
            return s

    if supabase:
        try:
            active_statuses = [st.value for st in ACTIVE_SESSION_STATUSES]
            res = (
                supabase.table("live_quiz_sessions")
                .select("*")
                .eq("join_code", clean_code)
                .in_("status", active_statuses)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                _MEM_SESSIONS[rows[0]["id"]] = rows[0]
                return rows[0]
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase find code failed: {e}")

    return None


def update_live_session(
    session_id: str,
    fields: Dict[str, Any],
    expected_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Update live session row with optimistic concurrency bump."""
    sess = get_live_session(session_id)
    if not sess:
        raise NotFoundError("Session not found")

    cur_version = sess.get("version", 1)
    if expected_version is not None and expected_version != cur_version:
        raise StateTransitionError(
            f"Optimistic lock failure: expected version {expected_version}, found {cur_version}"
        )

    updated_fields = dict(fields)
    updated_fields["version"] = cur_version + 1
    updated_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    sess.update(updated_fields)
    _MEM_SESSIONS[session_id] = sess

    if is_persistence_enabled():
        try:
            supabase.table("live_quiz_sessions").update(updated_fields).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"[LiveQuizRepo] Supabase update session failed: {e}")
            raise DatabaseWriteError(f"Failed to persist live session update for {session_id}: {e}") from e

    return sess


# ─── Participant Operations ──────────────────────────────────────────────────

def create_participant(p_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a new participant.
    Raises DatabaseWriteError if Supabase persistence is enabled and write fails.
    """
    pid = p_data["id"]

    if is_persistence_enabled():
        try:
            res = supabase.table("live_quiz_participants").insert(p_data).execute()
            if res.data:
                _MEM_PARTICIPANTS[pid] = res.data[0]
                return res.data[0]
            raise DatabaseWriteError(f"Supabase returned empty response on participant insert for {pid}")
        except Exception as e:
            _MEM_PARTICIPANTS.pop(pid, None)
            logger.error(f"[LiveQuizRepo] Supabase create participant failed: {e}")
            raise DatabaseWriteError(f"Failed to persist participant {pid}: {e}") from e

    _MEM_PARTICIPANTS[pid] = dict(p_data)
    return p_data


def get_participant(participant_id: str) -> Optional[Dict[str, Any]]:
    if participant_id in _MEM_PARTICIPANTS:
        return _MEM_PARTICIPANTS[participant_id]

    if supabase:
        try:
            res = supabase.table("live_quiz_participants").select("*").eq("id", participant_id).limit(1).execute()
            rows = res.data or []
            if rows:
                _MEM_PARTICIPANTS[participant_id] = rows[0]
                return rows[0]
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase get participant failed: {e}")

    return None


def list_participants(session_id: str) -> List[Dict[str, Any]]:
    """List all participants for a session."""
    mem_matches = [
        p for p in _MEM_PARTICIPANTS.values()
        if p.get("session_id") == session_id
    ]

    if supabase:
        try:
            res = (
                supabase.table("live_quiz_participants")
                .select("*")
                .eq("session_id", session_id)
                .order("score", desc=True)
                .execute()
            )
            rows = res.data or []
            if rows:
                for r in rows:
                    _MEM_PARTICIPANTS[r["id"]] = r
                return rows
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase list participants failed: {e}")

    return sorted(mem_matches, key=lambda x: x.get("score", 0), reverse=True)


def update_participant(participant_id: str, fields: Dict[str, Any]) -> None:
    p = get_participant(participant_id)
    if p:
        p.update(fields)
        p["updated_at"] = datetime.now(timezone.utc).isoformat()
        _MEM_PARTICIPANTS[participant_id] = p

    if is_persistence_enabled():
        try:
            supabase.table("live_quiz_participants").update(fields).eq("id", participant_id).execute()
        except Exception as e:
            logger.error(f"[LiveQuizRepo] Supabase update participant failed: {e}")
            raise DatabaseWriteError(f"Failed to persist participant update for {participant_id}: {e}") from e


# ─── Response Deduplication & Persistence ────────────────────────────────────

def record_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record an answer submission with idempotency guard.
    (session_id, participant_id, question_id) is unique.
    """
    sid = response_data["session_id"]
    pid = response_data["participant_id"]
    qid = response_data["question_id"]
    key = (sid, pid, qid)

    # Idempotency check: if already recorded, return existing row
    if key in _MEM_RESPONSES:
        return _MEM_RESPONSES[key]

    _MEM_RESPONSES[key] = dict(response_data)

    if is_persistence_enabled():
        try:
            res = supabase.table("live_quiz_responses").insert(response_data).execute()
            if res.data:
                _MEM_RESPONSES[key] = res.data[0]
                return res.data[0]
        except Exception as e:
            err_str = str(e).lower()
            if "duplicate" in err_str or "unique constraint" in err_str or "23505" in err_str:
                logger.info(f"[LiveQuizRepo] Duplicate response submission for {key}, returning cached response.")
                return _MEM_RESPONSES.get(key, response_data)
            _MEM_RESPONSES.pop(key, None)
            logger.error(f"[LiveQuizRepo] Supabase insert response failed: {e}")
            raise DatabaseWriteError(f"Failed to persist response {key}: {e}") from e

    _MEM_RESPONSES[key] = dict(response_data)
    return response_data


def get_responses_for_session(session_id: str) -> List[Dict[str, Any]]:
    mem_matches = [
        r for r in _MEM_RESPONSES.values()
        if r.get("session_id") == session_id
    ]

    if supabase:
        try:
            res = (
                supabase.table("live_quiz_responses")
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase get session responses failed: {e}")

    return mem_matches


def get_responses_for_participant(session_id: str, participant_id: str) -> List[Dict[str, Any]]:
    mem_matches = [
        r for r in _MEM_RESPONSES.values()
        if r.get("session_id") == session_id and r.get("participant_id") == participant_id
    ]

    if supabase:
        try:
            res = (
                supabase.table("live_quiz_responses")
                .select("*")
                .eq("session_id", session_id)
                .eq("participant_id", participant_id)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase get participant responses failed: {e}")

    return mem_matches


# ─── Audit Event Log ─────────────────────────────────────────────────────────

def log_event(session_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    row = {
        "session_id": session_id,
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEM_EVENTS.append(row)

    if supabase:
        try:
            supabase.table("live_quiz_events").insert(row).execute()
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase log event failed: {e}")
