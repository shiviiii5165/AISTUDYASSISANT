"""
LearnByGenie — Feature 3: Mastery Transition Engine
===================================================
Deterministic state transition rules (§5, §9, §11, §12).
Evaluates persistent learner skill state from the immutable evidence ledger.

Educational Mastery States:
- NOT_ASSESSED: No meaningful evidence
- DEVELOPING: Some evidence of understanding, insufficient consistency
- NEEDS_REPAIR: Repeated evidence shows conceptual/prerequisite failure
- FRAGILE: Previously secure but recent contradictory failure evidence
- SECURE: Consistent evidence supports independent understanding (>=2 independent items, >=80% accuracy)

Invariants:
- Never labels student intelligence, ability, or rank
- Labels concepts only
- No one-item SECURE
- No one-item NEEDS_REPAIR where evidence is insufficient
- Assisted evidence cannot alone promote to SECURE
- Time does NOT downgrade SECURE to NEEDS_REPAIR (review_status tracks freshness)
- Deterministic, explainable, testable
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

from .schemas import (
    MasteryState, ReviewStatus, ConfidenceClass,
    AssistanceLevel, LearnerSkillEvidence, LearnerSkillState
)


class MasteryTransitionEngine:
    """
    Deterministic rule engine that derives LearnerSkillState from a sequence of LearnerSkillEvidence.
    """

    @staticmethod
    def evaluate_state(
        current_state: Optional[LearnerSkillState],
        evidence_list: List[LearnerSkillEvidence],
        now: Optional[datetime] = None
    ) -> Tuple[MasteryState, ConfidenceClass, ReviewStatus, str, str]:
        """
        Computes (mastery_state, confidence_class, review_status, why, next_action)
        based on immutable evidence records.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        if not evidence_list:
            return (
                MasteryState.NOT_ASSESSED,
                ConfidenceClass.LOW_EVIDENCE,
                ReviewStatus.FRESH,
                "No diagnostic or practice evidence recorded yet.",
                "Complete a diagnostic assessment or concept check to gauge understanding."
            )

        # Sort evidence chronologically
        sorted_ev = sorted(evidence_list, key=lambda e: e.occurred_at or now)

        total_count = len(sorted_ev)
        independent_ev = [e for e in sorted_ev if e.independence_level == AssistanceLevel.INDEPENDENT]
        assisted_ev = [e for e in sorted_ev if e.independence_level != AssistanceLevel.INDEPENDENT]

        indep_count = len(independent_ev)
        indep_correct = sum(1 for e in independent_ev if e.correctness)
        indep_incorrect = indep_count - indep_correct

        all_correct = sum(1 for e in sorted_ev if e.correctness)
        all_incorrect = total_count - all_correct

        latest_ev = sorted_ev[-1]
        previous_mastery = current_state.mastery_state if current_state else MasteryState.NOT_ASSESSED

        # ─── CONFIDENCE CLASS ─────────────────────────────────────────────────
        if indep_count >= 3 or total_count >= 5:
            confidence = ConfidenceClass.HIGH_EVIDENCE
        elif indep_count >= 2 or total_count >= 3:
            confidence = ConfidenceClass.MODERATE_EVIDENCE
        else:
            confidence = ConfidenceClass.LOW_EVIDENCE

        # ─── MASTERY TRANSITION RULES ─────────────────────────────────────────

        # Rule 1: Previous SECURE with recent contradictory failure -> FRAGILE (§5, §11)
        if previous_mastery == MasteryState.SECURE:
            if not latest_ev.correctness and latest_ev.independence_level == AssistanceLevel.INDEPENDENT:
                why = (
                    f"Previously verified secure, but recent independent attempt was incorrect. "
                    f"Retention or edge-case transfer is fragile."
                )
                next_action = "Review core concept and complete a quick verification check."
                return (
                    MasteryState.FRAGILE,
                    confidence,
                    MasteryTransitionEngine._calc_review_status(latest_ev.occurred_at, now),
                    why,
                    next_action
                )

        # Rule 2: Single item evidence cannot leap to SECURE or drop to NEEDS_REPAIR (§41)
        if total_count == 1:
            ev = sorted_ev[0]
            if ev.correctness:
                # Single correct attempt -> DEVELOPING (never SECURE)
                why = (
                    f"1 initial correct attempt recorded ({ev.independence_level.value.lower()}). "
                    f"Requires consistent repeated independent demonstration to verify secure understanding."
                )
                next_action = "Complete another independent check to solidify this concept."
                return (
                    MasteryState.DEVELOPING,
                    ConfidenceClass.LOW_EVIDENCE,
                    MasteryTransitionEngine._calc_review_status(ev.occurred_at, now),
                    why,
                    next_action
                )
            else:
                # Single incorrect attempt -> DEVELOPING with caution (insufficient to declare NEEDS_REPAIR)
                why = (
                    f"1 incorrect attempt recorded. Single failure is insufficient to declare concept broken."
                )
                next_action = "Attempt another question or review explanations to verify comprehension."
                return (
                    MasteryState.DEVELOPING,
                    ConfidenceClass.LOW_EVIDENCE,
                    MasteryTransitionEngine._calc_review_status(ev.occurred_at, now),
                    why,
                    next_action
                )

        # Rule 3: Repeated failures -> NEEDS_REPAIR (§5)
        # At least 2 incorrect attempts, and incorrect >= correct
        if all_incorrect >= 2 and all_incorrect >= all_correct:
            why = (
                f"{all_incorrect} incorrect attempts out of {total_count} total evidence items. "
                f"Demonstrates consistent conceptual difficulty."
            )
            next_action = "Repair foundational prerequisites before attempting further questions on this concept."
            return (
                MasteryState.NEEDS_REPAIR,
                confidence,
                MasteryTransitionEngine._calc_review_status(latest_ev.occurred_at, now),
                why,
                next_action
            )

        # Rule 4: SECURE criteria (§5, §8, §41)
        # Requirements:
        # - At least 2 INDEPENDENT attempts (assisted attempts alone cannot satisfy SECURE)
        # - Independent success rate >= 80% (e.g. 2/2, 4/5)
        # - Most recent attempt was correct
        if indep_count >= 2 and (indep_correct / indep_count) >= 0.8 and latest_ev.correctness:
            why = (
                f"{indep_correct}/{indep_count} independent correct attempts ({int(indep_correct/indep_count*100)}% accuracy). "
                f"Consistent independent understanding confirmed."
            )
            next_action = "Concept is secure. Proceed to dependent topics or higher applications."
            return (
                MasteryState.SECURE,
                confidence,
                MasteryTransitionEngine._calc_review_status(latest_ev.occurred_at, now),
                why,
                next_action
            )

        # Rule 5: FRAGILE recovery or partial contradictory evidence
        if previous_mastery in (MasteryState.FRAGILE, MasteryState.SECURE) and not latest_ev.correctness:
            why = (
                f"Concept demonstrated prior strength but recent performance shows inconsistency ({all_correct}/{total_count} correct)."
            )
            next_action = "Reinforce core rules and test on mixed problem variations."
            return (
                MasteryState.FRAGILE,
                confidence,
                MasteryTransitionEngine._calc_review_status(latest_ev.occurred_at, now),
                why,
                next_action
            )

        # Rule 6: All other active cases -> DEVELOPING
        # (e.g. 1 independent + 2 assisted correct, or 2/3 correct, or resolving from needs_repair)
        why = (
            f"{all_correct}/{total_count} correct items recorded. "
            f"Understanding is developing but requires further independent verification."
        )
        next_action = "Continue guided practice and aim for independent correct solutions."
        return (
            MasteryState.DEVELOPING,
            confidence,
            MasteryTransitionEngine._calc_review_status(latest_ev.occurred_at, now),
            why,
            next_action
        )

    @staticmethod
    def _calc_review_status(last_evidence_at: Optional[datetime], now: datetime) -> ReviewStatus:
        """
        Knowledge freshness indicator (§12).
        Does NOT alter mastery state (never downgrades SECURE to NEEDS_REPAIR).
        """
        if not last_evidence_at:
            return ReviewStatus.FRESH

        # Normalize timezone
        if last_evidence_at.tzinfo is None:
            last_evidence_at = last_evidence_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        age_days = (now - last_evidence_at).days
        if age_days > 60:
            return ReviewStatus.REASSESSMENT_DUE
        elif age_days > 30:
            return ReviewStatus.REVIEW_SOON
        return ReviewStatus.FRESH
