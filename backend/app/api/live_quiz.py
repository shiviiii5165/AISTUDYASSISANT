"""
Live Classroom Quiz API (§10, VNEXT Scale & Security)
=====================================================
Canonical endpoints for the live classroom quiz experience.
Host actions are authenticated via Supabase JWT (Depends(get_current_user)).
Participant actions are authenticated via signed Participant JWTs.
Enforces ban revocation, progression token integrity, microbatching, and backpressure.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from app.core.security import limiter
from app.core.dependencies import get_current_user
from app.models.live_quiz import (
    StartLiveSessionRequest, JoinSessionRequest, SubmitLiveResponseRequest,
    InterventionRequest, UpdateSettingsRequest, ParticipantJoinResponse,
    BanParticipantRequest, ActivitySignalRequest
)
from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz import scoring
from app.services.live_quiz import intervention as interv_svc
from app.services.live_quiz import integrations as integ_svc
from app.services.live_quiz.realtime import broadcast_session_event
from app.services.live_quiz.schemas import LiveEventType, ConnectionState
from app.services.live_quiz.microbatch_writer import BackpressureError

router = APIRouter()


# ─── Participant Authentication Dependency ───────────────────────────────────

def get_current_participant(
    session_id: str,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Extract and verify signed participant JWT from Bearer header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid participant authorization header",
        )
    token = authorization[len("Bearer "):].strip()
    try:
        payload = repo.verify_participant_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid participant token: {e}",
        )

    if payload.get("session_id") != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant token does not match this session",
        )

    p = repo.get_participant(payload.get("sub"))
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found",
        )

    # Authoritative ban revocation check (§11)
    if p.get("is_banned"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ATTEMPT_REVOKED",
        )

    return p


# ─── Host / Teacher Endpoints ────────────────────────────────────────────────

@router.post("/{quiz_id}/start")
@limiter.limit("10/minute")
async def start_live_session(
    request: Request,
    quiz_id: str,
    payload: StartLiveSessionRequest,
    current_user=Depends(get_current_user),
):
    """Launch a live session with a frozen question snapshot."""
    try:
        sess = await mgr.initialize_live_session(
            quiz_id=quiz_id,
            host_user_id=current_user.id,
            mode=payload.mode,
            timer_seconds=payload.timer_seconds,
            speed_bonus=payload.speed_bonus,
            sound_fx=payload.sound_fx,
            leaderboard_enabled=payload.leaderboard_enabled,
            show_correctness_immediately=payload.show_correctness_immediately,
        )
        return sess
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_live_session_host_view(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Host dashboard state including roster and question status."""
    try:
        sess = repo.verify_session_host(session_id, current_user.id)
    except repo.NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except repo.OwnershipError:
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    participants = repo.list_participants(session_id)
    responses = repo.get_responses_for_session(session_id)

    idx = sess.get("current_question_index", 0)
    q_order = sess.get("question_order", [])
    snapshot = sess.get("questions_snapshot", [])
    target_qid = q_order[idx] if idx < len(q_order) else None
    q_dict = next((q for q in snapshot if q["id"] == target_qid), snapshot[idx] if idx < len(snapshot) else {})

    current_q_responses = [r for r in responses if r.get("question_id") == q_dict.get("id")]

    # Option counts for live bar chart
    opt_dist: Dict[str, int] = {}
    for opt in q_dict.get("options", []):
        opt_dist[opt] = sum(1 for r in current_q_responses if r.get("selected_option_id") == opt)

    return {
        "session": sess,
        "participants": participants,
        "current_question": q_dict,
        "current_response_count": len(current_q_responses),
        "option_distribution": opt_dist,
    }


