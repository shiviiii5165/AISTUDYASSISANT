"""
LearnByGenie — Feature 8: Step-Grader & Reasoning Diagnostics Engine Schemas
=============================================================================
Canonical data contracts for:
- Normalized multi-step representations
- First-wrong-step detection & error cascade models
- Subject-agnostic step types & validation statuses
- Bounded Socratic Tutor review handoffs
- Zero fake certainty (HIGH, MODERATE, LOW confidence classes only)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field

# Re-use canonical Mistake DNA taxonomy & Mastery Assistance Level (§21, §23)
from app.services.mistake_dna.schemas import ErrorType, ConfidenceClass
from app.services.mastery.schemas import AssistanceLevel


# ─── 1. CANONICAL ENUMS ────────────────────────────────────────────────────────

class StepType(str, Enum):
    """
    Canonical, extensible step taxonomy (§7).
    Subject-agnostic categorisation of reasoning actions.
    """
    SETUP = "SETUP"                        # Defining variables, writing given formulas, initial equations
    TRANSFORMATION = "TRANSFORMATION"      # Algebraic rearrangement, equality preservation, term shifting
    SUBSTITUTION = "SUBSTITUTION"          # Plugging in numbers, variables, or expressions
    CALCULATION = "CALCULATION"            # Direct arithmetic, numeric computation, evaluation
    RULE_APPLICATION = "RULE_APPLICATION"  # Applying a physical law, reaction rule, or theorem
    INFERENCE = "INFERENCE"                # Logical deduction, branch decision, condition check
    CONCLUSION = "CONCLUSION"              # Stating final solution, root, or deduced fact
    EXPLANATION = "EXPLANATION"            # Natural language justification
    UNKNOWN = "UNKNOWN"                    # Unrecognized or unstructured line


class StepValidationStatus(str, Enum):
    """
    Error cascade classification (§8, §9).
    Distinguishes the root error from downstream arithmetic consequences.
    """
    VALID_STEP = "VALID_STEP"              # Step reasoning is sound and verifiable
    ROOT_ERROR = "ROOT_ERROR"              # The EARLIEST step where invalid reasoning occurred
    DOWNSTREAM_ERROR = "DOWNSTREAM_ERROR"  # Step logically/arithmetically follows an earlier wrong step
    INDEPENDENT_ERROR = "INDEPENDENT_ERROR"# A new, separate error unrelated to previous corruption
    UNCERTAIN = "UNCERTAIN"                # Reasoning cannot be deterministically or rubric-verified


class ValidatorType(str, Enum):
    """
    Validation hierarchy tier (§10).
    A. Deterministic symbolic/numeric validator
    B. Domain-specific rule validator
    C. Structured rubric validator
    D. Constrained LLM semantic evaluation
    E. UNCERTAIN
    """
    DETERMINISTIC = "DETERMINISTIC"        # Exact AST arithmetic, algebraic equivalence, quadratic roots
    DOMAIN_RULE = "DOMAIN_RULE"            # Physical unit check, stoichiometric ratio, syntax rules
    RUBRIC = "RUBRIC"                      # Matched against structured rubric criteria
    SEMANTIC_LLM = "SEMANTIC_LLM"          # Constrained JSON evaluation for ambiguous text
    UNCERTAIN = "UNCERTAIN"                # Unsupported or unverified


class OverallOutcome(str, Enum):
    """
    Authoritative solution evaluation outcome (§17).
    """
    ALL_STEPS_VALID = "ALL_STEPS_VALID"
    ROOT_ERROR_DETECTED = "ROOT_ERROR_DETECTED"
    AMBIGUOUS_REASONING = "AMBIGUOUS_REASONING"
    UNRESOLVED = "UNRESOLVED"


class SessionStatus(str, Enum):
    """Lifecycle status of a grading session."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


# ─── 2. CANONICAL STEP REPRESENTATION ─────────────────────────────────────────

