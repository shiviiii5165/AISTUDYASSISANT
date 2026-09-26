"""
Live Quiz Engine — Server-Authoritative State Machine & Lifecycle (VNext Scale)
================================================================================
Manages 6-digit code recycling, question version freeze, transition validation,
server-enforced deadlines, opaque progression tokens, and micro-batched responses.
"""
from __future__ import annotations
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.services.quiz import repository as quiz_repo
from .schemas import (
    LiveSessionStatus, LiveSessionMode, LiveEventType, ConnectionState,
    to_student_question_dict, create_progression_token, verify_progression_token,
    ACTIVE_SESSION_STATUSES, TERMINATED_SESSION_STATUSES
)
from . import repository as repo
from .realtime import broadcast_session_event
from .microbatch_writer import batch_writer
from .realtime_aggregator import realtime_aggregator


# ─── 6-Digit Cryptographic Code Generator with Recycling Check ───────────────

def generate_join_code() -> str:
    """Generate a unique 6-digit numeric join code not active elsewhere."""
    for _ in range(50):
        code = str(secrets.randbelow(900000) + 100000)
        if not repo.find_active_session_by_code(code):
            return code
    raise RuntimeError("Failed to allocate a unique join code; pool temporarily saturated")


# ─── State Machine Transition Rules ──────────────────────────────────────────

_LEGAL_TRANSITIONS: Dict[str, List[str]] = {
    LiveSessionStatus.CREATED.value: [LiveSessionStatus.LOBBY.value, LiveSessionStatus.ENDED.value],
    LiveSessionStatus.LOBBY.value: [LiveSessionStatus.LIVE.value, LiveSessionStatus.ENDED.value],
    LiveSessionStatus.LIVE.value: [
        LiveSessionStatus.PAUSED.value,
        LiveSessionStatus.COMPLETED.value,
        LiveSessionStatus.ENDED.value,
    ],
    LiveSessionStatus.PAUSED.value: [
        LiveSessionStatus.LIVE.value,
        LiveSessionStatus.COMPLETED.value,
        LiveSessionStatus.ENDED.value,
    ],
    LiveSessionStatus.COMPLETED.value: [],
    LiveSessionStatus.ENDED.value: [],
    LiveSessionStatus.EXPIRED.value: [],
}


def assert_legal_transition(current_status: str, target_status: str) -> None:
    if target_status == LiveSessionStatus.EXPIRED.value:
        return  # Any state can expire
    allowed = _LEGAL_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise repo.StateTransitionError(
            f"Illegal state transition from {current_status} to {target_status}"
        )


# ─── Session Initialization & Version Freeze ─────────────────────────────────

