from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum


class XPReasonCode(str, Enum):
    # Canonical Blueprint XP Reasons (§8)
    BASELINE_DIAGNOSTIC = "BASELINE_DIAGNOSTIC"                      # Baseline diagnostic: +50 XP
    DIAGNOSTIC_COMPLETION = "DIAGNOSTIC_COMPLETION"                  # Alias
    ERROR_RESOLUTION_UNSEEN = "ERROR_RESOLUTION_UNSEEN"              # Active error resolution on an unseen item: +30 XP
    MISTAKE_REPAIRED = "MISTAKE_REPAIRED"                            # Alias
    TIER_3_INDEPENDENT_PROFICIENCY = "TIER_3_INDEPENDENT_PROFICIENCY"# Tier 3 independent proficiency: +40 XP
    STEP_CHECK_SUCCESS = "STEP_CHECK_SUCCESS"                        # Alias
    TIER_4_FRESH_TRANSFER = "TIER_4_FRESH_TRANSFER"                  # Tier 4 fresh transfer: +60 XP
    TRANSFER_VERIFIED = "TRANSFER_VERIFIED"                          # Alias
    TIER_5_DELAYED_RETENTION = "TIER_5_DELAYED_RETENTION"            # Tier 5 delayed Day-7/21 review: +45 XP
    TEACH_BACK_RUBRIC_PASS = "TEACH_BACK_RUBRIC_PASS"                # Quality teach-back with rubric >= 2/3: +25 XP
    REPEATED_EASY_PRACTICE = "REPEATED_EASY_PRACTICE"                # Repeated already-mastered easy items: 0–2 XP, capped at 10 XP/day
    DAILY_LOGIN = "DAILY_LOGIN"                                      # Daily consistency: +10 XP
    PRACTICE_STREAK = "PRACTICE_STREAK"                              # Practice streak: +15 XP
    SOCRATIC_SESSION_MILESTONE = "SOCRATIC_SESSION_MILESTONE"        # Socratic inquiry: +20 XP


CANONICAL_BLUEPRINT_XP_AMOUNTS = {
    XPReasonCode.BASELINE_DIAGNOSTIC: 50,
    XPReasonCode.DIAGNOSTIC_COMPLETION: 50,
    XPReasonCode.ERROR_RESOLUTION_UNSEEN: 30,
    XPReasonCode.MISTAKE_REPAIRED: 30,
    XPReasonCode.TIER_3_INDEPENDENT_PROFICIENCY: 40,
    XPReasonCode.STEP_CHECK_SUCCESS: 40,
    XPReasonCode.TIER_4_FRESH_TRANSFER: 60,
    XPReasonCode.TRANSFER_VERIFIED: 60,
    XPReasonCode.TIER_5_DELAYED_RETENTION: 45,
    XPReasonCode.TEACH_BACK_RUBRIC_PASS: 25,
    XPReasonCode.REPEATED_EASY_PRACTICE: 2,
    XPReasonCode.DAILY_LOGIN: 10,
    XPReasonCode.PRACTICE_STREAK: 15,
    XPReasonCode.SOCRATIC_SESSION_MILESTONE: 20,
}


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

