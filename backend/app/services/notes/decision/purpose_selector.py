"""
LearnByGenie Notes Decision Engine — Deterministic Purpose Selector
=================================================================
Selects primary and secondary purposes for notes generation based on
strict decision precedence. Zero LLM calls.
"""
import re
from typing import Tuple, List, Optional
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.schemas import NoteFormat
from .schemas import PurposePlan, PurposeType
from .policies import MasteryPolicy, MasteryBracket


class PurposeSelector:
    """Evaluates CanonicalNotesContext to determine primary and secondary purpose."""

    @classmethod
    def select(cls, ctx: CanonicalNotesContext, avg_mastery: Optional[float] = None) -> PurposePlan:
        """
        Selects primary and secondary purposes following strict precedence:
        1. Explicit user intent
        2. Explicit exam / revision state
        3. Severe misconception / low student mastery
        4. Lesson pedagogy / mode
        5. Topic structure
        6. Neutral defaults
        """
        secondary: List[str] = []
        instructions = (ctx.explicit_user_instructions or "").lower()
        topic_lower = (ctx.topic or "").lower()
        raw_topic_lower = (ctx.raw_topic or "").lower()
        combined_text = f"{topic_lower} {raw_topic_lower} {instructions}"

        # ── 1. Explicit User Intent (Highest Precedence) ──
        if "exam" in instructions or "test" in instructions or ctx.requested_format == NoteFormat.EXAM_PREPARATION:
            primary = PurposeType.EXAM_PREPARATION.value
            if "revision" in combined_text or ctx.requested_format == NoteFormat.QUICK_REVISION:
                secondary.append(PurposeType.REVISION.value)
            if ctx.student_misconceptions or ctx.expected_misconceptions or (avg_mastery is not None and avg_mastery < MasteryPolicy.LOW_THRESHOLD):
                secondary.append(PurposeType.REMEDIATION.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "revision" in instructions or ctx.requested_format == NoteFormat.QUICK_REVISION:
            primary = PurposeType.REVISION.value
            if ctx.student_misconceptions or (avg_mastery is not None and avg_mastery < MasteryPolicy.LOW_THRESHOLD):
                secondary.append(PurposeType.REMEDIATION.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "remedial" in instructions or "remediation" in instructions or ctx.requested_format == NoteFormat.REMEDIAL_NOTES:
            primary = PurposeType.REMEDIATION.value
            secondary.append(PurposeType.LEARNING.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "summary" in instructions:
            primary = PurposeType.LESSON_SUMMARY.value
            secondary.append(PurposeType.LEARNING.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "reference" in instructions or "cheat sheet" in instructions or ctx.requested_format == NoteFormat.FORMULA_SHEET:
            primary = PurposeType.CONCEPT_REFERENCE.value
            secondary.append(PurposeType.LEARNING.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "lecture" in instructions or ctx.requested_format == NoteFormat.LECTURE_NOTES:
            primary = PurposeType.LECTURE_CAPTURE.value
            secondary.append(PurposeType.LEARNING.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        # ── 2. Explicit Exam / Revision State in Context ──
        exam_keywords = ["exam", "test tomorrow", "midterm", "final exam", "board exam"]
        if any(k in topic_lower for k in exam_keywords):
            primary = PurposeType.EXAM_PREPARATION.value
            secondary.append(PurposeType.REVISION.value)
            if ctx.student_misconceptions or (avg_mastery is not None and avg_mastery < MasteryPolicy.LOW_THRESHOLD):
                secondary.append(PurposeType.REMEDIATION.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        if "revision" in topic_lower:
            primary = PurposeType.REVISION.value
            if ctx.student_misconceptions or (avg_mastery is not None and avg_mastery < MasteryPolicy.LOW_THRESHOLD):
                secondary.append(PurposeType.REMEDIATION.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        # ── 3. Severe Misconception / Low Mastery ──
        has_severe_low_mastery = avg_mastery is not None and avg_mastery < MasteryPolicy.LOW_THRESHOLD
        has_misconceptions = bool(ctx.student_misconceptions or ctx.expected_misconceptions or ctx.quiz_mistakes)

        if has_severe_low_mastery:
            primary = PurposeType.REMEDIATION.value
            secondary.append(PurposeType.LEARNING.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        # ── 4. Lesson Mode / Context ──
        if ctx.mode == "lesson_context" and (ctx.learning_objectives or ctx.stage_title):
            primary = PurposeType.LEARNING.value
            secondary.append(PurposeType.LESSON_SUMMARY.value)
            if has_misconceptions:
                secondary.append(PurposeType.REMEDIATION.value)
            return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))

        # ── 5. Topic / Curriculum Signals & Neutral Default ──
        primary = PurposeType.LEARNING.value
        if has_misconceptions:
            secondary.append(PurposeType.REMEDIATION.value)

        return PurposePlan(primary=primary, secondary=sorted(list(dict.fromkeys(secondary))))
