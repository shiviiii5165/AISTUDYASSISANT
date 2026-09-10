"""
Plan Compliance Validator
=========================
Verifies that the generated NotesDocument strictly satisfies the requirements,
constraints, blueprint, formats, difficulty, depth, and practice contracts set
by the authoritative NotesGenerationPlan.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument, NoteFormat
from ...context.schemas import CanonicalNotesContext
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class PlanComplianceValidator:
    """Evaluates strict compliance between NotesGenerationPlan and NotesDocument."""

    @staticmethod
    def validate(
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {}
        score: float = 100.0

        # ── 1. Purpose Validation ──
        primary_purpose = plan.purpose.primary.lower()
        details["purpose"] = primary_purpose

        if primary_purpose == "exam_preparation":
            # Exam preparation requires revision summary, exam-style practice, or key revision takeaways
            has_exam_cues = (
                bool(doc.revision_summary) or
                any("exam" in s.title.lower() or "revision" in s.title.lower() or "summary" in s.title.lower() for s in doc.sections) or
                any("tip" in str(c.type).lower() or "exam" in str(c.title).lower() for s in doc.sections for c in s.callouts)
            )
            if not has_exam_cues:
                violations.append(ValidationViolation(
                    code="PLAN_PURPOSE_MISMATCH",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message="Plan requires 'exam_preparation' purpose, but document lacks exam-focused revision summaries, tips, or checkpoints.",
                    expected="exam_preparation structure (revision summary, high-yield exam takeaways)",
                    actual="Generic topical notes without exam orientation",
                    repairable=True
                ))
                score -= 15.0

        elif primary_purpose == "remediation":
            # Remediation requires targeted misconception or weak-concept support
            has_remedial = (
                any(s.section_type in ("common_misconceptions", "remediation", "guided_practice") for s in doc.sections) or
                any(c.type == "misconception" for s in doc.sections for c in s.callouts)
            )
            if not has_remedial:
                violations.append(ValidationViolation(
                    code="PLAN_PURPOSE_MISMATCH",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message="Plan requires 'remediation' purpose, but document lacks remediation or misconception sections.",
                    expected="remediation section or misconception breakdown",
                    actual="No remediation content found",
                    repairable=True
                ))
                score -= 15.0

        # ── 2. Difficulty Validation ──
        plan_diff = plan.difficulty.value if hasattr(plan.difficulty, "value") else str(plan.difficulty)
        doc_diff = doc.difficulty.value if hasattr(doc.difficulty, "value") else str(doc.difficulty)
        details["expected_difficulty"] = plan_diff
        details["actual_difficulty"] = doc_diff

        if plan_diff != doc_diff:
            violations.append(ValidationViolation(
                code="PLAN_DIFFICULTY_MISMATCH",
                severity=ViolationSeverity.ERROR,
                dimension=ValidationDimension.PLAN_COMPLIANCE,
                message=f"Document difficulty metadata '{doc_diff}' contradicts authoritative plan difficulty '{plan_diff}'.",
                expected=plan_diff,
                actual=doc_diff,
                repairable=True
            ))
            score -= 15.0

        # Semantic difficulty check: If plan is advanced, verify content/practice is not purely trivial definitions
        if plan_diff == "advanced":
            # Check practice questions
            basic_definitions = [
                p for p in doc.practice
                if re.match(r'^(define|what is|state the definition of)\b', str(p.get("question", "")).strip().lower())
                and "boundary" not in str(p.get("question", "")).lower()
                and "derive" not in str(p.get("question", "")).lower()
            ]
            if len(basic_definitions) > 0 and len(basic_definitions) == len(doc.practice):
                violations.append(ValidationViolation(
                    code="PLAN_DIFFICULTY_SEMANTIC_MISMATCH",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message="Plan requires 'advanced' cognitive demand, but all practice questions are purely basic recall definitions.",
                    expected="Advanced application, boundary analysis, or derivations",
                    actual="Pure recall definitions",
                    repairable=True
                ))
                score -= 10.0

        # ── 3. Depth Validation ──
        plan_depth = plan.depth.value if hasattr(plan.depth, "value") else str(plan.depth)
        doc_depth = doc.depth.value if hasattr(doc.depth, "value") else str(doc.depth)
        details["expected_depth"] = plan_depth
        details["actual_depth"] = doc_depth

        if plan_depth != doc_depth:
            violations.append(ValidationViolation(
                code="PLAN_DEPTH_MISMATCH",
                severity=ViolationSeverity.ERROR,
                dimension=ValidationDimension.PLAN_COMPLIANCE,
                message=f"Document depth metadata '{doc_depth}' contradicts plan depth '{plan_depth}'.",
                expected=plan_depth,
                actual=doc_depth,
                repairable=True
            ))
            score -= 10.0

        # Content depth semantic check
        total_words = sum(len(s.content.split()) for s in doc.sections)
        details["total_words"] = total_words
        if plan_depth in ("detailed", "deep") and total_words < 60:
            violations.append(ValidationViolation(
                code="PLAN_DEPTH_INSUFFICIENT",
                severity=ViolationSeverity.ERROR,
                dimension=ValidationDimension.PLAN_COMPLIANCE,
                message=f"Plan specifies '{plan_depth}' depth, but total document content contains only {total_words} words.",
                expected="Comprehensive conceptual depth and elaboration",
                actual=f"{total_words} words",
                repairable=True
            ))
            score -= 10.0

        # ── 4. Format Compliance ──
        details["expected_formats"] = [f.value if hasattr(f, "value") else str(f) for f in plan.formats]
        for fmt in plan.formats:
            fmt_str = fmt.value if hasattr(fmt, "value") else str(fmt)
            if fmt == NoteFormat.FLOWCHART:
                has_flow = (
                    any(v.type == "flowchart" for v in doc.visuals) or
                    any(s.visual_spec and s.visual_spec.type == "flowchart" for s in doc.sections)
                )
                if not has_flow:
                    violations.append(ValidationViolation(
                        code="PLAN_FORMAT_MISSING_FLOWCHART",
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.PLAN_COMPLIANCE,
                        message="Plan required 'flowchart' format, but no flowchart visual specification exists.",
                        expected="Flowchart visual spec",
                        actual="Missing",
                        repairable=True
                    ))
                    score -= 10.0

            elif fmt == NoteFormat.FORMULA_SHEET:
                has_formulas = any(s.formulas or s.section_type == "formula_box" for s in doc.sections)
                if not has_formulas:
                    violations.append(ValidationViolation(
                        code="PLAN_FORMAT_MISSING_FORMULAS",
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.PLAN_COMPLIANCE,
                        message="Plan required 'formula_sheet' format, but no formula block or formulas exist.",
                        expected="Dedicated formulas or formula_box section",
                        actual="Missing",
                        repairable=True
                    ))
                    score -= 10.0

            elif fmt == NoteFormat.COMPARISON_NOTES or "comparison" in fmt_str:
                has_comp = any(
                    "comparison" in s.section_type or "comparison" in s.title.lower() or
                    any(v.type == "comparison_matrix" for v in doc.visuals)
                    for s in doc.sections
                )
                if not has_comp:
                    violations.append(ValidationViolation(
                        code="PLAN_FORMAT_MISSING_COMPARISON",
                        severity=ViolationSeverity.WARNING,
                        dimension=ValidationDimension.PLAN_COMPLIANCE,
                        message="Plan required 'comparison_matrix' format, but comparison table/matrix was not generated.",
                        expected="Comparison section or matrix visual",
                        actual="Missing",
                        repairable=True
                    ))
                    score -= 5.0

        # ── 5. Section Blueprint Compliance ──
        existing_types = [s.section_type for s in doc.sections]
        details["existing_section_types"] = existing_types
        for sec_plan in plan.section_plan:
            if sec_plan.required and sec_plan.type not in existing_types:
                violations.append(ValidationViolation(
                    code="PLAN_REQUIRED_SECTION_MISSING",
                    severity=ViolationSeverity.CRITICAL,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message=f"Mandatory blueprint section '{sec_plan.type}' was omitted from the generated document.",
                    expected=sec_plan.type,
                    actual="Missing",
                    repairable=True
                ))
                score -= 20.0

        # ── 6. Practice Contract Compliance ──
        if plan.practice_plan.required:
            expected_count = plan.practice_plan.count
            actual_count = len(doc.practice)
            details["expected_practice_count"] = expected_count
            details["actual_practice_count"] = actual_count

            if actual_count != expected_count:
                violations.append(ValidationViolation(
                    code="PLAN_PRACTICE_COUNT_MISMATCH",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message=f"Practice count {actual_count} does not satisfy authoritative plan count {expected_count}.",
                    expected=expected_count,
                    actual=actual_count,
                    repairable=True
                ))
                score -= 15.0

            expected_p_diff = plan.practice_plan.difficulty
            details["expected_practice_diff"] = expected_p_diff
            for idx, p in enumerate(doc.practice):
                p_diff = str(p.get("difficulty", "")).lower()
                if p_diff and p_diff != expected_p_diff.lower():
                    violations.append(ValidationViolation(
                        code="PLAN_PRACTICE_DIFFICULTY_MISMATCH",
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.PLAN_COMPLIANCE,
                        message=f"Practice question {idx+1} difficulty '{p_diff}' does not match plan practice difficulty '{expected_p_diff}'.",
                        section_id=f"practice_{idx+1}",
                        expected=expected_p_diff,
                        actual=p_diff,
                        repairable=True
                    ))
                    score -= 5.0

        # ── 7. Visual Contract Compliance ──
        if plan.visual_plan.required:
            has_visual = bool(doc.visuals) or any(s.visual_spec is not None for s in doc.sections)
            if not has_visual:
                violations.append(ValidationViolation(
                    code="PLAN_VISUAL_REQUIRED_MISSING",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PLAN_COMPLIANCE,
                    message="Plan explicitly required a visual diagram, but none was provided.",
                    expected="Visual specification",
                    actual="None",
                    repairable=True
                ))
                score -= 15.0

        return violations, details, max(0.0, min(100.0, score))
