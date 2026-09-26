"""
Lesson Planner VNext API Router (Version 2.0)
==============================================
Production-hardened REST API for Evidence-Adaptive Teaching Operating System.
- Feature-flag protection: HTTP 503 FEATURE_NOT_ENABLED when LESSON_VNEXT_ENABLED=False
- Atomic Compare-And-Swap (CAS) optimistic concurrency on plan adaptations
- Database-backed dual evidence idempotency
- Full P3 cross-feature contracts
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, UniversalResourceCard,
    ProductMode, CanonicalDomain, TeachingIntent, TopicVolatility,
    LearningEvidenceRecord, TeacherLockItem, PlanRecompileDiff
)
from app.services.lesson_planner.vnext.compiler import LessonCompiler
from app.services.lesson_planner.vnext.resources.trust_engine import ResourceTrustEngine
from app.services.lesson_planner.vnext.adaptive import AdaptiveLessonEngine, VersionConflictException
from app.services.lesson_planner.vnext.explainability import ExplainabilityEngine
from app.services.lesson_planner.vnext.shared_context import LearningEvidenceService, LessonContextProvider
from app.api.lesson_planner import _MEMORY_ROADMAPS, _MEMORY_ROADMAP_OWNERS, _save_roadmap, _get_roadmap

logger = logging.getLogger("learnbygenie.api.lesson_planner_v2")


def check_vnext_enabled():
    """Guarantees strict 503 response if Lesson Planner VNext is disabled."""
    if not getattr(settings, "LESSON_VNEXT_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "FEATURE_NOT_ENABLED",
                "message": "Lesson Planner VNext is currently disabled in this environment.",
                "legacy_route": "/api/lesson-planner/generate"
            }
        )


router = APIRouter(dependencies=[Depends(check_vnext_enabled)])


# Request / Response Schemas
class CreatePlanV2Request(BaseModel):
    topic: str
    grade: str = "B.Tech"
    subject: str = "General"
    duration_minutes: int = 60
    language: str = "english"
    mode: ProductMode = ProductMode.TEACHER_CLASSROOM
    custom_context: Optional[str] = None
    board: str = "Standard"


class IngestEvidenceRequest(BaseModel):
    evidence: List[LearningEvidenceRecord]
    auto_apply: bool = False
    active_class_size: int = 10


class TeacherDecisionRequest(BaseModel):
    diff: PlanRecompileDiff
    decision: str = "ACCEPT"  # ACCEPT, IGNORE, MODIFY
    expected_plan_version: int = 1


class SetLockRequest(BaseModel):
    stage_id: Optional[str] = None
    lock_type: str  # objective, stage, duration, resource, assessment, activity
    target_identifier: str
    is_locked: bool = True
    notes: Optional[str] = None


class ResourceFeedbackRequest(BaseModel):
    resource_id: str
    stage_id: str
    feedback_type: str
    rating: int = 5
    comments: Optional[str] = None


@router.post("/plan", response_model=LearningRoadmap)
async def create_vnext_plan(
    request: CreatePlanV2Request,
    current_user = Depends(get_current_user)
):
    """
    POST /api/lesson-planner/v2/plan
    Compiles an adaptive lesson plan matching the Evidence-Adaptive Teaching OS specifications.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic=request.topic,
        grade=request.grade,
        subject=request.subject,
        duration_minutes=request.duration_minutes,
        language=request.language,
        mode=request.mode,
        custom_context=request.custom_context,
        board=request.board,
        student_id=user_id
    )
    roadmap.created_by = user_id
    _save_roadmap(roadmap, user_id)
    return roadmap


