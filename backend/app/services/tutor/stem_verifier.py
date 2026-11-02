"""
LearnByGenie — Feature 4: Deterministic STEM Verifier
======================================================
Safe AST-based arithmetic and numerical equation verification (§19).
Validates mathematical calculations deterministically before presenting them as authoritative.
Does NOT use unsafe eval() or arbitrary code execution.
"""
import ast
import operator
import math
import re
from typing import Optional, Tuple, List
from app.services.tutor.schemas import STEMVerificationResult

# Safe operator mapping
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval_expr(node: ast.AST) -> float:
    """Recursively evaluates a safe AST expression containing only numbers and basic operators."""
    if isinstance(node, ast.Expression):
        return safe_eval_expr(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif hasattr(ast, 'Num') and isinstance(node, ast.Num):  # for older python compatibility
        return float(node.n)
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left = safe_eval_expr(node.left)
        right = safe_eval_expr(node.right)
        # Prevent division by zero
        if op_type == ast.Div and abs(right) < 1e-12:
            raise ZeroDivisionError("Division by zero")
        # Prevent enormous exponents
        if op_type == ast.Pow and (abs(right) > 20 or abs(left) > 1000):
            raise OverflowError("Exponent too large for safe verification")
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type}")
        return SAFE_OPERATORS[op_type](safe_eval_expr(node.operand))
    else:
        raise ValueError(f"Unsupported AST node: {type(node)}")


def evaluate_arithmetic(expr_str: str) -> Optional[float]:
    """Parse and evaluate an arithmetic string (e.g. '12 * (3 + 4) / 2')."""
    try:
        # Sanitize string: replace ^ with **
        sanitized = expr_str.strip().replace("^", "**")
        tree = ast.parse(sanitized, mode='eval')
        return safe_eval_expr(tree)
    except Exception:
        return None


def extract_numeric_value(text: str) -> Optional[float]:
    """Extract a single definitive numeric value or fraction from student or tutor text."""
    # Match e.g. "x = 5", "ans is 4.5", "3/4", "-12"
    patterns = [
        r'(?:x|y|z|ans|answer|result)\s*[:=]\s*(-?\d+(?:\.\d+)?(?:/\d+)?)',
        r'^(-?\d+(?:\.\d+)?)\s*$',
        r'(-?\d+(?:\.\d+)?/\d+)',
        r'\b(-?\d+(?:\.\d+)?)\b',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val_str = m.group(1)
            if "/" in val_str:
                parts = val_str.split("/")
                try:
                    num, den = float(parts[0]), float(parts[1])
                    if den != 0:
                        return num / den
                except Exception:
                    pass
            else:
                try:
                    return float(val_str)
                except Exception:
                    pass
    return None


def verify_numeric_equivalence(
    student_answer: str,
    expected_answer: str,
    tolerance: float = 1e-4
) -> STEMVerificationResult:
    """
    Deterministically verify if student's answer numerically equals expected answer.
    Handles decimals, fractions (e.g. 1/2 == 0.5), and variable equations (x = 4 vs 4).
    """
    student_val = extract_numeric_value(student_answer)
    expected_val = extract_numeric_value(expected_answer)

    if student_val is None or expected_val is None:
        # Attempt arithmetic evaluation on whole strings if extraction didn't work
        student_val = student_val or evaluate_arithmetic(student_answer)
        expected_val = expected_val or evaluate_arithmetic(expected_answer)

    if student_val is None or expected_val is None:
        return STEMVerificationResult(
            is_verified=False,
            expression=f"{student_answer} vs {expected_answer}",
            note="Could not extract definitive numeric quantities for deterministic verification"
        )

    diff = abs(student_val - expected_val)
    is_match = diff <= tolerance

    return STEMVerificationResult(
        is_verified=is_match,
        expression=f"{student_answer} == {expected_answer}",
        computed_value=student_val,
        expected_value=expected_val,
        error_margin=diff,
        note="Exact numerical match" if is_match else f"Values differ by {diff:.6f}"
    )


def solve_quadratic_roots(a: float, b: float, c: float) -> Tuple[Optional[float], Optional[float]]:
    """Deterministically compute roots of ax^2 + bx + c = 0."""
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return None, None
        return (-c / b), None
    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        return None, None  # Complex roots not handled as real numbers
    r1 = (-b + math.sqrt(discriminant)) / (2 * a)
    r2 = (-b - math.sqrt(discriminant)) / (2 * a)
    return (r1, r2)
