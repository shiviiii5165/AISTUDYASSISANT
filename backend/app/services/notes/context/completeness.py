"""
TeachGenie Notes Context Engine — Completeness Evaluator
========================================================
Calculates deterministic, rule-based completeness scores, lists missing fields,
and emits actionable diagnostic warnings. Never invokes LLMs.
"""
from typing import List, Dict, Any
from .schemas import (
    ContextCompleteness, ResolvedContext, ExplicitInputContext,
    LessonContext, AssessmentContext, TeachMeContext, StudentContext,
    CurriculumContext, PPTContext
)


class CompletenessEvaluator:
    """Evaluates context completeness deterministically based on pedagogical weighting."""

    WEIGHTS = {
        "topic": 30.0,            # Required
        "class_level": 15.0,      # Recommended
        "subject": 15.0,          # Recommended
        "curriculum": 10.0,       # Recommended
        "language": 10.0,         # Recommended
        "lesson": 10.0,           # Contextual Enrichment
        "assessment": 4.0,        # Assessment Enrichment
        "teach_me": 3.0,          # Tutoring Enrichment
        "ppt": 3.0,               # Presentation Enrichment
    }

    @classmethod
    def evaluate(
        cls,
        resolved: ResolvedContext,
        explicit: ExplicitInputContext,
        lesson: LessonContext,
        curriculum: CurriculumContext,
        student: StudentContext,
        assessment: AssessmentContext,
        teachme: TeachMeContext,
        ppt: PPTContext,
    ) -> ContextCompleteness:
        """Computes completeness score, missing fields list, and warnings."""
        score = 0.0
        missing_fields: List[str] = []
        warnings: List[str] = []
        breakdown: Dict[str, float] = {}

        # 1. Topic (Required - 30 pts)
        if resolved.topic:
            score += cls.WEIGHTS["topic"]
            breakdown["topic"] = cls.WEIGHTS["topic"]
        else:
            missing_fields.append("topic")
            breakdown["topic"] = 0.0

        # 2. Class Level (Recommended - 15 pts)
        if resolved.class_level:
            score += cls.WEIGHTS["class_level"]
            breakdown["class_level"] = cls.WEIGHTS["class_level"]
        else:
            missing_fields.append("class_level")
            breakdown["class_level"] = 0.0

        # 3. Subject (Recommended - 15 pts)
        if resolved.subject and resolved.subject.lower() != "general":
            score += cls.WEIGHTS["subject"]
            breakdown["subject"] = cls.WEIGHTS["subject"]
        elif resolved.subject:
            # "General" gets half weight
            score += cls.WEIGHTS["subject"] * 0.5
            breakdown["subject"] = cls.WEIGHTS["subject"] * 0.5
        else:
            missing_fields.append("subject")
            breakdown["subject"] = 0.0

        # 4. Curriculum (Recommended - 10 pts)
        if resolved.curriculum:
            score += cls.WEIGHTS["curriculum"]
            breakdown["curriculum"] = cls.WEIGHTS["curriculum"]
        else:
            missing_fields.append("curriculum")
            warnings.append("Curriculum context missing; notes will rely on generic standards.")
            breakdown["curriculum"] = 0.0

        # 5. Language (Recommended - 10 pts)
        if resolved.language:
            score += cls.WEIGHTS["language"]
            breakdown["language"] = cls.WEIGHTS["language"]
        else:
            missing_fields.append("language")
            breakdown["language"] = 0.0

        # 6. Lesson Context (Optional Enrichment - 10 pts)
        has_lesson = bool(lesson.stage_title or lesson.learning_objectives or lesson.roadmap_id)
        if has_lesson:
            score += cls.WEIGHTS["lesson"]
            breakdown["lesson"] = cls.WEIGHTS["lesson"]
        else:
            missing_fields.append("lesson.stage")
            breakdown["lesson"] = 0.0

        # 7. Assessment Context (Optional Enrichment - 4 pts)
        has_assessment = bool(assessment.quiz_id or assessment.weak_concepts or assessment.latest_score is not None)
        if has_assessment:
            score += cls.WEIGHTS["assessment"]
            breakdown["assessment"] = cls.WEIGHTS["assessment"]
        else:
            missing_fields.append("assessment.quiz")
            if assessment.status == "unavailable":
                warnings.append("Assessment context unavailable")
            breakdown["assessment"] = 0.0

        # 8. TeachMe Context (Optional Enrichment - 3 pts)
        has_teachme = bool(teachme.session_id or teachme.misconceptions or teachme.confused_concepts)
        if has_teachme:
            score += cls.WEIGHTS["teach_me"]
            breakdown["teach_me"] = cls.WEIGHTS["teach_me"]
        else:
            missing_fields.append("teachme.session")
            if teachme.status == "unavailable":
                warnings.append("TeachMe tutoring context unavailable")
            breakdown["teach_me"] = 0.0

        # 9. PPT Context (Optional Enrichment - 3 pts)
        has_ppt = bool(ppt.deck_id or ppt.slide_topics)
        if has_ppt:
            score += cls.WEIGHTS["ppt"]
            breakdown["ppt"] = cls.WEIGHTS["ppt"]
        else:
            missing_fields.append("ppt.deck")
            breakdown["ppt"] = 0.0

        # Student mastery check
        if not resolved.mastery_state:
            missing_fields.append("student.mastery")

        return ContextCompleteness(
            score=round(score, 1),
            missing_fields=missing_fields,
            warnings=warnings,
            breakdown=breakdown
        )
