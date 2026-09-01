"""
Teach Me API Endpoints (Hardened & Secure)
===========================================
FastAPI endpoints for Adaptive Interactive Teacher sessions, commands,
checkpoint answer evaluations, YouTube ingestion, telemetry metrics, and PPT exports.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from app.core.dependencies import get_current_user
from app.core.plan_guards import check_daily_question_limit
from app.models.teach import (
    StartTeachRequest, TeachMessageRequest, TeachCommandRequest,
    TeachAnswerRequest, YouTubeIngestRequest, ExportPPTRequest,
    ExportVideoRequest
)
from app.services.teach import (
    start_teaching_session, handle_user_turn, handle_quick_command,
    evaluate_student_answer, export_lesson_to_pptx,
    get_learning_state, get_lesson_plan, verify_session_ownership,
    get_session_aggregate_metrics
)
from app.services.knowledge.youtube_processor import process_youtube_video_and_store

router = APIRouter()


@router.post("/start")
async def start_session(
    request: StartTeachRequest,
    current_user=Depends(check_daily_question_limit),
):
    """
    Initializes an adaptive lesson plan and begins teaching Concept 1 with an embedded checkpoint.
    """
    try:
        source_ids = list(request.source_ids or [])

        # Ingest YouTube URL if provided
        if request.youtube_url and request.youtube_url.strip():
            try:
                yt_res = process_youtube_video_and_store(
                    url=request.youtube_url.strip(),
                    user_id=current_user.id,
                    title=f"Video: {request.topic}",
                    subject="TeachMe YouTube Source",
                )
                if yt_res.get("document_id") and yt_res["document_id"] not in source_ids:
                    source_ids.append(yt_res["document_id"])
            except Exception as yt_err:
                print(f"[TeachAPI] YouTube ingestion note: {yt_err}")

        session_data = await start_teaching_session(
            topic=request.topic.strip(),
            user_id=current_user.id,
            level=request.level,
            language=request.language,
            depth=request.depth,
            mode=request.mode,
            source_type=request.source_type,
            source_ids=source_ids,
        )
        return session_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start teaching session: {str(e)[:500]}"
        )


@router.post("/message")
async def send_message(
    request: TeachMessageRequest,
    current_user=Depends(check_daily_question_limit),
):
    """
    Handles a regular conversational student question or teaching interaction.
    """
    if not verify_session_ownership(request.session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    try:
        turn_res = await handle_user_turn(
            session_id=request.session_id,
            user_message=request.message,
            user_id=current_user.id,
        )
        return turn_res
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to session.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)[:500]}"
        )


@router.post("/command")
async def execute_command(
    request: TeachCommandRequest,
    current_user=Depends(check_daily_question_limit),
):
    """
    Dispatches quick pedagogical actions (continue, explain_again, make_simpler, go_deeper, give_example, ask_question, exam_points, show_visual, explain_it_back).
    """
    if not verify_session_ownership(request.session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    try:
        cmd_res = await handle_quick_command(
            session_id=request.session_id,
            command=request.command,
            user_id=current_user.id,
        )
        return cmd_res
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to session.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute command '{request.command}': {str(e)[:500]}"
        )


@router.post("/answer")
async def submit_answer(
    request: TeachAnswerRequest,
    current_user=Depends(check_daily_question_limit),
):
    """
    Evaluates student response to the active checkpoint, detects misconceptions, and calculates mastery delta.
    """
    if not verify_session_ownership(request.session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    try:
        eval_res = await evaluate_student_answer(
            session_id=request.session_id,
            student_answer=request.answer,
            user_id=current_user.id,
            idempotency_key=request.idempotency_key,
        )
        return eval_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate answer: {str(e)[:500]}"
        )


@router.post("/youtube/ingest")
async def ingest_youtube(
    request: YouTubeIngestRequest,
    current_user=Depends(get_current_user),
):
    """
    Parses, chunks, and indexes a public YouTube video transcript for Teach Me sessions.
    """
    try:
        res = process_youtube_video_and_store(
            url=request.url,
            user_id=current_user.id,
            title=request.title,
            subject=request.subject,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not process YouTube URL: {str(e)[:300]}"
        )


@router.post("/export/ppt")
async def export_to_ppt(
    request: ExportPPTRequest,
    current_user=Depends(get_current_user),
):
    """
    One-click export from active lesson roadmap to PowerPoint presentation (.pptx).
    """
    if not verify_session_ownership(request.session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    try:
        ppt_res = await export_lesson_to_pptx(
            session_id=request.session_id,
            user_id=current_user.id,
            slide_count=request.slide_count,
            design=request.design,
            theme=request.theme,
        )
        return ppt_res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export presentation: {str(e)[:500]}"
        )


@router.post("/export/video")
async def export_to_video_endpoint(
    request: ExportVideoRequest,
    current_user=Depends(get_current_user),
):
    """
    One-click export from active lesson roadmap into a full educational video.
    """
    if not verify_session_ownership(request.session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    try:
        from app.services.teach.exports import export_lesson_to_video
        vid_res = await export_lesson_to_video(
            session_id=request.session_id,
            user_id=current_user.id,
            duration=request.duration,
            quality=request.quality,
            style=request.style,
        )
        return vid_res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export video: {str(e)[:500]}"
        )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """
    Retrieves full learning state and concept roadmap for a session.
    """
    if not verify_session_ownership(session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    state = get_learning_state(session_id)
    plan = get_lesson_plan(session_id)
    if not state or not plan:
        raise HTTPException(status_code=404, detail="Teaching session not found")

    return {
        "session_id": session_id,
        "plan": plan.dict(),
        "state": state.dict(),
    }


@router.get("/session/{session_id}/metrics")
async def get_session_metrics(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """
    Returns aggregate token usage, latency, and cache metrics for this session.
    """
    if not verify_session_ownership(session_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this teaching session.")

    metrics = get_session_aggregate_metrics(session_id)
    return metrics
