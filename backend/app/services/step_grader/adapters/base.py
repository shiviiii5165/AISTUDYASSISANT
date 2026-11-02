"""
LearnByGenie — Feature 8: Domain Adapter Base Interface
========================================================
Subject-agnostic adapter contract. Domain logic lives strictly in adapters;
core StepGraderService orchestration remains subject-independent (§2, §40).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    ErrorType, GradedStep, StepType
)


class StepValidationResult(BaseModel):
    """Result of validating a single step through a domain adapter."""
    validation_status: StepValidationStatus = StepValidationStatus.VALID_STEP
    validator_type: ValidatorType = ValidatorType.DETERMINISTIC
    confidence: ConfidenceClass = ConfidenceClass.HIGH
    error_type: Optional[ErrorType] = None
    error_subtype: Optional[str] = None
    feedback: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepGraderAdapter(ABC):
    """
    Abstract adapter for domain-specific step validation.
    Core StepGraderService delegates step verification to registered adapters.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Name of the adapter (e.g. 'MathStepAdapter')."""
        pass

    @property
    @abstractmethod
    def supported_subjects(self) -> List[str]:
        """List of subjects this adapter handles."""
        pass

    @abstractmethod
    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        """Determines if this adapter can validate steps for this domain/problem."""
        pass

    @abstractmethod
    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        """Infers canonical StepType for a line in this domain."""
        pass

    @abstractmethod
    def validate_step(
        self,
        step_index: int,
        raw_text: str,
        prev_steps: List[GradedStep],
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StepValidationResult:
        """
        Validates whether this step is a valid, logical progression from previous steps.
        Does NOT alter other steps.
        """
        pass

    @abstractmethod
    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """
        Determines whether current_raw_text is a valid continuation of an earlier corrupted step.
        If TRUE: current step is a DOWNSTREAM_ERROR (consequence of earlier mistake),
                 NOT an independent root conceptual error (§8, §9).
        """
        pass
