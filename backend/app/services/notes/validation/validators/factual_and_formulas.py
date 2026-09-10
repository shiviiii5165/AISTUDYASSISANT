"""
Factual & Formula Validator
===========================
Executes deterministic mathematical, formulaic, and physical consistency audits.
Validates arithmetic equations, answers to numerical practice questions,
and standard scientific formula definitions without relying on probabilistic LLM judgment.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class FactualAndFormulaValidator:
    """Deterministic validator for scientific formulas, equations, and arithmetic assertions."""

    # Canonical laws and standard mathematical relations: (pattern_regex, forbidden_corruptions, name)
    CANONICAL_FORMULAS = [
        # Newton's Second Law: F = ma
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
        # Ohm's Law: V = IR, I = V/R, R = V/I
        (
            r'\bV\s*=\s*I\s*\/\s*R\b',
            "Ohm's Law is V = IR. V = I/R is mathematically and physically inverted.",
            "FORMULA_CORRUPTED_OHMS_LAW"
        ),
        # Density: rho = m / V
        (
            r'\b(?:density|rho|\u03c1)\s*=\s*V\s*\/\s*m\b',
            "Density is mass divided by volume (rho = m / V), not volume divided by mass.",
            "FORMULA_CORRUPTED_DENSITY"
        ),
        # Kinetic Energy: KE = 1/2 m v^2
        (
            r'\b(?:KE|kinetic energy)\s*=\s*m\s*\*?\s*v\b(?!\^2)',
            "Kinetic energy is (1/2)mv^2, whereas mv represents linear momentum.",
            "FORMULA_CORRUPTED_KINETIC_ENERGY"
        ),
        # Momentum: p = mv
        (
            r'\bp\s*=\s*m\s*\/\s*v\b',
            "Momentum is product of mass and velocity (p = mv), not m / v.",
            "FORMULA_CORRUPTED_MOMENTUM"
        ),
        # Gravitational Force: F = G m1 m2 / r^2
        (
            r'\bF\s*=\s*G\s*\*?\s*m1\s*\*?\s*m2\s*\/\s*r\b(?!\^2)',
            "Universal gravitation requires inverse-square relationship with distance (r^2), not linear distance r.",
            "FORMULA_CORRUPTED_GRAVITATION"
        )
    ]

    @classmethod
    def validate(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {"verified_formulas": [], "arithmetic_checks": []}
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
            # Detect simple arithmetic claims: e.g. "2 + 2 = 5", "5 * 4 = 25"
            cls._audit_arithmetic(q_text, ans_text, exp_text, sec_id, violations, details)

        # ── 2. Scientific Formula Integrity ──
        for text, sec_id in all_text_blocks:
            for pattern, err_msg, code in cls.CANONICAL_FORMULAS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
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
                    # Allow slight float precision difference
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
            # Check answer
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
