"""
LearnByGenie — Feature 7: Transfer Policy & Deterministic Rules
================================================================
Config-driven, versioned policies governing:
- Eligibility conditions (§2, §42)
- Independence verification enforcement (§1, §4)
- Item novelty & exclusion (§6, §45)
- Audience-calibrated badge phrasing (Class 3-5 vs. Senior Secondary/UG) (§33, §34)
- Pass/Fail educational outcome mapping (§10, §32)
"""
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from .schemas import (
    TransferTrigger, TransferLevel, TransferSessionStatus,
    TransferOutcome, TransferPolicyConfig
)
from app.services.practice.schemas import PracticeItem, VerificationStatus


class TransferPolicy:
    """
    Versioned transfer check policy (§9).
    Prevents scattered magic numbers across the codebase.
    """

    def __init__(self, config: Optional[TransferPolicyConfig] = None):
        self.config = config or TransferPolicyConfig()
        self.version = self.config.version

    def is_eligible_trigger(self, trigger: TransferTrigger) -> bool:
        """
        Determines if a trigger qualifies for independent verification (§2, §42).
        Casual chat or passive browsing is strictly ineligible.
        """
        valid_triggers = {
            TransferTrigger.TUTOR_REPAIR,
            TransferTrigger.PRACTICE_REPAIR,
            TransferTrigger.MISTAKE_DNA_REPAIR,
            TransferTrigger.MASTERY_PROVISIONAL,
            TransferTrigger.STUDENT_REQUEST,
            TransferTrigger.MANUAL
        }
        return trigger in valid_triggers

    def check_cooldown(self, last_failure_time: Optional[datetime]) -> int:
        """Returns remaining cooldown seconds after a previous failure (§9)."""
        if not last_failure_time:
            return 0
        now = datetime.now(timezone.utc)
        elapsed = (now - last_failure_time).total_seconds()
        remaining = int(self.config.cooldown_seconds_after_failure - elapsed)
        return max(0, remaining)

    def select_eligible_items(
        self,
        candidate_items: List[PracticeItem],
        excluded_item_ids: Set[str],
        transfer_level: TransferLevel = TransferLevel.NEAR_TRANSFER
    ) -> List[PracticeItem]:
        """
        Selects verified, novel items for transfer check (§7, §8, §45).
        - Must have verification_status == VERIFIED
        - Must NOT have been answered in the triggering repair session
        - Preserves novelty
        """
        eligible = []
        for it in candidate_items:
            # 1. Verification status must be VERIFIED
            if it.verification_status != VerificationStatus.VERIFIED:
                continue
            # 2. Must not be recently served / answered in the repair loop
            if it.id in excluded_item_ids:
                continue
            eligible.append(it)
        return eligible

    def evaluate_attempt(
        self,
        is_correct: bool,
        assistance_level: str
    ) -> tuple[TransferOutcome, TransferSessionStatus, str, str]:
        """
        Evaluates attempt without judgment or shame (§10, §32).
        Returns (outcome, session_status, headline, next_step).
        """
        # Strict independence check: any support invalidates transfer
        if assistance_level != "INDEPENDENT":
            return (
                TransferOutcome.ABORTED,
                TransferSessionStatus.ABORTED,
                "Support requested during check.",
                "Let's review this concept together before trying independently."
            )

        if is_correct:
            return (
                TransferOutcome.PASSED,
                TransferSessionStatus.PASSED,
                "You solved this independently.",
                "This concept is now verified. Continue to the next challenge."
            )
        else:
            return (
                TransferOutcome.NEEDS_MORE_EVIDENCE,
                TransferSessionStatus.NEEDS_MORE_EVIDENCE,
                "This concept still needs a little more practice.",
                "Review the method with the Socratic Tutor or practice a targeted question."
            )

    def format_badge_text(self, grade_band: str) -> str:
        """
        Age-appropriate badge phrasing (§33, §34).
        Class 3-5 gets simple encouraging text; older students get professional phrasing.
        """
        g_lower = grade_band.lower()
        if "primary" in g_lower or any(c in g_lower for c in ["3", "4", "5"]):
            return "Try this one by yourself"
        return "Independent Check — AI Assistance Disabled"


DEFAULT_TRANSFER_POLICY_V1 = TransferPolicy()

_POLICY_REGISTRY: Dict[str, TransferPolicy] = {
    "1.0.0": DEFAULT_TRANSFER_POLICY_V1
}


def get_transfer_policy(version: Optional[str] = None) -> TransferPolicy:
    """Retrieves versioned policy instance."""
    if not version:
        return DEFAULT_TRANSFER_POLICY_V1
    return _POLICY_REGISTRY.get(version, DEFAULT_TRANSFER_POLICY_V1)
