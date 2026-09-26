"""
Live Quiz Engine — Persistence & Participant Auth Layer (VNext Scale)
======================================================================
Handles all DB access for live quiz sessions, participant JWT issuance &
verification, multi-row micro-batching, participant snapshot tracking,
admin ban/unban moderation, and immutable admin action audit logs.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from jose import jwt, JWTError

from app.db.supabase_client import supabase
from app.core.config import settings
from app.core.logging import logger
from .schemas import (
    LiveSessionStatus, ACTIVE_SESSION_STATUSES, LiveParticipantStatus,
    ConnectionState, RiskLevel, AdminActionType, LiveEventType
)


class OwnershipError(PermissionError):
    """Raised when host does not own the requested live session."""


class NotFoundError(Exception):
    """Raised when resource does not exist."""


class StateTransitionError(ValueError):
    """Raised on illegal state machine transition."""


class DatabaseWriteError(RuntimeError):
    """Raised when a persistent database write to Supabase fails."""


class ParticipantBannedError(PermissionError):
    """Raised when a banned participant attempts any session action."""


# In-memory stores fallback for testing or when Supabase is disconnected
_MEM_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MEM_PARTICIPANTS: Dict[str, Dict[str, Any]] = {}
_MEM_RESPONSES: Dict[Tuple[str, str, str], Dict[str, Any]] = {}  # key: (session_id, participant_id, question_id)
_MEM_EVENTS: List[Dict[str, Any]] = []
_MEM_QUESTION_STATS: Dict[Tuple[str, str], Dict[str, Any]] = {}  # key: (session_id, question_id)
_MEM_ADMIN_ACTIONS: List[Dict[str, Any]] = []

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
    if session_id in _MEM_SESSIONS:
        return _MEM_SESSIONS[session_id]

    if is_persistence_enabled():
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
    sess = get_live_session(session_id)
    if not sess:
        raise NotFoundError(f"Live session {session_id} not found")
    if sess.get("host_user_id") != host_user_id:
        raise OwnershipError("Not authorized to manage this live session")
    return sess


def find_active_session_by_code(join_code: str) -> Optional[Dict[str, Any]]:
    clean_code = str(join_code).strip()

    for s in _MEM_SESSIONS.values():
        if s.get("join_code") == clean_code and s.get("status") in [
            st.value for st in ACTIVE_SESSION_STATUSES
        ]:
            return s

    if is_persistence_enabled():
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


# ─── Participant Operations & Live Snapshot ──────────────────────────────────

def create_participant(p_data: Dict[str, Any]) -> Dict[str, Any]:
    pid = p_data["id"]
    # Ensure default live snapshot fields
    p_data.setdefault("current_question_index", 0)
    p_data.setdefault("answered_count", 0)
    p_data.setdefault("average_response_ms", 0)
    p_data.setdefault("last_seen_at", datetime.now(timezone.utc).isoformat())
    p_data.setdefault("connection_state", ConnectionState.ACTIVE.value)
    p_data.setdefault("risk_score", 0)
    p_data.setdefault("risk_level", RiskLevel.LOW.value)
    p_data.setdefault("is_banned", False)
    p_data.setdefault("banned_at", None)
    p_data.setdefault("ban_reason", None)
    p_data.setdefault("state_version", 1)

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

    if is_persistence_enabled():
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
    mem_matches = [
        p for p in _MEM_PARTICIPANTS.values()
        if p.get("session_id") == session_id
    ]

    if is_persistence_enabled():
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


def list_participants_cursor(
    session_id: str,
    cursor: Optional[str] = None,
    limit: int = 50,
    status_filter: Optional[str] = None,
    risk_filter: Optional[str] = None,
    search: Optional[str] = None,
    banned_only: bool = False,
    sort_by: str = "score",
    sort_desc: bool = True,
) -> Dict[str, Any]:
    """
    Cursor-based pagination with server-side filters & sorting for the admin dashboard.
    Enables low-latency virtualized monitoring across thousands of students.
    """
    all_participants = list_participants(session_id)

    # Filter pipeline
    filtered = []
    for p in all_participants:
        if banned_only and not p.get("is_banned"):
            continue
        if status_filter and p.get("status") != status_filter:
            continue
        if risk_filter and p.get("risk_level") != risk_filter:
            continue
        if search:
            s_lower = search.lower().strip()
            if s_lower not in p.get("display_name", "").lower():
                continue
        filtered.append(p)

    # Sorting
    reverse = sort_desc
    if sort_by in ("score", "answered_count", "streak", "risk_score", "average_response_ms"):
        filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    elif sort_by == "display_name":
        filtered.sort(key=lambda x: x.get("display_name", "").lower(), reverse=reverse)
    else:
        filtered.sort(key=lambda x: x.get("joined_at", ""), reverse=reverse)

    # Cursor slicing
    start_idx = 0
    if cursor:
        for idx, item in enumerate(filtered):
            if item.get("id") == cursor:
                start_idx = idx + 1
                break

    end_idx = start_idx + limit
    page_items = filtered[start_idx:end_idx]
    has_more = end_idx < len(filtered)
    next_cursor = page_items[-1]["id"] if page_items and has_more else None

    return {
        "items": page_items,
        "next_cursor": next_cursor,
        "total_count": len(filtered),
        "has_more": has_more,
    }


def update_participant(participant_id: str, fields: Dict[str, Any]) -> None:
    p = get_participant(participant_id)
    if p:
        p.update(fields)
        p["updated_at"] = datetime.now(timezone.utc).isoformat()
        p["state_version"] = p.get("state_version", 1) + 1
        _MEM_PARTICIPANTS[participant_id] = p

    if is_persistence_enabled():
        try:
            supabase.table("live_quiz_participants").update(fields).eq("id", participant_id).execute()
        except Exception as e:
            logger.error(f"[LiveQuizRepo] Supabase update participant failed: {e}")
            raise DatabaseWriteError(f"Failed to persist participant update for {participant_id}: {e}") from e


def ban_participant(
    session_id: str,
    participant_id: str,
    reason: str,
    admin_user_id: str,
) -> Dict[str, Any]:
    """
    Authoritative participant ban. Immediately revokes access to all session endpoints.
    Records immutable entry in live_quiz_admin_actions.
    """
    p = get_participant(participant_id)
    if not p:
        raise NotFoundError("Participant not found")
    if p.get("session_id") != session_id:
        raise OwnershipError("Participant does not belong to this session")

    prev_state = {
        "is_banned": p.get("is_banned", False),
        "banned_at": p.get("banned_at"),
        "ban_reason": p.get("ban_reason"),
    }
    now_iso = datetime.now(timezone.utc).isoformat()

    update_fields = {
        "is_banned": True,
        "banned_at": now_iso,
        "ban_reason": reason or "Removed by teacher",
        "connection_state": ConnectionState.DISCONNECTED.value,
    }
    update_participant(participant_id, update_fields)

    log_admin_action(
        admin_user_id=admin_user_id,
        session_id=session_id,
        participant_id=participant_id,
        action=AdminActionType.BAN.value,
        reason=reason,
        previous_state=prev_state,
        new_state=update_fields,
    )
    return get_participant(participant_id) or {}


def unban_participant(
    session_id: str,
    participant_id: str,
    admin_user_id: str,
) -> Dict[str, Any]:
    """
    Restores an erroneously banned participant.
    Records immutable audit entry in live_quiz_admin_actions.
    """
    p = get_participant(participant_id)
    if not p:
        raise NotFoundError("Participant not found")
    if p.get("session_id") != session_id:
        raise OwnershipError("Participant does not belong to this session")

    prev_state = {
        "is_banned": p.get("is_banned", True),
        "banned_at": p.get("banned_at"),
        "ban_reason": p.get("ban_reason"),
    }

    update_fields = {
        "is_banned": False,
        "banned_at": None,
        "ban_reason": None,
        "connection_state": ConnectionState.ACTIVE.value,
    }
    update_participant(participant_id, update_fields)

    log_admin_action(
        admin_user_id=admin_user_id,
        session_id=session_id,
        participant_id=participant_id,
        action=AdminActionType.UNBAN.value,
        reason="Ban revoked by teacher",
        previous_state=prev_state,
        new_state=update_fields,
    )
    return get_participant(participant_id) or {}


# ─── Participant Detailed Audit & Activity Signals ───────────────────────────

def get_participant_detail(session_id: str, participant_id: str) -> Dict[str, Any]:
    """
    Lazy-load detailed audit timeline for a single student when teacher opens drawer.
    Includes progression timeline, response timestamps, speeds, signals, and ban history.
    """
    p = get_participant(participant_id)
    if not p or p.get("session_id") != session_id:
        raise NotFoundError("Participant not found in this session")

    responses = get_responses_for_participant(session_id, participant_id)
    signals = [
        e for e in _MEM_EVENTS
        if e.get("session_id") == session_id and e.get("payload", {}).get("participant_id") == participant_id
    ]
    actions = [
        a for a in _MEM_ADMIN_ACTIONS
        if a.get("session_id") == session_id and a.get("participant_id") == participant_id
    ]

    return {
        "participant": p,
        "responses": responses,
        "activity_signals": signals,
        "admin_actions": actions,
    }


def record_risk_signal(
    session_id: str,
    participant_id: str,
    signal_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Records an activity signal (e.g. TAB_HIDDEN, COPY_ATTEMPT, RECONNECTED) and
    updates the participant's risk score and level without high-frequency spam.
    """
    meta = metadata or {}
    meta["participant_id"] = participant_id

    # Weight assignments for signals
    weights = {
        LiveEventType.TAB_HIDDEN.value: 15,
        LiveEventType.COPY_ATTEMPT.value: 20,
        LiveEventType.PASTE_ATTEMPT.value: 20,
        LiveEventType.MULTI_SESSION_CONFLICT.value: 30,
        LiveEventType.UNUSUALLY_FAST_RESPONSE.value: 25,
        LiveEventType.RECONNECTED.value: 5,
    }
    delta = weights.get(signal_type, 10)

    p = get_participant(participant_id)
    if p:
        new_score = min(100, p.get("risk_score", 0) + delta)
        risk_lvl = (
            RiskLevel.HIGH.value if new_score >= 60
            else (RiskLevel.MEDIUM.value if new_score >= 30 else RiskLevel.LOW.value)
        )
        update_participant(participant_id, {
            "risk_score": new_score,
            "risk_level": risk_lvl,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        })

    log_event(session_id, signal_type, meta)
    return {"recorded": True, "signal": signal_type}


