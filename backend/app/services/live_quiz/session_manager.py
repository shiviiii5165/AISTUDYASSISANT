"""
Live Quiz Engine — Server-Authoritative State Machine & Lifecycle
=================================================================
Manages 6-digit code recycling, question version freeze, transition validation,
server-enforced deadlines, and sanitized broadcast dispatching.
"""
from __future__ import annotations
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.services.quiz import repository as quiz_repo
from .schemas import (
    LiveSessionStatus, LiveSessionMode, LiveEventType,
    to_student_question_dict, ACTIVE_SESSION_STATUSES, TERMINATED_SESSION_STATUSES
)
from . import repository as repo
from .realtime import broadcast_session_event


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
    """
    Launch a live session with a frozen question snapshot (Section 4).
    The running session reads only from questions_snapshot; editing the
    source quiz afterward has zero impact on this live session.
    """
    quiz = quiz_repo.verify_quiz_owner(quiz_id, host_user_id)
    questions = quiz_repo.get_questions(quiz_id)
    if not questions:
        raise ValueError("Cannot start live session for a quiz with no questions")

    # Preserve quiz order or shuffle
    config = quiz.get("config") or {}
    q_order = [q["id"] for q in questions]
    if config.get("shuffle_questions"):
        # Deterministic shuffle seed
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
    Calculates server deadline and emits sanitized broadcast.
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
        # All questions finished -> COMPLETE session
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

    # Extract current question & sanitize for broadcast
    q_order = updated.get("question_order", [])
    snapshot = updated.get("questions_snapshot", [])
    target_qid = q_order[next_index] if next_index < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[next_index] if next_index < len(snapshot) else {})

    sanitized = to_student_question_dict(q_dict)
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
    """Host reveals the answer and explanation to the class."""
    sess = repo.verify_session_host(session_id, host_user_id)
    if sess.get("status") != LiveSessionStatus.LIVE.value:
        raise repo.StateTransitionError("Can only reveal question in LIVE status")

    settings = dict(sess.get("settings") or {})
    settings["question_revealed"] = True

    updated = repo.update_live_session(session_id, {"settings": settings}, expected_version=sess.get("version"))

    # Prepare revealed answer payload
    idx = updated.get("current_question_index", 0)
    q_order = updated.get("question_order", [])
    snapshot = updated.get("questions_snapshot", [])
    target_qid = q_order[idx] if idx < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[idx] if idx < len(snapshot) else {})

    # Compute option distribution for the revealed question
    responses = repo.get_responses_for_session(session_id)
    this_q_responses = [r for r in responses if r.get("question_id") == q_dict.get("id")]
    dist: Dict[str, int] = {}
    for opt in q_dict.get("options", []):
        dist[opt] = sum(1 for r in this_q_responses if r.get("selected_option_id") == opt)

    broadcast_payload = {
        "question_index": idx,
        "question_id": q_dict.get("id"),
        "correct_answer": q_dict.get("correct_answer"),
        "explanation": q_dict.get("explanation", ""),
        "option_distribution": dist,
        "total_responses": len(this_q_responses),
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
    Zero-Leakage Invariant:
    Returns the student view of the room.
    If the question is unrevealed, answers and explanations are strictly omitted.
    """
    sess = repo.get_live_session(session_id)
    if not sess:
        raise repo.NotFoundError("Session not found")

    p = repo.get_participant(participant_id)
    if not p or p.get("session_id") != session_id:
        raise repo.OwnershipError("Not authorized for this session")

    # Check expiration
    now = datetime.now(timezone.utc)
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

    if is_revealed:
        question_payload = {
            "id": q_dict.get("id"),
            "question_text": q_dict.get("question_text"),
            "options": q_dict.get("options", []),
            "correct_answer": q_dict.get("correct_answer"),
            "explanation": q_dict.get("explanation", ""),
            "difficulty": q_dict.get("difficulty", "medium"),
            "concept_id": q_dict.get("concept_id"),
        }
    else:
        question_payload = to_student_question_dict(q_dict) if q_dict else None

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
        },
    }


def submit_student_response(
    session_id: str,
    participant_id: str,
    question_id: str,
    selected_option_id: Optional[str],
    response_time_ms: int = 0,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Authoritative helper to record, grade, and apply a student response.
    Idempotent against duplicate submissions.
    """
    from . import scoring
    sess = repo.get_live_session(session_id)
    if not sess or sess.get("status") != LiveSessionStatus.LIVE.value:
        raise repo.StateTransitionError("Session is not currently live")

    p = repo.get_participant(participant_id)
    if not p:
        raise repo.NotFoundError(f"Participant {participant_id} not found")

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
    saved = repo.record_response(resp_row)

    # If this is a fresh response (not a duplicate), update participant score
    if saved.get("id") == resp_row["id"]:
        streak = (p.get("streak", 0) + 1) if is_correct else 0
        new_score = p.get("score", 0) + points
        repo.update_participant(participant_id, {
            "score": new_score,
            "correct_count": p.get("correct_count", 0) + (1 if is_correct else 0),
            "answered_count": p.get("answered_count", 0) + 1,
            "streak": streak,
        })

    return saved

