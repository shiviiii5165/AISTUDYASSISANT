"""
LearnByGenie — Feature 5: Mistake DNA Engine Service
=====================================================
Canonical intelligence layer for persistent learning error detection,
multi-task pattern aggregation, prerequisite correlation, and verifiable repair memory.

Guiding Principles:
- Describes learning errors, NOT student identity, weakness, or shame (§MISSION).
- Deterministic error detection first, UNKNOWN fallback without fabricating certainty (§6, §7).
- Occurrence counting distinguishes isolated slips from recurring/persistent patterns (§8, §10).
- Idempotent ingestion: duplicate sources produce zero extra counts (§11, §12).
- MasteryGraphService remains the sole authority for mastery states; Mistake DNA never
  directly mutates mastery (§14).
- Repair requires independent educational evidence; hints do not mark repaired (§16, §17).
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.core.logging import logger
from .schemas import (
    ErrorType, PatternStatus, RepairStatus, ConfidenceClass,
    AssistanceLevel, MistakeSourceType, MistakeCandidate,
    ClassificationResult, MistakeEvent, MistakePattern,
    RepairEvent, RepairRecommendation, CompactMistakeSummary,
    MistakePatternSummary, StepGraderMistakeCandidate
)
from .classifier import MistakeClassifier
from .repository import MistakeDNARepository
from app.services.diagnostic.curriculum_blueprint import get_skill


class MistakeDNAService:
    """
    Canonical Mistake DNA Service (§27).
    """

    # ─── 1. INGESTION & CLASSIFICATION ────────────────────────────────────────

    @classmethod
    def classify_mistake(cls, candidate: MistakeCandidate) -> ClassificationResult:
        """Classifies candidate error using deterministic rules + structured rubrics."""
        return MistakeClassifier.classify(candidate)

    @classmethod
    def ingest_error_candidate(
        cls, candidate: MistakeCandidate
    ) -> Tuple[MistakeEvent, MistakePattern, bool]:
        """
        Idempotently ingests an error candidate from Diagnostic, Tutor check, or Quiz (§4, §12).
        Returns (mistake_event, mistake_pattern, is_new).
        """
        # 1. Classification
        classification = cls.classify_mistake(candidate)

        # 2. Check Prerequisite Correlation via Mastery Knowledge Graph (§13)
        likely_prereq_id, prereq_signal = cls._correlate_prerequisite(
            candidate.user_id, candidate.skill_id
        )

        # 3. Generate Explainable Repair Action Recommendation (§15)
        repair_action = cls._generate_repair_action(
            classification.primary_error_type,
            candidate.skill_id,
            likely_prereq_id
        )

        # 4. Construct Durable Mistake Event
        event = MistakeEvent(
            user_id=candidate.user_id,
            skill_id=candidate.skill_id,
            subject=candidate.subject,
            source_type=candidate.source_type,
            source_record_id=candidate.source_record_id,
            question_reference=candidate.question_reference or (candidate.prompt_text or "")[:120],
            primary_error_type=classification.primary_error_type,
            secondary_error_types=classification.secondary_error_types,
            error_subtype=classification.error_subtype,
            error_summary=classification.error_summary,
            confidence_class=classification.confidence,
            assistance_level=candidate.assistance_level,
            repair_status=RepairStatus.OPEN,
            engine_version="5.0.0",
            classifier_version=classification.classifier_version,
            metadata={
                **candidate.metadata,
                "deterministic_rule": classification.deterministic_rule,
                "likely_prerequisite_skill": likely_prereq_id,
                "prerequisite_signal": prereq_signal
            }
        )

        # 5. Save Event Idempotently (§12)
        saved_event, is_new = MistakeDNARepository.save_mistake_event(event)

        # 6. Retrieve Pattern if Duplicate Submission (§4, §12)
        if not is_new:
            existing_pat = MistakeDNARepository.get_pattern(
                user_id=candidate.user_id,
                skill_id=candidate.skill_id,
                error_type=classification.primary_error_type,
                error_subtype=classification.error_subtype
            )
            if existing_pat:
                # Duplicate submission intercepted: return existing state without inflating count!
                return saved_event, existing_pat, False

        # 7. Atomic Database-Level Pattern Ingestion/Progression (§3, §8, §9, §10, §31)
        saved_pat = MistakeDNARepository.record_mistake_occurrence_atomic(
            user_id=candidate.user_id,
            skill_id=candidate.skill_id,
            subject=candidate.subject,
            error_type=classification.primary_error_type,
            error_subtype=classification.error_subtype,
            source_record_id=candidate.source_record_id,
            confidence=classification.confidence,
            repair_action=repair_action,
            likely_prereq_id=likely_prereq_id,
            prereq_signal=prereq_signal,
        )
        return saved_event, saved_pat, True

    # ─── 2. REPAIR EVIDENCE LIFECYCLE ─────────────────────────────────────────

    @classmethod
    def mark_repair_evidence(
        cls,
        user_id: str,
        skill_id: str,
        evidence_source: MistakeSourceType,
        evidence_record_id: str,
        assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT,
        notes: str = ""
    ) -> List[RepairEvent]:
        """
        Records verifiable educational repair evidence (§16, §17).
        Only INDEPENDENT evidence can transition status to REPAIRED.
        Hint-assisted practice moves OPEN -> IN_REPAIR.
        """
        # Find all open patterns for this student and skill
        patterns = MistakeDNARepository.get_patterns_for_user(user_id=user_id, skill_id=skill_id)
        open_patterns = [
            p for p in patterns
            if p.repair_status in (RepairStatus.OPEN, RepairStatus.IN_REPAIR, RepairStatus.REASSESSMENT_NEEDED)
        ]

        if not open_patterns:
            return []

        recorded_repairs: List[RepairEvent] = []

        for p in open_patterns:
            if assistance_level == AssistanceLevel.INDEPENDENT:
                # Independent evidence achieves REPAIRED (§16, §17)
                p.repair_status = RepairStatus.REPAIRED
                p.pattern_status = PatternStatus.REPAIRED
                p.recent_occurrence_count = 0
                MistakeDNARepository.save_pattern(p)

                repair_ev = RepairEvent(
                    pattern_id=p.id,
                    user_id=user_id,
                    skill_id=skill_id,
                    repair_action=f"Independent validation check passed via {evidence_source.value}",
                    evidence_source=evidence_source,
                    evidence_record_id=evidence_record_id,
                    assistance_level=assistance_level,
                    notes=notes or "Independent educational mastery evidence recorded."
                )
                saved_rep, _ = MistakeDNARepository.save_repair_event(repair_ev)
                recorded_repairs.append(saved_rep)
            else:
                # Assisted evidence moves to IN_REPAIR but NOT REPAIRED (§17)
                if p.repair_status == RepairStatus.OPEN:
                    p.repair_status = RepairStatus.IN_REPAIR
                    MistakeDNARepository.save_pattern(p)

        return recorded_repairs

    # ─── 3. PREREQUISITE CORRELATION ──────────────────────────────────────────

    @classmethod
    def _correlate_prerequisite(
        cls, user_id: str, skill_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Queries MasteryGraphService without fabricating causal certainty (§13, §14).
        Uses language: 'Related prerequisite signal', NOT 'This is definitely why'.
        """
        try:
            from app.services.mastery.service import MasteryGraphService
            from app.services.mastery.repository import MasteryRepository
            from app.services.mastery.schemas import MasteryState

            dag = MasteryGraphService.get_dag_engine()
            direct_prereqs = dag.get_immediate_prerequisites(skill_id)

            for prereq_id in direct_prereqs:
                st = MasteryRepository.get_skill_state(user_id, prereq_id)
                if st and st.mastery_state in (MasteryState.NEEDS_REPAIR, MasteryState.FRAGILE):
                    prereq_obj = get_skill(prereq_id)
                    p_name = prereq_obj.skill_name if prereq_obj else prereq_id
                    signal = (
                        f"Related prerequisite signal: {p_name} currently needs repair, "
                        f"which may influence performance on this topic."
                    )
                    return prereq_id, signal
        except Exception as e:
            logger.debug(f"[MistakeDNA] Prerequisite correlation note: {e}")

        return None, None

    # ─── 4. REPAIR ACTION RECOMMENDATIONS ─────────────────────────────────────

    @classmethod
    def _generate_repair_action(
        cls, error_type: ErrorType, skill_id: str, prerequisite_id: Optional[str] = None
    ) -> str:
        """Generates explainable, constructive repair recommendation (§15)."""
        if prerequisite_id:
            prereq_obj = get_skill(prerequisite_id)
            p_name = prereq_obj.skill_name if prereq_obj else prerequisite_id
            return f"Review foundational prerequisite '{p_name}' first with your Socratic Tutor."

        repair_map = {
            ErrorType.CONCEPTUAL: "Review the core definition and underlying mechanism with Tutor.",
            ErrorType.PROCEDURAL: "Retry the problem step-by-step with structured guidance.",
            ErrorType.CALCULATION: "Recheck arithmetic calculations and intermediate steps.",
            ErrorType.SIGN_OR_NOTATION: "Practice algebraic transposition and verify negative sign changes.",
            ErrorType.FORMULA_RECALL: "Recheck the formula definition, terms, and constant factors.",
            ErrorType.MISREAD_QUESTION: "Highlight the required target and given constraints before solving.",
            ErrorType.UNIT_OR_DIMENSION: "Practice unit conversion and verify dimensional consistency.",
            ErrorType.REASONING: "Trace logical assumptions before concluding.",
            ErrorType.MEMORY_RECALL: "Review key terminology and essential definitions.",
            ErrorType.INCOMPLETE_RESPONSE: "Complete the full solution step-by-step without skipping work.",
            ErrorType.UNKNOWN: "Walk through this question with the Socratic Tutor."
        }
        return repair_map.get(error_type, "Review this step with the Tutor.")

    @classmethod
    def get_repair_recommendation(cls, pattern: MistakePattern) -> RepairRecommendation:
        """Constructs detailed explainable repair recommendation (§15, §37)."""
        sk_obj = get_skill(pattern.skill_id)
        sk_name = sk_obj.skill_name if sk_obj else pattern.skill_id

        why_text = (
            f"Marked as {pattern.pattern_status.value} because this {pattern.error_type.value.lower().replace('_', ' ')} "
            f"occurred {pattern.occurrence_count} time{'s' if pattern.occurrence_count != 1 else ''}. "
            f"Latest occurrence was recorded on {pattern.last_seen_at.strftime('%b %d')}."
        )

        return RepairRecommendation(
            action_type=pattern.error_type.value,
            skill_id=pattern.skill_id,
            skill_name=sk_name,
            recommended_repair_action=pattern.recommended_repair_action or cls._generate_repair_action(pattern.error_type, pattern.skill_id),
            likely_prerequisite_skill=pattern.likely_prerequisite_skill,
            prerequisite_signal=pattern.prerequisite_signal,
            explanation=why_text,
            pedagogical_mode="TUTOR"
        )

    # ─── 5. READ CONTRACTS ────────────────────────────────────────────────────

    @classmethod
    def get_recent_mistakes(cls, user_id: str, limit: int = 50) -> List[MistakeEvent]:
        return MistakeDNARepository.get_mistake_events(user_id, limit)

    @classmethod
    def get_patterns(
        cls, user_id: str, subject: Optional[str] = None
    ) -> List[MistakePattern]:
        return MistakeDNARepository.get_patterns_for_user(user_id=user_id, subject=subject)

    @classmethod
    def get_skill_patterns(cls, user_id: str, skill_id: str) -> List[MistakePattern]:
        return MistakeDNARepository.get_patterns_for_user(user_id=user_id, skill_id=skill_id)

    @classmethod
    def get_open_repairs(cls, user_id: str) -> List[RepairRecommendation]:
        patterns = MistakeDNARepository.get_patterns_for_user(user_id)
        open_pats = [p for p in patterns if p.repair_status in (RepairStatus.OPEN, RepairStatus.IN_REPAIR, RepairStatus.REASSESSMENT_NEEDED)]
        return [cls.get_repair_recommendation(p) for p in open_pats]

    # ─── 6. BOUNDED LEARNER CONTEXT INTEGRATION (§28) ─────────────────────────

    @classmethod
    def get_compact_mistake_summary(
        cls, user_id: str, subject: Optional[str] = None
    ) -> CompactMistakeSummary:
        """
        Constructs bounded summary for LearnerContextService (§28).
        Exposes top recurring and isolated patterns without dumping raw logs.
        """
        all_patterns = MistakeDNARepository.get_patterns_for_user(user_id=user_id, subject=subject)
        recurring = [p for p in all_patterns if p.pattern_status in (PatternStatus.RECURRING, PatternStatus.PERSISTENT)]
        isolated = [p for p in all_patterns if p.pattern_status == PatternStatus.ISOLATED]

        rec_summaries = [
            MistakePatternSummary(
                error_type=p.error_type,
                error_subtype=p.error_subtype,
                status=p.pattern_status,
                occurrence_count=p.occurrence_count,
                skill_id=p.skill_id,
                last_seen_at=p.last_seen_at
            ) for p in recurring[:5]
        ]

        iso_summaries = [
            MistakePatternSummary(
                error_type=p.error_type,
                error_subtype=p.error_subtype,
                status=p.pattern_status,
                occurrence_count=p.occurrence_count,
                skill_id=p.skill_id,
                last_seen_at=p.last_seen_at
            ) for p in isolated[:3]
        ]

        top_types = list(dict.fromkeys([p.error_type.value for p in (recurring + isolated)]))[:4]

        return CompactMistakeSummary(
            total_patterns=len(all_patterns),
            recurring_patterns=rec_summaries,
            isolated_patterns=iso_summaries,
            top_error_types=top_types
        )

    # ─── 7. FUTURE MODULE CONTRACTS (§24, §25, §26) ───────────────────────────

    @classmethod
    def get_open_patterns_for_practice(
        cls, user_id: str, subject: Optional[str] = None
    ) -> List[MistakePattern]:
        """Stable read contract for Future Adaptive Practice (§25)."""
        all_pats = MistakeDNARepository.get_patterns_for_user(user_id, subject=subject)
        return [p for p in all_pats if p.repair_status in (RepairStatus.OPEN, RepairStatus.IN_REPAIR, RepairStatus.REASSESSMENT_NEEDED)]

    @classmethod
    def get_patterns_for_revision(
        cls, user_id: str, subject: Optional[str] = None
    ) -> List[MistakePattern]:
        """Stable read contract for Future Spaced Revision (§26)."""
        all_pats = MistakeDNARepository.get_patterns_for_user(user_id, subject=subject)
        return [p for p in all_pats if p.occurrence_count >= 2]

    @classmethod
    def ingest_step_grader_error(
        cls, candidate: StepGraderMistakeCandidate
    ) -> Tuple[MistakeEvent, MistakePattern, bool]:
        """Stable ingestion contract for Future Step-Grader (§24)."""
        mistake_cand = MistakeCandidate(
            user_id=candidate.user_id,
            skill_id=candidate.skill_id,
            source_type=MistakeSourceType.STEP_GRADER,
            source_record_id=candidate.source_record_id,
            question_reference=f"Step {candidate.step_index}: {candidate.first_wrong_step}",
            student_response=candidate.first_wrong_step,
            assistance_level=AssistanceLevel.INDEPENDENT,
            metadata={"step_index": candidate.step_index, "subskill": candidate.subskill, "visual_ref": candidate.visual_ref}
        )
        return cls.ingest_error_candidate(mistake_cand)
