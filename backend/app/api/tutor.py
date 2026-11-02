"""
LearnByGenie — Feature 4: Socratic Tutor API Endpoint
======================================================
Production endpoints for Personalized Socratic Tutor V2:
- POST /api/tutor/session/turn: Canonical multi-turn teaching engine (§10-§35)
- GET  /api/tutor/session/active: Resume active learning session (§28)
- GET  /api/tutor/session/{session_id}: Retrieve session state with ownership enforcement (§40)
- POST /api/tutor/turn: Legacy additive endpoint for backward compatibility
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.core.security import limiter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.agents.librarian import LibrarianOutput
from app.agents.tutor import tutor_turn, TutorTurn
from app.core.dependencies import get_current_user
from app.services.tutor.schemas import TutorTurnResponse, TutorMode, TutorSessionState
from app.services.tutor.service import PersonalizedTutorService
from app.services.tutor.repository import TutorSessionRepository

router = APIRouter()


class TutorRequest(BaseModel):
    """Request body for legacy tutor turn endpoint."""
    topic: str = Field(..., description="The concept being taught.")
    librarian_context: LibrarianOutput = Field(
        ..., description="Structured context from the Librarian agent."
    )
    conversation_history: List[dict] = Field(
        default_factory=list,
        description="Prior turns as [{role, content}, ...].",
    )
    student_message: Optional[str] = Field(
        None,
        description="The student's latest reply. Null for the very first turn.",
    )


class SocraticSessionTurnRequest(BaseModel):
    """Canonical request body for Socratic Tutor V2 turn."""
    message: str = Field(..., description="Student input message, query, or check response.")
    session_id: Optional[str] = Field(None, description="Active session ID for multi-turn continuity.")
    mode: Optional[TutorMode] = Field(None, description="Explicit mode override: QUICK_ASK or TUTOR.")
    subject: Optional[str] = Field(None, description="Target subject (e.g. Mathematics, Physics).")
    pdf_id: Optional[str] = Field(None, description="Scoped uploaded document ID.")
    user_action: Optional[str] = Field(None, description="Natural action: HINT, FULL_EXPLANATION, SIMPLIFY, SKIP_PREREQUISITE.")


@router.post("/turn", response_model=TutorTurn)
@limiter.limit("20/minute")
async def tutor_turn_endpoint(request: Request, payload: TutorRequest, current_user=Depends(get_current_user)):
    """Legacy additive endpoint for backward compatibility."""
    result = await tutor_turn(
        topic=payload.topic,
        librarian_context=payload.librarian_context,
        conversation_history=payload.conversation_history,
        student_message=payload.student_message,
    )
    return result


@router.post("/session/turn", response_model=TutorTurnResponse)
@limiter.limit("30/minute")
async def socratic_session_turn_endpoint(
    request: Request,
    payload: SocraticSessionTurnRequest,
    current_user=Depends(get_current_user)
):
    """
    Canonical Personalized Socratic Tutor V2 turn endpoint (§10-§35).
    Executes Socratic state machine, Hint ladder, checks, and mastery updates.
    """
    user_id = str(current_user.id)
    # Server-Side Support Lock (§5, §6, §28, §29)
    from app.services.transfer.service import AIOffTransferCheckService
    if AIOffTransferCheckService.is_support_locked(user_id):
        AIOffTransferCheckService.record_support_attempt(user_id, support_channel="TUTOR_SESSION_TURN")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer Check in progress: AI assistance is disabled during independent verification. Active transfer session invalidated."
        )
    try:
        response = await PersonalizedTutorService.process_turn(
            user_id=user_id,
            message=payload.message,
            session_id=payload.session_id,
            explicit_mode=payload.mode,
            subject=payload.subject,
            pdf_id=payload.pdf_id,
            user_action=payload.user_action
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Socratic tutor turn failed: {str(e)}"
        )


@router.get("/session/active", response_model=Optional[TutorSessionState])
async def get_active_session(
    subject: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Retrieves current active tutoring session for resume (§28)."""
    user_id = str(current_user.id)
    return TutorSessionRepository.get_latest_session_for_user(user_id, subject)


@router.get("/session/{session_id}", response_model=TutorSessionState)
async def get_session_by_id(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Retrieves specific session with strict user ownership isolation (§40)."""
    user_id = str(current_user.id)
    session = TutorSessionRepository.get_session(session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutoring session not found or access denied."
        )
    return session
