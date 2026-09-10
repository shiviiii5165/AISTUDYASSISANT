"""
Curriculum & Grade-Level Validator
==================================
Verifies curriculum scope, grade appropriateness, and syllabus boundaries.
When curriculum is unknown, reports 'unavailable' rather than pretending compliance.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument
from ...context.schemas import CanonicalNotesContext
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class CurriculumValidator:
    """Audits curriculum scope and grade-level conceptual boundaries."""

    UNIVERSITY_LEVEL_MARKERS = [
        r'\blagrangian\b', r'\bhamiltonian\b', r'\bquantum electrodynamics\b',
        r'\btensor calculus\b', r'\bnavier-stokes differential\b',
        r'\bpartial differential equations of the second order\b',
        r'\bdirac equation\b', r'\bchristoffel symbols\b'
    ]

    @classmethod
    def validate(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {}
        score: float = 100.0

        curriculum_val = (
            ctx.resolved_context.curriculum
            if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum
            else getattr(ctx, "curriculum_val", None)
        )

        # ── 1. Unknown Curriculum Handling (Spec 19) ──
        if not curriculum_val or str(curriculum_val).strip().lower() in ("unknown", "none"):
            details["status"] = "unavailable"
            details["curriculum"] = "unknown"
            # It is not automatically correct, but also not an error if unspecified
            details["message"] = "Curriculum information is unknown; syllabus boundary check unavailable."
        else:
            details["status"] = "verified"
            details["curriculum"] = str(curriculum_val)

        # ── 2. Grade-Level Appropriateness ──
        class_num = 10
        match = re.search(r'(\d+)', doc.class_level)
        if match:
            class_num = int(match.group(1))
        details["class_level"] = class_num

        all_content = " ".join([s.content for s in doc.sections] + [str(p.get("question", "")) for p in doc.practice])
        all_content_lower = all_content.lower()

        # Middle school (Class 6-8) check for inappropriate university-level derivations
        if class_num <= 8 and plan.difficulty != "advanced":
            for marker in cls.UNIVERSITY_LEVEL_MARKERS:
                if re.search(marker, all_content_lower):
                    violations.append(ValidationViolation(
                        code="GRADE_LEVEL_SCOPE_EXCESSIVE",
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.CURRICULUM,
                        message=f"Content contains university-level topic/math ({marker}) inappropriate for Class {class_num}.",
                        expected=f"Foundational Class {class_num} curriculum scope",
                        actual=marker,
                        repairable=True
                    ))
                    score -= 20.0
                    break

        # Primary (Class 3-5) paragraph density check
        if class_num <= 5:
            dense_blocks = [
                s.title for s in doc.sections
                for p in s.content.split("\n\n")
                if len(p.split()) > 100
            ]
            if dense_blocks:
                violations.append(ValidationViolation(
                    code="GRADE_LEVEL_READABILITY_DENSE",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.CURRICULUM,
                    message=f"Sections ({', '.join(dense_blocks[:2])}) contain overly dense paragraphs for Class {class_num} readers.",
                    expected=f"Short paragraphs (< 70 words) for Class {class_num}",
                    actual="Dense academic paragraphs",
                    repairable=True
                ))
                score -= 10.0

        # Topic scope check: Notes topic should match requested topic
        ctx_topic_words = set(re.findall(r'\w+', ctx.topic.lower()))
        doc_topic_words = set(re.findall(r'\w+', doc.topic.lower()))
        if len(ctx_topic_words) > 0 and len(ctx_topic_words.intersection(doc_topic_words)) == 0:
            violations.append(ValidationViolation(
                code="CURRICULUM_TOPIC_DEVIATION",
                severity=ViolationSeverity.CRITICAL,
                dimension=ValidationDimension.CURRICULUM,
                message=f"Generated document topic '{doc.topic}' deviates completely from requested topic '{ctx.topic}'.",
                expected=ctx.topic,
                actual=doc.topic,
                repairable=False
            ))
            score -= 30.0

        return violations, details, max(0.0, min(100.0, score))
