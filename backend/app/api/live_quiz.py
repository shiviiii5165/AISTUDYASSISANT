"""
Live Classroom Quiz API (§10)
=============================
Canonical endpoints for the live classroom quiz experience.
Host actions are authenticated via Supabase JWT (Depends(get_current_user)).
Participant actions are authenticated via signed Participant JWTs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from app.core.security import limiter
from app.core.dependencies import get_current_user
from app.models.live_quiz import (
    StartLiveSessionRequest, JoinSessionRequest, SubmitLiveResponseRequest,
    InterventionRequest, UpdateSettingsRequest, ParticipantJoinResponse
)
from app.services.live_quiz import repository as repo
from app.services.live_quiz import session_manager as mgr
from app.services.live_quiz import scoring
from app.services.live_quiz import intervention as interv_svc
from app.services.live_quiz import integrations as integ_svc
from app.services.live_quiz.realtime import broadcast_session_event
from app.services.live_quiz.schemas import LiveEventType

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
        return await mgr.pause_live_session(session_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    try:
        return await mgr.resume_live_session(session_id, current_user.id)
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
        return {"session": sess, "sync": sync_result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/analytics")
async def get_session_analytics(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Live deterministic class analytics and concept heatmap."""
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
    """Immutable audit report and post-session recommendations."""
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
    """Teacher triggers a scoped remedial action (Explain, Visual, Example, Follow-up)."""
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
    """
    Join session using 6-digit code.
    Generates participant record and signed Participant JWT.
    """
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
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    created_p = repo.create_participant(p_data)
    token = repo.create_participant_token(pid, target_sid, p_data["display_name"])

    # Broadcast participant arrival to room
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
    Answers and explanations are strictly omitted if the question is unrevealed.
    """
    try:
        return mgr.get_sanitized_student_state(session_id, participant["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/response")
@limiter.limit("30/minute")
async def submit_participant_response(
    request: Request,
    session_id: str,
    payload: SubmitLiveResponseRequest,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    """
    Record and grade a participant's answer.
    Server-authoritative deadline and scoring. Idempotent.
    """
    sess = repo.get_live_session(session_id)
    if not sess or sess.get("status") != "LIVE":
        raise HTTPException(status_code=400, detail="Session is not currently live")

    pid = participant["id"]
    snapshot = sess.get("questions_snapshot", [])
    q_dict = next((q for q in snapshot if q["id"] == payload.question_id), None)
    if not q_dict:
        raise HTTPException(status_code=404, detail="Question not found in this session")

    # Server deadline enforcement (§6)
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

    started_iso = sess.get("current_question_started_at")
    response_time_ms = 0
    if started_iso:
        try:
            started_dt = datetime.fromisoformat(str(started_iso).replace("Z", "+00:00"))
            response_time_ms = max(0, int((now - started_dt).total_seconds() * 1000))
        except Exception:
            pass

    timer_config = sess.get("timer_config", {})
    if is_late:
        is_correct = False
        points = 0
    else:
        is_correct, points = scoring.grade_live_response(
            q_dict=q_dict,
            selected_option_id=payload.selected_option_id,
            response_time_ms=response_time_ms,
            timer_config=timer_config,
        )

    resp_row = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "participant_id": pid,
        "question_id": payload.question_id,
        "selected_option_id": payload.selected_option_id,
        "submitted_at": now.isoformat(),
        "response_time_ms": response_time_ms,
        "is_correct": is_correct if not is_late else None,
        "points": points,
        "attempt_number": 1,
        "concept_id": q_dict.get("concept_id"),
        "idempotency_key": payload.idempotency_key,
    }
    saved = repo.record_response(resp_row)

    # Update participant totals
    streak = (participant.get("streak", 0) + 1) if is_correct else 0
    new_score = participant.get("score", 0) + points
    new_correct = participant.get("correct_count", 0) + (1 if is_correct else 0)
    new_answered = participant.get("answered_count", 0) + 1

    repo.update_participant(pid, {
        "score": new_score,
        "streak": streak,
        "correct_count": new_correct,
        "answered_count": new_answered,
    })

    # Broadcast response increment to host
    await broadcast_session_event(session_id, "response:submitted", {
        "question_id": payload.question_id,
        "selected_option_id": payload.selected_option_id,
    })

    show_immediately = sess.get("settings", {}).get("show_correctness_immediately", True)
    return {
        "received": True,
        "question_id": payload.question_id,
        "is_late": is_late,
        "is_correct": is_correct if (show_immediately and not is_late) else None,
        "points_earned": points if show_immediately else None,
    }


@router.get("/{session_id}/my-result")
async def get_my_result(
    session_id: str,
    participant: Dict[str, Any] = Depends(get_current_participant),
):
    """Personal scorecard for the participant."""
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
