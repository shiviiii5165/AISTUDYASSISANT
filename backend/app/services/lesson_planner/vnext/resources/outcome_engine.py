"""
Resource Outcome Learning & Adaptive Ranking Engine
===================================================
Implements Sections 25–27:
- Long-term competitive moat: captures empirical learning effectiveness
  (pre/post mastery, misconception resolution, time spent, teacher/student feedback).
- Controlled outcome-aware ranking formula:
  Blends static pedagogical score with empirical outcome effectiveness
  ONLY after sufficient sample size (N >= 10) to avoid early overfitting.
- Weak-signal feedback logging (Helpful, Too Easy, Outdated, Broken Link, etc.).
"""

import uuid
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from .contracts import ResourceOutcomeSignal, ResourceFeedbackType
from ...schemas import UniversalResourceCard

logger = logging.getLogger("teachgenie.lesson_planner.outcome_engine")


class ResourceOutcomeEngine:
    """
    Manages resource outcome telemetry and adjusts rankings based on proven learning gains.
    """

    # In-memory store of outcome signals keyed by resource_id
    _signals: Dict[str, List[ResourceOutcomeSignal]] = {}

    MIN_SAMPLE_SIZE_FOR_RANKING = 10  # Section 25: Do not overfit rankings until sample size is met

    @classmethod
    def record_outcome_signal(
        cls,
        resource_id: str,
        concept_id: str,
        learner_level: str,
        pre_state: str = "novice",
        post_state: str = "mastered",
        misconception_before: Optional[str] = None,
        misconception_after: Optional[str] = None,
        time_spent_seconds: int = 0,
        teacher_feedback: Optional[ResourceFeedbackType] = None,
        student_feedback: Optional[ResourceFeedbackType] = None
    ) -> ResourceOutcomeSignal:
        """
        Records learning outcome telemetry after a student engages with a resource.
        """
        signal = ResourceOutcomeSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:12]}",
            resource_id=resource_id,
            concept_id=concept_id,
            learner_level=learner_level,
            pre_resource_state=pre_state,
            post_resource_state=post_state,
            misconception_before=misconception_before,
            misconception_after=misconception_after,
            time_spent_seconds=time_spent_seconds,
            teacher_feedback=teacher_feedback,
            student_feedback=student_feedback,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        if resource_id not in cls._signals:
            cls._signals[resource_id] = []
        cls._signals[resource_id].append(signal)

        # Log for longitudinal analytics
        logger.info(
            f"[ResourceOutcome] Recorded signal for {resource_id}: "
            f"{pre_state}->{post_state}, teacher={teacher_feedback}, student={student_feedback}"
        )
        return signal

    @classmethod
    def get_outcome_stats(cls, resource_id: str) -> Dict[str, Any]:
        """
        Calculates empirical effectiveness statistics for a resource.
        """
        signals = cls._signals.get(resource_id, [])
        total = len(signals)
        if total == 0:
            return {
                "sample_size": 0,
                "mastery_rate": 0.0,
                "misconception_resolution_rate": 0.0,
                "positive_feedback_rate": 0.0,
                "is_statistically_significant": False
            }

        mastery_gains = sum(
            1 for s in signals 
            if s.pre_resource_state in ["novice", "misconception"] and s.post_resource_state == "mastered"
        )
        misconceptions_resolved = sum(
            1 for s in signals
            if s.misconception_before and not s.misconception_after
        )
        total_with_misconception = sum(1 for s in signals if s.misconception_before)

        positive_feedback = sum(
            1 for s in signals
            if s.teacher_feedback in [ResourceFeedbackType.HELPFUL, ResourceFeedbackType.EXCELLENT_EXPLANATION]
            or s.student_feedback in [ResourceFeedbackType.HELPFUL, ResourceFeedbackType.EXCELLENT_EXPLANATION]
        )

        return {
            "sample_size": total,
            "mastery_rate": round(mastery_gains / float(total), 3),
            "misconception_resolution_rate": round(
                misconceptions_resolved / float(total_with_misconception), 3
            ) if total_with_misconception > 0 else 1.0,
            "positive_feedback_rate": round(positive_feedback / float(total), 3),
            "is_statistically_significant": total >= cls.MIN_SAMPLE_SIZE_FOR_RANKING
        }

    @classmethod
    def apply_outcome_aware_ranking(
        cls,
        cards: List[UniversalResourceCard]
    ) -> List[UniversalResourceCard]:
        """
        Section 26: Blends Static Quality with Historical Learning Effectiveness.
        Score = 0.80 * StaticScore + 0.20 * OutcomeScore (if sample size >= 10).
        If sample size < 10, retains static score without distortion.
        """
        for card in cards:
            stats = cls.get_outcome_stats(card.id)
            if stats["is_statistically_significant"]:
                # Outcome score normalized to 0-100
                outcome_score = int(round(
                    (stats["mastery_rate"] * 50.0) +
                    (stats["misconception_resolution_rate"] * 30.0) +
                    (stats["positive_feedback_rate"] * 20.0)
                ))
                card.outcome_effectiveness = outcome_score
                card.score_breakdown.outcome_effectiveness = outcome_score

                # Blended ranking
                static_score = card.quality_score
                blended = int(round((static_score * 0.80) + (outcome_score * 0.20)))
                card.quality_score = min(100, blended)

        # Re-sort cards
        return sorted(cards, key=lambda c: c.quality_score, reverse=True)

    @classmethod
    def clear_all_signals(cls) -> None:
        """Testing utility to clear recorded signals."""
        cls._signals.clear()
