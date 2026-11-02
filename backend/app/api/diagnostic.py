"""
LearnByGenie — Adaptive Diagnostic & Actual-Level Detection API (Feature 2)
=============================================================================
Endpoints for student adaptive diagnostic sessions, responses, and reports.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.services.diagnostic.service import DiagnosticService
from app.services.diagnostic.schemas import (
    DiagnosticStartRequest, AnswerSubmissionRequest,
    DiagnosticStepResponse, DiagnosticResult
)
from app.services.diagnostic.audit import audit_entire_item_bank, ContentAuditReport

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return user_id


@router.post(
    "/start",
    response_model=DiagnosticStepResponse,
    summary="Start or resume an adaptive diagnostic session",
    description="Initializes diagnostic using LearnerContextService. Selects initial anchor question without exposing answer keys."
)
async def start_diagnostic(
    req: DiagnosticStartRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    # Teacher accounts are restricted from student-owned diagnostics (§32)
    role = getattr(current_user, "role", "student")
    if role == "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Diagnostic sessions are intended for student accounts."
        )

    return DiagnosticService.start_diagnostic(
        user_id=user_id,
        subject=req.subject,
        retake=req.retake
    )


@router.post(
    "/{session_id}/answer",
    response_model=DiagnosticStepResponse,
    summary="Submit answer for the current diagnostic item",
    description="Grades answer server-side, idempotently records evidence, and adaptively selects the next question or finalizes the result."
)
async def submit_diagnostic_answer(
    session_id: str,
    submission: AnswerSubmissionRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return DiagnosticService.submit_answer(
        user_id=user_id,
        session_id=session_id,
        submission=submission
    )


@router.get(
    "/history",
    response_model=List[DiagnosticResult],
    summary="List student's historical diagnostic reports",
    description="Returns all completed diagnostic assessments for the authenticated student."
)
async def get_diagnostic_history(current_user=Depends(get_current_user)):
    user_id = _get_verified_user_id(current_user)
    return DiagnosticService.get_history(user_id=user_id)


@router.get(
    "/admin/audit",
    response_model=ContentAuditReport,
    summary="Audit diagnostic item bank quality",
    description="Tooling for validating item prompt completeness, skill linkages, MCQ options, and absence of broken items."
)
async def audit_items():
    return audit_entire_item_bank()


@router.get(
    "/{session_id}",
    response_model=DiagnosticStepResponse,
    summary="Get or resume diagnostic session state",
    description="Retrieves current session state and active unanswered question for safe resumption."
)
async def get_diagnostic_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return DiagnosticService.get_session_state(user_id=user_id, session_id=session_id)


@router.get(
    "/{session_id}/result",
    response_model=DiagnosticResult,
    summary="Get completed diagnostic result and recommendations",
    description="Returns immutable diagnostic assessment, prerequisite gap chain, and Feature 3 ingestion contract."
)
async def get_diagnostic_result(
    session_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return DiagnosticService.get_result(user_id=user_id, session_id=session_id)
