from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, AuthenticatedUser
from app.services.gamification.service import GamificationService
from app.services.gamification.schemas import (
    GamificationSummary,
    StreakSummary,
    AwardXPRequest,
    XPTransaction
)

router = APIRouter()


@router.get("/summary", response_model=GamificationSummary)
def get_gamification_summary(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the authenticated learner's complete gamification summary (XP, level, streak, badges)."""
    return GamificationService.get_summary(current_user.id)


@router.post("/streak/check-in", response_model=StreakSummary)
def record_streak_check_in(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Records daily activity and returns updated streak details."""
    return GamificationService.check_in_streak(current_user.id)


@router.post("/award", response_model=XPTransaction)
def award_xp_endpoint(payload: AwardXPRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Idempotently records an XP award event for verified educational completion."""
    tx, _ = GamificationService.award_xp(
        user_id=current_user.id,
        amount=payload.amount,
        reason_code=payload.reason_code,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        idempotency_key=payload.idempotency_key
    )
    return tx