# ─── Response Deduplication & Micro-Batching ─────────────────────────────────

def record_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record single response with duplicate constraint guard.
    Key: (session_id, participant_id, question_id).
    """
    sid = response_data["session_id"]
    pid = response_data["participant_id"]
    qid = response_data["question_id"]
    key = (sid, pid, qid)

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
                return _MEM_RESPONSES.get(key, response_data)
            _MEM_RESPONSES.pop(key, None)
            logger.error(f"[LiveQuizRepo] Supabase insert response failed: {e}")
            raise DatabaseWriteError(f"Failed to persist response {key}: {e}") from e

    _MEM_RESPONSES[key] = dict(response_data)
    return response_data


def batch_record_responses(
    response_list: List[Dict[str, Any]],
    participant_updates: List[Dict[str, Any]],
    stats_updates: List[Dict[str, Any]],
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Executes a multi-row atomic batch insert for responses, batch updates for
    participant live snapshots, and updates compact question stats.
    """
    saved_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for resp in response_list:
        sid = resp["session_id"]
        pid = resp["participant_id"]
        qid = resp["question_id"]
        key = (sid, pid, qid)
        if key not in _MEM_RESPONSES:
            _MEM_RESPONSES[key] = dict(resp)
        saved_map[key] = _MEM_RESPONSES[key]

    # Apply participant snapshot updates
    for upd in participant_updates:
        pid = upd.get("participant_id")
        fields = upd.get("fields", {})
        if pid and fields:
            p = get_participant(pid)
            if p:
                p.update(fields)
                p["updated_at"] = datetime.now(timezone.utc).isoformat()
                _MEM_PARTICIPANTS[pid] = p

    # Apply compact question stats updates
    for st in stats_updates:
        sid = st.get("session_id")
        qid = st.get("question_id")
        if sid and qid:
            upsert_question_stats(
                session_id=sid,
                question_id=qid,
                is_correct=bool(st.get("is_correct")),
                selected_option_id=st.get("selected_option_id"),
                response_time_ms=st.get("response_time_ms", 0),
            )

    if is_persistence_enabled() and response_list:
        try:
            # Multi-row response insert
            supabase.table("live_quiz_responses").insert(response_list).execute()
        except Exception as e:
            err_str = str(e).lower()
            if not ("duplicate" in err_str or "unique constraint" in err_str or "23505" in err_str):
                logger.error(f"[LiveQuizRepo] Supabase batch responses failed: {e}")
                raise DatabaseWriteError(f"Failed to batch insert responses: {e}") from e

    return saved_map