async def initialize_live_session(
    quiz_id: str,
    host_user_id: str,
    mode: str = "teacher_led",
    timer_seconds: int = 30,
    speed_bonus: bool = False,
    sound_fx: bool = True,
    leaderboard_enabled: bool = True,
    show_correctness_immediately: bool = True,
) -> Dict[str, Any]:
    quiz = quiz_repo.verify_quiz_owner(quiz_id, host_user_id)
    questions = quiz_repo.get_questions(quiz_id)
    if not questions:
        raise ValueError("Cannot start live session for a quiz with no questions")

    # Preserve quiz order or shuffle
    config = quiz.get("config") or {}
    q_order = [q["id"] for q in questions]
    if config.get("shuffle_questions"):
        rnd = secrets.SystemRandom()
        rnd.shuffle(q_order)

    join_code = generate_join_code()
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=4)

    session_data = {
        "id": session_id,
        "quiz_id": quiz_id,
        "host_user_id": host_user_id,
        "organization_id": quiz.get("organization_id"),
        "join_code": join_code,
        "status": LiveSessionStatus.LOBBY.value,
        "mode": mode,
        "current_question_index": 0,
        "current_question_started_at": None,
        "current_question_deadline": None,
        "total_questions": len(questions),
        "timer_config": {
            "enabled": timer_seconds > 0,
            "seconds": timer_seconds,
            "speed_bonus": speed_bonus,
        },
        "settings": {
            "sound_fx": sound_fx,
            "leaderboard_enabled": leaderboard_enabled,
            "show_correctness_immediately": show_correctness_immediately,
            "question_revealed": False,
        },
        "questions_snapshot": questions,
        "question_order": q_order,
        "started_at": None,
        "ended_at": None,
        "expires_at": expires_at.isoformat(),
        "version": 1,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    created = repo.create_live_session(session_data)
    repo.log_event(session_id, LiveEventType.SESSION_CREATED.value, {"quiz_id": quiz_id, "join_code": join_code})
    return created


# ─── Host Transition Operations ──────────────────────────────────────────────

async def advance_to_next_question(session_id: str, host_user_id: str) -> Dict[str, Any]:
    """
    Advance to next question (or start first question).
    Calculates server deadline, generates opaque progression token, and emits broadcast.
    """
    sess = repo.verify_session_host(session_id, host_user_id)
    cur_status = sess.get("status")

    if cur_status == LiveSessionStatus.LOBBY.value:
        assert_legal_transition(cur_status, LiveSessionStatus.LIVE.value)
        next_index = 0
        status_to_set = LiveSessionStatus.LIVE.value
        started_at = datetime.now(timezone.utc).isoformat()
    elif cur_status == LiveSessionStatus.LIVE.value:
        next_index = sess.get("current_question_index", 0) + 1
        status_to_set = LiveSessionStatus.LIVE.value
        started_at = sess.get("started_at")
    else:
        raise repo.StateTransitionError(f"Cannot advance question in status {cur_status}")

    total_q = sess.get("total_questions", 0)
    if next_index >= total_q:
        return await finalize_session(session_id, host_user_id, status=LiveSessionStatus.COMPLETED.value)

    timer_seconds = sess.get("timer_config", {}).get("seconds", 30)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(seconds=timer_seconds)

    settings = dict(sess.get("settings") or {})
    settings["question_revealed"] = False

    update_fields = {
        "status": status_to_set,
        "current_question_index": next_index,
        "current_question_started_at": now.isoformat(),
        "current_question_deadline": deadline.isoformat(),
        "started_at": started_at,
        "settings": settings,
    }
    updated = repo.update_live_session(session_id, update_fields, expected_version=sess.get("version"))

    # Extract current question & sanitize with progression token
    q_order = updated.get("question_order", [])
    snapshot = updated.get("questions_snapshot", [])
    target_qid = q_order[next_index] if next_index < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[next_index] if next_index < len(snapshot) else {})

    progression_token = create_progression_token(
        session_id=session_id,
        question_index=next_index,
        question_id=q_dict.get("id", ""),
        deadline_iso=deadline.isoformat(),
    )

    sanitized = to_student_question_dict(q_dict, progression_token=progression_token)
    broadcast_payload = {
        "question_index": next_index,
        "total_questions": total_q,
        "question": sanitized,
        "timer_seconds": timer_seconds,
        "deadline": deadline.isoformat(),
    }

    await broadcast_session_event(session_id, "question:started", broadcast_payload)
    repo.log_event(session_id, LiveEventType.QUESTION_STARTED.value, {"question_index": next_index, "question_id": q_dict.get("id")})
    return updated


