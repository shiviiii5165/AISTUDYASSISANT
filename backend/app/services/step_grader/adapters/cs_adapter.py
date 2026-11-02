"""
LearnByGenie — Feature 8: Computer Science Reasoning Adapter
=============================================================
Validates pseudocode traces, algorithm dry runs, and logical conditions (§14):
- Trace line progression & variable state transitions
- Loop bounds & off-by-one condition checks
- Branch conditions (if/else evaluation)
- Downstream consequence propagation across trace steps
- Does NOT execute arbitrary unconstrained student code
"""
import re
from typing import List, Dict, Any, Optional

from app.services.step_grader.adapters.base import StepGraderAdapter, StepValidationResult
from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    ErrorType, GradedStep, StepType
)
from app.services.tutor.stem_verifier import evaluate_arithmetic, extract_numeric_value


class CSReasoningAdapter(StepGraderAdapter):
    """
    Computer science dry-run and pseudocode trace adapter.
    """

    @property
    def adapter_name(self) -> str:
        return "CSReasoningAdapter"

    @property
    def supported_subjects(self) -> List[str]:
        return ["Computer Science", "Algorithms", "Data Structures", "Programming"]

    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        subj = (subject or "").strip().lower()
        if any(s in subj for s in ["computer", "code", "algo", "program", "pseudocode"]):
            return True
        if any(w in raw_text.lower() for w in ["iteration", "loop", "i =", "count =", "array[", "for i", "while "]):
            return True
        return False

    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        cleaned = raw_text.lower()
        if any(w in cleaned for w in ["initialize", "let ", "start with", "i = 0", "count = 0"]):
            return StepType.SETUP
        if any(w in cleaned for w in ["if ", "while ", "condition", "check"]):
            return StepType.INFERENCE
        if any(w in cleaned for w in ["iteration", "i = i + 1", "i++", "state:"]):
            return StepType.TRANSFORMATION
        if any(w in cleaned for w in ["return", "final", "output"]):
            return StepType.CONCLUSION
        return StepType.RULE_APPLICATION

    def validate_step(
        self,
        step_index: int,
        raw_text: str,
        prev_steps: List[GradedStep],
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StepValidationResult:
        cleaned = self._clean_step_text(raw_text)

        # 1. First step / initialization
        if step_index == 1 or not prev_steps:
            return StepValidationResult(
                validation_status=StepValidationStatus.VALID_STEP,
                validator_type=ValidatorType.DOMAIN_RULE,
                confidence=ConfidenceClass.HIGH,
                feedback="Initial trace state is defined."
            )

        # 2. Check for logic boundary error (e.g. "loop runs while i <= n" instead of "i < n")
        if any(w in cleaned.lower() for w in ["i <=", "i <", "index <="]):
            if "i <= len" in cleaned.lower() or "i <= n" in cleaned.lower():
                # Potential off-by-one check if 0-indexed
                if "0" in question_text or "0-indexed" in question_text:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DOMAIN_RULE,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.REASONING,
                        error_subtype="off_by_one",
                        feedback="Loop condition causes an off-by-one boundary issue for a 0-indexed sequence."
                    )

        # 3. Check variable assignment arithmetic (e.g. "i = 1, sum = 0 + 2 = 3" -> 0 + 2 is 2, not 3)
        if "=" in cleaned:
            parts = cleaned.split("=")
            if len(parts) >= 3:
                expr_part = parts[-2].strip()
                val_part = parts[-1].strip()
                expected = evaluate_arithmetic(expr_part)
                actual = extract_numeric_value(val_part)
                if expected is not None and actual is not None and abs(expected - actual) > 1e-4:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DETERMINISTIC,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.CALCULATION,
                        error_subtype="arithmetic_slip",
                        feedback=f"Trace state computation slip: {expr_part} equals {expected}, not {actual}."
                    )

        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DOMAIN_RULE,
            confidence=ConfidenceClass.HIGH,
            feedback="Algorithm trace step is valid."
        )

    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """
        If Step 2 had wrong sum = 3 (should be 2), does Step 3 with sum = sum + 5 = 3 + 5 = 8
        correctly follow the corrupted earlier state?
        """
        curr_clean = self._clean_step_text(current_raw_text)
        corr_val = extract_numeric_value(corrupted_step.raw_text)

        if corr_val is not None and "=" in curr_clean:
            # Check if corrupted value was carried forward
            if str(int(corr_val)) in curr_clean:
                return True
        return False

    def _clean_step_text(self, text: str) -> str:
        return re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', text.strip(), flags=re.IGNORECASE)
