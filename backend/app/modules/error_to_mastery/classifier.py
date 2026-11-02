"""Stage 2: E01-E20 classification.

Tier 1 covers item traps, confidence, and the existing Mistake DNA rules. Tier 2 uses the
SymPy result of the student's own working and prerequisite evidence. Anything left is
E20 and deterministic=False, which is what the 70% target measures. No LLM is called.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from app.modules.learning_core.math_verifier import Verdict, verify_derivation, verify_equal
from app.services.mistake_dna.classifier import MistakeClassifier
from app.services.mistake_dna.schemas import MistakeCandidate, MistakeSourceType

DETERMINISTIC_TARGET = 0.70
_GAVE_UP = re.compile(r"\b(no idea|don'?t know|dont know|not sure|pata nahi|nahi pata|skip)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TokenResult:
    token: str
    tier: int
    rule: str
    deterministic: bool
    bad_step: Optional[int] = None


def _source_type() -> MistakeSourceType:
    return next(iter(MistakeSourceType))


def _classify_working(steps: Sequence[str]) -> Optional[TokenResult]:
    result = verify_derivation(steps)
    if result.verdict is not Verdict.REFUTED or result.first_bad_step is None:
        return None
    index = result.first_bad_step
    previous, current = steps[index - 1], steps[index]
    try:
        p_lhs, p_rhs = previous.split("=")
        c_lhs, c_rhs = current.split("=")
        if verify_equal(c_rhs, f"-({p_rhs})") is Verdict.VERIFIED:
            return TokenResult("E07", 2, "WORKING_SIGN_FLIP", True, index)
    except ValueError:
        pass
    if index == 1:
        token, rule = "E06", "WORKING_FIRST_TRANSPOSITION"
    elif index == len(steps) - 1:
        token, rule = "E14", "WORKING_INVALID_FINAL_STEP"
    else:
        token, rule = "E06", "WORKING_TRANSPOSITION"
    return TokenResult(token, 2, rule, True, index)


def classify_error(
    *,
    prompt: str,
    expected: str,
    response: str,
    subject: str,
    concept_id: str,
    student_id: str,
    item_id: str,
    traps: dict[str, str],
    steps: Sequence[str] = (),
    confidence: Optional[str] = None,
    weak_prerequisites: Sequence[str] = (),
) -> TokenResult:
    clean = response.strip()
    for wrong_value, token in traps.items():
        if clean and verify_equal(clean, wrong_value) is Verdict.VERIFIED:
            return TokenResult(token, 1, "ITEM_TRAP", True)

    if confidence == "Guess":
        return TokenResult("E19", 1, "SELF_REPORTED_GUESS", True)

    if len(steps) >= 2:
        working = _classify_working(steps)
        if working is not None:
            return working

    outcome = MistakeClassifier.classify(MistakeCandidate(
        user_id=student_id,
        skill_id=concept_id,
        subject=subject,
        source_type=_source_type(),
        source_record_id=item_id,
        prompt_text=prompt,
        expected_answer=expected,
        student_response=response,
    ))
    token = (outcome.error_token_id or "E20")[:3]
    if token not in ("E20", "E01"):
        return TokenResult(token, 1, outcome.deterministic_rule or "MISTAKE_DNA", True)

    # A gap in an earlier concept explains an otherwise unclassified error.
    if weak_prerequisites:
        return TokenResult("E02", 2, "WEAK_PREREQUISITE", True)
    if token == "E01":
        return TokenResult("E01", 1, outcome.deterministic_rule or "MISTAKE_DNA", True)
    if _GAVE_UP.search(clean):
        return TokenResult("E18", 1, "GAVE_UP_PHRASE", True)
    if clean and not re.search(r"\d", clean):
        return TokenResult("E19", 1, "NON_NUMERIC_ANSWER", True)
    return TokenResult("E20", 3, "UNCLASSIFIED", False)


def deterministic_rate(results: Sequence[TokenResult]) -> float:
    return sum(r.deterministic for r in results) / len(results) if results else 0.0