async def reveal_current_question(session_id: str, host_user_id: str) -> Dict[str, Any]:
    sess = repo.verify_session_host(session_id, host_user_id)
    if sess.get("status") != LiveSessionStatus.LIVE.value:
        raise repo.StateTransitionError("Can only reveal question in LIVE status")

    settings = dict(sess.get("settings") or {})
    settings["question_revealed"] = True

    updated = repo.update_live_session(session_id, {"settings": settings}, expected_version=sess.get("version"))

    idx = updated.get("current_question_index", 0)
    q_order = updated.get("question_order", [])
    snapshot = updated.get("questions_snapshot", [])
    target_qid = q_order[idx] if idx < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[idx] if idx < len(snapshot) else {})

    # Check compact question stats first
    stat = repo.get_question_stats(session_id, q_dict.get("id", ""))
    if stat:
        dist = stat.get("option_counts", {})
        total_resp = stat.get("answered_count", 0)
    else:
        responses = repo.get_responses_for_session(session_id)
        this_q_responses = [r for r in responses if r.get("question_id") == q_dict.get("id")]
        dist = {}
        for opt in q_dict.get("options", []):
            dist[opt] = sum(1 for r in this_q_responses if r.get("selected_option_id") == opt)
        total_resp = len(this_q_responses)

    broadcast_payload = {
        "question_index": idx,
        "question_id": q_dict.get("id"),
        "correct_answer": q_dict.get("correct_answer"),
        "explanation": q_dict.get("explanation", ""),
        "option_distribution": dist,
        "total_responses": total_resp,
    }

    await broadcast_session_event(session_id, "question:revealed", broadcast_payload)
    repo.log_event(session_id, LiveEventType.QUESTION_REVEALED.value, {"question_index": idx, "question_id": q_dict.get("id")})
    return updated


async def pause_live_session(session_id: str, host_user_id: str) -> Dict[str, Any]:
    sess = repo.verify_session_host(session_id, host_user_id)
    assert_legal_transition(sess.get("status"), LiveSessionStatus.PAUSED.value)
    updated = repo.update_live_session(session_id, {"status": LiveSessionStatus.PAUSED.value}, expected_version=sess.get("version"))
    await broadcast_session_event(session_id, "session:paused", {"status": "PAUSED"})
    repo.log_event(session_id, LiveEventType.SESSION_PAUSED.value, {})
    return updated


async def resume_live_session(session_id: str, host_user_id: str) -> Dict[str, Any]:
    sess = repo.verify_session_host(session_id, host_user_id)
    assert_legal_transition(sess.get("status"), LiveSessionStatus.LIVE.value)
    updated = repo.update_live_session(session_id, {"status": LiveSessionStatus.LIVE.value}, expected_version=sess.get("version"))
    await broadcast_session_event(session_id, "session:resumed", {"status": "LIVE"})
    repo.log_event(session_id, LiveEventType.SESSION_RESUMED.value, {})
    return updated


async def finalize_session(
    session_id: str,
    host_user_id: str,
    status: str = LiveSessionStatus.COMPLETED.value,
) -> Dict[str, Any]:
    sess = repo.verify_session_host(session_id, host_user_id)
    assert_legal_transition(sess.get("status"), status)
    now = datetime.now(timezone.utc).isoformat()
    updated = repo.update_live_session(session_id, {"status": status, "ended_at": now}, expected_version=sess.get("version"))
    await broadcast_session_event(session_id, "session:ended", {"status": status, "ended_at": now})
    repo.log_event(session_id, LiveEventType.SESSION_ENDED.value, {"status": status})
    return updated


# ─── Participant State Sanitizer ─────────────────────────────────────────────

