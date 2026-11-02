"""
LearnByGenie — Learner Intelligence Core API
Endpoints for student academic profile, preferences, learner context,
and database-driven academic configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.services.learner_context.service import LearnerContextService
from app.services.learner_context.schemas import (
    LearnerProfileUpdate,
    LearnerProfileResponse,
    LearnerContext,
    AcademicConfigResponse
)

router = APIRouter()


@router.get(
    "/academic-config",
    response_model=AcademicConfigResponse,
    summary="Get database-driven academic configuration",
    description="Returns canonical education levels (Class 3-12, UG), boards, exams, streams, subjects, goals, and languages."
)
async def get_academic_config():
    """Returns database/config-driven canonical records for frontend selectors."""
    return LearnerContextService.get_academic_config()


@router.get(
    "/profile",
    response_model=LearnerProfileResponse,
    summary="Get current student's learner profile",
    description="Retrieves the canonical academic profile. Falls back safely if profile not yet completed."
)
async def get_learner_profile(current_user=Depends(get_current_user)):
    """Retrieves authenticated student profile without exposing other users' data."""
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return LearnerContextService.get_profile(user_id)


@router.patch(
    "/profile",
    response_model=LearnerProfileResponse,
    summary="Update student learner profile",
    description="Validates and updates mutable academic profile fields, incrementing profile_version."
)
async def update_learner_profile(
    updates: LearnerProfileUpdate,
    current_user=Depends(get_current_user)
):
    """Updates authenticated student profile with strict backend validation."""
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return LearnerContextService.update_profile(user_id, updates)


@router.get(
    "/context",
    response_model=LearnerContext,
    summary="Get unified learner context",
    description="Canonical educational state consumed by AI Chat, Teach Me, Notes, Tutor, and future intelligence engines."
)
async def get_learner_context(current_user=Depends(get_current_user)):
    """Generates canonical LearnerContext for the current authenticated user."""
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    
    # Determine user role from app_metadata or user_metadata
    app_meta = getattr(current_user, "app_metadata", {}) or {}
    user_meta = getattr(current_user, "user_metadata", {}) or {}
    role = app_meta.get("role") or user_meta.get("role") or "student"

    return LearnerContextService.get_learner_context(user_id, role=role)
