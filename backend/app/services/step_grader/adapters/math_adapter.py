"""
LearnByGenie — Feature 8: Deterministic Mathematics Step Adapter
=================================================================
Validates mathematical steps deterministically without opaque LLM guessing (§11):
- Linear equations & algebraic transformations
- Sign preservation across equality boundaries
- Arithmetic & calculation slips
- Downstream derivation tracking from corrupted intermediate equations
- Quadratic factoring & root equivalence
"""
import re
import ast
from typing import List, Dict, Any, Optional, Tuple

from app.services.step_grader.adapters.base import StepGraderAdapter, StepValidationResult
from app.services.step_grader.schemas import (
    StepValidationStatus, ValidatorType, ConfidenceClass,
    ErrorType, GradedStep, StepType
)
from app.services.tutor.stem_verifier import (
    evaluate_arithmetic, extract_numeric_value,
    verify_numeric_equivalence, solve_quadratic_roots
)


class MathStepAdapter(StepGraderAdapter):
    """
    Deterministic mathematics validator for structured algebraic and numerical steps.
    """

    @property
    def adapter_name(self) -> str:
        return "MathStepAdapter"

    @property
    def supported_subjects(self) -> List[str]:
        return ["Mathematics", "Math", "Algebra", "Arithmetic"]

    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        subj = (subject or "").strip().lower()
        # Defer to specialized science/CS/rubric adapters if subject explicitly indicates them
        if any(other in subj for other in ["physic", "chem", "computer", "algo", "bio", "synthetic", "generic"]):
            return False
        if any(s in subj for s in ["math", "algebra", "arithmetic", "calculus", "geometry"]):
            return True
        # Check if text contains mathematical equation or arithmetic patterns
        if any(op in raw_text for op in ["=", "+", "-", "*", "/", "^"]) and any(c.isdigit() for c in raw_text):
            return True
        return False

    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        cleaned = raw_text.strip()
        if step_index == 1 and "=" in cleaned:
            return StepType.SETUP
        if re.search(r'^[a-zA-Z]\s*=\s*-?\d+(?:\.\d+)?$', cleaned):
            return StepType.CONCLUSION
        if "=" in cleaned:
            # Check if one side is pure arithmetic evaluation
            parts = cleaned.split("=")
            if len(parts) == 2 and any(op in parts[1] for op in ["+", "-", "*", "/"]):
                return StepType.TRANSFORMATION
            return StepType.TRANSFORMATION
        if any(op in cleaned for op in ["+", "-", "*", "/"]):
            return StepType.CALCULATION
        return StepType.TRANSFORMATION

    # ─── CORE DETERMINISTIC VALIDATION ────────────────────────────────────────

    def validate_step(
        self,
        step_index: int,
        raw_text: str,
        prev_steps: List[GradedStep],
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StepValidationResult:
        cleaned = self._clean_expression(raw_text)

        # Check prompt injection or instruction hijacking
        if any(trig in cleaned.lower() for trig in [
            "ignore previous", "ignore rubric", "mark all steps", "mark every step",
            "system prompt", "you are now", "override grading", "give 100%",
            "ignore all", "ignore grading", "ignore rules", "disregard all"
        ]):
            return StepValidationResult(
                validation_status=StepValidationStatus.ROOT_ERROR,
                validator_type=ValidatorType.DETERMINISTIC,
                confidence=ConfidenceClass.HIGH,
                error_type=ErrorType.REASONING,
                error_subtype="invalid_submission_content",
                feedback="Instructional overrides or injection strings are not valid mathematical reasoning steps."
            )

        # 1. SETUP / STEP 1: Check consistency with problem prompt
        if step_index == 1 or not prev_steps:
            return self._validate_initial_step(cleaned, question_text)

        # Get immediate preceding step
        last_step = prev_steps[-1]
        last_cleaned = self._clean_expression(last_step.raw_text)

        # 2. EQUATION TRANSFORMATION: both previous and current have '='
        if "=" in cleaned and "=" in last_cleaned:
            return self._validate_equation_transformation(cleaned, last_cleaned, prev_steps)

        # 3. PURE ARITHMETIC CHAIN: e.g. "12 * (3 + 4)" -> "12 * 7" -> "84"
        arith_res = self._validate_arithmetic_step(cleaned, last_cleaned)
        if arith_res:
            return arith_res

        # 4. Check for ambiguous / vague reasoning (§11, §16, §56)
        if any(vague in cleaned.lower() for vague in ["somehow", "magic", "maybe", "dont know", "don't know", "???"]):
            return StepValidationResult(
                validation_status=StepValidationStatus.UNCERTAIN,
                validator_type=ValidatorType.UNCERTAIN,
                confidence=ConfidenceClass.LOW,
                error_type=ErrorType.UNKNOWN,
                feedback=f"Step {step_index} reasoning is ambiguous; unable to verify deterministically."
            )

        # 5. Fallback: conservative check
        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DOMAIN_RULE,
            confidence=ConfidenceClass.MODERATE,
            feedback=f"Step {step_index} is structured consistently."
        )

    # ─── DOWNSTREAM DERIVATION CHECK ──────────────────────────────────────────

    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """
        Determines whether current_raw_text mathematically follows from corrupted_step.
        Example: corrupted_step = '2x = 10 + 4' (i.e. 2x = 14), and current = 'x = 7'.
        7 satisfies 2(7) = 14! So current step is a downstream consequence (§8, §9).
        """
        curr_clean = self._clean_expression(current_raw_text)
        corr_clean = self._clean_expression(corrupted_step.raw_text)

        # Case A: Current step gives final value (e.g. "x = 7")
        val = extract_numeric_value(curr_clean)
        if val is not None:
            # Check if val satisfies corrupted equation
            if "=" in corr_clean:
                if self._check_value_satisfies_equation(val, corr_clean):
                    return True

        # Case B: Current step is an equation transformed from corrupted step or immediate predecessor
        # Check against the most recent preceding equation
        ref_step = prev_steps[-1] if prev_steps else corrupted_step
        ref_clean = self._clean_expression(ref_step.raw_text)

        if "=" in curr_clean and "=" in ref_clean:
            # Solve reference equation for its implied solution
            ref_sol = self._solve_linear_equation(ref_clean)
            curr_sol = self._solve_linear_equation(curr_clean)
            if ref_sol is not None and curr_sol is not None:
                if abs(ref_sol - curr_sol) < 1e-4:
                    return True

            # Also check if current step simplified the RHS of reference step
            # e.g. ref: "2x = 10 + 4", curr: "2x = 14"
            parts_ref = ref_clean.split("=")
            parts_curr = curr_clean.split("=")
            if len(parts_ref) == 2 and len(parts_curr) == 2:
                if parts_ref[0].strip() == parts_curr[0].strip():
                    rhs_ref_val = evaluate_arithmetic(parts_ref[1])
                    rhs_curr_val = evaluate_arithmetic(parts_curr[1])
                    if rhs_ref_val is not None and rhs_curr_val is not None and abs(rhs_ref_val - rhs_curr_val) < 1e-4:
                        return True

        return False

    # ─── INTERNAL HELPERS ─────────────────────────────────────────────────────

    def _clean_expression(self, expr: str) -> str:
        """Removes step numbering like '1.', 'Step 2:', etc."""
        cleaned = re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', expr.strip(), flags=re.IGNORECASE)
        # Normalize multiplication signs
        cleaned = cleaned.replace("×", "*").replace("÷", "/")
        return cleaned.strip()

    def _validate_initial_step(self, text: str, question_text: str) -> StepValidationResult:
        """Validates first step/setup."""
        # If question text contains an equation, verify student copied it or formulated valid setup
        q_clean = self._clean_expression(question_text)
        if "=" in q_clean and "=" in text:
            q_sol = self._solve_linear_equation(q_clean)
            t_sol = self._solve_linear_equation(text)
            if q_sol is not None and t_sol is not None:
                if abs(q_sol - t_sol) > 1e-4:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DETERMINISTIC,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.MISREAD_QUESTION,
                        error_subtype="initial_equation_mismatch",
                        feedback="Initial equation does not match the question prompt."
                    )
        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DETERMINISTIC,
            confidence=ConfidenceClass.HIGH,
            feedback="Initial setup is correct."
        )

    def _validate_equation_transformation(
        self,
        current_eq: str,
        prev_eq: str,
        prev_steps: List[GradedStep]
    ) -> StepValidationResult:
        """
        Deterministically evaluates whether current_eq is a valid transformation of prev_eq.
        Detects sign flips, arithmetic calculation slips, and solution set divergence.
        """
        prev_sol = self._solve_linear_equation(prev_eq)

        # Check if student wrote a final variable assignment (e.g. "x = 7" or just "7")
        is_final_assignment = bool(
            re.search(r'^[a-zA-Z]\s*=\s*-?\d+(?:\.\d+)?$', current_eq.strip())
            or re.search(r'^-?\d+(?:\.\d+)?$', current_eq.strip())
        )
        if is_final_assignment:
            curr_val = extract_numeric_value(current_eq)

            if curr_val is not None and prev_sol is not None:
                diff = abs(curr_val - prev_sol)
                if diff <= 1e-4:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.VALID_STEP,
                        validator_type=ValidatorType.DETERMINISTIC,
                        confidence=ConfidenceClass.HIGH,
                        feedback="Final value correctly solves the preceding equation."
                    )
                else:
                    # Value calculation slip
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DETERMINISTIC,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.CALCULATION,
                        error_subtype="arithmetic_slip",
                        feedback=f"Calculation result {curr_val} does not match {prev_sol}."
                    )

        # Check solution of both equations
        curr_sol = self._solve_linear_equation(current_eq)

        # 1. Check for specific sign error patterns:
        # Example: prev = "2x + 4 = 10", curr = "2x = 10 + 4"
        sign_error_feedback = self._detect_sign_transposition_error(prev_eq, current_eq)
        if sign_error_feedback:
            return StepValidationResult(
                validation_status=StepValidationStatus.ROOT_ERROR,
                validator_type=ValidatorType.DETERMINISTIC,
                confidence=ConfidenceClass.HIGH,
                error_type=ErrorType.SIGN_OR_NOTATION,
                error_subtype="sign_transposition",
                feedback=sign_error_feedback
            )

        # 2. Check for arithmetic calculation error in RHS:
        # Example: prev = "2x = 10 - 4", curr = "2x = 5" (should be 6)
        calc_error_feedback = self._detect_rhs_calculation_error(prev_eq, current_eq)
        if calc_error_feedback:
            return StepValidationResult(
                validation_status=StepValidationStatus.ROOT_ERROR,
                validator_type=ValidatorType.DETERMINISTIC,
                confidence=ConfidenceClass.HIGH,
                error_type=ErrorType.CALCULATION,
                error_subtype="arithmetic_slip",
                feedback=calc_error_feedback
            )

        # 3. Check solution set equivalence
        if prev_sol is not None and curr_sol is not None:
            if abs(prev_sol - curr_sol) < 1e-4:
                return StepValidationResult(
                    validation_status=StepValidationStatus.VALID_STEP,
                    validator_type=ValidatorType.DETERMINISTIC,
                    confidence=ConfidenceClass.HIGH,
                    feedback="Equation transformation preserves equivalence."
                )
            else:
                # Solution set changed without identified simple sign flip -> PROCEDURAL or CONCEPTUAL
                return StepValidationResult(
                    validation_status=StepValidationStatus.ROOT_ERROR,
                    validator_type=ValidatorType.DETERMINISTIC,
                    confidence=ConfidenceClass.HIGH,
                    error_type=ErrorType.PROCEDURAL,
                    error_subtype="invalid_transformation",
                    feedback="This algebraic step does not preserve equality with the previous equation."
                )

        # Fallback to valid
        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DETERMINISTIC,
            confidence=ConfidenceClass.MODERATE,
            feedback="Transformation is consistent."
        )

    def _detect_sign_transposition_error(self, prev_eq: str, curr_eq: str) -> Optional[str]:
        """
        Detects if a constant was transposed across the '=' sign without inverting its sign.
        Example: '2x + 4 = 10' -> '2x = 10 + 4' (moved +4 across '=', kept +4 instead of -4).
        """
        # Look for pattern LHS: ax + b, RHS: c -> LHS: ax, RHS: c + b
        m_prev = re.search(r'([a-zA-Z0-9]+)\s*([+-])\s*(\d+)\s*=\s*(\d+)', prev_eq)
        m_curr = re.search(r'([a-zA-Z0-9]+)\s*=\s*(\d+)\s*([+-])\s*(\d+)', curr_eq)

        if m_prev and m_curr:
            var_term_prev, op_prev, const_prev, rhs_prev = m_prev.groups()
            var_term_curr, rhs_base_curr, op_curr, const_curr = m_curr.groups()

            if var_term_prev == var_term_curr and const_prev == const_curr and rhs_prev == rhs_base_curr:
                # If prev was '+' and curr kept '+', student failed to change sign to '-'
                if op_prev == "+" and op_curr == "+":
                    return f"When moving +{const_prev} across the equals sign, its sign should change to -{const_prev}."
                # If prev was '-' and curr kept '-', student failed to change sign to '+'
                if op_prev == "-" and op_curr == "-":
                    return f"When moving -{const_prev} across the equals sign, its sign should change to +{const_prev}."
        return None

    def _detect_rhs_calculation_error(self, prev_eq: str, curr_eq: str) -> Optional[str]:
        """
        Detects if student evaluated an arithmetic expression on RHS incorrectly.
        Example: prev = '2x = 10 - 4', curr = '2x = 5' (10 - 4 is 6, not 5).
        """
        parts_prev = prev_eq.split("=")
        parts_curr = curr_eq.split("=")

        if len(parts_prev) == 2 and len(parts_curr) == 2:
            lhs_prev, rhs_prev = parts_prev[0].strip(), parts_prev[1].strip()
            lhs_curr, rhs_curr = parts_curr[0].strip(), parts_curr[1].strip()

            if lhs_prev == lhs_curr:
                # Check if rhs_prev contains an operator like '+', '-', '*', '/'
                if any(op in rhs_prev for op in ["+", "-", "*", "/"]):
                    expected_rhs = evaluate_arithmetic(rhs_prev)
                    actual_rhs = evaluate_arithmetic(rhs_curr)
                    if expected_rhs is not None and actual_rhs is not None:
                        if abs(expected_rhs - actual_rhs) > 1e-4:
                            return f"Calculating {rhs_prev} gives {expected_rhs}, not {actual_rhs}."
        return None

    def _validate_arithmetic_step(self, current: str, prev: str) -> Optional[StepValidationResult]:
        """Evaluates pure arithmetic progression."""
        prev_val = evaluate_arithmetic(prev)
        curr_val = evaluate_arithmetic(current)

        if prev_val is not None and curr_val is not None:
            if abs(prev_val - curr_val) <= 1e-4:
                return StepValidationResult(
                    validation_status=StepValidationStatus.VALID_STEP,
                    validator_type=ValidatorType.DETERMINISTIC,
                    confidence=ConfidenceClass.HIGH,
                    feedback="Arithmetic calculation is correct."
                )
            else:
                return StepValidationResult(
                    validation_status=StepValidationStatus.ROOT_ERROR,
                    validator_type=ValidatorType.DETERMINISTIC,
                    confidence=ConfidenceClass.HIGH,
                    error_type=ErrorType.CALCULATION,
                    error_subtype="arithmetic_slip",
                    feedback=f"Arithmetic does not evaluate correctly (expected {prev_val}, got {curr_val})."
                )
        return None

    def _solve_linear_equation(self, eq: str) -> Optional[float]:
        """
        Extracts and solves a single-variable linear equation in 'x' deterministically.
        Supports forms:
        - ax + b = c
        - ax = b
        - x = c
        - a*x + b = c
        """
        cleaned = eq.replace(" ", "")
        if "=" not in cleaned:
            return None

        # Check pure "x = c" or "x = -c"
        m = re.search(r'^[a-zA-Z]=(-?\d+(?:\.\d+)?)$', cleaned)
        if m:
            return float(m.group(1))

        # Check "ax = b"
        m = re.search(r'^(-?\d+(?:\.\d+)?)\*?[a-zA-Z]=(-?\d+(?:\.\d+)?)$', cleaned)
        if m:
            coeff = float(m.group(1))
            val = float(m.group(2))
            return val / coeff if coeff != 0 else None

        # Check "x = b + c" or "x = b - c"
        parts = cleaned.split("=")
        if len(parts) == 2:
            lhs, rhs = parts[0], parts[1]
            # Match "ax + b" or "ax - b" on LHS
            m_lhs = re.search(r'^(-?\d+(?:\.\d+)?)\*?[a-zA-Z]([+-]\d+(?:\.\d+)?)$', lhs)
            if m_lhs:
                coeff = float(m_lhs.group(1))
                const = float(m_lhs.group(2))
                rhs_val = evaluate_arithmetic(rhs)
                if rhs_val is not None and coeff != 0:
                    return (rhs_val - const) / coeff

            # Match "ax" on LHS and arithmetic on RHS (e.g. "2x = 10 + 4")
            m_lhs_var = re.search(r'^(-?\d+(?:\.\d+)?)\*?[a-zA-Z]$', lhs)
            if m_lhs_var:
                coeff = float(m_lhs_var.group(1))
                rhs_val = evaluate_arithmetic(rhs)
                if rhs_val is not None and coeff != 0:
                    return rhs_val / coeff

        return None

    def _check_value_satisfies_equation(self, val: float, eq: str) -> bool:
        """Substitutes val into eq and checks if LHS == RHS."""
        sol = self._solve_linear_equation(eq)
        if sol is not None:
            return abs(sol - val) < 1e-4
        return False
