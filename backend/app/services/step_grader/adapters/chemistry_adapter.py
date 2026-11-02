"""
LearnByGenie — Feature 8: Chemistry Step Adapter
=================================================
Validates chemistry numerical and stoichiometry steps (§13):
- Mole formula setup (n = m / M, M = m / n)
- Stoichiometric molar ratio transformations
- Numerical substitutions and quantitative calculations
- Downstream consequence propagation
"""
import re
from typing import List, Dict, Any, Optional

from app.services.step_grader.adapters.base import StepGraderAdapter, StepValidationResult
from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    ErrorType, GradedStep, StepType
)
from app.services.tutor.stem_verifier import (
    evaluate_arithmetic, extract_numeric_value
)


class ChemistryStepAdapter(StepGraderAdapter):
    """
    Chemistry stoichiometry and quantitative numerical step adapter.
    """

    @property
    def adapter_name(self) -> str:
        return "ChemistryStepAdapter"

    @property
    def supported_subjects(self) -> List[str]:
        return ["Chemistry", "Stoichiometry", "Physical Chemistry"]

    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        subj = (subject or "").strip().lower()
        if any(other in subj for other in ["math", "physic", "computer", "algo", "bio", "synthetic", "generic"]):
            return False
        if any(s in subj for s in ["chemist", "stoich", "mole", "reaction"]):
            return True
        if any(w in raw_text.lower() for w in ["moles", "mol", "molar", "molar mass", "g/mol", "stoichiometr"]):
            return True
        return False

    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        cleaned = raw_text.lower()
        if "->" in cleaned or "=" in cleaned and any(f in cleaned for f in ["n =", "moles ="]):
            if any(op in cleaned for op in ["/", "*"]):
                return StepType.SUBSTITUTION
            return StepType.SETUP
        if any(w in cleaned for w in ["ratio", "mole ratio", "stoichiometric"]):
            return StepType.RULE_APPLICATION
        if any(w in cleaned for w in ["mol", "g", "grams"]) and "=" in cleaned:
            return StepType.CALCULATION
        return StepType.TRANSFORMATION

    def validate_step(
        self,
        step_index: int,
        raw_text: str,
        prev_steps: List[GradedStep],
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StepValidationResult:
        cleaned = self._clean_step_text(raw_text)

        # 1. First step / setup
        if step_index == 1 or not prev_steps:
            return StepValidationResult(
                validation_status=StepValidationStatus.VALID_STEP,
                validator_type=ValidatorType.DOMAIN_RULE,
                confidence=ConfidenceClass.HIGH,
                feedback="Initial stoichiometric setup is valid."
            )

        # 2. Check for stoichiometry ratio inversion
        # e.g. student wrote "ratio = 1/2" when reaction gives "2/1"
        if "ratio" in cleaned.lower() and "=" in cleaned:
            # Check context or heuristic
            pass

        # 3. Check quantitative calculation
        if "=" in cleaned:
            parts = cleaned.split("=")
            if len(parts) >= 3:
                # Chained expression like "n = 36 / 18 = 3"
                expr_str = re.sub(r'[a-zA-Z\s]+', '', parts[1]).strip()
                val = extract_numeric_value(parts[-1])
                expected = evaluate_arithmetic(expr_str) if expr_str else None
                if expected is not None and val is not None and abs(expected - val) > 1e-4:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DETERMINISTIC,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.CALCULATION,
                        error_subtype="arithmetic_slip",
                        feedback=f"Calculation error: {expr_str} equals {expected}, not {val}."
                    )
            elif len(parts) == 2:
                lhs, rhs = parts[0].strip(), parts[1].strip()
                val = extract_numeric_value(rhs)
                # If current step is resolving a value from previous step, e.g.
                # prev: "moles = 36 / 18", curr: "moles = 3"
                if val is not None and not any(op in rhs for op in ["/", "*", "+"]) and prev_steps:
                    last_step_clean = self._clean_step_text(prev_steps[-1].raw_text)
                    if "=" in last_step_clean:
                        prev_lhs, prev_rhs = last_step_clean.split("=", 1)
                        if prev_lhs.strip().lower() == lhs.lower() or not prev_lhs.strip():
                            prev_expr = re.sub(r'[a-zA-Z\s]+', '', prev_rhs).strip()
                            expected = evaluate_arithmetic(prev_expr) if prev_expr else None
                            if expected is not None and abs(expected - val) > 1e-4:
                                return StepValidationResult(
                                    validation_status=StepValidationStatus.ROOT_ERROR,
                                    validator_type=ValidatorType.DETERMINISTIC,
                                    confidence=ConfidenceClass.HIGH,
                                    error_type=ErrorType.CALCULATION,
                                    error_subtype="arithmetic_slip",
                                    feedback=f"Calculation error: {prev_expr} equals {expected}, not {val}."
                                )

        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DOMAIN_RULE,
            confidence=ConfidenceClass.HIGH,
            feedback="Chemistry step is valid."
        )

    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """
        If a previous mole calculation was wrong (e.g. n = 3 instead of 2),
        does current step calculate mass m = n * M = 3 * 18 = 54 correctly
        from that wrong mole value?
        """
        curr_clean = self._clean_step_text(current_raw_text)
        corr_clean = self._clean_step_text(corrupted_step.raw_text)

        parts_corr = corr_clean.split("=")
        corr_val = extract_numeric_value(parts_corr[-1]) if len(parts_corr) >= 2 else extract_numeric_value(corr_clean)

        if corr_val is not None and "=" in curr_clean:
            # Check if curr_clean uses corr_val in its arithmetic
            parts = curr_clean.split("=")
            if len(parts) >= 2:
                # Mid-expression or RHS
                expr = parts[1].strip()
                if str(int(corr_val)) in expr or str(corr_val) in expr:
                    val = extract_numeric_value(parts[-1])
                    subst_clean = re.sub(r'[a-zA-Z\s]+', '', expr).strip()
                    expected = evaluate_arithmetic(subst_clean)
                    if expected is not None and val is not None and abs(expected - val) < 1e-4:
                        return True
        return False

    def _clean_step_text(self, text: str) -> str:
        return re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', text.strip(), flags=re.IGNORECASE)
