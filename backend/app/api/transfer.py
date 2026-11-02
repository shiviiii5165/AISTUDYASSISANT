"""
LearnByGenie — AI-Off Transfer Check API (Feature 7)
=====================================================
Endpoints for independent verification sessions, response submission,
strict AI support locking, and pedagogical summaries.
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user

from app.services.transfer.service import AIOffTransferCheckService
from app.services.transfer.schemas import (
    TransferTrigger, TransferLevel, TransferSessionStatus,
    StudentTransferItemView, TransferFeedback, TransferSummary,
    TransferEligibilityResult, TransferSession
)
from app.services.transfer.audit import TransferAuditor, TransferAuditReport

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return user_id


class TransferEligibilityRequest(BaseModel):
    skill_id: str
    trigger: TransferTrigger = TransferTrigger.PRACTICE_REPAIR
    trigger_id: str = ""


class TransferStartRequest(BaseModel):
    skill_id: str
    subject: str = "Mathematics"
    source_trigger: TransferTrigger = TransferTrigger.PRACTICE_REPAIR
    source_trigger_id: str = ""
    transfer_level: TransferLevel = TransferLevel.NEAR_TRANSFER
    excluded_item_ids: Optional[List[str]] = None


class TransferSubmitRequest(BaseModel):
    item_id: str
    student_response: Any
    response_time_ms: int = 0
    question_index: int = 0


class TransferAbortRequest(BaseModel):
    reason: str = "SUPPORT_REQUESTED"


@router.post(
    "/eligibility",
    summary="Check transfer verification eligibility",
    description="Determines whether an independent check is eligible for a skill and trigger."
)
async def check_eligibility(
    req: TransferEligibilityRequest,
    current_user=Depends(get_current_user)
) -> TransferEligibilityResult:
    user_id = _get_verified_user_id(current_user)
    return AIOffTransferCheckService.check_eligibility(
        user_id=user_id,
        skill_id=req.skill_id,
        trigger=req.trigger,
        trigger_id=req.trigger_id
    )


@router.post(
    "/start",
    summary="Start an independent transfer check",
    description="Initializes a durable transfer session with AI assistance locked off."
)
async def start_transfer_session(
    req: TransferStartRequest,
    current_user=Depends(get_current_user)
) -> TransferSession:
    user_id = _get_verified_user_id(current_user)
    session = AIOffTransferCheckService.start_session(
        user_id=user_id,
        skill_id=req.skill_id,
        subject=req.subject,
        source_trigger=req.source_trigger,
        source_trigger_id=req.source_trigger_id,
        transfer_level=req.transfer_level,
        excluded_item_ids=req.excluded_item_ids
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="INSUFFICIENT_TRANSFER_CONTENT: No eligible unrepeated transfer items available for this skill."
        )
    return session


@router.get(
    "/{session_id}/item",
    summary="Fetch the current independent transfer item",
    description="Returns sanitized question view without correct answers or hints."
)
async def get_transfer_item(
    session_id: str,
    current_user=Depends(get_current_user)
) -> StudentTransferItemView:
    user_id = _get_verified_user_id(current_user)
    item_view = AIOffTransferCheckService.get_current_item(session_id, user_id)
    if not item_view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active transfer question found for this session."
        )
    return item_view


@router.post(
    "/{session_id}/submit",
    summary="Submit independent response",
    description="Evaluates answer, enforces independence, updates Mastery Graph and Mistake DNA."
)
async def submit_transfer_response(
    session_id: str,
    req: TransferSubmitRequest,
    current_user=Depends(get_current_user)
) -> TransferFeedback:
    user_id = _get_verified_user_id(current_user)
    feedback = AIOffTransferCheckService.submit_response(
        session_id=session_id,
        user_id=user_id,
        item_id=req.item_id,
        student_response=req.student_response,
        response_time_ms=req.response_time_ms,
        question_index=req.question_index
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process transfer response. Please verify session ownership and question index."
        )
    return feedback


@router.post(
    "/{session_id}/abort",
    summary="Abort transfer check",
    description="Interrupted or aborted if student requests help or leaves."
)
async def abort_transfer_session(
    session_id: str,
    req: TransferAbortRequest,
    current_user=Depends(get_current_user)
) -> TransferSession:
    user_id = _get_verified_user_id(current_user)
    session = AIOffTransferCheckService.abort_session(session_id, user_id, reason=req.reason)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer session not found or unauthorized."
        )
    return session


@router.get(
    "/{session_id}/summary",
    summary="Get transfer check outcome summary",
    description="Returns pedagogical outcome without gamification or fake scores."
)
async def get_transfer_summary(
    session_id: str,
    current_user=Depends(get_current_user)
) -> TransferSummary:
    user_id = _get_verified_user_id(current_user)
    summary = AIOffTransferCheckService.get_session_summary(session_id, user_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer summary not found."
        )
    return summary


@router.get(
    "/{session_id}/resume",
    summary="Resume transfer session",
    description="Cold restart recovery for active session."
)
async def resume_transfer_session(
    session_id: str,
    current_user=Depends(get_current_user)
) -> dict:
    user_id = _get_verified_user_id(current_user)
    res = AIOffTransferCheckService.resume_session(session_id, user_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session could not be resumed."
        )
    sess, item = res
    return {
        "session": sess,
        "item": item
    }


@router.get(
    "/audit/report",
    summary="Run Transfer Check integrity audit",
    description="Audits all sessions for independence, unverified items, and evidence round trips."
)
async def run_transfer_audit(
    current_user=Depends(get_current_user)
) -> TransferAuditReport:
    _get_verified_user_id(current_user)
    return TransferAuditor.audit_all()
