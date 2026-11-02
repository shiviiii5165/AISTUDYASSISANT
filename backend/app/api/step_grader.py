"""
LearnByGenie — Feature 8: Step-Grader & Reasoning Diagnostics API
==================================================================
Endpoints for:
- Multi-step solution grading with first-wrong-step pinpointing
- Solution resubmission & versioning
- Bounded Socratic Tutor review context
- Grading capability matrix reporting
- System audit endpoint
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.services.step_grader.service import StepGraderService
from app.services.step_grader.repository import StepGraderRepository
from app.services.step_grader.schemas import (
    StepGraderResult, StepGraderSession, StepGraderAttempt,
    GradedStep, TutorHandoffContext, CapabilityMatrixItem
)
from app.services.step_grader.audit import StepGraderAuditor
from app.services.mastery.schemas import AssistanceLevel

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        # Fallback for dev / guest testing
        return "f1c205c6-03b3-479e-b7b8-ef435dd9f595"
    return user_id


class GradeSolutionRequest(BaseModel):
    question_text: str = Field(..., description="Problem prompt or initial equation")
    raw_input: str = Field(..., description="Multi-step solution text")
    subject: str = Field("Mathematics", description="Domain subject")
    skill_id: Optional[str] = Field(None, description="Target skill ID")
    assistance_level: AssistanceLevel = Field(AssistanceLevel.INDEPENDENT, description="Level of AI assistance")
    idempotency_key: Optional[str] = Field(None, description="Client idempotency token")
    rubric: Optional[Dict[str, Any]] = Field(None, description="Optional structured rubric criteria")
    audience_level: str = Field("standard", description="Audience adaptation ('young', 'standard', 'advanced')")


class ResubmitSolutionRequest(BaseModel):
    session_id: str = Field(..., description="Existing grading session ID")
    updated_raw_input: str = Field(..., description="Corrected solution steps")
    assistance_level: AssistanceLevel = Field(AssistanceLevel.INDEPENDENT, description="Level of AI assistance")
    audience_level: str = Field("standard", description="Audience adaptation")


@router.post("/grade", response_model=StepGraderResult)
async def grade_solution(
    req: GradeSolutionRequest,
    current_user=Depends(get_current_user)
):
    """
    Grades a multi-step student solution. Identifies the FIRST wrong step and classifies
    downstream consequences without double-counting.
    """
    user_id = _get_verified_user_id(current_user)
    try:
        result = StepGraderService.grade_solution(
            user_id=user_id,
            subject=req.subject,
            question_text=req.question_text,
            raw_input=req.raw_input,
            skill_id=req.skill_id,
            assistance_level=req.assistance_level,
            idempotency_key=req.idempotency_key,
            rubric=req.rubric,
            audience_level=req.audience_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/resubmit", response_model=StepGraderResult)
async def resubmit_solution(
    req: ResubmitSolutionRequest,
    current_user=Depends(get_current_user)
):
    """
    Resubmits an edited solution under an existing session.
    Increments attempt sequence and preserves parent lineage.
    """
    user_id = _get_verified_user_id(current_user)
    try:
        result = StepGraderService.resubmit_solution(
            session_id=req.session_id,
            user_id=user_id,
            updated_raw_input=req.updated_raw_input,
            assistance_level=req.assistance_level,
            audience_level=req.audience_level
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Retrieves session state and historical attempts for the authenticated student."""
    user_id = _get_verified_user_id(current_user)
    session = StepGraderRepository.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or unauthorized.")
    attempts = StepGraderRepository.get_attempts_for_session(session_id, user_id)
    return {
        "session": session,
        "attempts": attempts
    }


@router.get("/tutor-context/{attempt_id}", response_model=TutorHandoffContext)
async def get_tutor_context(
    attempt_id: str,
    current_user=Depends(get_current_user)
):
    """
    Retrieves bounded Socratic Tutor review context for a specific attempt's first wrong step.
    """
    user_id = _get_verified_user_id(current_user)
    try:
        return StepGraderService.get_tutor_context(attempt_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/capability-matrix", response_model=List[CapabilityMatrixItem])
async def get_capability_matrix():
    """Returns honest domain grading capability matrix separating engine support from coverage."""
    return StepGraderService.get_capability_matrix()


@router.get("/audit")
async def run_audit(current_user=Depends(get_current_user)):
    """Runs StepGraderAuditor invariant checks."""
    user_id = _get_verified_user_id(current_user)
    return StepGraderAuditor.run_system_audit(user_id)
