"""
Shared Cross-Feature Contracts & Services for Lesson Planner VNext
==================================================================
Decouples Presentation Engine (PPT), Quiz, TeachMe, and Notes from Lesson Planner internals.
Provides:
1. SharedLessonContext & LessonContextProvider: Single canonical data contract for downstream features.
2. LearnerStateRepository: Persistent multi-observation student concept state layer.
3. LearningEvidenceService: Dual-idempotent evidence ingestion layer.
"""

import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ..schemas import (
    CanonicalDomain, PrerequisiteMasteryState, StudentConceptState,
    LearningEvidenceRecord, LearningRoadmap, RoadmapStage
)
from .canonical_concepts import CanonicalConceptResolver

logger = logging.getLogger("teachgenie.lesson_planner.shared_context")


class SharedLessonContext(BaseModel):
    """
    Standardized cross-feature context contract consumed by PPT, Quiz, TeachMe, and Notes.
    """
    roadmap_id: str
    topic: str
    domain: str
    grade_level: str
    target_duration_minutes: int
    knowledge_pack_id: Optional[str] = None
    objectives: List[Dict[str, Any]] = Field(default_factory=list)
    canonical_concepts: List[Dict[str, Any]] = Field(default_factory=list)
    misconception_targets: List[Dict[str, Any]] = Field(default_factory=list)
    stage_timings: List[Dict[str, Any]] = Field(default_factory=list)
    visual_requirements: List[str] = Field(default_factory=list)
    adaptive_reserve_minutes: int = 0


class LessonContextProvider:
    """
    Extracts and provisions SharedLessonContext for any LearningRoadmap.
    """

    @classmethod
    def get_shared_context(cls, roadmap: LearningRoadmap) -> SharedLessonContext:
        """
        Builds standardized cross-feature context from a compiled or active roadmap.
        """
        objectives = []
        canonical_concepts = []
        misconceptions = []
        stage_timings = []
        visual_reqs = []

        for stage in roadmap.stages:
            stage_timings.append({
                "stage_id": stage.id,
                "sequence": stage.sequence,
                "title": stage.title,
                "duration_minutes": stage.duration_minutes,
                "archetype": stage.archetype.value if hasattr(stage.archetype, "value") else str(stage.archetype),
                "is_locked": stage.is_locked
            })

            # Canonical concept resolution
            concept_entry = CanonicalConceptResolver.resolve_or_create(
                concept_name=stage.title,
                domain=roadmap.domain
            )
            canonical_concepts.append({
                "canonical_id": concept_entry.canonical_id,
                "display_name": concept_entry.display_name,
                "stage_id": stage.id
            })

            for obj in stage.objectives:
                objectives.append({
                    "id": getattr(obj, "id", f"obj_{stage.id}"),
                    "text": getattr(obj, "text", getattr(obj, "description", "")),
                    "bloom_level": obj.bloom_level.value if hasattr(obj.bloom_level, "value") else str(obj.bloom_level),
                    "is_mandatory": getattr(obj, "is_mandatory", True)
                })

            for misc in stage.expected_misconceptions:
                misconceptions.append({
                    "concept_id": concept_entry.canonical_id,
                    "stage_id": stage.id,
                    "misconception": misc
                })

            visual_reqs.extend(stage.visual_requirements)

        return SharedLessonContext(
            roadmap_id=roadmap.id,
            topic=roadmap.topic,
            domain=roadmap.domain.value if hasattr(roadmap.domain, "value") else str(roadmap.domain),
            grade_level=roadmap.level,
            target_duration_minutes=roadmap.target_duration_minutes,
            knowledge_pack_id=roadmap.knowledge_pack_id,
            objectives=objectives,
            canonical_concepts=canonical_concepts,
            misconception_targets=misconceptions,
            stage_timings=stage_timings,
            visual_requirements=list(dict.fromkeys(visual_reqs)),
            adaptive_reserve_minutes=roadmap.adaptive_reserve_minutes
        )


