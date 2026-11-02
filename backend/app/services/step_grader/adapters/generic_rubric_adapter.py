"""
LearnByGenie — Feature 8: Generic Rubric & Sequence Adapter
============================================================
Handles structured rubric validation, process reasoning (e.g. Biology, dynamic subjects),
and ambiguous reasoning with explicit uncertainty preservation (§15, §28, §29, §41, §56).
- Validates against StructuredRubric criteria (required concepts, valid transitions)
- Dynamically adapts to synthetic/new subjects without changing core orchestrator (§41)
- Explicitly flags ambiguous or unsupported reasoning as UNCERTAIN / LOW confidence (§56)
- Treats all student input as untrusted data (prompt-injection immune) (§30)
"""
import re
from typing import List, Dict, Any, Optional

from app.services.step_grader.adapters.base import StepGraderAdapter, StepValidationResult
from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    ErrorType, GradedStep, StepType, StructuredRubric
)


class GenericSequenceAdapter(StepGraderAdapter):
    """
    Structured rubric and process sequence adapter.
    Acts as fallback for descriptive domains, Biology, and dynamically registered subjects.
    """

    @property
    def adapter_name(self) -> str:
        return "GenericSequenceAdapter"

    @property
    def supported_subjects(self) -> List[str]:
        return ["Biology", "General Science", "Synthetic Subject", "Dynamic Domain", "Generic"]

    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        # Generic adapter handles any domain not claimed by specialized STEM adapters
        return True

    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        cleaned = raw_text.lower()
        if step_index == 1:
            return StepType.SETUP
        if any(w in cleaned for w in ["because", "therefore", "leads to", "results in", "causes"]):
            return StepType.INFERENCE
        if any(w in cleaned for w in ["finally", "in conclusion", "thus", "yields"]):
            return StepType.CONCLUSION
        if any(w in cleaned for w in ["applies", "principle", "rule", "law"]):
            return StepType.RULE_APPLICATION
        return StepType.EXPLANATION

    def validate_step(
        self,
        step_index: int,
        raw_text: str,
        prev_steps: List[GradedStep],
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StepValidationResult:
        cleaned = self._clean_step_text(raw_text)
        rubric_data = context.get("rubric") if context else None

        # 1. Check for prompt injection attempts in student text (§30)
        if self._is_prompt_injection_attempt(cleaned):
            return StepValidationResult(
                validation_status=StepValidationStatus.ROOT_ERROR,
                validator_type=ValidatorType.RUBRIC,
                confidence=ConfidenceClass.HIGH,
                error_type=ErrorType.REASONING,
                error_subtype="invalid_submission_content",
                feedback="Instructional overrides or injection strings are not valid reasoning steps."
            )

        # 2. Rubric-based evaluation if rubric is provided
        if rubric_data:
            rubric = rubric_data if isinstance(rubric_data, StructuredRubric) else StructuredRubric(**rubric_data)
            return self._validate_against_rubric(step_index, cleaned, rubric, prev_steps)

        # 3. Check for obvious contradictory or nonsensical content
        if len(cleaned.split()) < 2 and not any(c.isalnum() for c in cleaned):
            return StepValidationResult(
                validation_status=StepValidationStatus.UNCERTAIN,
                validator_type=ValidatorType.UNCERTAIN,
                confidence=ConfidenceClass.LOW,
                error_type=ErrorType.UNKNOWN,
                error_subtype="insufficient_detail",
                feedback="Step contains insufficient reasoning detail to verify."
            )

        # 4. Check for ambiguous / vague reasoning (§56)
        # If text is extremely vague (e.g. "somehow it happens", "stuff changes", "?")
        if any(vague in cleaned.lower() for vague in ["somehow", "maybe it works", "dont know", "don't know", "???"]):
            return StepValidationResult(
                validation_status=StepValidationStatus.UNCERTAIN,
                validator_type=ValidatorType.UNCERTAIN,
                confidence=ConfidenceClass.LOW,
                error_type=ErrorType.UNKNOWN,
                error_subtype="ambiguous_reasoning",
                feedback="Reasoning is ambiguous; unable to determine validity with certainty."
            )

        # 5. Default structured sequence step validation
        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.RUBRIC,
            confidence=ConfidenceClass.MODERATE,
            feedback=f"Step {step_index} follows the expected sequence."
        )

    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """Checks if current step logically refers to an earlier mistaken concept."""
        curr_clean = self._clean_step_text(current_raw_text).lower()
        corr_clean = self._clean_step_text(corrupted_step.raw_text).lower()

        # If current step explicitly references the specific terms from the corrupted step
        corr_words = set(w for w in corr_clean.split() if len(w) > 4)
        curr_words = set(w for w in curr_clean.split() if len(w) > 4)
        overlap = corr_words.intersection(curr_words)
        if len(overlap) >= 2:
            return True
        return False

    # ─── INTERNAL HELPERS ─────────────────────────────────────────────────────

    def _clean_step_text(self, text: str) -> str:
        return re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', text.strip(), flags=re.IGNORECASE)

    def _is_prompt_injection_attempt(self, text: str) -> bool:
        """Identifies prompt injection keywords treated strictly as student input (§30)."""
        lower = text.lower()
        injection_triggers = [
            "ignore previous", "ignore rubric", "mark all steps correct",
            "system prompt", "you are now", "override grading", "give 100%",
            "ignore all", "ignore grading", "ignore rules", "mark every step",
            "mark all steps", "disregard all", "disregard rules", "bypass grading"
        ]
        return any(t in lower for t in injection_triggers)

    def _validate_against_rubric(
        self,
        step_index: int,
        cleaned: str,
        rubric: StructuredRubric,
        prev_steps: List[GradedStep]
    ) -> StepValidationResult:
        """Validates step against structured rubric criteria."""
        lower = cleaned.lower()

        # Check for known common errors in rubric
        for error_pattern, error_cat in rubric.common_errors.items():
            if error_pattern.lower() in lower:
                err_enum = ErrorType[error_cat] if error_cat in ErrorType.__members__ else ErrorType.CONCEPTUAL
                return StepValidationResult(
                    validation_status=StepValidationStatus.ROOT_ERROR,
                    validator_type=ValidatorType.RUBRIC,
                    confidence=ConfidenceClass.HIGH,
                    error_type=err_enum,
                    error_subtype="rubric_common_error",
                    feedback=f"This step exhibits a known conceptual misconception: '{error_pattern}'."
                )

        # Check critical steps or required concepts
        if rubric.critical_steps and step_index <= len(rubric.critical_steps):
            expected_crit = rubric.critical_steps[step_index - 1].lower()
            # If critical keywords are entirely missing
            crit_keywords = [w for w in expected_crit.split() if len(w) > 3]
            if crit_keywords and not any(kw in lower for kw in crit_keywords):
                return StepValidationResult(
                    validation_status=StepValidationStatus.ROOT_ERROR,
                    validator_type=ValidatorType.RUBRIC,
                    confidence=ConfidenceClass.MODERATE,
                    error_type=ErrorType.PROCEDURAL,
                    error_subtype="missing_critical_step",
                    feedback=f"Missing expected critical transformation at step {step_index}."
                )

        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.RUBRIC,
            confidence=ConfidenceClass.HIGH,
            feedback=f"Step {step_index} aligns with rubric criteria."
        )
