"""
LearnByGenie — Mistake DNA Engine API (Feature 5)
=================================================
REST API endpoints for:
- Student mistake patterns (ISOLATED, RECURRING, PERSISTENT, REPAIRED)
- Chronological error occurrence event history
- Explainable pattern detail & prerequisite correlation
- Verifiable repair recommendations
- Bounded summary for learner context
- Deterministic health audit

Security (§30):
- Student identity derived strictly from validated JWT (get_current_user).
- Students can only read their own records.
- Direct client writes of error types, pattern statuses, or repair statuses are blocked.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.repository import MistakeDNARepository
from app.services.mistake_dna.schemas import (
    MistakePattern, MistakeEvent, RepairRecommendation,
    RepairEvent, CompactMistakeSummary, MistakeDNAAuditReport,
    PatternStatus, RepairStatus, ErrorType
)
from app.services.mistake_dna.audit import MistakeDNAAuditor
from app.services.diagnostic.curriculum_blueprint import get_skill

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return user_id


class PatternDetailResponse(BaseModel):
    pattern: MistakePattern
    skill_name: str
    explainability: str
    recommended_repair: RepairRecommendation
    repair_history: List[RepairEvent]


@router.get(
    "/patterns",
    response_model=List[MistakePattern],
    summary="Get student's mistake patterns",
    description="Returns aggregated mistake patterns (ISOLATED, RECURRING, PERSISTENT, REPAIRED)."
)
async def get_mistake_patterns(
    skill_id: Optional[str] = Query(default=None, description="Optional skill ID filter"),
    subject: Optional[str] = Query(default=None, description="Optional subject filter"),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    if skill_id:
        return MistakeDNAService.get_skill_patterns(user_id=user_id, skill_id=skill_id)
    return MistakeDNAService.get_patterns(user_id=user_id, subject=subject)


@router.get(
    "/recent",
    response_model=List[MistakeEvent],
    summary="Get student's recent mistake occurrence events",
    description="Returns chronological ledger of detected learning errors."
)
async def get_recent_mistakes(
    limit: int = Query(default=50, ge=1, le=100),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MistakeDNAService.get_recent_mistakes(user_id=user_id, limit=limit)


@router.get(
    "/detail/{pattern_id}",
    response_model=PatternDetailResponse,
    summary="Get pattern detail and explainability",
    description="Provides detailed diagnosis, why the pattern is recurring/persistent, prerequisite signals, and repair evidence."
)
async def get_pattern_detail(
    pattern_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    pattern = MistakeDNARepository.get_pattern_by_id(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Mistake pattern not found.")

    # Cross-user data isolation (§30, §45)
    if pattern.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to mistake pattern.")

    sk_obj = get_skill(pattern.skill_id)
    sk_name = sk_obj.skill_name if sk_obj else pattern.skill_id

    rec = MistakeDNAService.get_repair_recommendation(pattern)
    repairs = MistakeDNARepository.get_repairs_for_pattern(pattern_id)

    explain_str = (
        f"This pattern is classified as {pattern.pattern_status.value} based on {pattern.occurrence_count} "
        f"independent occurrence{'s' if pattern.occurrence_count != 1 else ''}. "
        f"First observed on {pattern.first_seen_at.strftime('%b %d, %Y')} and most recently on "
        f"{pattern.last_seen_at.strftime('%b %d, %Y')}."
    )

    return PatternDetailResponse(
        pattern=pattern,
        skill_name=sk_name,
        explainability=explain_str,
        recommended_repair=rec,
        repair_history=repairs
    )


@router.get(
    "/repairs",
    response_model=List[RepairRecommendation],
    summary="Get open repair recommendations",
    description="Returns actionable repair tasks for active mistake patterns without weakness scoring."
)
async def get_open_repairs(
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MistakeDNAService.get_open_repairs(user_id)


@router.get(
    "/summary",
    response_model=CompactMistakeSummary,
    summary="Get compact bounded mistake summary",
    description="Returns lightweight summary for student profile or AI context integration."
)
async def get_mistake_summary(
    subject: Optional[str] = Query(default=None),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MistakeDNAService.get_compact_mistake_summary(user_id=user_id, subject=subject)


@router.post(
    "/audit",
    response_model=MistakeDNAAuditReport,
    summary="Run Mistake DNA integrity audit",
    description="Performs deterministic checks on taxonomy labels, orphan skills, duplicate events, and repair evidence."
)
async def run_audit(
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MistakeDNAAuditor.run_audit(user_id=user_id)
