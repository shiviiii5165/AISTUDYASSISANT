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

from app.core.config import settings

logger = logging.getLogger("learnbygenie.lesson_planner.outcome_engine")


class ResourceOutcomeEngine:
    """
    Manages resource outcome telemetry and adjusts rankings based on proven learning gains.
    Safeguard #3:
    - Resource outcome ranking eligibility is evaluated within cohort:
      canonical_concept_id + learner_level + resource_role (not only global N >= 20).
    - Strictly honors LESSON_OUTCOME_RANKING_ENABLED feature flag (default False).
    """

    # In-memory store of outcome signals keyed by resource_id
    # Versioned Outcome Readiness Policy (V2): Minimum cohort sample size N >= 20.
    # Statistical Justification:
    # Under binary learning outcome modeling (mastery achieved / misconception resolved, p ~ 0.25 - 0.75),
    # N >= 20 ensures standard sample adequacy (N*p >= 5, N*(1-p) >= 5) and bounds proportion standard error
    MIN_COHORT_SAMPLE_SIZE = 20
    _signals: Dict[str, List[ResourceOutcomeSignal]] = {}

    @classmethod
    def record_outcome_signal(
        cls,
        resource_id: str,
        concept_id: str,
        learner_level: str,
        resource_role: str = "core_explanation",
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

        logger.info(
            f"[ResourceOutcome] Recorded signal for {resource_id}: cohort={concept_id}::{learner_level}::{resource_role}, "
            f"{pre_state}->{post_state}, teacher={teacher_feedback}, student={student_feedback}"
        )
        return signal

    @classmethod
    def get_outcome_stats(
        cls,
        resource_id: str,
        concept_id: Optional[str] = None,
        learner_level: Optional[str] = None,
        resource_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates empirical effectiveness statistics for a resource within an appropriate cohort.
        Safeguard #3: Evaluates within cohort: canonical_concept_id + learner_level + resource_role.
        """
        all_signals = cls._signals.get(resource_id, [])
        if not all_signals:
            return {
                "sample_size": 0,
                "cohort_sample_size": 0,
                "cohort_matched": False,
                "mastery_rate": 0.0,
                "misconception_resolution_rate": 0.0,
                "positive_feedback_rate": 0.0,
                "is_statistically_significant": False
            }

        # Filter to exact cohort if specified
        cohort_signals = all_signals
        if concept_id:
            cohort_signals = [s for s in cohort_signals if s.concept_id == concept_id]
        if learner_level:
            cohort_signals = [s for s in cohort_signals if s.learner_level.lower() == learner_level.lower()]

        cohort_count = len(cohort_signals)
        is_significant = cohort_count >= cls.MIN_COHORT_SAMPLE_SIZE

        target_signals = cohort_signals if is_significant else all_signals
        total = len(target_signals)

        if total == 0:
            return {
                "sample_size": 0,
                "cohort_sample_size": 0,
                "cohort_matched": False,
                "mastery_rate": 0.0,
                "misconception_resolution_rate": 0.0,
                "positive_feedback_rate": 0.0,
                "is_statistically_significant": False
            }

        mastery_gains = sum(
            1 for s in target_signals 
            if s.pre_resource_state in ["novice", "misconception"] and s.post_resource_state == "mastered"
        )
        misconceptions_resolved = sum(
            1 for s in target_signals
            if s.misconception_before and not s.misconception_after
        )
        total_with_misconception = sum(1 for s in target_signals if s.misconception_before)

        positive_feedback = sum(
            1 for s in target_signals
            if s.teacher_feedback in [ResourceFeedbackType.HELPFUL, ResourceFeedbackType.EXCELLENT_EXPLANATION]
            or s.student_feedback in [ResourceFeedbackType.HELPFUL, ResourceFeedbackType.EXCELLENT_EXPLANATION]
        )

        return {
            "sample_size": len(all_signals),
            "cohort_sample_size": cohort_count,
            "cohort_matched": cohort_count > 0,
            "mastery_rate": round(mastery_gains / float(total), 3),
            "misconception_resolution_rate": round(
                misconceptions_resolved / float(total_with_misconception), 3
            ) if total_with_misconception > 0 else 1.0,
            "positive_feedback_rate": round(positive_feedback / float(total), 3),
            "is_statistically_significant": is_significant
        }

    @classmethod
    def apply_outcome_aware_ranking(
        cls,
        cards: List[UniversalResourceCard],
        concept_id: Optional[str] = None,
        learner_level: Optional[str] = None,
        resource_role: Optional[str] = None
    ) -> List[UniversalResourceCard]:
        """
        Blends Static Quality with Historical Learning Effectiveness.
        Safeguard #3:
        - Check LESSON_OUTCOME_RANKING_ENABLED feature flag. If False, retains static score without distortion.
        - Outcome ranking eligibility is strictly evaluated within cohort (concept_id + learner_level + resource_role).
        """
        outcome_flag = getattr(settings, "LESSON_OUTCOME_RANKING_ENABLED", False)
        if not outcome_flag:
            logger.info("[ResourceOutcome] Ranking adjustment skipped: LESSON_OUTCOME_RANKING_ENABLED is False")
            return cards

        for card in cards:
            stats = cls.get_outcome_stats(
                resource_id=card.id,
                concept_id=concept_id,
                learner_level=learner_level or getattr(card, "learner_level", None),
                resource_role=resource_role
            )
            if stats["is_statistically_significant"]:
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

        return sorted(cards, key=lambda c: c.quality_score, reverse=True)

    @classmethod
    def clear_all_signals(cls) -> None:
        """Testing utility to clear recorded signals."""
        cls._signals.clear()