def get_sanitized_student_state(session_id: str, participant_id: str) -> Dict[str, Any]:
    """
    Zero-Leakage Invariant (§2):
    Student receives current authorized question only.
    Future questions and answers are strictly omitted.
    Banned participants are immediately locked out.
    """
    sess = repo.get_live_session(session_id)
    if not sess:
        raise repo.NotFoundError("Session not found")

    p = repo.get_participant(participant_id)
    if not p or p.get("session_id") != session_id:
        raise repo.OwnershipError("Not authorized for this session")

    # Authoritative ban enforcement (§11)
    if p.get("is_banned"):
        raise repo.ParticipantBannedError("ATTEMPT_REVOKED")

    # Touch participant last seen
    now = datetime.now(timezone.utc)
    repo.update_participant(participant_id, {
        "last_seen_at": now.isoformat(),
        "connection_state": ConnectionState.ACTIVE.value,
    })

    # Check session expiration
    exp = sess.get("expires_at")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if now > exp_dt and sess.get("status") not in [s.value for s in TERMINATED_SESSION_STATUSES]:
                sess = repo.update_live_session(session_id, {"status": LiveSessionStatus.EXPIRED.value})
        except Exception:
            pass

    status = sess.get("status")
    idx = sess.get("current_question_index", 0)
    q_order = sess.get("question_order", [])
    snapshot = sess.get("questions_snapshot", [])
    target_qid = q_order[idx] if idx < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[idx] if idx < len(snapshot) else {})

    settings = sess.get("settings") or {}
    is_revealed = settings.get("question_revealed", False)

    # Participant submission check
    responses = repo.get_responses_for_participant(session_id, participant_id)
    current_response = next((r for r in responses if r.get("question_id") == q_dict.get("id")), None)

    deadline_iso = sess.get("current_question_deadline")
    remaining_sec = 0
    if deadline_iso:
        try:
            deadline_dt = datetime.fromisoformat(str(deadline_iso).replace("Z", "+00:00"))
            remaining_sec = max(0, int((deadline_dt - now).total_seconds()))
        except Exception:
            remaining_sec = 0

    # Issue opaque progression token for current question
    prog_token = create_progression_token(
        session_id=session_id,
        question_index=idx,
        question_id=q_dict.get("id", ""),
        deadline_iso=deadline_iso,
    )

    if is_revealed:
        question_payload = {
            "id": q_dict.get("id"),
            "question_text": q_dict.get("question_text"),
            "options": q_dict.get("options", []),
            "correct_answer": q_dict.get("correct_answer"),
            "explanation": q_dict.get("explanation", ""),
            "difficulty": q_dict.get("difficulty", "medium"),
            "concept_id": q_dict.get("concept_id"),
            "progression_token": prog_token,
        }
    else:
        question_payload = to_student_question_dict(q_dict, progression_token=prog_token) if q_dict else None

    return {
        "session_id": session_id,
        "status": status,
        "mode": sess.get("mode"),
        "current_question_index": idx,
        "total_questions": sess.get("total_questions", len(snapshot)),
        "question": question_payload,
        "is_revealed": is_revealed,
        "remaining_seconds": remaining_sec,
        "has_submitted": current_response is not None,
        "selected_option_id": current_response.get("selected_option_id") if current_response else None,
        "participant": {
            "id": p.get("id"),
            "display_name": p.get("display_name"),
            "avatar_seed": p.get("avatar_seed"),
            "score": p.get("score", 0),
            "streak": p.get("streak", 0),
            "risk_level": p.get("risk_level", "low"),
            "is_banned": p.get("is_banned", False),
        },
    }


class AwaitableResult(dict):
    """
    Subclass of dict that is directly subscriptable/accessible in synchronous tests
    and can also be awaited in async coroutines.
    """
    def __init__(self, data: dict, coro=None):
        super().__init__(data)
        self._coro = coro

    def __await__(self):
        if self._coro is not None:
            return self._coro.__await__()
        async def _ret():
            return dict(self)
        return _ret().__await__()


# ─── High-Concurrency Micro-Batched Response Submission ──────────────────────