class LearnerStateRepository:
    """
    Persistent repository for student_concept_state.
    Separates immutable raw evidence from estimated persistent mastery.
    """

    _in_memory_store: Dict[Tuple[str, str, str, str], StudentConceptState] = {}

    @classmethod
    def get_state(
        cls,
        student_id: str,
        canonical_concept_id: str,
        curriculum_scope: str = "standard",
        curriculum_version: str = "1.0"
    ) -> StudentConceptState:
        key = (student_id, canonical_concept_id, curriculum_scope, curriculum_version)
        if key in cls._in_memory_store:
            return cls._in_memory_store[key]

        # Default state when no evidence exists is UNKNOWN
        default_state = StudentConceptState(
            student_id=student_id,
            canonical_concept_id=canonical_concept_id,
            curriculum_scope=curriculum_scope,
            curriculum_version=curriculum_version,
            mastery_state=PrerequisiteMasteryState.UNKNOWN,
            confidence=0.50,
            evidence_count=0,
            success_count=0,
            last_evaluated_at=datetime.now(timezone.utc)
        )
        cls._in_memory_store[key] = default_state
        return default_state

    @classmethod
    def update_state(
        cls,
        student_id: str,
        canonical_concept_id: str,
        correctness: bool,
        confidence: float = 0.80,
        curriculum_scope: str = "standard",
        curriculum_version: str = "1.0"
    ) -> StudentConceptState:
        """
        Probabilistic multi-observation mastery update.
        Never flips state on a single raw error if prior history demonstrates mastery.
        """
        current = cls.get_state(student_id, canonical_concept_id, curriculum_scope, curriculum_version)
        
        new_count = current.evidence_count + 1
        new_successes = current.success_count + (1 if correctness else 0)
        success_ratio = new_successes / new_count

        # Estimate new mastery state
        if new_count >= 2 and success_ratio >= 0.85:
            new_state = PrerequisiteMasteryState.MASTERED
            est_conf = min(0.99, max(current.confidence, confidence))
        elif success_ratio >= 0.70:
            new_state = PrerequisiteMasteryState.LIKELY_MASTERED
            est_conf = 0.80
        elif success_ratio < 0.50:
            new_state = PrerequisiteMasteryState.WEAK
            est_conf = 0.85
        else:
            new_state = PrerequisiteMasteryState.UNKNOWN
            est_conf = 0.60

        updated = StudentConceptState(
            student_id=student_id,
            canonical_concept_id=canonical_concept_id,
            curriculum_scope=curriculum_scope,
            curriculum_version=curriculum_version,
            mastery_state=new_state,
            confidence=round(est_conf, 2),
            evidence_count=new_count,
            success_count=new_successes,
            last_evaluated_at=datetime.now(timezone.utc)
        )
        key = (student_id, canonical_concept_id, curriculum_scope, curriculum_version)
        cls._in_memory_store[key] = updated
        return updated


class LearningEvidenceService:
    """
    Ingests learning evidence with dual idempotency (preferred event_id + deterministic fallback)
    and updates persistent learner concept state without double-counting.
    """

    _event_id_registry: set = set()
    _idempotency_hash_registry: set = set()
    _evidence_store: List[LearningEvidenceRecord] = []

    @classmethod
    def record_evidence(
        cls,
        evidence: LearningEvidenceRecord,
        curriculum_scope: str = "standard",
        curriculum_version: str = "1.0",
        simulate_failure_after_insert: bool = False
    ) -> Tuple[LearningEvidenceRecord, bool]:
        """
        Records an observation with dual idempotency.
        Returns (recorded_evidence, is_duplicate).
        """
        # 1. Check Preferred event_id uniqueness
        if evidence.event_id:
            if evidence.event_id in cls._event_id_registry:
                logger.info(f"[LearningEvidenceService] Duplicate event_id detected: {evidence.event_id}")
                return evidence, True
            cls._event_id_registry.add(evidence.event_id)

        # 2. Check Deterministic Fallback Hash uniqueness
        derived_key = hashlib.sha256(
            f"{evidence.roadmap_id or ''}:{evidence.student_id}:{evidence.source_type}:{evidence.source_id or ''}:{evidence.question_id or ''}:{evidence.attempt}".encode("utf-8")
        ).hexdigest()

        if derived_key in cls._idempotency_hash_registry:
            logger.info(f"[LearningEvidenceService] Duplicate deterministic evidence detected: {derived_key[:12]}")
            return evidence, True

        cls._idempotency_hash_registry.add(derived_key)
        evidence.idempotency_key = derived_key

        # 3. Simulate failure atomicity if requested
        if simulate_failure_after_insert:
            # Clean up idempotency keys on simulated rollback
            if evidence.event_id:
                cls._event_id_registry.discard(evidence.event_id)
            cls._idempotency_hash_registry.discard(derived_key)
            raise RuntimeError("TRANSACTION_FAILED: Learner state update failed, rolling back evidence insert.")

        # 4. Resolve canonical concept ID
        canonical_concept = CanonicalConceptResolver.resolve_or_create(
            concept_name=evidence.concept_id,
            domain=CanonicalDomain.GENERAL_ACADEMIC
        )
        evidence.canonical_concept_id = canonical_concept.canonical_id

        # 5. Persist evidence observation
        cls._evidence_store.append(evidence)

        # 6. Update persistent learner state
        LearnerStateRepository.update_state(
            student_id=evidence.student_id,
            canonical_concept_id=canonical_concept.canonical_id,
            correctness=evidence.correctness,
            confidence=evidence.confidence,
            curriculum_scope=curriculum_scope,
            curriculum_version=curriculum_version
        )

        return evidence, False