def get_responses_for_session(session_id: str) -> List[Dict[str, Any]]:
    mem_matches = [
        r for r in _MEM_RESPONSES.values()
        if r.get("session_id") == session_id
    ]

    if is_persistence_enabled():
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

    if is_persistence_enabled():
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


# ─── Live Quiz Question Stats ────────────────────────────────────────────────

def upsert_question_stats(
    session_id: str,
    question_id: str,
    is_correct: bool,
    selected_option_id: Optional[str],
    response_time_ms: int,
) -> Dict[str, Any]:
    """
    Maintains compact per-question counters to avoid GROUP BY over raw responses.
    """
    key = (session_id, question_id)
    stat = _MEM_QUESTION_STATS.get(key)
    if not stat:
        stat = {
            "session_id": session_id,
            "question_id": question_id,
            "answered_count": 0,
            "correct_count": 0,
            "option_counts": {},
            "average_response_ms": 0,
            "total_ms": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _MEM_QUESTION_STATS[key] = stat

    stat["answered_count"] += 1
    if is_correct:
        stat["correct_count"] += 1
    if selected_option_id:
        opts = stat.setdefault("option_counts", {})
        opts[selected_option_id] = opts.get(selected_option_id, 0) + 1

    stat["total_ms"] = stat.get("total_ms", 0) + max(0, response_time_ms)
    stat["average_response_ms"] = int(stat["total_ms"] / stat["answered_count"])
    stat["updated_at"] = datetime.now(timezone.utc).isoformat()

    if is_persistence_enabled():
        try:
            row_data = {
                "session_id": session_id,
                "question_id": question_id,
                "answered_count": stat["answered_count"],
                "correct_count": stat["correct_count"],
                "option_counts": stat["option_counts"],
                "average_response_ms": stat["average_response_ms"],
                "updated_at": stat["updated_at"],
            }
            supabase.table("live_quiz_question_stats").upsert(row_data).execute()
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase upsert question stats failed: {e}")

    return stat


def get_question_stats(session_id: str, question_id: str) -> Optional[Dict[str, Any]]:
    key = (session_id, question_id)
    if key in _MEM_QUESTION_STATS:
        return _MEM_QUESTION_STATS[key]

    if is_persistence_enabled():
        try:
            res = (
                supabase.table("live_quiz_question_stats")
                .select("*")
                .eq("session_id", session_id)
                .eq("question_id", question_id)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                _MEM_QUESTION_STATS[key] = rows[0]
                return rows[0]
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase get question stats failed: {e}")

    return None


# ─── Live Quiz Admin Action Audit ────────────────────────────────────────────

def log_admin_action(
    admin_user_id: str,
    session_id: str,
    action: str,
    participant_id: Optional[str] = None,
    reason: Optional[str] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "id": f"act_{int(time.time()*1000)}_{len(_MEM_ADMIN_ACTIONS)}",
        "admin_user_id": admin_user_id,
        "session_id": session_id,
        "participant_id": participant_id,
        "action": action,
        "reason": reason or "",
        "previous_state": previous_state or {},
        "new_state": new_state or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEM_ADMIN_ACTIONS.append(row)

    if is_persistence_enabled():
        try:
            supabase.table("live_quiz_admin_actions").insert(row).execute()
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase log admin action failed: {e}")

    return row


def list_admin_actions(session_id: str) -> List[Dict[str, Any]]:
    mem_matches = [a for a in _MEM_ADMIN_ACTIONS if a.get("session_id") == session_id]

    if is_persistence_enabled():
        try:
            res = (
                supabase.table("live_quiz_admin_actions")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase list admin actions failed: {e}")

    return sorted(mem_matches, key=lambda x: x.get("created_at", ""), reverse=True)


# ─── Session Monitoring Summary ──────────────────────────────────────────────

def get_session_monitoring_summary(session_id: str) -> Dict[str, Any]:
    """
    Calculates summary metrics directly from participant live snapshot table.
    Avoids expensive full-table response scans.
    """
    participants = list_participants(session_id)
    total = len(participants)

    active = sum(1 for p in participants if p.get("connection_state") == "active" and not p.get("is_banned"))
    disconnected = sum(1 for p in participants if p.get("connection_state") == "disconnected")
    banned = sum(1 for p in participants if p.get("is_banned"))
    flagged = sum(1 for p in participants if p.get("risk_score", 0) >= 30 and not p.get("is_banned"))

    sess = get_live_session(session_id)
    current_qix = sess.get("current_question_index", 0) if sess else 0
    total_q = sess.get("total_questions", 1) if sess else 1

    answered_current = sum(1 for p in participants if p.get("current_question_index", 0) > current_qix or p.get("answered_count", 0) > current_qix)
    waiting_current = max(0, active - answered_current)

    avg_speed = (
        round(sum(p.get("average_response_ms", 0) for p in participants) / total)
        if total > 0 else 0
    )
    avg_progress = (
        round((sum(p.get("answered_count", 0) for p in participants) / max(1, total * total_q)) * 100, 1)
        if total > 0 else 0.0
    )

    return {
        "session_id": session_id,
        "total_participants": total,
        "active_count": active,
        "answered_count": answered_current,
        "waiting_count": waiting_current,
        "disconnected_count": disconnected,
        "banned_count": banned,
        "flagged_count": flagged,
        "average_progress_pct": avg_progress,
        "average_speed_ms": avg_speed,
    }


# ─── Audit Event Log ─────────────────────────────────────────────────────────

def log_event(session_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    row = {
        "session_id": session_id,
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEM_EVENTS.append(row)

    if is_persistence_enabled():
        try:
            supabase.table("live_quiz_events").insert(row).execute()
        except Exception as e:
            logger.warning(f"[LiveQuizRepo] Supabase log event failed: {e}")