def submit_student_response(
    session_id: str,
    participant_id: str,
    question_id: str,
    selected_option_id: Optional[str],
    response_time_ms: int = 0,
    idempotency_key: Optional[str] = None,
    progression_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Authoritative synchronous submission and grading with deduplication protection.
    Returns an AwaitableResult so it can be called synchronously in legacy tests or awaited.
    """
    from . import scoring
    sess = repo.get_live_session(session_id)
    if not sess or sess.get("status") != LiveSessionStatus.LIVE.value:
        raise repo.StateTransitionError("Session is not currently live")

    p = repo.get_participant(participant_id)
    if not p:
        raise repo.NotFoundError(f"Participant {participant_id} not found")
    if p.get("is_banned"):
        raise repo.ParticipantBannedError("ATTEMPT_REVOKED")

    # Validate progression token if supplied (§2)
    cur_qix = sess.get("current_question_index", 0)
    if progression_token:
        verify_progression_token(
            token=progression_token,
            session_id=session_id,
            expected_question_index=cur_qix,
        )

    snapshot = sess.get("questions_snapshot", [])
    q_dict = next((q for q in snapshot if q["id"] == question_id), None)
    if not q_dict:
        raise repo.NotFoundError(f"Question {question_id} not found in session")

    now = datetime.now(timezone.utc)
    deadline_iso = sess.get("current_question_deadline")
    is_late = False
    if deadline_iso:
        try:
            deadline_dt = datetime.fromisoformat(str(deadline_iso).replace("Z", "+00:00"))
            if now > deadline_dt:
                is_late = True
        except Exception:
            pass

    timer_config = sess.get("timer_config", {})
    if is_late:
        is_correct = False
        points = 0
    else:
        is_correct, points = scoring.grade_live_response(
            q_dict=q_dict,
            selected_option_id=selected_option_id,
            response_time_ms=response_time_ms,
            timer_config=timer_config,
        )

    resp_row = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "participant_id": participant_id,
        "question_id": question_id,
        "selected_option_id": selected_option_id,
        "submitted_at": now.isoformat(),
        "response_time_ms": response_time_ms,
        "is_correct": is_correct if not is_late else None,
        "points": points,
        "attempt_number": 1,
        "concept_id": q_dict.get("concept_id"),
        "idempotency_key": idempotency_key,
    }

    # Deduplication check: verify if participant has already answered this question
    existing_responses = repo.get_responses_for_participant(session_id, participant_id)
    is_duplicate = any(r.get("question_id") == question_id for r in existing_responses)

    saved = repo.record_response(resp_row)

    if not is_duplicate and saved.get("id") == resp_row["id"]:
        streak = (p.get("streak", 0) + 1) if is_correct else 0
        new_score = p.get("score", 0) + points
        new_correct = p.get("correct_count", 0) + (1 if is_correct else 0)
        new_answered = p.get("answered_count", 0) + 1
        total_prev_ms = p.get("average_response_ms", 0) * p.get("answered_count", 0)
        new_avg_speed = int((total_prev_ms + max(0, response_time_ms)) / new_answered)

        repo.update_participant(participant_id, {
            "score": new_score,
            "correct_count": new_correct,
            "answered_count": new_answered,
            "current_question_index": cur_qix + 1,
            "average_response_ms": new_avg_speed,
            "streak": streak,
            "last_seen_at": now.isoformat(),
        })

        repo.upsert_question_stats(
            session_id=session_id,
            question_id=question_id,
            is_correct=is_correct,
            selected_option_id=selected_option_id,
            response_time_ms=response_time_ms,
        )

    show_immediately = sess.get("settings", {}).get("show_correctness_immediately", True)
    result = dict(saved)
    result["received"] = True
    result["question_id"] = question_id
    result["is_late"] = is_late
    result["is_correct"] = is_correct if (show_immediately and not is_late) else None
    result["points_earned"] = points if show_immediately else None
    result["points"] = points if show_immediately else None

    return AwaitableResult(result)


async def submit_student_response_batched(
    session_id: str,
    participant_id: str,
    question_id: str,
    selected_option_id: Optional[str],
    response_time_ms: int = 0,
    idempotency_key: Optional[str] = None,
    progression_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-concurrency response submission via BoundedResponseMicroBatchWriter (§4).
    Awaits authoritative multi-row database commit before acknowledging client.
    Feeds realtime aggregator (§5) in 250-500ms windows.
    """
    from . import scoring
    sess = repo.get_live_session(session_id)
    if not sess or sess.get("status") != LiveSessionStatus.LIVE.value:
        raise repo.StateTransitionError("Session is not currently live")

    p = repo.get_participant(participant_id)
    if not p:
        raise repo.NotFoundError(f"Participant {participant_id} not found")
    if p.get("is_banned"):
        raise repo.ParticipantBannedError("ATTEMPT_REVOKED")

    # Validate progression token if supplied (§2)
    cur_qix = sess.get("current_question_index", 0)
    if progression_token:
        verify_progression_token(
            token=progression_token,
            session_id=session_id,
            expected_question_index=cur_qix,
        )

    snapshot = sess.get("questions_snapshot", [])
    q_dict = next((q for q in snapshot if q["id"] == question_id), None)
    if not q_dict:
        raise repo.NotFoundError(f"Question {question_id} not found in session")

    now = datetime.now(timezone.utc)
    deadline_iso = sess.get("current_question_deadline")
    is_late = False
    if deadline_iso:
        try:
            deadline_dt = datetime.fromisoformat(str(deadline_iso).replace("Z", "+00:00"))
            if now > deadline_dt:
                is_late = True
        except Exception:
            pass

    timer_config = sess.get("timer_config", {})
    if is_late:
        is_correct = False
        points = 0
    else:
        is_correct, points = scoring.grade_live_response(
            q_dict=q_dict,
            selected_option_id=selected_option_id,
            response_time_ms=response_time_ms,
            timer_config=timer_config,
        )

    resp_row = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "participant_id": participant_id,
        "question_id": question_id,
        "selected_option_id": selected_option_id,
        "submitted_at": now.isoformat(),
        "response_time_ms": response_time_ms,
        "is_correct": is_correct if not is_late else None,
        "points": points,
        "attempt_number": 1,
        "concept_id": q_dict.get("concept_id"),
        "idempotency_key": idempotency_key,
    }

    # Prepare participant live snapshot delta
    streak = (p.get("streak", 0) + 1) if is_correct else 0
    new_score = p.get("score", 0) + points
    new_correct = p.get("correct_count", 0) + (1 if is_correct else 0)
    new_answered = p.get("answered_count", 0) + 1
    total_prev_ms = p.get("average_response_ms", 0) * p.get("answered_count", 0)
    new_avg_speed = int((total_prev_ms + max(0, response_time_ms)) / new_answered)

    participant_delta = {
        "participant_id": participant_id,
        "fields": {
            "score": new_score,
            "correct_count": new_correct,
            "answered_count": new_answered,
            "current_question_index": cur_qix + 1,
            "average_response_ms": new_avg_speed,
            "streak": streak,
            "last_seen_at": now.isoformat(),
        }
    }

    stats_delta = {
        "session_id": session_id,
        "question_id": question_id,
        "is_correct": is_correct,
        "selected_option_id": selected_option_id,
        "response_time_ms": response_time_ms,
    }

    # Enqueue in BoundedResponseMicroBatchWriter (§4)
    # Awaits authoritative DB commit before returning ACK to student
    saved_response = await batch_writer.enqueue(
        response_row=resp_row,
        participant_delta=participant_delta,
        stats_delta=stats_delta,
    )

    # Feed Realtime Aggregator (§5)
    await realtime_aggregator.record_answer_event(
        session_id=session_id,
        question_id=question_id,
        selected_option_id=selected_option_id,
        response_time_ms=response_time_ms,
    )

    show_immediately = sess.get("settings", {}).get("show_correctness_immediately", True)
    return {
        "received": True,
        "question_id": question_id,
        "is_late": is_late,
        "is_correct": is_correct if (show_immediately and not is_late) else None,
        "points_earned": points if show_immediately else None,
        "points": points if show_immediately else None,
    }