@router.get("/{session_id}/participants")
async def get_session_participants_paginated(
    session_id: str,
    cursor: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None,
    risk: Optional[str] = None,
    search: Optional[str] = None,
    banned_only: bool = False,
    sort_by: str = "score",
    sort_desc: bool = True,
    current_user=Depends(get_current_user),
):
    """Cursor-paginated, filtered, and sorted participant list for the admin dashboard."""
    try:
        repo.verify_session_host(session_id, current_user.id)
    except repo.NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except repo.OwnershipError:
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    return repo.list_participants_cursor(
        session_id=session_id,
        cursor=cursor,
        limit=min(200, max(1, limit)),
        status_filter=status,
        risk_filter=risk,
        search=search,
        banned_only=banned_only,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.get("/{session_id}/participants/{participant_id}/detail")
async def get_participant_detail_view(
    session_id: str,
    participant_id: str,
    current_user=Depends(get_current_user),
):
    """Lazy-load detailed audit timeline when teacher clicks a student."""
    try:
        repo.verify_session_host(session_id, current_user.id)
    except (repo.NotFoundError, repo.OwnershipError):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    try:
        return repo.get_participant_detail(session_id, participant_id)
    except repo.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/participants/{participant_id}/ban")
async def ban_participant_endpoint(
    session_id: str,
    participant_id: str,
    payload: BanParticipantRequest,
    current_user=Depends(get_current_user),
):
    """Authoritative ban action by teacher. Immediately revokes participant access."""
    try:
        repo.verify_session_host(session_id, current_user.id)
    except (repo.NotFoundError, repo.OwnershipError):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    updated = repo.ban_participant(
        session_id=session_id,
        participant_id=participant_id,
        reason=payload.reason or "Removed by teacher",
        admin_user_id=current_user.id,
    )

    # Broadcast ban event to room
    await broadcast_session_event(session_id, "participant:banned", {
        "participant_id": participant_id,
        "reason": payload.reason,
    })

    return {"banned": True, "participant": updated}


@router.post("/{session_id}/participants/{participant_id}/unban")
async def unban_participant_endpoint(
    session_id: str,
    participant_id: str,
    current_user=Depends(get_current_user),
):
    """Authoritative unban action by teacher."""
    try:
        repo.verify_session_host(session_id, current_user.id)
    except (repo.NotFoundError, repo.OwnershipError):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    updated = repo.unban_participant(
        session_id=session_id,
        participant_id=participant_id,
        admin_user_id=current_user.id,
    )

    await broadcast_session_event(session_id, "participant:unbanned", {
        "participant_id": participant_id,
    })

    return {"unbanned": True, "participant": updated}


@router.get("/{session_id}/monitoring-summary")
async def get_monitoring_summary(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Compact summary of class metrics derived from live snapshot table."""
    try:
        repo.verify_session_host(session_id, current_user.id)
    except (repo.NotFoundError, repo.OwnershipError):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    return repo.get_session_monitoring_summary(session_id)


@router.post("/{session_id}/next")
async def next_question(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Host advances to the next question or starts session."""
    try:
        return await mgr.advance_to_next_question(session_id, current_user.id)
    except (repo.NotFoundError, repo.OwnershipError, repo.StateTransitionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/reveal")
async def reveal_answer(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Host reveals the answer and explanation to students."""
    try:
        return await mgr.reveal_current_question(session_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/pause")
async def pause_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    try:
        sess = await mgr.pause_live_session(session_id, current_user.id)
        repo.log_admin_action(current_user.id, session_id, "PAUSE")
        return sess
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    try:
        sess = await mgr.resume_live_session(session_id, current_user.id)
        repo.log_admin_action(current_user.id, session_id, "RESUME")
        return sess
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Host terminates session and triggers mastery sync."""
    try:
        sess = await mgr.finalize_session(session_id, current_user.id, status="ENDED")
        sync_result = await integ_svc.sync_session_with_mastery_and_roadmap(session_id)
        repo.log_admin_action(current_user.id, session_id, "END")
        return {"session": sess, "sync": sync_result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/analytics")
async def get_session_analytics(
    session_id: str,
    current_user=Depends(get_current_user),
):
    try:
        repo.verify_session_host(session_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    return scoring.compute_session_analytics(session_id)


@router.get("/{session_id}/report")
async def get_session_report(
    session_id: str,
    current_user=Depends(get_current_user),
):
    try:
        sess = repo.verify_session_host(session_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    analytics = scoring.compute_session_analytics(session_id)
    participants = repo.list_participants(session_id)

    return {
        "session": sess,
        "analytics": analytics,
        "participants": participants,
        "suggested_actions": [
            {"id": "remedial_lesson", "label": "Create Remedial Lesson", "type": "lesson"},
            {"id": "revision_quiz", "label": "Create Revision Quiz", "type": "quiz"},
            {"id": "teach_me", "label": "Launch Interactive Teach Me", "type": "teach"},
            {"id": "presentation", "label": "Generate Review PPT", "type": "presentation"},
        ],
    }


@router.post("/{session_id}/intervention")
async def trigger_intervention(
    session_id: str,
    payload: InterventionRequest,
    current_user=Depends(get_current_user),
):
    try:
        repo.verify_session_host(session_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    result = await interv_svc.generate_live_intervention(
        session_id=session_id,
        action_type=payload.type,
        question_id=payload.question_id,
    )
    return result


# ─── Participant / Student Endpoints ─────────────────────────────────────────

@router.post("/join")
@router.post("/{session_id}/join")
@limiter.limit("20/minute")
async def join_live_session(
    request: Request,
    payload: JoinSessionRequest,
    session_id: Optional[str] = None,
):
    sess = repo.find_active_session_by_code(payload.join_code)
    if not sess:
        raise HTTPException(status_code=404, detail="Active live session not found for this code")

    target_sid = sess["id"]
    if session_id and session_id != target_sid:
        raise HTTPException(status_code=400, detail="Join code does not match this session")

    pid = str(uuid.uuid4())
    avatar_seed = payload.avatar_seed or f"avatar_{pid[:6]}"

    p_data = {
        "id": pid,
        "session_id": target_sid,
        "user_id": None,
        "display_name": payload.display_name.strip(),
        "avatar_seed": avatar_seed,
        "status": "active",
        "score": 0,
        "correct_count": 0,
        "answered_count": 0,
        "streak": 0,
        "current_question_index": 0,
        "average_response_ms": 0,
        "connection_state": ConnectionState.ACTIVE.value,
        "risk_score": 0,
        "risk_level": "low",
        "is_banned": False,
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }
    created_p = repo.create_participant(p_data)
    token = repo.create_participant_token(pid, target_sid, p_data["display_name"])

    await broadcast_session_event(target_sid, "participant:joined", {
        "participant_id": pid,
        "display_name": p_data["display_name"],
        "avatar_seed": avatar_seed,
    })
    repo.log_event(target_sid, LiveEventType.PARTICIPANT_JOINED.value, {"participant_id": pid, "name": p_data["display_name"]})

    return ParticipantJoinResponse(
        participant_id=pid,
        session_id=target_sid,
        display_name=p_data["display_name"],
        avatar_seed=avatar_seed,
        participant_token=token,
        status="active",
    )


@router.get("/{session_id}/state")
async def get_participant_state(
    session_id: str,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    """
    Returns sanitized student room state.
    Includes opaque progression token. Answers are strictly omitted before reveal.
    """
    try:
        return mgr.get_sanitized_student_state(session_id, participant["id"])
    except repo.ParticipantBannedError:
        raise HTTPException(status_code=403, detail="ATTEMPT_REVOKED")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/activity")
async def record_participant_activity(
    session_id: str,
    payload: ActivitySignalRequest,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    """Records participant activity signal (e.g. TAB_HIDDEN, COPY_ATTEMPT, RECONNECTED)."""
    return repo.record_risk_signal(
        session_id=session_id,
        participant_id=participant["id"],
        signal_type=payload.signal_type,
        metadata=payload.metadata,
    )


@router.post("/{session_id}/response")
@limiter.limit("60/minute")
async def submit_participant_response(
    request: Request,
    session_id: str,
    payload: SubmitLiveResponseRequest,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    """
    Record and grade a participant's answer via BoundedResponseMicroBatchWriter.
    Enforces server deadline, progression token validation, and graceful backpressure.
    """
    try:
        res = await mgr.submit_student_response_batched(
            session_id=session_id,
            participant_id=participant["id"],
            question_id=payload.question_id,
            selected_option_id=payload.selected_option_id,
            response_time_ms=payload.response_time_ms or 0,
            idempotency_key=payload.idempotency_key,
            progression_token=payload.progression_token,
        )
        return res
    except repo.ParticipantBannedError:
        raise HTTPException(status_code=403, detail="ATTEMPT_REVOKED")
    except BackpressureError as be:
        # Return 429 with Retry-After so client retains in IndexedDB journal
        return JSONResponse(
            status_code=429,
            content={"detail": "Server queue saturated, retry with backoff", "retry_after": be.retry_after},
            headers={"Retry-After": str(be.retry_after)},
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/my-result")
async def get_my_result(
    session_id: str,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    p = repo.get_participant(participant["id"])
    responses = repo.get_responses_for_participant(session_id, participant["id"])
    sess = repo.get_live_session(session_id)
    snapshot = sess.get("questions_snapshot", []) if sess else []

    total_q = len(snapshot)
    correct_count = p.get("correct_count", 0)
    accuracy = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0

    return {
        "participant": p,
        "score": p.get("score", 0),
        "accuracy_pct": accuracy,
        "correct_count": correct_count,
        "total_questions": total_q,
        "responses": responses,
    }


@router.get("/observability/metrics")
async def get_live_quiz_observability_metrics():
    """
    Exposes safe operational metrics for Live Quiz VNext monitoring (§10).
    Provides queue depths, batch metrics, error rates, and session tallies
    without exposing any sensitive user data, questions, or secrets.
    """
    bw_metrics = batch_writer.get_metrics()
    rt_metrics = realtime_aggregator.get_metrics()

    # Query repository summary
    active_sessions = len([s for s in repo._MEM_SESSIONS.values() if s.get("status") in ("waiting", "live")])
    active_participants = len([p for p in repo._MEM_PARTICIPANTS.values() if p.get("connection_state") == "active"])
    reconnect_count = len([e for e in repo._MEM_EVENTS if e.get("event_type") == "RECONNECTED"])
    ban_unban_count = len([a for a in repo._MEM_ADMIN_ACTIONS if a.get("action") in ("BAN", "UNBAN")])

    return {
        "active_sessions": active_sessions,
        "active_participants": active_participants,
        "queue_depth": bw_metrics.get("queue_depth", 0),
        "max_queue_depth": bw_metrics.get("max_queue_depth", 10000),
        "total_enqueued": bw_metrics.get("total_enqueued", 0),
        "total_committed": bw_metrics.get("total_committed", 0),
        "total_batches": bw_metrics.get("total_batches", 0),
        "http_429_rejected": bw_metrics.get("total_rejected", 0),
        "avg_batch_size": bw_metrics.get("avg_batch_size", 0.0),
        "reconnect_count": reconnect_count,
        "ban_unban_count": ban_unban_count,
        "realtime_events_absorbed": rt_metrics.get("total_events_absorbed", 0),
        "realtime_broadcasts_emitted": rt_metrics.get("total_broadcasts_emitted", 0),
        "free_tier_mode": getattr(settings, "LIVE_QUIZ_FREE_TIER_MODE", True),
    }

