"""
LearnByGenie — Feature 3: Mastery Repository
============================================
Durable persistence for the prerequisite DAG, learner skill evidence ledger,
and persistent student mastery states.
Interfaces with Supabase PostgreSQL (migration 023) with resilient in-memory
store for deterministic test isolation.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.db.supabase_client import supabase
from app.core.logging import logger
from .schemas import (
    SkillPrerequisiteEdge, LearnerSkillEvidence, LearnerSkillState,
    MasteryState, ReadinessState, ReviewStatus, ConfidenceClass,
    RelationshipType, EvidenceSource, AssistanceLevel
)
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS


class MasteryRepository:
    """
    Persistence layer for Mastery Knowledge Graph.
    """
    _MEMORY_EDGES: List[SkillPrerequisiteEdge] = []
    _MEMORY_EVIDENCE: Dict[str, List[LearnerSkillEvidence]] = {}  # user_id -> [evidence]
    _MEMORY_STATES: Dict[Tuple[str, str], LearnerSkillState] = {}  # (user_id, skill_id) -> state

    @classmethod
    def clear_memory_cache(cls) -> None:
        """Resets in-memory storage for test isolation."""
        cls._MEMORY_EDGES.clear()
        cls._MEMORY_EVIDENCE.clear()
        cls._MEMORY_STATES.clear()

    # ─── 1. PREREQUISITE EDGES ────────────────────────────────────────────────

    @classmethod
    def get_prerequisite_edges(cls) -> List[SkillPrerequisiteEdge]:
        """Loads all active prerequisite edges from Supabase or fallback memory/blueprint."""
        if supabase is not None:
            try:
                res = supabase.table("skill_prerequisites").select("*").eq("is_active", True).execute()
                if res.data and len(res.data) > 0:
                    edges = []
                    for row in res.data:
                        edges.append(SkillPrerequisiteEdge(
                            id=row.get("id"),
                            prerequisite_skill_id=row["prerequisite_skill_id"],
                            dependent_skill_id=row["dependent_skill_id"],
                            relationship_type=RelationshipType(row.get("relationship_type", "STRICT_PREREQUISITE")),
                            is_active=row.get("is_active", True),
                            version=row.get("version", 1)
                        ))
                    return edges
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase load edges fallback: {e}")

        # Return memory edges if present
        if cls._MEMORY_EDGES:
            return [e for e in cls._MEMORY_EDGES if e.is_active]

        # Seed from canonical skills blueprint if memory is empty
        canonical_edges = []
        for s in CANONICAL_SKILLS:
            for pid in s.prerequisite_skill_ids:
                edge = SkillPrerequisiteEdge(
                    prerequisite_skill_id=pid,
                    dependent_skill_id=s.id,
                    relationship_type=RelationshipType.STRICT_PREREQUISITE,
                    is_active=True
                )
                canonical_edges.append(edge)
        cls._MEMORY_EDGES = canonical_edges
        return canonical_edges

    @classmethod
    def save_prerequisite_edge(cls, edge: SkillPrerequisiteEdge) -> SkillPrerequisiteEdge:
        if not edge.id:
            edge.id = str(uuid.uuid4())

        # Check memory
        for i, existing in enumerate(cls._MEMORY_EDGES):
            if (existing.prerequisite_skill_id == edge.prerequisite_skill_id and
                existing.dependent_skill_id == edge.dependent_skill_id):
                cls._MEMORY_EDGES[i] = edge
                break
        else:
            cls._MEMORY_EDGES.append(edge)

        if supabase is not None:
            try:
                row = {
                    "id": edge.id,
                    "prerequisite_skill_id": edge.prerequisite_skill_id,
                    "dependent_skill_id": edge.dependent_skill_id,
                    "relationship_type": edge.relationship_type.value,
                    "is_active": edge.is_active,
                    "version": edge.version
                }
                supabase.table("skill_prerequisites").upsert(row, on_conflict="prerequisite_skill_id,dependent_skill_id").execute()
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase save edge fallback: {e}")

        return edge

    # ─── 2. EVIDENCE LEDGER (APPEND-ONLY & IDEMPOTENT) ─────────────────────────

    @classmethod
    def record_evidence(cls, evidence: LearnerSkillEvidence) -> Tuple[LearnerSkillEvidence, bool]:
        """
        Appends evidence to the ledger (§7, §26).
        Enforces idempotency:
        Returns (evidence, is_new). If already recorded for this source, returns (existing, False).
        """
        user_id = evidence.user_id
        if not evidence.id:
            evidence.id = str(uuid.uuid4())

        user_ev_list = cls._MEMORY_EVIDENCE.setdefault(user_id, [])

        # Idempotency check: (user_id, source_type, source_record_id, skill_id)
        for existing in user_ev_list:
            if (existing.source_type == evidence.source_type and
                existing.source_record_id == evidence.source_record_id and
                existing.skill_id == evidence.skill_id):
                return existing, False

        # Not found in memory, check Supabase
        if supabase is not None:
            try:
                row = {
                    "id": evidence.id,
                    "user_id": evidence.user_id,
                    "skill_id": evidence.skill_id,
                    "source_type": evidence.source_type.value,
                    "source_record_id": evidence.source_record_id,
                    "correctness": evidence.correctness,
                    "evidence_strength": float(evidence.evidence_strength),
                    "independence_level": evidence.independence_level.value,
                    "confidence_class": evidence.confidence_class.value,
                    "occurred_at": evidence.occurred_at.isoformat() if evidence.occurred_at else datetime.now(timezone.utc).isoformat(),
                    "engine_version": evidence.engine_version,
                    "metadata": evidence.metadata
                }
                res = supabase.table("learner_skill_evidence").upsert(
                    row,
                    on_conflict="user_id,source_type,source_record_id,skill_id"
                ).execute()
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase save evidence fallback: {e}")

        user_ev_list.append(evidence)
        return evidence, True

    @classmethod
    def get_evidence_for_skill(cls, user_id: str, skill_id: str) -> List[LearnerSkillEvidence]:
        """Returns all evidence for a specific user and skill."""
        user_ev = cls._MEMORY_EVIDENCE.get(user_id, [])
        skill_ev = [e for e in user_ev if e.skill_id == skill_id]

        if supabase is not None and not skill_ev:
            try:
                res = supabase.table("learner_skill_evidence").select("*").eq("user_id", user_id).eq("skill_id", skill_id).order("occurred_at").execute()
                if res.data:
                    evs = []
                    for row in res.data:
                        ev = LearnerSkillEvidence(
                            id=row.get("id"),
                            user_id=row["user_id"],
                            skill_id=row["skill_id"],
                            source_type=EvidenceSource(row["source_type"]),
                            source_record_id=row["source_record_id"],
                            correctness=row["correctness"],
                            evidence_strength=float(row.get("evidence_strength", 1.0)),
                            independence_level=AssistanceLevel(row.get("independence_level", "INDEPENDENT")),
                            confidence_class=ConfidenceClass(row.get("confidence_class", "MODERATE_EVIDENCE")),
                            occurred_at=datetime.fromisoformat(row["occurred_at"]) if row.get("occurred_at") else datetime.now(timezone.utc),
                            engine_version=row.get("engine_version", "3.0.0"),
                            metadata=row.get("metadata", {})
                        )
                        evs.append(ev)
                    # Cache in memory
                    cls._MEMORY_EVIDENCE.setdefault(user_id, []).extend(evs)
                    return evs
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase get evidence fallback: {e}")

        return skill_ev

    @classmethod
    def get_evidence_for_user(cls, user_id: str) -> List[LearnerSkillEvidence]:
        return cls._MEMORY_EVIDENCE.get(user_id, [])

    # ─── 3. LEARNER SKILL STATES ──────────────────────────────────────────────

    @classmethod
    def get_skill_state(cls, user_id: str, skill_id: str) -> Optional[LearnerSkillState]:
        key = (user_id, skill_id)
        if key in cls._MEMORY_STATES:
            return cls._MEMORY_STATES[key]

        if supabase is not None:
            try:
                res = supabase.table("learner_skill_states").select("*").eq("user_id", user_id).eq("skill_id", skill_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    state = LearnerSkillState(
                        id=row.get("id"),
                        user_id=row["user_id"],
                        skill_id=row["skill_id"],
                        subject=row["subject"],
                        mastery_state=MasteryState(row["mastery_state"]),
                        readiness_state=ReadinessState(row["readiness_state"]),
                        confidence_class=ConfidenceClass(row.get("confidence_class", "LOW_EVIDENCE")),
                        total_evidence_count=row.get("total_evidence_count", 0),
                        independent_evidence_count=row.get("independent_evidence_count", 0),
                        correct_count=row.get("correct_count", 0),
                        last_evidence_at=datetime.fromisoformat(row["last_evidence_at"]) if row.get("last_evidence_at") else None,
                        last_independent_evidence_at=datetime.fromisoformat(row["last_independent_evidence_at"]) if row.get("last_independent_evidence_at") else None,
                        review_status=ReviewStatus(row.get("review_status", "FRESH")),
                        state_version=row.get("state_version", 1),
                        engine_version=row.get("engine_version", "3.0.0")
                    )
                    cls._MEMORY_STATES[key] = state
                    return state
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase get skill state fallback: {e}")

        return None

    @classmethod
    def save_skill_state(cls, state: LearnerSkillState) -> LearnerSkillState:
        key = (state.user_id, state.skill_id)
        if not state.id:
            state.id = str(uuid.uuid4())

        cls._MEMORY_STATES[key] = state

        if supabase is not None:
            try:
                row = {
                    "id": state.id,
                    "user_id": state.user_id,
                    "skill_id": state.skill_id,
                    "subject": state.subject,
                    "mastery_state": state.mastery_state.value,
                    "readiness_state": state.readiness_state.value,
                    "confidence_class": state.confidence_class.value,
                    "total_evidence_count": state.total_evidence_count,
                    "independent_evidence_count": state.independent_evidence_count,
                    "correct_count": state.correct_count,
                    "last_evidence_at": state.last_evidence_at.isoformat() if state.last_evidence_at else None,
                    "last_independent_evidence_at": state.last_independent_evidence_at.isoformat() if state.last_independent_evidence_at else None,
                    "review_status": state.review_status.value,
                    "state_version": state.state_version,
                    "engine_version": state.engine_version,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                supabase.table("learner_skill_states").upsert(
                    row,
                    on_conflict="user_id,skill_id"
                ).execute()
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase save skill state fallback: {e}")

        return state

    @classmethod
    def get_all_states_for_user(cls, user_id: str, subject: Optional[str] = None) -> List[LearnerSkillState]:
        states = [s for (u, _), s in cls._MEMORY_STATES.items() if u == user_id]
        if subject:
            states = [s for s in states if s.subject.lower() == subject.lower()]

        if supabase is not None and not states:
            try:
                query = supabase.table("learner_skill_states").select("*").eq("user_id", user_id)
                if subject:
                    query = query.eq("subject", subject)
                res = query.execute()
                if res.data:
                    for row in res.data:
                        s = LearnerSkillState(
                            id=row.get("id"),
                            user_id=row["user_id"],
                            skill_id=row["skill_id"],
                            subject=row["subject"],
                            mastery_state=MasteryState(row["mastery_state"]),
                            readiness_state=ReadinessState(row["readiness_state"]),
                            confidence_class=ConfidenceClass(row.get("confidence_class", "LOW_EVIDENCE")),
                            total_evidence_count=row.get("total_evidence_count", 0),
                            independent_evidence_count=row.get("independent_evidence_count", 0),
                            correct_count=row.get("correct_count", 0),
                            last_evidence_at=datetime.fromisoformat(row["last_evidence_at"]) if row.get("last_evidence_at") else None,
                            last_independent_evidence_at=datetime.fromisoformat(row["last_independent_evidence_at"]) if row.get("last_independent_evidence_at") else None,
                            review_status=ReviewStatus(row.get("review_status", "FRESH")),
                            state_version=row.get("state_version", 1),
                            engine_version=row.get("engine_version", "3.0.0")
                        )
                        cls._MEMORY_STATES[(user_id, s.skill_id)] = s
                    return cls.get_all_states_for_user(user_id, subject)
            except Exception as e:
                logger.debug(f"[MasteryRepo] Supabase get all states fallback: {e}")

        return states
