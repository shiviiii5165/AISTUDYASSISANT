"""Writes dual-ledger XP events idempotently and mirrors them to the existing XP balance."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.core.logging import logger
from app.modules import store
from app.modules.learning_core import xp_rules
from app.services.gamification.schemas import XPReasonCode
from app.services.gamification.service import GamificationService

_LEGACY_REASON = {
    "RULE_XP_01": XPReasonCode.BASELINE_DIAGNOSTIC,
    "RULE_XP_02": XPReasonCode.ERROR_RESOLUTION_UNSEEN,
    "RULE_XP_03": XPReasonCode.TIER_3_INDEPENDENT_PROFICIENCY,
    "RULE_XP_04": XPReasonCode.TIER_4_FRESH_TRANSFER,
    "RULE_XP_05": XPReasonCode.TIER_5_DELAYED_RETENTION,
    "RULE_XP_06": XPReasonCode.TEACH_BACK_RUBRIC_PASS,
    "RULE_XP_07": XPReasonCode.REPEATED_EASY_PRACTICE,
}
_KEY = ("student_id", "rule_id", "target_entity_id", "time_window_bucket")


def award(rule_id: str, student_id: str, target: str, **conditions) -> Optional[dict]:
    """Award a rule once per target and window; returns the new event, or None."""
    now = datetime.now(timezone.utc)
    if rule_id == "RULE_XP_01":
        previous = store.select("xp_events", student_id=student_id, rule_id=rule_id,
                                target_entity_id=target)
        if previous:
            latest = max(row["created_at"] for row in previous)
            conditions["last_award_at"] = store.parse_time(latest)
    if rule_id == "RULE_XP_07":
        today = (now - xp_rules._EPOCH).days
        conditions["easy_repeat_xp_today"] = sum(
            row["amount"] for row in store.select(
                "xp_events", student_id=student_id, rule_id=rule_id, time_window_bucket=today)
        )

    outcome = xp_rules.evaluate(rule_id, student_id, target, now, **conditions)
    if outcome is None:
        return None
    event, is_new = store.insert_unique("xp_events", {
        "student_id": student_id,
        "rule_id": rule_id,
        "target_entity_id": target,
        "time_window_bucket": outcome.time_window_bucket,
        "ledger": outcome.ledger.value,
        "amount": outcome.amount,
        "badge": outcome.badge,
        "created_at": now.isoformat(),
    }, _KEY)
    if not is_new:
        return None
    try:
        GamificationService.award_xp(
            user_id=student_id,
            amount=outcome.amount,
            reason_code=_LEGACY_REASON[rule_id],
            source_entity_type="xp_event",
            idempotency_key=f"v1:{student_id}:{rule_id}:{target}:{outcome.time_window_bucket}",
        )
    except Exception as exc:  # The ledger row above is the source of truth.
        logger.error(f"[XP] Mirror to legacy balance failed: {exc}")
    return event


def balances(student_id: str) -> dict[str, int]:
    totals = {"A": 0, "B": 0}
    for row in store.select("xp_events", student_id=student_id):
        totals[row["ledger"]] += row["amount"]
    return totals
