"""
LearnByGenie — Feature 3: Canonical Mastery Graph Service
=========================================================
Centralized service for (§22):
- Managing learner skill states and append-only evidence ledger
- Ingesting Feature 2 diagnostic results idempotently (§10, §26)
- Ingesting generic evidence (practice, quiz, tutor) (§6, §36)
- Calculating DAG readiness, blocked concepts, and repair paths (§13, §14)
- Generating explainable next concept recommendations (§15, §29)
- Providing bounded summary for LearnerContextService (§23)
- Topology auditing (§40)
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timezone
import uuid

from app.core.logging import logger
from .schemas import (
    MasteryState, ReadinessState, ReviewStatus, ConfidenceClass,
    EvidenceSource, AssistanceLevel, RelationshipType,
    SkillPrerequisiteEdge, LearnerSkillEvidence, LearnerSkillState,
    SkillNodeView, LearningRecommendation, SubjectGraphView,
    GraphAuditReport, CompactMasterySummary
)
from .dag_engine import PrerequisiteDAGEngine
from .transition_engine import MasteryTransitionEngine
from .repository import MasteryRepository
from .audit import GraphAuditor
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill, CANONICAL_DOMAINS
from app.services.diagnostic.schemas import Feature3SkillEvidence


class MasteryGraphService:
    """
    Canonical Mastery and Prerequisite Knowledge Graph engine.
    """

    @classmethod
    def get_dag_engine(cls) -> PrerequisiteDAGEngine:
        edges = MasteryRepository.get_prerequisite_edges()
        return PrerequisiteDAGEngine(edges)

    # ─── 1. SKILL STATE RETRIEVAL ─────────────────────────────────────────────

    @classmethod
    def get_skill_state(cls, user_id: str, skill_id: str) -> Optional[LearnerSkillState]:
        return MasteryRepository.get_skill_state(user_id, skill_id)

    # ─── 2. EVIDENCE INGESTION (FEATURE 2 & GENERAL) ──────────────────────────

    @classmethod
    def ingest_diagnostic_evidence(
        cls,
        user_id: str,
        session_id: str,
        contract_payload: List[Feature3SkillEvidence]
    ) -> List[LearnerSkillState]:
        """
        Ingests Feature 2 diagnostic evidence contract idempotently (§10, §26).
        Reprocessing the same session produces zero duplicate entries.
        """
        updated_states: List[LearnerSkillState] = []

        for item in contract_payload:
            sk_obj = get_skill(item.skill_id)
            if not sk_obj:
                logger.warning(f"[MasteryService] Unknown skill in diagnostic payload: {item.skill_id}")
                continue

            # Deterministic discrete evidence items based on evidence_count & correct_count
            ev_count = max(1, item.evidence_count)
            corr_count = min(ev_count, max(0, item.correct_count))

            any_new_in_batch = False
            has_new = False
            for i in range(ev_count):
                is_correct = (i < corr_count)
                evidence = LearnerSkillEvidence(
                    user_id=user_id,
                    skill_id=item.skill_id,
                    source_type=EvidenceSource.DIAGNOSTIC,
                    source_record_id=f"{session_id}_item_{i+1}",
                    correctness=is_correct,
                    evidence_strength=1.0,
                    independence_level=AssistanceLevel.INDEPENDENT,
                    confidence_class=ConfidenceClass(item.confidence) if item.confidence in ConfidenceClass.__members__ else ConfidenceClass.MODERATE_EVIDENCE,
                    occurred_at=datetime.fromisoformat(item.timestamp) if item.timestamp else datetime.now(timezone.utc),
                    engine_version="3.0.0",
                    metadata={
                        "diagnostic_session_id": session_id,
                        "diagnostic_state": item.diagnostic_state,
                        "recommended_action": item.recommended_action
                    }
                )
                _, is_new = MasteryRepository.record_evidence(evidence)
                if is_new:
                    has_new = True
                    any_new_in_batch = True

            # Recalculate persistent skill state only if new evidence was added
            existing_st = MasteryRepository.get_skill_state(user_id, item.skill_id)
            if has_new or existing_st is None:
                state = cls.recalculate_skill_state(user_id, item.skill_id, sk_obj.subject)
            else:
                state = existing_st
            updated_states.append(state)

        # After updating skills, recompute readiness for subject skills if any new evidence was recorded
        if contract_payload and updated_states and any_new_in_batch:
            subj = updated_states[0].subject
            cls._recalculate_subject_readiness(user_id, subj)

        return updated_states

    @classmethod
    def ingest_evidence(
        cls,
        user_id: str,
        skill_id: str,
        source_type: EvidenceSource,
        source_record_id: str,
        correctness: bool,
        independence_level: AssistanceLevel = AssistanceLevel.INDEPENDENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[LearnerSkillState, bool]:
        """
        General evidence ingestion interface for future Practice, Quiz, Tutor Check (§6, §36).
        Returns (updated_state, is_new_evidence).
        """
        sk_obj = get_skill(skill_id)
        subject = sk_obj.subject if sk_obj else "Mathematics"

        evidence = LearnerSkillEvidence(
            user_id=user_id,
            skill_id=skill_id,
            source_type=source_type,
            source_record_id=source_record_id,
            correctness=correctness,
            evidence_strength=1.0 if independence_level == AssistanceLevel.INDEPENDENT else 0.6,
            independence_level=independence_level,
            confidence_class=ConfidenceClass.MODERATE_EVIDENCE,
            occurred_at=datetime.now(timezone.utc),
            engine_version="3.0.0",
            metadata=metadata or {}
        )

        _, is_new = MasteryRepository.record_evidence(evidence)
        existing_st = MasteryRepository.get_skill_state(user_id, skill_id)
        if is_new or existing_st is None:
            state = cls.recalculate_skill_state(user_id, skill_id, subject)
            cls._recalculate_subject_readiness(user_id, subject)
        else:
            state = existing_st
        return state, is_new

    # ─── 3. STATE RECALCULATION & CONCURRENCY VERSIONING ──────────────────────

    @classmethod
    def recalculate_skill_state(
        cls,
        user_id: str,
        skill_id: str,
        subject: str
    ) -> LearnerSkillState:
        """
        Derives state from the evidence ledger and increments state_version (§27, §28).
        """
        existing = MasteryRepository.get_skill_state(user_id, skill_id)
        evidence_list = MasteryRepository.get_evidence_for_skill(user_id, skill_id)

        now = datetime.now(timezone.utc)
        mastery_state, confidence, review_status, why, next_action = (
            MasteryTransitionEngine.evaluate_state(existing, evidence_list, now=now)
        )

        indep_ev = [e for e in evidence_list if e.independence_level == AssistanceLevel.INDEPENDENT]
        last_ev_at = max([e.occurred_at for e in evidence_list], default=None)
        last_indep_at = max([e.occurred_at for e in indep_ev], default=None)

        new_version = (existing.state_version + 1) if existing else 1

        state = LearnerSkillState(
            id=existing.id if existing else str(uuid.uuid4()),
            user_id=user_id,
            skill_id=skill_id,
            subject=subject,
            mastery_state=mastery_state,
            readiness_state=existing.readiness_state if existing else ReadinessState.NOT_ENOUGH_EVIDENCE,
            confidence_class=confidence,
            total_evidence_count=len(evidence_list),
            independent_evidence_count=len(indep_ev),
            correct_count=sum(1 for e in evidence_list if e.correctness),
            last_evidence_at=last_ev_at,
            last_independent_evidence_at=last_indep_at,
            review_status=review_status,
            state_version=new_version,
            engine_version="3.0.0",
            created_at=existing.created_at if existing else now,
            updated_at=now
        )

        return MasteryRepository.save_skill_state(state)

    @classmethod
    def _recalculate_subject_readiness(cls, user_id: str, subject: str) -> None:
        """Updates readiness_state for all recorded states in subject based on DAG."""
        dag = cls.get_dag_engine()
        states = MasteryRepository.get_all_states_for_user(user_id, subject)
        mastery_map = {s.skill_id: s.mastery_state for s in states}

        for s in states:
            readiness, _ = dag.compute_readiness(s.skill_id, mastery_map)
            if s.readiness_state != readiness:
                s.readiness_state = readiness
                s.state_version += 1
                MasteryRepository.save_skill_state(s)

    # ─── 4. SUBJECT GRAPH VIEW ────────────────────────────────────────────────

    @classmethod
    def get_subject_graph(cls, user_id: str, subject: str) -> SubjectGraphView:
        """
        Assembles the explainable subject knowledge graph view (§22, §30).
        """
        dag = cls.get_dag_engine()

        # 1. Fetch all canonical skills for subject
        all_subj_skills = [
            s for s in CANONICAL_SKILLS
            if s.subject.lower() == subject.lower()
        ]

        # 2. Fetch existing states
        persisted_states = {
            s.skill_id: s
            for s in MasteryRepository.get_all_states_for_user(user_id, subject)
        }

        # 3. Build comprehensive mastery map (defaults to NOT_ASSESSED)
        mastery_map: Dict[str, MasteryState] = {
            s.id: persisted_states[s.id].mastery_state if s.id in persisted_states else MasteryState.NOT_ASSESSED
            for s in all_subj_skills
        }

        # 4. Build node views
        nodes: List[SkillNodeView] = []
        blocked_nodes: List[SkillNodeView] = []
        repair_paths: Dict[str, List[str]] = {}

        now = datetime.now(timezone.utc)

        for sk in all_subj_skills:
            st = persisted_states.get(sk.id)
            m_state = st.mastery_state if st else MasteryState.NOT_ASSESSED
            r_state, blockers = dag.compute_readiness(sk.id, mastery_map)

            # If state exists, update readiness in memory
            conf = st.confidence_class if st else ConfidenceClass.LOW_EVIDENCE
            rev = st.review_status if st else ReviewStatus.FRESH

            # Derive explainable why and next action
            if st and st.total_evidence_count > 0:
                ev_list = MasteryRepository.get_evidence_for_skill(user_id, sk.id)
                _, _, _, why, next_act = MasteryTransitionEngine.evaluate_state(st, ev_list, now=now)
            else:
                if r_state == ReadinessState.BLOCKED_BY_PREREQUISITE:
                    blocker_names = [get_skill(b).skill_name for b in blockers if get_skill(b)]
                    why = f"Prerequisite requirement unmet: {', '.join(blocker_names)} needs repair."
                    next_act = f"Repair foundational skills before tackling this concept."
                elif r_state == ReadinessState.READY:
                    why = "No evidence recorded. All strict prerequisites are met."
                    next_act = "Ready to begin learning or assess baseline understanding."
                else:
                    why = "No evidence recorded yet."
                    next_act = "Complete prerequisite assessments to gauge progression."

            node = SkillNodeView(
                skill_id=sk.id,
                skill_code=sk.skill_code,
                skill_name=sk.skill_name,
                subject=sk.subject,
                domain_id=sk.domain_id,
                grade_band=sk.grade_band,
                topic=sk.topic,
                description=sk.description,
                mastery_state=m_state,
                readiness_state=r_state,
                confidence_class=conf,
                review_status=rev,
                prerequisites=dag.get_immediate_prerequisites(sk.id),
                dependents=dag.get_immediate_dependents(sk.id),
                blocking_prerequisites=blockers,
                why=why,
                next_action=next_act
            )
            nodes.append(node)

            if r_state == ReadinessState.BLOCKED_BY_PREREQUISITE:
                blocked_nodes.append(node)
                path = dag.get_repair_path(sk.id, mastery_map)
                if path:
                    repair_paths[sk.id] = path

        # 5. Recommendations
        recs = dag.get_recommendations(subject, mastery_map)

        # 6. Domain groups
        subj_domains = [
            {"id": d.id, "name": d.domain_name, "stage": d.education_stage}
            for d in CANONICAL_DOMAINS
            if d.subject.lower() == subject.lower()
        ]

        return SubjectGraphView(
            subject=subject,
            user_id=user_id,
            domains=subj_domains,
            nodes=nodes,
            blocked_skills=blocked_nodes,
            repair_paths=repair_paths,
            recommendations=recs
        )

    # ─── 5. BLOCKED SKILLS & REPAIR PATH ──────────────────────────────────────

    @classmethod
    def get_blocked_skills(cls, user_id: str, subject: str) -> List[SkillNodeView]:
        graph = cls.get_subject_graph(user_id, subject)
        return graph.blocked_skills

    @classmethod
    def get_repair_path(cls, user_id: str, skill_id: str) -> List[str]:
        sk = get_skill(skill_id)
        subject = sk.subject if sk else "Mathematics"
        dag = cls.get_dag_engine()

        states = {
            s.skill_id: s.mastery_state
            for s in MasteryRepository.get_all_states_for_user(user_id, subject)
        }
        return dag.get_repair_path(skill_id, states)

    # ─── 6. NEXT LEARNING RECOMMENDATIONS ─────────────────────────────────────

    @classmethod
    def get_next_learning_recommendations(cls, user_id: str, subject: str) -> List[LearningRecommendation]:
        dag = cls.get_dag_engine()
        states = {
            s.skill_id: s.mastery_state
            for s in MasteryRepository.get_all_states_for_user(user_id, subject)
        }
        return dag.get_recommendations(subject, states)

    # ─── 7. COMPACT SUMMARY FOR LEARNER CONTEXT ───────────────────────────────

    @classmethod
    def get_compact_mastery_summary(cls, user_id: str, subject: str) -> CompactMasterySummary:
        """
        Produces bounded summary for LearnerContextService without prompt bloat (§23).
        """
        states = MasteryRepository.get_all_states_for_user(user_id, subject)
        secure: List[str] = []
        developing: List[str] = []
        needs_repair: List[str] = []

        for s in states:
            sk = get_skill(s.skill_id)
            name = sk.skill_name if sk else s.skill_id
            if s.mastery_state == MasteryState.SECURE:
                secure.append(name)
            elif s.mastery_state == MasteryState.DEVELOPING:
                developing.append(name)
            elif s.mastery_state == MasteryState.NEEDS_REPAIR:
                needs_repair.append(name)

        recs = cls.get_next_learning_recommendations(user_id, subject)
        rec_starts = [r.skill_name for r in recs[:2]]

        return CompactMasterySummary(
            subject=subject,
            secure_skills=secure[:6],
            developing_skills=developing[:4],
            needs_repair_skills=needs_repair[:4],
            recommended_starting_skills=rec_starts
        )

    # ─── 8. AUDIT ─────────────────────────────────────────────────────────────

    @classmethod
    def audit_prerequisite_graph(cls) -> GraphAuditReport:
        edges = MasteryRepository.get_prerequisite_edges()
        return GraphAuditor.audit_graph(edges)
