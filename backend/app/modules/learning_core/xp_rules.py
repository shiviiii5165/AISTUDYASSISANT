"""Dual-ledger XP rules.

Rule evaluation is pure. The database enforces
UNIQUE(student_id, rule_id, target_entity_id, time_window_bucket) on the result.
Fixed 30-day buckets alone would allow two RULE_XP_01 awards a few days apart across
a bucket boundary, so last_award_at is also checked for that rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

EASY_REPEAT_DAILY_CAP = 10
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class Ledger(str, Enum):
    ENGAGEMENT = "A"
    MASTERY = "B"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    ledger: Ledger
    amount: int
    badge: Optional[str]
    window_days: Optional[int]  # None means once ever per target.


RULES = {
    rule.rule_id: rule
    for rule in (
        Rule("RULE_XP_01", Ledger.ENGAGEMENT, 50, "Pathfinder", 30),
        Rule("RULE_XP_02", Ledger.ENGAGEMENT, 30, "Mistake Detective", None),
        Rule("RULE_XP_03", Ledger.MASTERY, 40, "Concept Builder", None),
        Rule("RULE_XP_04", Ledger.MASTERY, 60, "Transfer Strategist", None),
        Rule("RULE_XP_05", Ledger.MASTERY, 45, "Retention Champion", None),
        Rule("RULE_XP_06", Ledger.ENGAGEMENT, 25, None, None),
        Rule("RULE_XP_07", Ledger.ENGAGEMENT, 2, None, 1),
    )
}


@dataclass(frozen=True)
class Award:
    student_id: str
    rule_id: str
    target_entity_id: str
    time_window_bucket: int
    ledger: Ledger
    amount: int
    badge: Optional[str]


def evaluate(
    rule_id: str,
    student_id: str,
    target_entity_id: str,
    now: datetime,
    *,
    last_award_at: Optional[datetime] = None,
    item_unseen: bool = False,
    teach_back_score: Optional[int] = None,
    easy_repeat_xp_today: int = 0,
) -> Optional[Award]:
    """Return the award this event earns, or None when the rule's conditions fail."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    rule = RULES[rule_id]
    amount = rule.amount

    if rule_id == "RULE_XP_01" and last_award_at is not None:
        if now - last_award_at < timedelta(days=30):
            return None
    if rule_id == "RULE_XP_02" and not item_unseen:
        return None
    if rule_id == "RULE_XP_06" and (teach_back_score is None or teach_back_score < 2):
        return None
    if rule_id == "RULE_XP_07":
        amount = max(0, min(amount, EASY_REPEAT_DAILY_CAP - easy_repeat_xp_today))

    bucket = (now - _EPOCH).days // rule.window_days if rule.window_days else 0
    return Award(
        student_id, rule_id, target_entity_id, bucket, rule.ledger, amount, rule.badge
    )
