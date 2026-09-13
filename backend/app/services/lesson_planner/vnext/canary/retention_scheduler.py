"""
TeachGenie Canary Infrastructure — Idempotent Delayed Retention Scheduler
========================================================================
Safeguard #4:
- Ensures delayed retention scheduling is strictly idempotent.
- Prevents duplicate pending 24h/72h/168h checks for the same learner,
  concept, misconception, and lifecycle episode.
- Respects completed, expired, and cancelled states.
"""

import uuid
import logging
from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("teachgenie.canary.retention")


class RetentionCheckStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DelayedRetentionCheck(BaseModel):
    """
    Structured model for a longitudinal retention verification event.
    """
    check_id: str = Field(default_factory=lambda: f"ret_{uuid.uuid4().hex[:12]}")
    idempotency_key: str
    learner_pseudonym_id: str
    canonical_concept_id: str
    misconception_id: str
    lifecycle_episode_id: str
    window: str  # "24h", "72h", "168h"
    scheduled_for: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: RetentionCheckStatus = RetentionCheckStatus.PENDING
    completed_at: Optional[datetime] = None
    retention_score: Optional[float] = None
    misconception_reappeared: Optional[bool] = None
    notes: Optional[str] = None


class IdempotentRetentionScheduler:
    """
    Manages longitudinal retention probes across spaced repetition intervals
    with complete idempotency guarantees.
    """
    # Keyed by idempotency_key
    _checks: Dict[str, DelayedRetentionCheck] = {}
    _deduplication_count: int = 0

    @classmethod
    def compute_idempotency_key(
        cls,
        learner_pseudonym_id: str,
        canonical_concept_id: str,
        misconception_id: str,
        lifecycle_episode_id: str,
        window: str
    ) -> str:
        """
        Deterministic idempotency signature binding learner, concept, misconception,
        lifecycle episode, and evaluation window.
        """
        return (
            f"{learner_pseudonym_id.strip()}::"
            f"{canonical_concept_id.strip()}::"
            f"{misconception_id.strip()}::"
            f"{lifecycle_episode_id.strip()}::"
            f"{window.strip().lower()}"
        )

    @classmethod
    def schedule_retention_check(
        cls,
        learner_pseudonym_id: str,
        canonical_concept_id: str,
        misconception_id: str,
        lifecycle_episode_id: str,
        window: str = "24h"
    ) -> Tuple[DelayedRetentionCheck, bool]:
        """
        Idempotently schedules a delayed retention probe.
        Returns (check_record, was_created: bool).
        If a probe for this episode and window already exists (in any state: PENDING,
        COMPLETED, CANCELLED, or EXPIRED), returns the existing record and was_created=False.
        """
        key = cls.compute_idempotency_key(
            learner_pseudonym_id=learner_pseudonym_id,
            canonical_concept_id=canonical_concept_id,
            misconception_id=misconception_id,
            lifecycle_episode_id=lifecycle_episode_id,
            window=window
        )

        if key in cls._checks:
            existing = cls._checks[key]
            cls._deduplication_count += 1
            logger.info(
                f"[RetentionScheduler] Idempotent hit: check already exists for {key} "
                f"with status '{existing.status.value}'. Deduplicating request."
            )
            return existing, False

        # Calculate scheduled target time based on window
        delay_map = {
            "24h": timedelta(hours=24),
            "72h": timedelta(hours=72),
            "168h": timedelta(hours=168)
        }
        delta = delay_map.get(window.lower(), timedelta(hours=24))
        scheduled_for = datetime.now(timezone.utc) + delta

        new_check = DelayedRetentionCheck(
            idempotency_key=key,
            learner_pseudonym_id=learner_pseudonym_id,
            canonical_concept_id=canonical_concept_id,
            misconception_id=misconception_id,
            lifecycle_episode_id=lifecycle_episode_id,
            window=window,
            scheduled_for=scheduled_for,
            status=RetentionCheckStatus.PENDING
        )
        cls._checks[key] = new_check
        logger.info(f"[RetentionScheduler] Successfully scheduled {window} check {new_check.check_id} for {key}")
        return new_check, True

    @classmethod
    def record_check_result(
        cls,
        idempotency_key: str,
        retention_score: float,
        misconception_reappeared: bool
    ) -> Optional[DelayedRetentionCheck]:
        """Records outcome for a completed check."""
        check = cls._checks.get(idempotency_key)
        if check and check.status == RetentionCheckStatus.PENDING:
            check.status = RetentionCheckStatus.COMPLETED
            check.completed_at = datetime.now(timezone.utc)
            check.retention_score = round(retention_score, 3)
            check.misconception_reappeared = misconception_reappeared
            return check
        return None

    @classmethod
    def cancel_check(cls, idempotency_key: str, reason: str = "Class lesson reschedule") -> bool:
        """Cancels an existing pending check."""
        check = cls._checks.get(idempotency_key)
        if check and check.status == RetentionCheckStatus.PENDING:
            check.status = RetentionCheckStatus.CANCELLED
            check.notes = f"Cancelled: {reason}"
            return True
        return False

    @classmethod
    def cancel_pending_checks_for_learner(
        cls,
        learner_pseudonym_id: str,
        reason: str = "Participant revocation"
    ) -> int:
        """
        Cancels all pending delayed retention checks for a participant upon consent revocation.
        Fulfills data lifecycle requirement: cancellation of pending delayed-retention checks.
        """
        cancelled_count = 0
        for check in cls._checks.values():
            if check.learner_pseudonym_id == learner_pseudonym_id and check.status == RetentionCheckStatus.PENDING:
                check.status = RetentionCheckStatus.CANCELLED
                check.notes = f"Cancelled: {reason}"
                cancelled_count += 1
        logger.info(f"[RetentionScheduler] Cancelled {cancelled_count} pending checks for learner {learner_pseudonym_id[:12]} ({reason})")
        return cancelled_count

    @classmethod
    def expire_overdue_checks(cls, grace_hours: int = 48) -> int:
        """Marks pending checks past scheduled_for + grace_hours as EXPIRED."""
        now = datetime.now(timezone.utc)
        expired_count = 0
        for check in cls._checks.values():
            if check.status == RetentionCheckStatus.PENDING:
                if now > (check.scheduled_for + timedelta(hours=grace_hours)):
                    check.status = RetentionCheckStatus.EXPIRED
                    check.notes = "Expired: student did not engage within observation window"
                    expired_count += 1
        return expired_count

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Telemetry statistics for canary reporting."""
        by_status = {s.value: 0 for s in RetentionCheckStatus}
        for c in cls._checks.values():
            by_status[c.status.value] += 1
        return {
            "total_checks": len(cls._checks),
            "deduplications_blocked": cls._deduplication_count,
            "status_breakdown": by_status
        }

    @classmethod
    def clear_all(cls) -> None:
        """Testing utility."""
        cls._checks.clear()
        cls._deduplication_count = 0
