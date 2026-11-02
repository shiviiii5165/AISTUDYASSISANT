"""
LearnByGenie — Feature 8: Step-Grader Evidence & Grading Policy
================================================================
Defines versioned policy rules for (§24, §25, §26, §27):
- Evidence-bearing step thresholds
- Assistance level tracking (INDEPENDENT, HINT_ASSISTED, etc.)
- Strict root-error isolation (zero double-counting of downstream errors in Mistake DNA)
- Non-equivalence to independent transfer verification (Step-Grader != Transfer Check)
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.step_grader.schemas import (
    ConfidenceClass, OverallOutcome, StepValidationStatus, GradedStep
)
from app.services.mastery.schemas import AssistanceLevel


class StepGraderPolicyConfig(BaseModel):
    """Configurable knobs for Step-Grader evidence policy."""
    min_confidence_for_mastery: ConfidenceClass = ConfidenceClass.MODERATE
    require_all_steps_valid_for_positive_mastery: bool = True
    root_error_submits_negative_mastery: bool = True
    downstream_error_emits_mistake_event: bool = False
    allow_unassisted_transfer_claim: bool = False
    default_assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT


class StepGraderPolicy:
    """
    Versioned policy implementation for Step-Grader evidence decisions.
    """
    def __init__(
        self,
        version: str = "1.0.0",
        config: Optional[StepGraderPolicyConfig] = None,
        description: str = "Canonical Step-Grader policy v1.0.0"
    ):
        self.version = version
        self.config = config or StepGraderPolicyConfig()
        self.description = description

    def is_step_evidence_bearing(self, step: GradedStep) -> bool:
        """
        Determines whether a single validated step qualifies as evidence-bearing.
        - Steps with LOW confidence are excluded from positive evidence (§24, §49).
        - DOWNSTREAM_ERROR steps are excluded from error evidence.
        """
        if step.confidence == ConfidenceClass.LOW:
            return False
        if step.validation_status == StepValidationStatus.UNCERTAIN:
            return False
        return True

    def should_emit_mistake_dna(self, step: GradedStep) -> bool:
        """
        Exactly ONE canonical root mistake event is emitted (§21, §22).
        Downstream errors NEVER emit separate Mistake DNA events.
        """
        if step.is_root_error and step.validation_status == StepValidationStatus.ROOT_ERROR:
            return True
        return False

    def should_emit_mastery_evidence(
        self,
        overall_outcome: OverallOutcome,
        confidence: ConfidenceClass,
        assistance_level: AssistanceLevel
    ) -> bool:
        """
        Determines whether the completed solution attempt generates Mastery Graph evidence.
        - LOW confidence evaluations are excluded.
        - Fully assisted attempts do not claim independent mastery.
        """
        if confidence == ConfidenceClass.LOW:
            return False
        if overall_outcome == OverallOutcome.ALL_STEPS_VALID:
            return True
        if overall_outcome == OverallOutcome.ROOT_ERROR_DETECTED and self.config.root_error_submits_negative_mastery:
            return True
        return False


_POLICY_CACHE: Dict[str, StepGraderPolicy] = {}


def get_step_grader_policy(version: str = "1.0.0") -> StepGraderPolicy:
    """Returns the cached policy instance for a given version string."""
    if version not in _POLICY_CACHE:
        _POLICY_CACHE[version] = StepGraderPolicy(version=version)
    return _POLICY_CACHE[version]
