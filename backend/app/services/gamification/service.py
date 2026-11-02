from typing import List, Dict, Any, Optional
import math

from app.services.gamification.schemas import (
    XPTransaction,
    XPReasonCode,
    StreakSummary,
    BadgeItem,
    GamificationSummary
)
from app.services.gamification.repository import GamificationRepository


class GamificationService:
    """Core domain service for XP balances, streaks, level progression, and badges."""

    # 100 XP per level baseline with quadratic progression: Level N requires 100 * N XP
    @classmethod
    def calculate_level_progression(cls, total_xp: int) -> tuple[int, int, int]:
        """Returns (current_level, xp_needed_for_next, progress_percentage)."""
        if total_xp <= 0:
            return 1, 100, 0
        
        # Level N requires cumulative XP: sum_{i=1}^{N-1} (100 * i) = 50 * (N-1) * N
        level = 1
        cum_xp = 0
        while True:
            xp_for_next = level * 100
            if cum_xp + xp_for_next > total_xp:
                current_level_xp = total_xp - cum_xp
                pct = int((current_level_xp / xp_for_next) * 100)
                return level, xp_for_next - current_level_xp, pct
            cum_xp += xp_for_next
            level += 1

    @classmethod
    def award_xp(
        cls,
        user_id: str,
        amount: int,
        reason_code: XPReasonCode,
        source_entity_type: str,
        idempotency_key: str,
        source_entity_id: Optional[str] = None
    ) -> tuple[XPTransaction, bool]:
        """Awards XP idempotently and checks for milestone badges."""
        # Enforce canonical blueprint daily cap on repeated easy items (§8)
        if reason_code == XPReasonCode.REPEATED_EASY_PRACTICE:
            from datetime import datetime, timezone
            today_str = datetime.now(timezone.utc).date().isoformat()
            history = GamificationRepository.get_user_transactions(user_id)
            today_easy_xp = sum(
                t.amount for t in history
                if t.reason_code == XPReasonCode.REPEATED_EASY_PRACTICE and t.created_at.date().isoformat() == today_str
            )
            if today_easy_xp >= 10:
                amount = 0
            else:
                amount = min(amount, 10 - today_easy_xp)

        tx, is_new = GamificationRepository.record_xp_transaction(
            user_id=user_id,
            amount=amount,
            reason_code=reason_code,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            idempotency_key=idempotency_key
        )

        if is_new:
            # Check milestone badges
            total_xp = GamificationRepository.get_total_xp(user_id)
            if total_xp >= 100:
                GamificationRepository.award_badge(
                    user_id=user_id,
                    badge_key="CENTURION_XP",
                    title="Centurion",
                    description="Earned your first 100 XP in learning activities.",
                    tier="bronze"
                )
            if total_xp >= 500:
                GamificationRepository.award_badge(
                    user_id=user_id,
                    badge_key="SCHOLAR_XP",
                    title="Rising Scholar",
                    description="Accumulated 500 XP through rigorous study.",
                    tier="silver"
                )
            if reason_code in (XPReasonCode.MISTAKE_REPAIRED, XPReasonCode.ERROR_RESOLUTION_UNSEEN):
                GamificationRepository.award_badge(
                    user_id=user_id,
                    badge_key="ERROR_TERMINATOR",
                    title="Error Terminator",
                    description="Successfully repaired a recurring misconception.",
                    tier="bronze"
                )
            if reason_code in (XPReasonCode.STEP_CHECK_SUCCESS, XPReasonCode.TIER_3_INDEPENDENT_PROFICIENCY):
                GamificationRepository.award_badge(
                    user_id=user_id,
                    badge_key="FIRST_STEP_MASTER",
                    title="Logic Master",
                    description="Verified full derivation without a single step error.",
                    tier="bronze"
                )

        return tx, is_new

    @classmethod
    def award_blueprint_xp(
        cls,
        user_id: str,
        reason_code: XPReasonCode,
        source_entity_type: str,
        idempotency_key: str,
        source_entity_id: Optional[str] = None
    ) -> tuple[XPTransaction, bool]:
        """Awards canonical blueprint XP amount for verified educational behavior."""
        from app.services.gamification.schemas import CANONICAL_BLUEPRINT_XP_AMOUNTS
        amt = CANONICAL_BLUEPRINT_XP_AMOUNTS.get(reason_code, 20)
        return cls.award_xp(
            user_id=user_id,
            amount=amt,
            reason_code=reason_code,
            source_entity_type=source_entity_type,
            idempotency_key=idempotency_key,
            source_entity_id=source_entity_id
        )

    @classmethod
    def check_in_streak(cls, user_id: str) -> StreakSummary:
        """Updates and maintains student streak."""
        summary = GamificationRepository.update_streak(user_id)
        if summary.current_streak_days >= 3:
            GamificationRepository.award_badge(
                user_id=user_id,
                badge_key="STREAK_3_DAYS",
                title="Consistent Learner",
                description="Maintained a 3-day continuous learning streak.",
                tier="bronze"
            )
        if summary.current_streak_days >= 7:
            GamificationRepository.award_badge(
                user_id=user_id,
                badge_key="STREAK_7_DAYS",
                title="Weekly Champion",
                description="Maintained a 7-day learning streak without missing a day.",
                tier="silver"
            )
        return summary

    @classmethod
    def get_summary(cls, user_id: str) -> GamificationSummary:
        """Assembles unified gamification summary."""
        total_xp = GamificationRepository.get_total_xp(user_id)
        level, xp_needed, pct = cls.calculate_level_progression(total_xp)
        streak = GamificationRepository.get_or_create_streak(user_id)
        badges = GamificationRepository.get_badges(user_id)
        txs = GamificationRepository.get_user_transactions(user_id, limit=10)

        # Baseline badges if none exist
        if not badges:
            b = GamificationRepository.award_badge(
                user_id=user_id,
                badge_key="GENIE_EXPLORER",
                title="Genie Explorer",
                description="Joined the LearnByGenie personalized learning platform.",
                tier="bronze"
            )
            if b:
                badges = [b]

        return GamificationSummary(
            user_id=user_id,
            total_xp=total_xp,
            level=level,
            xp_to_next_level=xp_needed,
            level_progress_percentage=pct,
            streak=streak,
            badges=badges,
            recent_transactions=txs
        )

