"""
LearnByGenie — Feature 5: Mistake DNA Schemas & Canonical Taxonomy
==================================================================
Canonical data models and enums for persistent error intelligence,
extensible domain-specific subtypes, and verifiable repair memory.

Labels describe learning errors, NOT student identity, weakness, or shame.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field


# ─── 1. CANONICAL ERROR TAXONOMY ──────────────────────────────────────────────

class ErrorType(str, Enum):
    """
    Canonical, extensible mistake categories (§2).
    Cleanly classifies error mechanisms without fragile micro-labels.
    """
    CONCEPTUAL = "CONCEPTUAL"                    # Misunderstanding of core principles/mechanisms
    PROCEDURAL = "PROCEDURAL"                    # Faulty step sequencing or algorithm execution
    CALCULATION = "CALCULATION"                  # Pure arithmetic or computation slip
    SIGN_OR_NOTATION = "SIGN_OR_NOTATION"        # Sign flip, algebraic transposition slip, notation confusion
    FORMULA_RECALL = "FORMULA_RECALL"            # Misremembered formula, terms, or constants
    MISREAD_QUESTION = "MISREAD_QUESTION"        # Overlooked constraints, inverted target, read slip
    UNIT_OR_DIMENSION = "UNIT_OR_DIMENSION"      # Dimensional mismatch, wrong or omitted units
    REASONING = "REASONING"                      # Flawed logical deduction or invalid assumption
    MEMORY_RECALL = "MEMORY_RECALL"              # Fact/definition recall gap
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"  # Partial attempt abandoned before completion
    UNKNOWN = "UNKNOWN"                          # Cannot be reliably classified; auditable gap


class PatternStatus(str, Enum):
    """
    Deterministic pattern states (§9, §10).
    Progression rules:
    - 1 occurrence -> ISOLATED
    - >= 2 independent occurrences across tasks -> RECURRING
    - >= 4 occurrences over time/contexts -> PERSISTENT
    - Validated independent repair evidence -> REPAIRED
    """
    ISOLATED = "ISOLATED"
    RECURRING = "RECURRING"
    PERSISTENT = "PERSISTENT"
    REPAIRED = "REPAIRED"


class RepairStatus(str, Enum):
    """
    Educational repair lifecycle (§16).
    Viewing an explanation does NOT mark REPAIRED.
    Requires independent educational evidence to achieve REPAIRED.
    """
    OPEN = "OPEN"
    IN_REPAIR = "IN_REPAIR"
    REPAIRED = "REPAIRED"
    REASSESSMENT_NEEDED = "REASSESSMENT_NEEDED"


# ─── 1.1 PATTERN THRESHOLD VERSIONING (§7, §9, §10) ───────────────────────────

class MistakePatternThresholds:
    """
    Centralized, versioned rules for mistake pattern progression (§7, §9, §10).
    Progression logic:
    - 1 occurrence: ISOLATED (never overgeneralize single slip)
    - 2-3 independent occurrences: RECURRING
    - >= 4 occurrences: PERSISTENT
    - Independent validated repair: REPAIRED
    - Recurrence after repair: REASSESSMENT_NEEDED (§44)
    """
    VERSION: str = "1.0.0"
    ISOLATED_COUNT: int = 1
    RECURRING_MIN: int = 2
    RECURRING_MAX: int = 3
    PERSISTENT_MIN: int = 4

    @classmethod
    def determine_pattern_status(
        cls,
        occurrence_count: int,
        current_pattern_status: Optional[PatternStatus] = None,
        current_repair_status: Optional[RepairStatus] = None,
    ) -> tuple[PatternStatus, RepairStatus]:
        """
        Deterministic, versioned transition rules for mistake patterns.
        """
        # If pattern was previously REPAIRED, new recurrence triggers REASSESSMENT_NEEDED (§44)
        if (
            current_pattern_status == PatternStatus.REPAIRED
            or current_repair_status == RepairStatus.REPAIRED
        ):
            new_pattern_status = (
                PatternStatus.RECURRING
                if occurrence_count < cls.PERSISTENT_MIN
                else PatternStatus.PERSISTENT
            )
            return new_pattern_status, RepairStatus.REASSESSMENT_NEEDED

        if occurrence_count >= cls.PERSISTENT_MIN:
            return PatternStatus.PERSISTENT, RepairStatus.OPEN
        elif occurrence_count >= cls.RECURRING_MIN:
            return PatternStatus.RECURRING, RepairStatus.OPEN
        else:
            return PatternStatus.ISOLATED, RepairStatus.OPEN


class ConfidenceClass(str, Enum):
    """
    Classification certainty (§7).
    Deterministic evidence yields HIGH; structured rubric yields MODERATE;
    ambiguous signals yield LOW with ErrorType.UNKNOWN.
    """
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class AssistanceLevel(str, Enum):
    """
    Telemetry level from Feature 3 & 4 (§17).
    Only INDEPENDENT evidence can transition status to REPAIRED.
    """
    INDEPENDENT = "INDEPENDENT"
    HINT_ASSISTED = "HINT_ASSISTED"
    PARTIALLY_ASSISTED = "PARTIALLY_ASSISTED"
    FULLY_ASSISTED = "FULLY_ASSISTED"


class MistakeSourceType(str, Enum):
    """
    Authoritative mistake source channels (§5).
    Active: DIAGNOSTIC, TUTOR_CHECK, QUIZ.
    Reserved future contracts: PRACTICE, TRANSFER_CHECK, STEP_GRADER, SIMULATION, REVISION.
    """
    DIAGNOSTIC = "DIAGNOSTIC"
    TUTOR_CHECK = "TUTOR_CHECK"
    QUIZ = "QUIZ"
    PRACTICE = "PRACTICE"
    TRANSFER_CHECK = "TRANSFER_CHECK"
    STEP_GRADER = "STEP_GRADER"
    SIMULATION = "SIMULATION"
    REVISION = "REVISION"


# ─── 2. DOMAIN-SPECIFIC ERROR SUBTYPES ────────────────────────────────────────

COMMON_DOMAIN_SUBTYPES: Dict[str, List[str]] = {
    "Mathematics": [
        "sign_transposition",
        "algebra_manipulation",
        "fraction_operations",
        "wrong_operation",
        "formula_misuse",
        "arithmetic_slip",
        "coordinate_swap"
    ],
    "Physics": [
        "direction_or_vector_error",
        "unit_mismatch",
        "sign_convention",
        "wrong_physical_principle",
        "formula_misapplication"
    ],
    "Chemistry": [
        "reaction_rule_confusion",
        "valency_or_charge_issue",
        "stoichiometric_ratio_setup",
        "state_symbol_omission"
    ],
    "Biology": [
        "term_confusion",
        "process_order_confusion",
        "structure_function_mismatch"
    ],
    "Computer Science": [
        "off_by_one",
        "logic_condition_inverted",
        "data_structure_misuse",
        "variable_scope_error",
        "unhandled_edge_case"
    ]
}


# ─── 3. CLASSIFICATION & INGESTION CANDIDATES ─────────────────────────────────

class MistakeCandidate(BaseModel):
    """
    Inbound candidate submitted by Diagnostic, Tutor check, or Quiz (§21, §22, §23).
    """
    user_id: str
    skill_id: str
    subject: str = "Mathematics"
    source_type: MistakeSourceType
    source_record_id: str
    question_reference: str = ""
    prompt_text: Optional[str] = None
    expected_answer: Optional[str] = None
    student_response: str
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    feedback_reason: Optional[str] = None
    distractor_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """
    Structured outcome of the Error Detection Authority (§6, §7).
    """
    primary_error_type: ErrorType
    secondary_error_types: List[ErrorType] = Field(default_factory=list)
    error_subtype: str = ""
    error_summary: str
    confidence: ConfidenceClass
    classifier_version: str = "5.0.0"
    deterministic_rule: Optional[str] = None


# ─── 4. DURABLE EVENT & PATTERN MODELS ────────────────────────────────────────

class MistakeEvent(BaseModel):
    """
    Durable, immutable record of an individual error occurrence (§4).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    skill_id: Optional[str] = None
    subject: str = "Mathematics"
    source_type: MistakeSourceType
    source_record_id: str
    question_reference: str = ""

    primary_error_type: ErrorType
    secondary_error_types: List[ErrorType] = Field(default_factory=list)
    error_subtype: str = ""
    error_summary: str = ""

    confidence_class: ConfidenceClass = ConfidenceClass.MODERATE
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    repair_status: RepairStatus = RepairStatus.OPEN

    engine_version: str = "5.0.0"
    classifier_version: str = "5.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MistakePattern(BaseModel):
    """
    Aggregated mistake pattern (§9, §10).
    Aggregates occurrences across independent tasks and sessions.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    skill_id: str
    subject: str = "Mathematics"

    error_type: ErrorType
    error_subtype: str = ""

    occurrence_count: int = 1
    recent_occurrence_count: int = 1
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    pattern_status: PatternStatus = PatternStatus.ISOLATED
    confidence: ConfidenceClass = ConfidenceClass.MODERATE

    repair_status: RepairStatus = RepairStatus.OPEN
    recommended_repair_action: str = ""

    likely_prerequisite_skill: Optional[str] = None
    prerequisite_signal: Optional[str] = None

    engine_version: str = "5.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepairEvent(BaseModel):
    """
    Verifiable educational repair evidence record (§16, §17).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_id: str
    user_id: str
    skill_id: str

    repair_action: str
    evidence_source: MistakeSourceType
    evidence_record_id: str
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT

    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = "5.0.0"
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── 5. REPAIR RECOMMENDATION CONTRACT ────────────────────────────────────────

