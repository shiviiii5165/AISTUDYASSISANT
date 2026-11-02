"""
LearnByGenie — Feature 3: Mastery + Prerequisite Knowledge Graph Schemas
========================================================================
Canonical data contracts for:
- Directed Acyclic Graph (DAG) prerequisite edges
- Append-only evidence ledger with assistance levels
- Durable per-student per-skill mastery and readiness states
- Explainable node views and next-concept recommendations
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class MasteryState(str, Enum):
    """
    Educational mastery states (§5).
    Labels concepts, NOT student identity or intelligence.
    """
    NOT_ASSESSED = "NOT_ASSESSED"  # No meaningful evidence
    NEEDS_REPAIR = "NEEDS_REPAIR"  # Repeated evidence shows conceptual/prerequisite failure
    DEVELOPING = "DEVELOPING"      # Some evidence of understanding, insufficient consistency
    FRAGILE = "FRAGILE"            # Previously secure but recent contradictory evidence
    SECURE = "SECURE"              # Consistent evidence of independent understanding


class ReadinessState(str, Enum):
    """
    Prerequisite readiness separate from concept mastery (§13).
    A student may be unassessed on a concept while being blocked by a prerequisite.
    """
    READY = "READY"                              # All strict prerequisites are secure
    PARTIALLY_READY = "PARTIALLY_READY"          # Prerequisites are developing/mixed, non-critical
    BLOCKED_BY_PREREQUISITE = "BLOCKED_BY_PREREQUISITE" # At least one prerequisite needs repair
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"  # Prerequisites have not been assessed


class ReviewStatus(str, Enum):
    """
    Knowledge freshness and reassessment indicator (§12).
    Distinguishes retention monitoring from naive time decay.
    """
    FRESH = "FRESH"
    REVIEW_SOON = "REVIEW_SOON"
    REASSESSMENT_DUE = "REASSESSMENT_DUE"


class EvidenceSource(str, Enum):
    """
    Authoritative evidence sources (§6).
    """
    DIAGNOSTIC = "DIAGNOSTIC"
    PRACTICE = "PRACTICE"
    QUIZ = "QUIZ"
    TUTOR_CHECK = "TUTOR_CHECK"
    REVISION = "REVISION"
    TRANSFER_CHECK = "TRANSFER_CHECK"
    STEP_GRADER = "STEP_GRADER"
    SIMULATION = "SIMULATION"


class AssistanceLevel(str, Enum):
    """
    Assisted vs. independent solving telemetry (§8).
    Diagnostic evidence is INDEPENDENT. Hint-assisted practice counts differently.
    """
    INDEPENDENT = "INDEPENDENT"
    HINT_ASSISTED = "HINT_ASSISTED"
    PARTIALLY_ASSISTED = "PARTIALLY_ASSISTED"
    FULLY_ASSISTED = "FULLY_ASSISTED"


class RelationshipType(str, Enum):
    STRICT_PREREQUISITE = "STRICT_PREREQUISITE"
    ADVISORY_PREREQUISITE = "ADVISORY_PREREQUISITE"


class ConfidenceClass(str, Enum):
    LOW_EVIDENCE = "LOW_EVIDENCE"
    MODERATE_EVIDENCE = "MODERATE_EVIDENCE"
    HIGH_EVIDENCE = "HIGH_EVIDENCE"


# ─── MODELS ───────────────────────────────────────────────────────────────────

class SkillPrerequisiteEdge(BaseModel):
    id: Optional[str] = None
    prerequisite_skill_id: str
    dependent_skill_id: str
    relationship_type: RelationshipType = RelationshipType.STRICT_PREREQUISITE
    is_active: bool = True
    version: int = 1
    created_at: Optional[datetime] = None


class LearnerSkillEvidence(BaseModel):
    id: Optional[str] = None
    user_id: str
    skill_id: str
    source_type: EvidenceSource
    source_record_id: str  # e.g. diagnostic session ID or attempt UUID
    correctness: bool
    evidence_strength: float = 1.0
    independence_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    confidence_class: ConfidenceClass = ConfidenceClass.MODERATE_EVIDENCE
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = "3.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class LearnerSkillState(BaseModel):
    id: Optional[str] = None
    user_id: str
    skill_id: str
    subject: str
    mastery_state: MasteryState = MasteryState.NOT_ASSESSED
    readiness_state: ReadinessState = ReadinessState.NOT_ENOUGH_EVIDENCE
    confidence_class: ConfidenceClass = ConfidenceClass.LOW_EVIDENCE
    total_evidence_count: int = 0
    independent_evidence_count: int = 0
    correct_count: int = 0
    last_evidence_at: Optional[datetime] = None
    last_independent_evidence_at: Optional[datetime] = None
    review_status: ReviewStatus = ReviewStatus.FRESH
    state_version: int = 1
    engine_version: str = "3.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillNodeView(BaseModel):
    """Rich presentation model for a skill node in the knowledge graph."""
    skill_id: str
    skill_code: str
    skill_name: str
    subject: str
    domain_id: Optional[str] = None
    grade_band: str
    topic: str
    description: str = ""
    mastery_state: MasteryState
    readiness_state: ReadinessState
    confidence_class: ConfidenceClass
    review_status: ReviewStatus
    prerequisites: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    blocking_prerequisites: List[str] = Field(default_factory=list)
    why: str
    next_action: str


class LearningRecommendation(BaseModel):
    """Explainable next learning recommendation (§15)."""
    skill_id: str
    skill_name: str
    subject: str
    recommendation_type: str  # 'REPAIR_PREREQUISITE', 'NEXT_CONCEPT'
    priority: int             # 1 = Highest (repair blocking dependencies), 2 = Next unlocked
    reason: str
    unblocks_skills: List[str] = Field(default_factory=list)


class SubjectGraphView(BaseModel):
    """Full subject knowledge graph representation (§22, §30)."""
    subject: str
    user_id: str
    domains: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[SkillNodeView] = Field(default_factory=list)
    blocked_skills: List[SkillNodeView] = Field(default_factory=list)
    repair_paths: Dict[str, List[str]] = Field(default_factory=dict)
    recommendations: List[LearningRecommendation] = Field(default_factory=list)


class GraphAuditReport(BaseModel):
    """Integrity audit report for DAG topology (§40)."""
    total_skills: int = 0
    total_edges: int = 0
    is_dag: bool = True
    cycles: List[List[str]] = Field(default_factory=list)
    orphan_skills: List[str] = Field(default_factory=list)
    self_edges: List[str] = Field(default_factory=list)
    duplicate_edges: List[str] = Field(default_factory=list)
    inactive_edges: List[str] = Field(default_factory=list)
    is_healthy: bool = True


class CompactMasterySummary(BaseModel):
    """Compact summary injected into LearnerContextService without prompt bloat (§23)."""
    subject: str
    secure_skills: List[str] = Field(default_factory=list)
    developing_skills: List[str] = Field(default_factory=list)
    needs_repair_skills: List[str] = Field(default_factory=list)
    recommended_starting_skills: List[str] = Field(default_factory=list)
