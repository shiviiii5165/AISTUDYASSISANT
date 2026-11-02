"""
LearnByGenie — Feature 8: Physics Step Adapter
===============================================
Validates physics numerical steps (§12, §54):
- Formula identification & selection (e.g. F = m * a, v = u + a * t)
- Known variable substitution
- Deterministic unit consistency verification (N, J, W, m/s, m/s^2, kg, s, etc.)
- Numeric arithmetic progression & downstream consequence tracking
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

# Standard physics variable to unit associations
STANDARD_PHYSICS_UNITS = {
    "force": ["n", "newton", "newtons"],
    "f": ["n", "newton", "newtons"],
    "energy": ["j", "joule", "joules"],
    "work": ["j", "joule", "joules"],
    "w": ["j", "joule", "joules"],
    "power": ["w", "watt", "watts"],
    "p": ["w", "watt", "watts"],
    "velocity": ["m/s", "km/h", "meters/second"],
    "v": ["m/s", "km/h", "meters/second"],
    "acceleration": ["m/s^2", "m/s2"],
    "a": ["m/s^2", "m/s2"],
    "mass": ["kg", "g", "kilogram", "grams"],
    "m": ["kg", "g", "kilogram", "grams"],
    "time": ["s", "sec", "seconds"],
    "t": ["s", "sec", "seconds"],
    "distance": ["m", "meter", "meters", "km"],
    "d": ["m", "meter", "meters", "km"],
    "s_dist": ["m", "meter", "meters", "km"],
}

KNOWN_PHYSICS_FORMULAS = [
    r'f\s*=\s*m\s*\*?\s*a',
    r'v\s*=\s*u\s*\+\s*a\s*\*?\s*t',
    r's\s*=\s*u\s*\*?\s*t\s*\+\s*0?\.?5\s*\*?\s*a\s*\*?\s*t\^?2',
    r'w\s*=\s*f\s*\*?\s*d',
    r'p\s*=\s*w\s*/\s*t',
    r'k\s*=\s*0?\.?5\s*\*?\s*m\s*\*?\s*v\^?2',
]


class PhysicsStepAdapter(StepGraderAdapter):
    """
    Physics numerical and formula validator.
    """

    @property
    def adapter_name(self) -> str:
        return "PhysicsStepAdapter"

    @property
    def supported_subjects(self) -> List[str]:
        return ["Physics", "Mechanics", "Electrodynamics", "Thermodynamics"]

    def can_handle(self, subject: str, skill_id: Optional[str], raw_text: str) -> bool:
        subj = (subject or "").strip().lower()
        if any(other in subj for other in ["math", "chem", "computer", "algo", "bio", "synthetic", "generic"]):
            return False
        if any(s in subj for s in ["physic", "mechanic", "kinematic", "dynamic"]):
            return True
        # Check for physics units or formulas
        if any(unit in raw_text.lower() for unit in [" m/s", " m/s^2", " newton", " joule", " watts", " kg"]):
            return True
        return False

    def infer_step_type(self, raw_text: str, step_index: int) -> StepType:
        cleaned = raw_text.lower().strip()
        if step_index == 1 and any(re.search(f, cleaned) for f in KNOWN_PHYSICS_FORMULAS):
            return StepType.RULE_APPLICATION
        if "=" in cleaned and any(var in cleaned for var in ["m =", "a =", "v =", "t =", "f ="]):
            # Substitution or setup
            if any(op in cleaned for op in ["*", "/", "+", "-"]):
                return StepType.SUBSTITUTION
            return StepType.SETUP
        if any(u in cleaned for u in ["n", "j", "m/s", "kg"]):
            return StepType.CONCLUSION
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

        # 1. First step: formula selection or known variables setup
        if step_index == 1 or not prev_steps:
            return self._validate_initial_physics_step(cleaned, question_text)

        # 2. Check for Unit Error (§54)
        unit_res = self._check_unit_consistency(cleaned)
        if unit_res is not None:
            return unit_res

        # 3. Check for substitution and calculation
        calc_res = self._check_physics_calculation(cleaned, prev_steps)
        if calc_res is not None:
            return calc_res

        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DOMAIN_RULE,
            confidence=ConfidenceClass.HIGH,
            feedback="Physics step is valid and consistent."
        )

    def check_downstream_derivation(
        self,
        corrupted_step: GradedStep,
        current_raw_text: str,
        prev_steps: List[GradedStep]
    ) -> bool:
        """
        If student used a wrong substituted value earlier, does the current step
        correctly compute the arithmetic from that corrupted value?
        """
        curr_clean = self._clean_step_text(current_raw_text)
        corr_clean = self._clean_step_text(corrupted_step.raw_text)

        curr_val = extract_numeric_value(curr_clean)
        # Check direct arithmetic derivation from corrupted step or any prior step
        steps_to_check = [corrupted_step] + [p for p in prev_steps if p.step_index >= corrupted_step.step_index]
        for step in steps_to_check:
            clean_s = self._clean_step_text(step.raw_text)
            if "=" in clean_s:
                parts = clean_s.split("=")
                rhs_expr = parts[1].strip()
                rhs_clean = re.sub(r'[a-zA-Z]+', '', rhs_expr).strip()
                rhs_val = evaluate_arithmetic(rhs_clean)
                if rhs_val is not None and curr_val is not None and abs(rhs_val - curr_val) < 1e-4:
                    return True

        # Check if current step is a numeric substitution into the corrupted formula
        if ("/" in corr_clean and "/" in curr_clean) or ("*" in corr_clean and "*" in curr_clean) or ("+" in corr_clean and "+" in curr_clean) or ("-" in corr_clean and "-" in curr_clean):
            return True

        return False

    # ─── INTERNAL HELPERS ─────────────────────────────────────────────────────

    def _clean_step_text(self, text: str) -> str:
        return re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', text.strip(), flags=re.IGNORECASE)

    def _validate_initial_physics_step(self, text: str, question_text: str) -> StepValidationResult:
        """Validates first formula or given values."""
        cleaned = text.lower().strip()
        # If it's a formula definition (contains variables on both sides)
        if "=" in cleaned:
            # Check for known incorrect formula variants for Force / Newton's 2nd law
            if any(term in question_text.lower() for term in ["force", "mass", "acceleration"]):
                if re.search(r'f\s*=\s*m\s*/\s*a', cleaned) or re.search(r'f\s*=\s*a\s*/\s*m', cleaned) or re.search(r'f\s*=\s*m\s*\+\s*a', cleaned):
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DOMAIN_RULE,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.FORMULA_RECALL,
                        error_subtype="incorrect_formula",
                        feedback="Incorrect formula selection: Force is defined as F = m * a, not F = m / a."
                    )
                if any(re.search(f, cleaned) for f in KNOWN_PHYSICS_FORMULAS):
                    return StepValidationResult(
                        validation_status=StepValidationStatus.VALID_STEP,
                        validator_type=ValidatorType.DOMAIN_RULE,
                        confidence=ConfidenceClass.HIGH,
                        feedback="Initial formula is correct."
                    )
        return StepValidationResult(
            validation_status=StepValidationStatus.VALID_STEP,
            validator_type=ValidatorType.DOMAIN_RULE,
            confidence=ConfidenceClass.HIGH,
            feedback="Initial formula/setup is correct."
        )

    def _check_unit_consistency(self, text: str) -> Optional[StepValidationResult]:
        """
        Checks whether variable matches standard SI unit.
        Example: 'F = 10 J' -> Error: Force is measured in Newtons (N), not Joules (J).
        """
        # Ensure unit starts with an alphabetic character so arithmetic slashes like '/ 5' are not captured as units
        m = re.search(r'([a-zA-Z]+)\s*=\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z][a-zA-Z0-9/^\^2]*)', text)
        if m:
            var, val, unit = m.group(1).lower(), m.group(2), m.group(3).lower()
            if var in STANDARD_PHYSICS_UNITS:
                valid_units = STANDARD_PHYSICS_UNITS[var]
                if unit not in valid_units:
                    return StepValidationResult(
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=ValidatorType.DOMAIN_RULE,
                        confidence=ConfidenceClass.HIGH,
                        error_type=ErrorType.UNIT_OR_DIMENSION,
                        error_subtype="unit_mismatch",
                        feedback=f"Unit mismatch for {var.upper()}: expected {valid_units[0].upper()}, but got {unit.upper()}."
                    )
        return None

    def _check_physics_calculation(self, current: str, prev_steps: List[GradedStep]) -> Optional[StepValidationResult]:
        """Checks arithmetic progression within physics calculations."""
        # e.g. "F = 2 * 5 = 10 N"
        if "=" in current:
            parts = current.split("=")
            if len(parts) >= 2:
                # If there are 3 parts, e.g. "F = 2 * 5 = 10 N"
                if len(parts) == 3:
                    subst = re.sub(r'[a-zA-Z/]+', '', parts[1]).strip()
                    res_val = extract_numeric_value(parts[2])
                    expected = evaluate_arithmetic(subst)
                    if expected is not None and res_val is not None:
                        if abs(expected - res_val) > 1e-4:
                            return StepValidationResult(
                                validation_status=StepValidationStatus.ROOT_ERROR,
                                validator_type=ValidatorType.DETERMINISTIC,
                                confidence=ConfidenceClass.HIGH,
                                error_type=ErrorType.CALCULATION,
                                error_subtype="arithmetic_slip",
                                feedback=f"Calculation error: {subst} evaluates to {expected}, not {res_val}."
                            )
        return None
