"""Gate 3: deterministic algebra verification with SymPy.

Input is untrusted (student and LLM text), and sympy.parse_expr calls eval, so it is
not used. Expressions are parsed with Python's ast module, and only an allowlisted
tree is converted into SymPy objects. Anything outside the allowlist, or too large to
check quickly, returns UNVERIFIABLE, so callers can fail closed.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

import sympy

MAX_LENGTH = 200
MAX_NODES = 120
MAX_EXPONENT = 20
_ALLOWED_TEXT = re.compile(r"^[0-9A-Za-z_+\-*/^().,\s]+$")
_FUNCTIONS = {
    "sqrt": sympy.sqrt,
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "log": sympy.log,
    "ln": sympy.log,
    "exp": sympy.exp,
}
_CONSTANTS = {"pi": sympy.pi}


class Verdict(str, Enum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class DerivationResult:
    verdict: Verdict
    # Zero-based index of the first line that does not follow from the one before it.
    first_bad_step: Optional[int] = None


class _Rejected(ValueError):
    pass


def _split_identifier(match: re.Match[str]) -> str:
    word = match.group(0)
    if word in _FUNCTIONS or word in _CONSTANTS:
        return word
    # Algebraic juxtaposition (xy means x*y), but longer words are not algebra.
    if not word.isalpha() or len(word) > 3:
        raise _Rejected(word)
    return "*".join(word)


def _normalize(text: str) -> str:
    if len(text) > MAX_LENGTH or not _ALLOWED_TEXT.match(text):
        raise _Rejected("disallowed input")
    text = text.replace("^", "**")
    text = re.sub(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)\s*(?=[A-Za-z(])", r"\1*", text)
    text = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", _split_identifier, text)
    text = re.sub(r"\)\s*(?=[A-Za-z0-9(])", ")*", text)
    # x(y+1) is multiplication unless the name before the bracket is a function.
    return re.sub(
        r"\b([A-Za-z]+)\s*\(",
        lambda m: f"{m.group(1)}(" if m.group(1) in _FUNCTIONS else f"{m.group(1)}*(",
        text,
    )


def _numeric_literal(node: ast.AST) -> bool:
    """True for bounded exponents such as 2, -1 or (1/2); blocks 9**9**9."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _numeric_literal(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _numeric_literal(node.left) and _numeric_literal(node.right)
    return False


def _convert(node: ast.AST) -> sympy.Expr:
    if isinstance(node, ast.Expression):
        return _convert(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _Rejected("constant")
        return sympy.Rational(str(node.value))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        if len(node.id) != 1:
            raise _Rejected(node.id)
        return sympy.Symbol(node.id, real=True)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _convert(node.operand)
        return -operand if isinstance(node.op, ast.USub) else operand
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            if not _numeric_literal(node.right):
                raise _Rejected("exponent")
            exponent = _convert(node.right)
            if abs(exponent) > MAX_EXPONENT:
                raise _Rejected("exponent")
            return _convert(node.left) ** exponent
        left, right = _convert(node.left), _convert(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise _Rejected("division by zero")
            return left / right
    if isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS
            and len(node.args) == 1
            and not node.keywords
        ):
            return _FUNCTIONS[node.func.id](_convert(node.args[0]))
    raise _Rejected(type(node).__name__)


def parse_math(text: str) -> sympy.Expr:
    """Parse a math expression; raises ValueError for anything outside the allowlist."""
    try:
        tree = ast.parse(_normalize(text.strip()), mode="eval")
    except (SyntaxError, RecursionError, MemoryError) as exc:
        raise _Rejected("syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise _Rejected("too large")
    return _convert(tree)


def verify_equal(lhs: str, rhs: str) -> Verdict:
    """Check whether two expressions are identically equal."""
    try:
        difference = sympy.simplify(parse_math(lhs) - parse_math(rhs))
    except (ValueError, TypeError, ZeroDivisionError, RecursionError):
        return Verdict.UNVERIFIABLE
    if difference == 0:
        return Verdict.VERIFIED
    if difference.is_nonzero or not difference.is_constant():
        return Verdict.REFUTED
    return Verdict.UNVERIFIABLE


def _equation_residual(line: str) -> sympy.Expr:
    parts = line.split("=")
    if len(parts) != 2:
        raise ValueError("expected exactly one '='")
    return parse_math(parts[0]) - parse_math(parts[1])


def _equations_equivalent(first: sympy.Expr, second: sympy.Expr) -> Optional[bool]:
    """Return whether two residuals have the same solutions; None if undecided."""
    ratio = sympy.simplify(first / second) if second != 0 else None
    if ratio is not None and ratio.is_number and ratio != 0:
        return True
    symbols = first.free_symbols | second.free_symbols
    if len(symbols) != 1:
        return None
    symbol = symbols.pop()
    try:
        return set(sympy.solve(first, symbol)) == set(sympy.solve(second, symbol))
    except (NotImplementedError, ValueError):
        return None


def verify_derivation(lines: Sequence[str]) -> DerivationResult:
    """Check each equation line against the previous one, reporting the first bad step.

    Each step must keep the same solution set. Reports UNVERIFIABLE at the first line
    that cannot be decided, because later lines depend on it.
    """
    try:
        residuals = [_equation_residual(line) for line in lines]
    except (ValueError, TypeError, ZeroDivisionError, RecursionError):
        return DerivationResult(Verdict.UNVERIFIABLE)
    for index in range(1, len(residuals)):
        equivalent = _equations_equivalent(residuals[index - 1], residuals[index])
        if equivalent is None:
            return DerivationResult(Verdict.UNVERIFIABLE, index)
        if not equivalent:
            return DerivationResult(Verdict.REFUTED, index)
    return DerivationResult(Verdict.VERIFIED)