class RepairRecommendation(BaseModel):
    """
    Explainable repair guidance (§15).
    """
    action_type: str
    skill_id: str
    skill_name: str
    recommended_repair_action: str
    likely_prerequisite_skill: Optional[str] = None
    prerequisite_signal: Optional[str] = None
    explanation: str
    pedagogical_mode: str = "TUTOR"


# ─── 6. BOUNDED LEARNER CONTEXT & AUDIT MODELS ────────────────────────────────

class MistakePatternSummary(BaseModel):
    error_type: ErrorType
    error_subtype: str = ""
    status: PatternStatus
    occurrence_count: int
    skill_id: str
    last_seen_at: datetime


class CompactMistakeSummary(BaseModel):
    """
    Bounded summary for LearnerContextService (§28).
    Prevents unbounded prompt injection while providing pedagogical signal.
    """
    total_patterns: int = 0
    recurring_patterns: List[MistakePatternSummary] = Field(default_factory=list)
    isolated_patterns: List[MistakePatternSummary] = Field(default_factory=list)
    top_error_types: List[str] = Field(default_factory=list)


class MistakeDNAAuditReport(BaseModel):
    """
    Audit report (§41) returned by the Mistake DNA Auditor.
    """
    total_events: int = 0
    total_patterns: int = 0
    total_repairs: int = 0
    orphan_skill_ids: List[str] = Field(default_factory=list)
    invalid_taxonomy_labels: List[str] = Field(default_factory=list)
    duplicate_source_events: int = 0
    negative_occurrence_counts: int = 0
    repairs_without_evidence: int = 0
    unknown_classifications_count: int = 0
    unknown_heavy_domains: List[str] = Field(default_factory=list)
    cross_user_isolation_passed: bool = True
    audit_passed: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── 7. FUTURE CONTRACTS ──────────────────────────────────────────────────────

class StepGraderMistakeCandidate(BaseModel):
    """
    Contract reserved for Future Step-Grader (§24).
    """
    user_id: str
    skill_id: str
    subskill: Optional[str] = None
    first_wrong_step: str
    step_index: int
    error_type: ErrorType
    error_subtype: Optional[str] = None
    visual_ref: Optional[str] = None
    source_record_id: str
