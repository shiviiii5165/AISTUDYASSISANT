from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum


class XPReasonCode(str, Enum):
    DIAGNOSTIC_COMPLETION = "DIAGNOSTIC_COMPLETION"
    MISTAKE_REPAIRED = "MISTAKE_REPAIRED"
    STEP_CHECK_SUCCESS = "STEP_CHECK_SUCCESS"
    PRACTICE_STREAK = "PRACTICE_STREAK"
    TRANSFER_VERIFIED = "TRANSFER_VERIFIED"
    DAILY_LOGIN = "DAILY_LOGIN"
    SOCRATIC_SESSION_MILESTONE = "SOCRATIC_SESSION_MILESTONE"


class XPTransaction(BaseModel):
    id: str
    user_id: str
    amount: int
    reason_code: XPReasonCode
    source_entity_type: str
    source_entity_id: Optional[str] = None
    idempotency_key: str
    created_at: datetime


class StreakSummary(BaseModel):
    user_id: str
    current_streak_days: int
    longest_streak_days: int
    last_activity_date: date
    freeze_credits_remaining: int
    is_active_today: bool


class BadgeItem(BaseModel):
    id: str
    user_id: str
    badge_key: str
    title: str
    description: str
    tier: str
    awarded_at: datetime


class GamificationSummary(BaseModel):
    user_id: str
    total_xp: int
    level: int
    xp_to_next_level: int
    level_progress_percentage: int
    streak: StreakSummary
    badges: List[BadgeItem]
    recent_transactions: List[XPTransaction]


class AwardXPRequest(BaseModel):
    amount: int = Field(..., gt=0, le=500)
    reason_code: XPReasonCode
    source_entity_type: str
    source_entity_id: Optional[str] = None
    idempotency_key: str

