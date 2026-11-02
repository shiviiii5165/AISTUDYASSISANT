"""
LearnByGenie — Adaptive Practice Engine API (Feature 6)
========================================================
Endpoints for student adaptive practice sessions, responses, hints, explainability, and summaries.
"""
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.services.practice.service import AdaptivePracticeService
from app.services.practice.schemas import (
    PracticeMode, DifficultyBand, StudentPracticeItemView,
    PracticeSession, PracticeFeedback, PracticeSelectionExplanation,
    SessionSummary, ContentAuditReport
)
from app.services.practice.audit import ContentAuditor

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return user_id


class PracticeStartRequest(BaseModel):
    subject: str = "Mathematics"
    mode: PracticeMode = PracticeMode.ADAPTIVE
    requested_skill_id: Optional[str] = None
    question_budget: Optional[Union[int, str]] = 10
    curriculum: str = "CBSE"
    exam_track: str = "Boards"
    enrolled_grade: int = 10
    grade_band: str = "secondary"


class PracticeResponseRequest(BaseModel):
    item_id: str
    question_index: int
    student_response: Any
    response_time_ms: int = 0
    attempt_sequence: int = 1


class PracticeHintRequest(BaseModel):
    item_id: str


@router.post(
    "/start",
    summary="Start an adaptive practice session",
    description="Initializes a durable, server-authoritative practice session and selects first item."
)
async def start_practice(
    req: PracticeStartRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    session = AdaptivePracticeService.start_session(
        user_id=user_id,
        subject=req.subject,
        mode=req.mode,
        requested_skill_id=req.requested_skill_id,
        question_budget=req.question_budget,
        curriculum=req.curriculum,
        exam_track=req.exam_track,
        enrolled_grade=req.enrolled_grade,
        grade_band=req.grade_band
    )
    first_item = AdaptivePracticeService.get_next_item(session.id, user_id)
    return {
        "session": session,
        "current_item": first_item
    }


@router.get(
    "/{session_id}/next",
    response_model=Optional[StudentPracticeItemView],
    summary="Get the next practice item",
    description="Returns the next server-authoritative question view, omitting answers and branch secrets."
)
async def get_next_practice_item(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    item = AdaptivePracticeService.get_next_item(session_id, user_id)
    return item


@router.post(
    "/{session_id}/response",
    response_model=Optional[PracticeFeedback],
    summary="Submit student response for practice item",
    description="Validates response, updates difficulty, feeds Mastery Graph & Mistake DNA, and advances session."
)
async def submit_practice_response(
    session_id: str,
    req: PracticeResponseRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    feedback = AdaptivePracticeService.submit_response(
        session_id=session_id,
        user_id=user_id,
        item_id=req.item_id,
        student_response=req.student_response,
        question_index=req.question_index,
        response_time_ms=req.response_time_ms,
        attempt_sequence=req.attempt_sequence
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response submission could not be processed for this session."
        )
    return feedback


@router.post(
    "/{session_id}/hint",
    summary="Request hint for current practice item",
    description="Provides progressive hint ladder. Note: hint usage downgrades independence level."
)
async def request_practice_hint(
    session_id: str,
    req: PracticeHintRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)

    # Server-Side Support Lock (§29): Intercept attempts to fetch hints during transfer
    from app.services.transfer.repository import TransferRepository
    from app.services.transfer.service import AIOffTransferCheckService
    ts = TransferRepository.get_session(session_id)
    if ts:
        AIOffTransferCheckService.abort_session(session_id, user_id, reason="HINT_REQUESTED_DURING_TRANSFER")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI assistance is locked during an active Transfer Check. Attempt invalidated."
        )

    hint_text, revealed, total = AdaptivePracticeService.request_hint(
        session_id=session_id,
        user_id=user_id,
        item_id=req.item_id
    )
    if not hint_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hints available for this item."
        )
    return {
        "hint": hint_text,
        "hints_revealed": revealed,
        "total_hints": total
    }


@router.get(
    "/{session_id}",
    response_model=Optional[PracticeSession],
    summary="Get practice session details"
)
async def get_practice_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    session = AdaptivePracticeService.get_session(session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found."
        )
    return session


@router.post(
    "/{session_id}/resume",
    summary="Resume practice session across reloads"
)
async def resume_practice_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    result = AdaptivePracticeService.resume_session(session_id, user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found or access denied."
        )
    session, item = result
    return {
        "session": session,
        "current_item": item
    }


@router.get(
    "/{session_id}/explain",
    response_model=Optional[PracticeSelectionExplanation],
    summary="Explain question selection rationale",
    description="Returns real pedagogical evidence explaining why the question was chosen."
)
async def explain_practice_selection(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    explanation = AdaptivePracticeService.explain_selection(session_id, user_id)
    if not explanation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selection explanation not available for this session item."
        )
    return explanation


@router.get(
    "/{session_id}/summary",
    response_model=Optional[SessionSummary],
    summary="Get session completion pedagogical summary",
    description="Provides pedagogical outcomes without gamified tokens or fake mastery %."
)
async def get_practice_session_summary(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    summary = AdaptivePracticeService.get_session_summary(session_id, user_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session summary not available."
        )
    return summary


@router.get(
    "/content/audit",
    response_model=ContentAuditReport,
    summary="Audit practice content bank coverage and validity"
)
async def audit_practice_content(
    current_user=Depends(get_current_user)
):
    # Verified students and teachers can inspect content coverage matrix
    return ContentAuditor.audit_all()
