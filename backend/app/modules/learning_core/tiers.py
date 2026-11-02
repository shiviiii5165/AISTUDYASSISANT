"""Stage 6: the six-state mastery evidence hierarchy (Tiers 0-5).

Rules the blueprint leaves open, decided here:
- The 3 unhinted passes for Tier 3 must be consecutive; a wrong answer resets them.
- The review ladder has Day 8 rather than Day 7, so "Day-7" means a pass at least
  7 days after the Tier 4 transfer, and "Day-21" at least 21 days after it.
- A failed retention check restarts the clock, and Tier 5 falls back to Tier 4.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Optional


class Evidence(str, Enum):
    INTERVENTION_COMPLETED = "intervention_completed"
    PRACTICE_PASS = "practice_pass"
    PRACTICE_FAIL = "practice_fail"
    TRANSFER_PASS = "transfer_pass"
    RETENTION_PASS = "retention_pass"
    RETENTION_FAIL = "retention_fail"


@dataclass(frozen=True)
class MasteryState:
    tier: int = 0
    unhinted_streak: int = 0
    retention_clock_start: Optional[datetime] = None
    day7_passed: bool = False

    @property
    def unlocks_children(self) -> bool:
        return self.tier >= 3


def advance(
    state: MasteryState,
    evidence: Evidence,
    occurred_at: datetime,
    hinted: bool = False,
    item_previously_seen: bool = False,
) -> MasteryState:
    if evidence is Evidence.INTERVENTION_COMPLETED:
        return replace(state, tier=max(state.tier, 1))

    if evidence is Evidence.PRACTICE_FAIL:
        return replace(state, unhinted_streak=0)

    if evidence is Evidence.PRACTICE_PASS:
        if hinted:
            return replace(state, tier=max(state.tier, 1), unhinted_streak=0)
        streak = state.unhinted_streak + 1
        tier = max(state.tier, 3 if streak >= 3 else 2)
        return replace(state, tier=tier, unhinted_streak=streak)

    if evidence is Evidence.TRANSFER_PASS:
        if state.tier != 3 or hinted or item_previously_seen:
            return state
        return replace(state, tier=4, retention_clock_start=occurred_at, day7_passed=False)

    if state.tier < 4 or state.retention_clock_start is None:
        return state

    if evidence is Evidence.RETENTION_FAIL:
        return replace(state, tier=4, retention_clock_start=occurred_at, day7_passed=False)

    elapsed_days = (occurred_at - state.retention_clock_start).total_seconds() / 86400
    if not state.day7_passed:
        return replace(state, day7_passed=True) if elapsed_days >= 7 else state
    return replace(state, tier=5) if elapsed_days >= 21 else state