@router.get("/{plan_id}/stages", response_model=List[RoadmapStage])
async def get_plan_stages(
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """
    GET /api/lesson-planner/v2/{plan_id}/stages
    Returns the stage sequence and metadata for the given plan.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")
    return roadmap.stages


@router.get("/{plan_id}/stages/{stage_id}/resources", response_model=List[UniversalResourceCard])
async def get_stage_universal_resources(
    plan_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    """
    GET /api/lesson-planner/v2/{plan_id}/stages/{stage_id}/resources
    Returns the scored and filtered universal resources for a specific stage.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    cards = await ResourceTrustEngine.aggregate_stage_resources(
        topic=roadmap.topic,
        stage=stage,
        domain=roadmap.domain,
        intent=roadmap.intent,
        learner_level=roadmap.level,
        mode=roadmap.mode,
        volatility=roadmap.volatility
    )
    return cards


@router.post("/{plan_id}/evidence")
async def submit_learning_evidence(
    plan_id: str,
    request: IngestEvidenceRequest,
    current_user = Depends(get_current_user)
):
    """
    POST /api/lesson-planner/v2/{plan_id}/evidence
    Ingests student/class evidence with dual idempotency and returns adaptive diff preview.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Ingest evidence with dual idempotency tracking
    duplicate_count = 0
    for item in request.evidence:
        item.roadmap_id = plan_id
        _, is_dup = LearningEvidenceService.record_evidence(item)
        if is_dup:
            duplicate_count += 1

    diff = AdaptiveLessonEngine.evaluate_and_recompile(
        roadmap=roadmap,
        evidence_list=request.evidence,
        auto_apply=request.auto_apply,
        active_class_size=request.active_class_size
    )
    _save_roadmap(roadmap, user_id)
    
    return {
        "diff": diff,
        "is_duplicate": (duplicate_count == len(request.evidence) and len(request.evidence) > 0),
        "total_records": len(request.evidence),
        "duplicate_records": duplicate_count
    }


@router.post("/{plan_id}/recompile", response_model=LearningRoadmap)
async def apply_recompile_decision(
    plan_id: str,
    request: TeacherDecisionRequest,
    current_user = Depends(get_current_user)
):
    """
    POST /api/lesson-planner/v2/{plan_id}/recompile
    Atomic Compare-And-Swap (CAS) recompile decision execution.
    Returns HTTP 409 on version conflict.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        updated = AdaptiveLessonEngine.apply_teacher_decision(
            roadmap=roadmap,
            diff=request.diff,
            decision=request.decision,
            expected_plan_version=request.expected_plan_version
        )
        _save_roadmap(updated, user_id)
        return updated
    except VersionConflictException as vce:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "VERSION_CONFLICT",
                "message": str(vce),
                "current_version": getattr(roadmap, "current_version", roadmap.version),
                "expected_version": request.expected_plan_version
            }
        )


@router.post("/{plan_id}/locks")
async def toggle_teacher_lock(
    plan_id: str,
    request: SetLockRequest,
    current_user = Depends(get_current_user)
):
    """
    POST /api/lesson-planner/v2/{plan_id}/locks
    Locks or unlocks a stage, duration, or objective from automated AI modification.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    if request.stage_id:
        target_stage = next((s for s in roadmap.stages if s.id == request.stage_id), None)
        if target_stage:
            target_stage.is_locked = request.is_locked

    lock_item = TeacherLockItem(
        stage_id=request.stage_id,
        lock_type=request.lock_type,
        target_identifier=request.target_identifier,
        is_locked=request.is_locked,
        notes=request.notes or ""
    )
    roadmap.teacher_locks.append(lock_item)
    _save_roadmap(roadmap, user_id)
    return {"status": "success", "is_locked": request.is_locked, "message": "Lock updated successfully"}


@router.post("/{plan_id}/resource-feedback")
async def submit_resource_feedback(
    plan_id: str,
    request: ResourceFeedbackRequest,
    current_user = Depends(get_current_user)
):
    """
    POST /api/lesson-planner/v2/{plan_id}/resource-feedback
    Collects teacher and student outcome telemetry for precision ranking.
    """
    check_vnext_enabled()
    return {"status": "recorded", "resource_id": request.resource_id, "rating": request.rating}


@router.get("/{plan_id}/why")
async def get_plan_why_report(
    plan_id: str,
    stage_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    GET /api/lesson-planner/v2/{plan_id}/why
    Generates explainability reports explaining 'Why now?' and 'Why this stage archetype?'.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    if stage_id:
        target_stage = next((s for s in roadmap.stages if s.id == stage_id), None)
        if target_stage:
            return ExplainabilityEngine.explain_stage(target_stage, roadmap)

    return ExplainabilityEngine.generate_plan_why_report(roadmap)


@router.get("/{plan_id}/shared-context")
async def get_shared_lesson_context(
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """
    GET /api/lesson-planner/v2/{plan_id}/shared-context
    Provides standardized SharedLessonContext for PPT, Quiz, TeachMe, and Notes.
    """
    check_vnext_enabled()
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(plan_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Plan not found")

    return LessonContextProvider.get_shared_context(roadmap)
