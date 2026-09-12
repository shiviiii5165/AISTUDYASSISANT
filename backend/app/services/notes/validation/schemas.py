"""
TeachGenie Notes Validation Engine — Core Schemas (Step 4)
=========================================================
Strict, immutable, and explainable contracts for validating generated NotesDocuments
against canonical learner context, grounded sources, and trusted NotesGenerationPlans.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    REPAIRABLE = "repairable"
    INVALID = "invalid"
    VALIDATION_FAILED = "validation_failed"


class ViolationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationDimension(str, Enum):
    SCHEMA = "schema"
    PLAN_COMPLIANCE = "plan_compliance"
    STRUCTURAL = "structural"
    GROUNDING = "grounding"
    FACTUAL = "factual"
    CURRICULUM = "curriculum"
    PEDAGOGY = "pedagogy"
    MISCONCEPTION = "misconception"
    PRACTICE = "practice"
    FORMULA = "formula"
    VISUAL = "visual"
    HALLUCINATION = "hallucination"
    COMPLETENESS = "completeness"
    SAFETY = "safety"


class GroundingSupportType(str, Enum):
    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
    PARAPHRASE_SUPPORTED = "PARAPHRASE_SUPPORTED"
    INFERRED_SUPPORTED = "INFERRED_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class SourceGroundingFinding(BaseModel):
    """Detailed grounding assessment for an individual claim or cited assertion."""
    claim: str
    source_ids: List[str] = Field(default_factory=list)
    support_type: GroundingSupportType
    evidence: Optional[str] = None
    confidence: float = 1.0
    severity: ViolationSeverity = ViolationSeverity.INFO


class FormulaValidationStatus(str, Enum):
    VERIFIED_DETERMINISTICALLY = "VERIFIED_DETERMINISTICALLY"
    VERIFIED_SEMANTICALLY = "VERIFIED_SEMANTICALLY"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


class DimensionStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"


class ValidationViolation(BaseModel):
    """Structured, actionable violation item explaining an observed defect."""
    code: str
    severity: ViolationSeverity
    dimension: ValidationDimension
    message: str
    section_id: Optional[str] = None
    evidence: Optional[Union[str, Dict[str, Any]]] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    repairable: bool = False


class RepairAction(str, Enum):
    ACCEPT = "accept"
    WARN = "warn"
    REPAIR = "repair"
    REJECT = "reject"


class RepairTarget(BaseModel):
    """Identifies a specific defective section or component targeted for bounded repair."""
    section_id: Optional[str] = None
    reason: str
    violation_code: str
    expected: Optional[str] = None
    repair_prompt: Optional[str] = None


class RepairRecommendation(BaseModel):
    """Actionable recommendation produced by Step 4 for application orchestration."""
    action: RepairAction = RepairAction.ACCEPT
    targets: List[RepairTarget] = Field(default_factory=list)


class RepairMetadata(BaseModel):
    """Observability metadata tracking global repair budget and attempt history."""
    repair_budget: int = 1
    repair_attempts: int = 0
    repair_source: str = "validation"
    repaired_sections: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """
    Step 4 Validation Engine Output Contract.
    Contains overall pass/fail status, numerical dimension scores, explicit violations,
    grounding results, and repair recommendations.
    """
    schema_version: str = "1.0"
    valid: bool
    status: ValidationStatus
    overall_score: float = Field(default=100.0, ge=0.0, le=100.0)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    dimension_statuses: Dict[str, DimensionStatus] = Field(default_factory=dict)
    violations: List[ValidationViolation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    section_results: List[Dict[str, Any]] = Field(default_factory=list)
    source_grounding_results: Dict[str, Any] = Field(default_factory=dict)
    plan_compliance_results: Dict[str, Any] = Field(default_factory=dict)
    factual_results: Dict[str, Any] = Field(default_factory=dict)
    curriculum_results: Dict[str, Any] = Field(default_factory=dict)
    pedagogical_results: Dict[str, Any] = Field(default_factory=dict)
    hallucination_results: Dict[str, Any] = Field(default_factory=dict)
    repair_recommendation: Optional[RepairRecommendation] = None
    repair_metadata: Optional[RepairMetadata] = None
    validator_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)

    @property
    def has_errors(self) -> bool:
        return any(v.severity in (ViolationSeverity.ERROR, ViolationSeverity.CRITICAL) for v in self.violations)

    @property
    def is_repairable(self) -> bool:
        if not self.violations:
            return False
        # If there are errors, they must all be marked repairable and not critical non-repairable
        errors = [v for v in self.violations if v.severity in (ViolationSeverity.ERROR, ViolationSeverity.CRITICAL)]
        return len(errors) > 0 and all(v.repairable for v in errors)


class ValidateNotesRequest(BaseModel):
    """Wire request for external validation invocation."""
    context: Optional[Dict[str, Any]] = None
    snapshot_id: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    document: Dict[str, Any]
    sources: Optional[Dict[str, Any]] = None
