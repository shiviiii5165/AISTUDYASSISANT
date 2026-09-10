"""
Factual & Formula Validator
===========================
Executes deterministic mathematical, formulaic, and physical consistency audits.
Validates arithmetic equations, answers to numerical practice questions,
and standard scientific formula definitions without relying on probabilistic LLM judgment.

Enforces explicit formula validation statuses:
    VERIFIED_DETERMINISTICALLY, VERIFIED_SEMANTICALLY, INVALID, UNVERIFIED
Unknown formulas not in the canonical rule database are marked UNVERIFIED
rather than being penalized as invalid.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension,
    FormulaValidationStatus
)


class FactualAndFormulaValidator:
    """Deterministic validator for scientific formulas, equations, and arithmetic assertions."""

    # Canonical laws: (correct_pattern, name)
    CANONICAL_CORRECT_FORMULAS = [
        (r'\bF\s*=\s*m\s*\*?\s*a\b', "Newton's Second Law (F = ma)"),
        (r'\ba\s*=\s*F\s*\/\s*m\b', "Acceleration (a = F/m)"),
        (r'\bV\s*=\s*I\s*\*?\s*R\b', "Ohm's Law (V = IR)"),
        (r'\bI\s*=\s*V\s*\/\s*R\b', "Current (I = V/R)"),
        (r'\bR\s*=\s*V\s*\/\s*I\b', "Resistance (R = V/I)"),
        (r'\b(?:density|rho|\u03c1)\s*=\s*m\s*\/\s*V\b', "Density (rho = m/V)"),
        (r'\bp\s*=\s*m\s*\*?\s*v\b', "Momentum (p = mv)"),
        (r'\b(?:KE|kinetic energy)\s*=\s*(?:1\/2|0\.5)\s*\*?\s*m\s*\*?\s*v\^2\b', "Kinetic Energy (KE = 1/2 m v^2)"),
        (r'\b(?:speed|velocity|v)\s*=\s*(?:distance|d|s)\s*\/\s*(?:time|t)\b', "Speed/Velocity (v = d/t)"),
    ]

    # Canonical corruptions: (pattern_regex, forbidden_corruptions, code)
    CANONICAL_CORRUPTED_FORMULAS = [
        (
            r'\bF\s*=\s*m\s*\/\s*a\b',
            "Newton's Second Law is F = ma (or a = F/m). F = m/a is physically incorrect.",
            "FORMULA_CORRUPTED_NEWTON_SECOND_LAW"
        ),
        (
            r'\bF\s*=\s*m\s*\+\s*a\b',
            "Newton's Second Law relates force to product of mass and acceleration (F = ma), not sum.",
            "FORMULA_CORRUPTED_NEWTON_SECOND_LAW"
        ),
        (
            r'\bV\s*=\s*I\s*\/\s*R\b',
            "Ohm's Law is V = IR. V = I/R is mathematically and physically inverted.",
            "FORMULA_CORRUPTED_OHMS_LAW"
        ),
        (
            r'\b(?:density|rho|\u03c1)\s*=\s*V\s*\/\s*m\b',
            "Density is mass divided by volume (rho = m / V), not volume divided by mass.",
            "FORMULA_CORRUPTED_DENSITY"
        ),
        (
            r'\b(?:KE|kinetic energy)\s*=\s*m\s*\*?\s*v\b(?!\^2)',
            "Kinetic energy is (1/2)mv^2, whereas mv represents linear momentum.",
            "FORMULA_CORRUPTED_KINETIC_ENERGY"
        ),
        (
            r'\bp\s*=\s*m\s*\/\s*v\b',
            "Momentum is product of mass and velocity (p = mv), not m / v.",
            "FORMULA_CORRUPTED_MOMENTUM"
        ),
        (
            r'\bF\s*=\s*G\s*\*?\s*m1\s*\*?\s*m2\s*\/\s*r\b(?!\^2)',
            "Universal gravitation requires inverse-square relationship with distance (r^2), not linear distance r.",
            "FORMULA_CORRUPTED_GRAVITATION"
        )
    ]

    # Variable Mismatch: canonical laws where a key variable is replaced incorrectly
    VARIABLE_MISMATCH_RULES = [
        (
            r'\bF\s*=\s*m\s*\*?\s*v\b(?!\s*\/)',
            "Force is defined as mass times acceleration (F = ma), not mass times velocity (mv is momentum).",
            "FORMULA_VARIABLE_MISMATCH"
        ),
        (
            r'\b(?:speed|velocity|v)\s*=\s*(?:distance|d|s)\s*\*?\s*(?:time|t)\b',
            "Velocity is distance divided by time (v = d/t), not distance multiplied by time.",
            "FORMULA_VARIABLE_MISMATCH"
        )
    ]

    # Unit Mismatches: (regex, error_msg, code)
    UNIT_MISMATCH_RULES = [
        (
            r'\b(?:speed|velocity)\s*(?:of|=|is)\s*\d+(?:\.\d+)?\s*(?:m\/s\^2|m\s*s\^-2)\b',
            "Speed or velocity expressed in units of acceleration (m/s^2 instead of m/s).",
            "FORMULA_UNIT_MISMATCH"
        ),
        (
            r'\bacceleration\s*(?:of|=|is)\s*\d+(?:\.\d+)?\s*(?:m\/s|km\/h)(?!\^2|\/s)\b',
            "Acceleration expressed in units of speed (m/s instead of m/s^2).",
            "FORMULA_UNIT_MISMATCH"
        ),
        (
            r'\bforce\s*(?:of|=|is)\s*\d+(?:\.\d+)?\s*(?:joules?|J)\b',
            "Force expressed in units of energy (Joules instead of Newtons).",
            "FORMULA_UNIT_MISMATCH"
        ),
        (
            r'\b(?:work|energy)\s*(?:of|=|is)\s*\d+(?:\.\d+)?\s*(?:newtons?|N)\b',
            "Work or energy expressed in units of force (Newtons instead of Joules).",
            "FORMULA_UNIT_MISMATCH"
        )
    ]

    @classmethod
    def validate(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {
            "formula_audits": [],
            "verified_formulas": [],
            "arithmetic_checks": []
        }
        score: float = 100.0

        all_text_blocks: List[Tuple[str, str]] = []
        for s in doc.sections:
            all_text_blocks.append((s.content, s.id or s.section_type))
            for f in s.formulas:
                all_text_blocks.append((f, s.id or s.section_type))
            for ex in s.examples:
                all_text_blocks.append((ex, s.id or s.section_type))

        for idx, p in enumerate(doc.practice):
            q_text = str(p.get("question", ""))
            ans_text = str(p.get("answer", ""))
            exp_text = str(p.get("explanation", ""))
            sec_id = f"practice_{idx+1}"
            all_text_blocks.append((f"{q_text}\n{ans_text}\n{exp_text}", sec_id))

            # ── 1. Arithmetic evaluation on Practice Questions ──
            cls._audit_arithmetic(q_text, ans_text, exp_text, sec_id, violations, details)

        # Collect explicit formula strings from doc
        found_formulas: List[Tuple[str, str]] = []
        for s in doc.sections:
            for f in s.formulas:
                found_formulas.append((f, s.id or s.section_type))

        # ── 2. Formula Audits & Categorization ──
        for f_text, sec_id in found_formulas:
            formula_clean = f_text.strip()
            is_handled = False

            # Check known corruptions
            for pattern, err_msg, code in cls.CANONICAL_CORRUPTED_FORMULAS:
                if re.search(pattern, formula_clean, re.IGNORECASE):
                    details["formula_audits"].append({
                        "formula": formula_clean,
                        "status": FormulaValidationStatus.INVALID.value,
                        "reason": err_msg
                    })
                    violations.append(ValidationViolation(
                        code=code,
                        severity=ViolationSeverity.CRITICAL,
                        dimension=ValidationDimension.FORMULA,
                        message=f"Corrupted scientific formula detected: {err_msg}",
                        section_id=sec_id,
                        evidence=formula_clean,
                        expected="Valid canonical formulation",
                        actual=formula_clean,
                        repairable=True
                    ))
                    score -= 25.0
                    is_handled = True
                    break

            if is_handled:
                continue

            # Check variable mismatches
            for pattern, err_msg, code in cls.VARIABLE_MISMATCH_RULES:
                if re.search(pattern, formula_clean, re.IGNORECASE):
                    details["formula_audits"].append({
                        "formula": formula_clean,
                        "status": FormulaValidationStatus.INVALID.value,
                        "reason": err_msg
                    })
                    violations.append(ValidationViolation(
                        code=code,
                        severity=ViolationSeverity.CRITICAL,
                        dimension=ValidationDimension.FORMULA,
                        message=err_msg,
                        section_id=sec_id,
                        evidence=formula_clean,
                        expected="Accurate physical variable relations",
                        actual=formula_clean,
                        repairable=True
                    ))
                    score -= 25.0
                    is_handled = True
                    break

            if is_handled:
                continue

            # Check known correct formulas
            for pattern, name in cls.CANONICAL_CORRECT_FORMULAS:
                if re.search(pattern, formula_clean, re.IGNORECASE):
                    details["formula_audits"].append({
                        "formula": formula_clean,
                        "status": FormulaValidationStatus.VERIFIED_DETERMINISTICALLY.value,
                        "name": name
                    })
                    details["verified_formulas"].append(formula_clean)
                    is_handled = True
                    break

            if is_handled:
                continue

            # Unknown formula: neither corrupt nor contradictory -> mark UNVERIFIED (Spec 10)
            details["formula_audits"].append({
                "formula": formula_clean,
                "status": FormulaValidationStatus.UNVERIFIED.value,
                "note": "Formula not in known canonical database; marked UNVERIFIED without penalty."
            })

        # ── 3. Text Block Corruptions and Unit Mismatches ──
        for text, sec_id in all_text_blocks:
            # Check canonical formula corruptions in general text
            for pattern, err_msg, code in cls.CANONICAL_CORRUPTED_FORMULAS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Avoid double-adding if already caught in formula list
                    if not any(v.code == code and v.section_id == sec_id for v in violations):
                        violations.append(ValidationViolation(
                            code=code,
                            severity=ViolationSeverity.CRITICAL,
                            dimension=ValidationDimension.FORMULA,
                            message=f"Corrupted scientific formula detected: {err_msg}",
                            section_id=sec_id,
                            evidence=match.group(0),
                            expected="Valid canonical formulation",
                            actual=match.group(0),
                            repairable=True
                        ))
                        score -= 25.0

            # Check unit mismatches in text
            for pattern, err_msg, code in cls.UNIT_MISMATCH_RULES:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    violations.append(ValidationViolation(
                        code=code,
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.FORMULA,
                        message=f"Physical unit mismatch detected: {err_msg}",
                        section_id=sec_id,
                        evidence=match.group(0),
                        expected="Physical quantity with dimensionally consistent standard SI units",
                        actual=match.group(0),
                        repairable=True
                    ))
                    score -= 15.0

        details["formula_violations_count"] = len([v for v in violations if v.dimension == ValidationDimension.FORMULA])
        return violations, details, max(0.0, min(100.0, score))

    @classmethod
    def _audit_arithmetic(
        cls,
        q_text: str,
        ans_text: str,
        exp_text: str,
        sec_id: str,
        violations: List[ValidationViolation],
        details: Dict[str, Any]
    ) -> None:
        """Audits explicit simple arithmetic statements for mathematical contradictions."""
        combined = f"{q_text} {ans_text} {exp_text}"

        # Match simple patterns: "X + Y = Z" or "X * Y = Z" or "X - Y = Z"
        arithmetic_pattern = re.compile(r'(\b\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)')
        for match in arithmetic_pattern.finditer(combined):
            left_str, op, right_str, res_str = match.groups()
            try:
                left = float(left_str)
                right = float(right_str)
                stated_res = float(res_str)

                expected_res = None
                if op == "+":
                    expected_res = left + right
                elif op == "-":
                    expected_res = left - right
                elif op == "*":
                    expected_res = left * right
                elif op == "/" and right != 0:
                    expected_res = left / right

                if expected_res is not None:
                    if abs(expected_res - stated_res) > 0.001:
                        violations.append(ValidationViolation(
                            code="ARITHMETIC_CALCULATION_ERROR",
                            severity=ViolationSeverity.CRITICAL,
                            dimension=ValidationDimension.FACTUAL,
                            message=f"Arithmetic error in practice calculation: '{match.group(0)}' is mathematically invalid. Expected {expected_res}.",
                            section_id=sec_id,
                            evidence=match.group(0),
                            expected=str(expected_res),
                            actual=str(stated_res),
                            repairable=True
                        ))
                    else:
                        details["arithmetic_checks"].append(match.group(0))
            except Exception:
                pass

        # Also detect explicit prompt: "What is 2 + 2?" with "Answer: 5"
        q_simple_add = re.search(r'what\s+is\s+(\d+)\s*\+\s*(\d+)', q_text, re.IGNORECASE)
        if q_simple_add:
            n1 = int(q_simple_add.group(1))
            n2 = int(q_simple_add.group(2))
            correct_sum = n1 + n2
            ans_digits = re.findall(r'\b\d+\b', ans_text)
            if ans_digits and str(correct_sum) not in ans_digits:
                violations.append(ValidationViolation(
                    code="PRACTICE_ANSWER_INCORRECT",
                    severity=ViolationSeverity.CRITICAL,
                    dimension=ValidationDimension.PRACTICE,
                    message=f"Practice answer is incorrect for question '{q_text}'. Expected {correct_sum}, got '{ans_text}'.",
                    section_id=sec_id,
                    evidence=f"Question asks {n1} + {n2}, answer is {ans_text}",
                    expected=str(correct_sum),
                    actual=ans_text,
                    repairable=True
                ))
