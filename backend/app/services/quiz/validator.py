"""
Quiz Engine — Deterministic Validator (§44, §45, §46)
=====================================================
Pure-Python, zero-token validation of question shape, correctness integrity,
and duplicate detection. Duplicate detection uses normalized token-set
similarity (Jaccard), NOT an LLM (§46). Semantic-quality checks that genuinely
require an LLM are handled separately by the QA agent (Phase 3, §45) — this
module never calls a provider.
"""
from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from .schemas import QuizQuestion, QuestionType

# Two questions whose normalized token sets overlap by >= this ratio are
# treated as duplicates (§46). Tuned to catch reworded near-duplicates without
# flagging distinct questions that share domain vocabulary.
DUPLICATE_SIMILARITY_THRESHOLD = 0.82

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "is", "are", "was", "were",
    "what", "which", "who", "how", "why", "does", "do", "did", "and", "or",
}


def _normalize_tokens(text: str) -> set:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class ValidationIssue(BaseModel):
    index: int                 # position of the offending question (-1 = quiz-level)
    code: str
    message: str


class ValidationReport(BaseModel):
    ok: bool = True
    issues: List[ValidationIssue] = Field(default_factory=list)
    duplicate_pairs: List[Tuple[int, int]] = Field(default_factory=list)

    def add(self, index: int, code: str, message: str) -> None:
        self.ok = False
        self.issues.append(ValidationIssue(index=index, code=code, message=message))


def _validate_shape(idx: int, q: QuizQuestion, report: ValidationReport) -> None:
    """Per-question structural checks (§44)."""
    if not q.question_text or not q.question_text.strip():
        report.add(idx, "empty_text", "question_text is empty")

    ca = q.correct_answer
    ca_list = ca if isinstance(ca, list) else [ca]
    ca_nonempty = [str(x).strip() for x in ca_list if str(x).strip()]

    if not ca_nonempty:
        report.add(idx, "no_correct_answer", "correct_answer is missing")

    if q.type == QuestionType.MCQ:
        opts = [o.strip() for o in q.options if o and o.strip()]
        if len(opts) < 3:
            report.add(idx, "too_few_options", "mcq needs at least 3 non-empty options")
        if len(set(o.lower() for o in opts)) != len(opts):
            report.add(idx, "duplicate_options", "mcq has duplicate option text")
        # Every correct answer must actually be one of the options.
        opt_lower = {o.lower() for o in opts}
        for c in ca_nonempty:
            if c.lower() not in opt_lower:
                report.add(idx, "answer_not_in_options",
                           "mcq correct_answer is not present in options")
                break
        # No "all of the above" tell unless justified (§20).
        if any(re.search(r"all of the above|none of the above", o, re.I) for o in opts):
            report.add(idx, "banned_option",
                       "avoid 'all/none of the above' distractors (§20)")

    elif q.type == QuestionType.TRUE_FALSE:
        if not all(c.lower() in ("true", "false") for c in ca_nonempty):
            report.add(idx, "bad_tf_answer", "tf correct_answer must be true/false")

    elif q.type in (QuestionType.FILL_BLANK, QuestionType.SHORT_ANSWER):
        # Options are not used; correct_answer is the accepted answer set.
        if q.options:
            report.add(idx, "unexpected_options",
                       f"{q.type.value} should not carry options")


def validate_questions(questions: List[QuizQuestion]) -> ValidationReport:
    """
    Full deterministic validation pass over a generated question set.
    Returns a ValidationReport; callers decide whether to drop/regenerate the
    flagged questions (§58 — one bad question must not fail the whole quiz).
    """
    report = ValidationReport()

    if not questions:
        report.add(-1, "empty_quiz", "quiz has no questions")
        return report

    token_sets: List[set] = []
    for idx, q in enumerate(questions):
        _validate_shape(idx, q, report)
        token_sets.append(_normalize_tokens(q.question_text or ""))

    # Pairwise duplicate detection (§46), normalized text similarity — no LLM.
    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            sim = _jaccard(token_sets[i], token_sets[j])
            if sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                report.duplicate_pairs.append((i, j))
                report.add(j, "duplicate_question",
                           f"near-duplicate of question {i} (similarity {sim:.2f})")

    return report
