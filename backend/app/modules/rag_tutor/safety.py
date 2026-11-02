"""Gate 4: deterministic child-safety filter and Gate 3 output checks.

The filter is a phrase list (English, Hindi, Hinglish), so it catches known phrases only
and should sit alongside a moderation model before a wide launch. It blocks rather than
scores, and a distress message always gets a supportive reply instead of a tutor answer.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence

from app.modules.learning_core import math_verifier
from app.modules.learning_core.math_verifier import Verdict

_DISTRESS = re.compile(
    r"\b(kill myself|end my life|suicide|want to die|self[- ]?harm|hurt myself|marna chahta|marna chahti|"
    r"jeena nahi|khudkushi|aatmahatya)\b|आत्महत्या|मरना चाहत",
    re.IGNORECASE,
)
_TOXIC = re.compile(
    r"\b(fuck\w*|shit|bitch|bastard|asshole|chutiya|madarchod|behenchod|bhosdi\w*|gandu|"
    r"porn\w*|nude\w*|sexting|rape\w*|kill (you|him|her|them)|make a bomb|buy drugs)\b",
    re.IGNORECASE,
)
DISTRESS_REPLY = (
    "I'm really glad you told me. This matters more than any lesson, and you don't have to "
    "handle it alone. Please talk to a parent, teacher or another adult you trust today. "
    "You can also call Tele-MANAS on 14416, free and open at any hour. If you are in danger "
    "right now, call 112."
)
_INLINE_ARITHMETIC = re.compile(r"(?<![\w.])([\d.+\-*/^() ]*\d[\d.+\-*/^() ]*)=([\d.+\-*/^() ]*\d[\d.+\-*/^() ]*)(?![\w.])")


def is_distress(text: str) -> bool:
    return bool(_DISTRESS.search(text))


def is_toxic(text: str) -> bool:
    return bool(_TOXIC.search(text))


def leaks_answer(text: str, answer: str) -> bool:
    """True if the final answer appears as its own value in the text."""
    return bool(re.search(rf"(?<![\w./]){re.escape(answer)}(?![\w/]|\.\d)", text))


def verify_math(text: str, steps: Sequence[str] = ()) -> tuple[bool, Optional[str]]:
    """Check tagged derivation steps as a chain, plus every inline numeric equality.

    Equality checks are exact, and anything undecidable counts as a failure.
    """
    if steps:
        result = math_verifier.verify_derivation(steps)
        if result.verdict is not Verdict.VERIFIED:
            return False, f"step_{result.first_bad_step}:{result.verdict.value}"
    for match in _INLINE_ARITHMETIC.finditer(text):
        if _continues_algebra(text[:match.start()]):
            continue
        left, right = match.group(1).strip(), match.group(2).strip()
        if math_verifier.verify_equal(left, right) is not Verdict.VERIFIED:
            return False, f"inline:{left}={right}"
    return True, None


def _continues_algebra(before: str) -> bool:
    """True if the numbers belong to a longer expression, like the "+ 2" in "x + 2 = 3"."""
    tokens = before.split()
    if not tokens:
        return False
    previous = tokens[-1]
    return len(previous) == 1 and previous.isalpha() or any(c.isdigit() or c == ")" for c in previous)
