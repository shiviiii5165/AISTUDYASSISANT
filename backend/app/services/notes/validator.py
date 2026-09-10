"""
AI Notes Generation Engine — Quality Validator
===============================================
Pure Python deterministic evaluation engine scoring generated notes from 0 to 100:
- Accuracy (25 pts)
- Curriculum Alignment (20 pts)
- Grade Appropriateness (15 pts)
- Clarity (15 pts)
- Completeness (10 pts)
- Relevance (5 pts)
- Format Compliance (5 pts)
- Misconception Coverage (5 pts)
"""
import re
from typing import List, Dict, Any

from .schemas import (
    CanonicalNotesContext, DecisionOutput,
    NotesDocument, NotesQualityReport, NoteFormat
)


class NotesValidator:
    """Evaluates the pedagogical and structural quality of generated notes documents."""

    @staticmethod
    def evaluate(
        doc: NotesDocument,
        ctx: CanonicalNotesContext,
        decision: DecisionOutput
    ) -> NotesQualityReport:
        warnings: List[str] = []
        feedback: List[str] = []

        # ── 1. Completeness (10 pts) ──
        comp_score = 10.0
        sec_types = {s.section_type for s in doc.sections}
        missing_sections = [req for req in decision.required_sections if req not in sec_types]

        if missing_sections:
            penalty = min(8.0, len(missing_sections) * 2.0)
            comp_score -= penalty
            warnings.append(f"Missing planned section(s): {', '.join(missing_sections)}")
        else:
            feedback.append("All planned pedagogical sections are present.")

        # ── 2. Curriculum Alignment (20 pts) ──
        curr_score = 20.0
        if ctx.learning_objectives:
            all_text = " ".join([f"{s.title} {s.content}" for s in doc.sections]).lower()
            matched_objs = 0
            for obj in ctx.learning_objectives:
                # Check for significant words
                words = [w for w in re.findall(r'\w+', obj.lower()) if len(w) > 4]
                if any(w in all_text for w in words):
                    matched_objs += 1
            
            coverage_ratio = matched_objs / len(ctx.learning_objectives)
            if coverage_ratio < 0.6:
                curr_score = max(8.0, curr_score * coverage_ratio)
                warnings.append(f"Notes only cover {int(coverage_ratio*100)}% of the specific lesson objectives.")
            else:
                feedback.append(f"Strong curriculum alignment: {int(coverage_ratio*100)}% of objectives covered.")
        else:
            feedback.append("Curriculum alignment confirmed against standard syllabus.")

        # ── 3. Accuracy & Internal Consistency (25 pts) ──
        acc_score = 25.0
        empty_sections = [s.title for s in doc.sections if len(s.content.strip()) < 20]
        if empty_sections:
            acc_score -= min(10.0, len(empty_sections) * 3.0)
            warnings.append(f"Section(s) have thin or placeholder content: {', '.join(empty_sections)}")

        # Check for non-empty examples
        has_examples = any(s.examples for s in doc.sections)
        if not has_examples and "worked_example" in decision.required_sections:
            acc_score -= 3.0
            warnings.append("No worked examples found in the generated notes.")
        else:
            feedback.append("Practical worked examples provided.")

        # ── 4. Grade Appropriateness (15 pts) ──
        grade_score = 15.0
        class_num = 10
        match = re.search(r'(\d+)', doc.class_level)
        if match:
            class_num = int(match.group(1))

        all_content = " ".join(s.content for s in doc.sections)
        # Class 3-5: Simple, shorter sentences
        if class_num <= 5:
            long_paragraphs = [p for s in doc.sections for p in s.content.split("\n\n") if len(p.split()) > 80]
            if long_paragraphs:
                grade_score -= 4.0
                warnings.append(f"Class {class_num} notes have dense paragraphs that may be hard for young readers.")
            else:
                feedback.append(f"Vocabulary and sentence length appropriately scaled for Class {class_num}.")
        elif class_num >= 11:
            # Senior secondary: Check for formal concepts or formulas
            has_formulas = any(s.formulas for s in doc.sections)
            if not has_formulas and ("physics" in doc.subject.lower() or "math" in doc.subject.lower() or "chemistry" in doc.subject.lower()):
                grade_score -= 3.0
                warnings.append(f"Class {class_num} {doc.subject} notes lack mathematical equations/formulas.")
            else:
                feedback.append(f"Rigorous conceptual depth verified for Class {class_num}.")

        # ── 5. Clarity & Visual Scaffolding (15 pts) ──
        clarity_score = 15.0
        has_key_points = any(s.key_points for s in doc.sections)
        has_callouts = any(s.callouts for s in doc.sections)
        if not has_key_points:
            clarity_score -= 3.0
            warnings.append("Notes lack bulleted key takeaway summaries.")
        if has_callouts:
            feedback.append("Visual callout boxes highlight crucial takeaways.")

        # ── 6. Relevance (5 pts) ──
        rel_score = 5.0
        topic_words = [w for w in re.findall(r'\w+', doc.topic.lower()) if len(w) > 3]
        if topic_words and not any(w in doc.title.lower() for w in topic_words):
            rel_score -= 2.0
            warnings.append("Note title deviates from requested topic.")

        # ── 7. Format Compliance (5 pts) ──
        format_score = 5.0
        if NoteFormat.FLOWCHART in decision.selected_formats:
            has_flow = any(s.visual_spec and s.visual_spec.type == "flowchart" for s in doc.sections) or any("flowchart" in s.section_type for s in doc.sections)
            if not has_flow:
                format_score -= 2.0
                warnings.append("Selected format 'flowchart' was not generated in visual specs.")
        if NoteFormat.FORMULA_SHEET in decision.selected_formats:
            has_form = any(s.formulas or s.section_type == "formula_box" for s in doc.sections)
            if not has_form:
                format_score -= 2.0
                warnings.append("Selected format 'formula_sheet' contains no dedicated formula block.")

        # ── 8. Misconception Coverage (5 pts) ──
        misc_score = 5.0
        if decision.misconceptions_to_target:
            covered_misc = 0
            for m in decision.misconceptions_to_target:
                words = [w for w in re.findall(r'\w+', m.lower()) if len(w) > 4]
                if any(w in all_content.lower() for w in words):
                    covered_misc += 1
            if covered_misc == 0:
                misc_score -= 3.0
                warnings.append("Known student misconceptions were not explicitly addressed in the notes.")
            else:
                feedback.append("Student misconceptions explicitly addressed with warnings.")

        # Final score aggregation
        total_score = round(max(10.0, min(100.0, (
            acc_score + curr_score + grade_score + clarity_score +
            comp_score + rel_score + format_score + misc_score
        ))), 2)

        return NotesQualityReport(
            score=total_score,
            accuracy=round(acc_score, 1),
            curriculum_alignment=round(curr_score, 1),
            grade_appropriateness=round(grade_score, 1),
            clarity=round(clarity_score, 1),
            completeness=round(comp_score, 1),
            relevance=round(rel_score, 1),
            format_compliance=round(format_score, 1),
            misconception_coverage=round(misc_score, 1),
            warnings=list(dict.fromkeys(warnings)),
            feedback=list(dict.fromkeys(feedback))
        )

    @staticmethod
    async def validate(
        doc: NotesDocument,
        plan: Any,
        ctx: CanonicalNotesContext,
        sources: Any = None,
        enable_llm: bool = True
    ) -> Any:
        """Step 4 Validation Engine bridge method."""
        from .validation.engine import validate_notes
        from .generation.engine import ensure_generation_plan
        plan_obj = ensure_generation_plan(plan)
        return await validate_notes(
            context=ctx,
            plan=plan_obj,
            document=doc,
            sources=sources,
            enable_llm=enable_llm
        )