class GradedStep(BaseModel):
    """
    Normalized internal step record (§6).
    Preserves raw student input alongside normalized expression and diagnostics.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_index: int                       # 1-indexed step position
    raw_text: str                         # Untouched student input string
    normalized_expression: str = ""       # Sanitized / canonical form
    step_type: StepType = StepType.TRANSFORMATION
    validation_status: StepValidationStatus = StepValidationStatus.VALID_STEP
    validator_type: ValidatorType = ValidatorType.DETERMINISTIC
    confidence: ConfidenceClass = ConfidenceClass.HIGH
    is_root_error: bool = False
    error_type: Optional[ErrorType] = None
    error_subtype: Optional[str] = None
    parent_step_index: Optional[int] = None
    student_explanation: Optional[str] = None
    feedback: str = ""                    # Concise, supportive, no-shame explanation (§18)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── 3. DURABLE ATTEMPTS & SESSIONS ───────────────────────────────────────────

class StepGraderAttempt(BaseModel):
    """
    Durable attempt record supporting solution edits & version history (§32, §35).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    attempt_sequence: int = 1             # 1 for first attempt, 2 for resubmission, etc.
    parent_attempt_id: Optional[str] = None
    question_text: str = ""
    raw_input: str
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    overall_outcome: OverallOutcome = OverallOutcome.ROOT_ERROR_DETECTED
    first_wrong_step_index: Optional[int] = None
    validated_step_count: int = 0
    root_error_type: Optional[ErrorType] = None
    root_error_subtype: Optional[str] = None
    confidence_class: ConfidenceClass = ConfidenceClass.HIGH
    repair_recommendation: str = ""
    idempotency_key: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StepGraderSession(BaseModel):
    """
    Durable grading session record (§31).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    subject: str = "Mathematics"
    skill_id: Optional[str] = None
    source_type: str = "STUDENT_DIRECT"   # 'STUDENT_DIRECT', 'PRACTICE', 'TUTOR', 'ASSIGNMENT'
    source_record_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    current_attempt_id: Optional[str] = None
    total_attempts: int = 1
    policy_version: str = "1.0.0"
    grader_version: str = "8.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── 4. STRUCTURED RUBRIC CONTRACT ─────────────────────────────────────────────

class StructuredRubric(BaseModel):
    """
    Structured rubric model (§28).
    Replaces opaque prompt instructions with auditable criteria.
    """
    required_concepts: List[str] = Field(default_factory=list)
    acceptable_transformations: List[str] = Field(default_factory=list)
    critical_steps: List[str] = Field(default_factory=list)
    common_errors: Dict[str, str] = Field(default_factory=dict) # e.g. {"sign_flip": "SIGN_OR_NOTATION"}
    final_requirements: List[str] = Field(default_factory=list)


# ─── 5. OUTPUT CONTRACT & TUTOR HANDOFF ───────────────────────────────────────

class StepGraderResult(BaseModel):
    """
    Strict external output contract (§17).
    No hidden chain-of-thought, no fake percentages.
    """
    session_id: str
    attempt_id: str
    attempt_sequence: int = 1
    overall_outcome: OverallOutcome
    first_wrong_step: Optional[int] = None
    validated_steps: List[GradedStep]
    downstream_steps: List[int] = Field(default_factory=list)
    error_type: Optional[ErrorType] = None
    error_subtype: Optional[str] = None
    confidence: ConfidenceClass = ConfidenceClass.HIGH
    skill_id: Optional[str] = None
    related_prerequisite: Optional[str] = None
    feedback_summary: str
    recommended_next_action: str
    can_review_with_tutor: bool = True
    engine_version: str = "8.0.0"
    policy_version: str = "1.0.0"


class TutorHandoffContext(BaseModel):
    """
    Bounded context payload sent to Socratic Tutor (§20).
    Only includes the specific issue, not full historical transcripts.
    """
    session_id: str
    attempt_id: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    first_wrong_step_index: int
    step_raw_text: str
    error_type: str
    error_subtype: Optional[str] = None
    feedback: str
    related_prerequisite: Optional[str] = None
    question_text: str = ""


# ─── 6. CAPABILITY MATRIX MODEL ───────────────────────────────────────────────

class CapabilityMatrixItem(BaseModel):
    """
    Grading capability matrix entry (§43).
    Separates engine support from grading coverage honestly (§42).
    """
    subject: str
    skill_name: str
    step_types_supported: List[str]
    validator_type: ValidatorType
    deterministic_support: bool
    rubric_support: bool
    confidence_capability: str             # e.g. 'HIGH', 'MODERATE', 'PARTIAL'
    notes: str = ""
