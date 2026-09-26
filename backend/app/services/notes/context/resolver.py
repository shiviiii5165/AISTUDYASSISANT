"""
LearnByGenie Notes Context Engine — Context Resolver
==================================================
Applies strict deterministic priority rankings (1 to 8) to resolve candidate
values into an authoritative ResolvedContext with complete field provenance.
"""
from typing import Dict, Any, List, Optional, Tuple
from .schemas import (
    NotesContextSource, ContextResolutionStatus, FieldProvenance,
    ContextConflict, ResolvedContext, ProvenanceContext,
    SOURCE_PRIORITY_MAP, SOURCE_CONFIDENCE_MAP,
    ExplicitInputContext, LessonContext, CurriculumContext,
    StudentContext, AssessmentContext, TeachMeContext, PPTContext, SourcesContext
)
from .conflict_detector import CandidateValue, ConflictDetector
from .normalizer import ContextNormalizer


class ContextResolver:
    """Resolves multi-source candidate inputs into a coherent CanonicalNotesContext."""

    @classmethod
    def resolve(
        cls,
        explicit: ExplicitInputContext,
        lesson: LessonContext,
        curriculum: CurriculumContext,
        student: StudentContext,
        assessment: AssessmentContext,
        teachme: TeachMeContext,
        ppt: PPTContext,
        sources: SourcesContext,
        mode: str = "topic",
    ) -> Tuple[ResolvedContext, ProvenanceContext]:
        """
        Executes priority resolution across all context signals.
        Returns (ResolvedContext, ProvenanceContext).
        """
        conflicts: List[ContextConflict] = []
        field_provenances: Dict[str, FieldProvenance] = {}

        # ── 1. Resolve Topic ──
        topic_candidates: List[CandidateValue] = []
        is_lesson_mode = (mode == "lesson_context")

        if lesson.stage_topic and is_lesson_mode and not explicit.additional_instructions:
            topic_candidates.append(CandidateValue(NotesContextSource.LESSON, lesson.stage_topic, lesson.stage_topic, 1))
        elif lesson.stage_title:
            topic_candidates.append(CandidateValue(NotesContextSource.LESSON, lesson.stage_title, lesson.stage_title, 2))

        if explicit.topic:
            prio = 2 if (is_lesson_mode and lesson.stage_topic and not explicit.additional_instructions) else 1
            topic_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, explicit.topic, explicit.raw_topic or explicit.topic, prio))

        if ppt.slide_topics:
            topic_candidates.append(CandidateValue(NotesContextSource.PPT, ppt.slide_topics[0], ppt.slide_topics[0], 7))

        res_topic_cand = cls._pick_highest_priority(topic_candidates)
        if not res_topic_cand and explicit.topic:
            res_topic_cand = CandidateValue(NotesContextSource.EXPLICIT_INPUT, explicit.topic, explicit.raw_topic, 1)

        res_raw_topic = str(res_topic_cand.raw_value) if (res_topic_cand and res_topic_cand.raw_value) else (explicit.raw_topic or (res_topic_cand.value if res_topic_cand else ""))
        _, norm_topic = ContextNormalizer.normalize_topic(res_topic_cand.value if res_topic_cand else "")
        topic_conflict = ConflictDetector.detect_field_conflict("topic", topic_candidates, res_topic_cand)
        if topic_conflict:
            conflicts.append(topic_conflict)

        field_provenances["topic"] = cls._build_provenance(
            res_topic_cand,
            norm_topic,
            has_conflict=bool(topic_conflict)
        )

        # ── 2. Resolve Class Level & Grade ──
        class_candidates: List[CandidateValue] = []
        if explicit.class_level:
            class_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, explicit.class_level, explicit.class_level, 1))
        if lesson.stage_objective:  # Stage might contain grade reference
            pass
        if curriculum.grade:
            class_candidates.append(CandidateValue(NotesContextSource.CURRICULUM, f"Class {curriculum.grade}", str(curriculum.grade), 3))
        if student.class_level:
            class_candidates.append(CandidateValue(NotesContextSource.STUDENT, student.class_level, student.class_level, 4))
        elif student.grade:
            class_candidates.append(CandidateValue(NotesContextSource.STUDENT, f"Class {student.grade}", str(student.grade), 4))

        res_class_cand = cls._pick_highest_priority(class_candidates)
        class_conflict = ConflictDetector.detect_field_conflict("class_level", class_candidates, res_class_cand)
        if class_conflict:
            conflicts.append(class_conflict)

        res_grade, res_class_display = (None, None)
        if res_class_cand:
            res_grade, res_class_display = ContextNormalizer.normalize_grade(res_class_cand.value)

        field_provenances["class_level"] = cls._build_provenance(
            res_class_cand,
            res_class_display,
            has_conflict=bool(class_conflict)
        )

        # ── 3. Resolve Subject ──
        subject_candidates: List[CandidateValue] = []
        if explicit.subject and explicit.subject.lower() != "general":
            subject_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, explicit.subject, explicit.subject, 1))
        # Lesson planner stage / roadmap subject
        if lesson.stage_title and ("physics" in lesson.stage_title.lower() or "chemistry" in lesson.stage_title.lower()):
            # Detect domain-specific subject in stage title
            for sub in ["Physics", "Chemistry", "Biology", "Mathematics", "Science", "History", "Geography"]:
                if sub.lower() in lesson.stage_title.lower():
                    subject_candidates.append(CandidateValue(NotesContextSource.LESSON, sub, lesson.stage_title, 2))
                    break
        if curriculum.subject:
            subject_candidates.append(CandidateValue(NotesContextSource.CURRICULUM, curriculum.subject, curriculum.subject, 3))
        if explicit.subject and explicit.subject.lower() == "general" and not subject_candidates:
            subject_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, "General", "General", 1))

        res_subject_cand = cls._pick_highest_priority(subject_candidates)
        subject_conflict = ConflictDetector.detect_field_conflict("subject", subject_candidates, res_subject_cand)
        if subject_conflict:
            conflicts.append(subject_conflict)

        resolved_subject = res_subject_cand.value if res_subject_cand else (explicit.subject or "General")
        field_provenances["subject"] = cls._build_provenance(
            res_subject_cand,
            resolved_subject,
            has_conflict=bool(subject_conflict)
        )

        # ── 4. Resolve Curriculum Board ──
        curriculum_candidates: List[CandidateValue] = []
        if explicit.curriculum:
            norm_c = ContextNormalizer.normalize_curriculum(explicit.curriculum)
            if norm_c:
                curriculum_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, norm_c, explicit.curriculum, 1))
        if curriculum.board:
            norm_c = ContextNormalizer.normalize_curriculum(curriculum.board)
            if norm_c:
                curriculum_candidates.append(CandidateValue(NotesContextSource.CURRICULUM, norm_c, curriculum.board, 3))

        res_curriculum_cand = cls._pick_highest_priority(curriculum_candidates)
        curr_conflict = ConflictDetector.detect_field_conflict("curriculum", curriculum_candidates, res_curriculum_cand)
        if curr_conflict:
            conflicts.append(curr_conflict)

        # Truthful missing representation: None if not available from authoritative source!
        resolved_curriculum = res_curriculum_cand.value if res_curriculum_cand else None
        field_provenances["curriculum"] = cls._build_provenance(
            res_curriculum_cand,
            resolved_curriculum,
            has_conflict=bool(curr_conflict)
        )

        # ── 5. Resolve Language ──
        lang_candidates: List[CandidateValue] = []
        if explicit.language:
            lang_candidates.append(CandidateValue(NotesContextSource.EXPLICIT_INPUT, explicit.language, explicit.language, 1))
        if student.language:
            lang_candidates.append(CandidateValue(NotesContextSource.STUDENT, student.language, student.language, 4))

        res_lang_cand = cls._pick_highest_priority(lang_candidates)
        lang_conflict = ConflictDetector.detect_field_conflict("language", lang_candidates, res_lang_cand)
        if lang_conflict:
            conflicts.append(lang_conflict)

        norm_lang = ContextNormalizer.normalize_language(res_lang_cand.value if res_lang_cand else "english")
        field_provenances["language"] = cls._build_provenance(
            res_lang_cand,
            norm_lang,
            has_conflict=bool(lang_conflict)
        )

        # ── 6. Resolve Teaching Method ──
        teaching_method_cand: Optional[CandidateValue] = None
        if lesson.teaching_method:
            teaching_method_cand = CandidateValue(NotesContextSource.LESSON, lesson.teaching_method.lower(), lesson.teaching_method, 2)
        
        resolved_teaching_method = teaching_method_cand.value if teaching_method_cand else "unknown"
        field_provenances["teaching_method"] = cls._build_provenance(
            teaching_method_cand,
            resolved_teaching_method,
            has_conflict=False
        )

        # ── 7. Resolve Mastery State ──
        merged_mastery: Dict[str, float] = {}
        mastery_provenance_src = NotesContextSource.GENERIC

        # Assessment mastery
        if assessment.mastery:
            for k, v in assessment.mastery.items():
                norm_m = ContextNormalizer.normalize_mastery(v)
                if norm_m is not None:
                    merged_mastery[k.lower()] = norm_m
            mastery_provenance_src = NotesContextSource.ASSESSMENT

        # TeachMe mastery
        if teachme.session_id and student.current_learning_state.get("mastery"):
            for k, v in student.current_learning_state["mastery"].items():
                norm_m = ContextNormalizer.normalize_mastery(v)
                if norm_m is not None and k.lower() not in merged_mastery:
                    merged_mastery[k.lower()] = norm_m
            if mastery_provenance_src == NotesContextSource.GENERIC:
                mastery_provenance_src = NotesContextSource.TEACHME

        # Student profile mastery
        if not merged_mastery and student.current_learning_state.get("mastery"):
            for k, v in student.current_learning_state["mastery"].items():
                norm_m = ContextNormalizer.normalize_mastery(v)
                if norm_m is not None:
                    merged_mastery[k.lower()] = norm_m
            mastery_provenance_src = NotesContextSource.STUDENT

        if merged_mastery:
            field_provenances["mastery_state"] = FieldProvenance(
                value=merged_mastery,
                source=mastery_provenance_src,
                priority=SOURCE_PRIORITY_MAP[mastery_provenance_src],
                confidence=SOURCE_CONFIDENCE_MAP[mastery_provenance_src],
                status=ContextResolutionStatus.RESOLVED
            )
        else:
            field_provenances["mastery_state"] = FieldProvenance(
                value={},
                source=NotesContextSource.GENERIC,
                priority=8,
                confidence=0.0,
                status=ContextResolutionStatus.UNKNOWN
            )

        # ── 8. Resolve Misconceptions & Weak Concepts ──
        resolved_misconceptions: List[str] = []
        resolved_weak_concepts: List[str] = []

        # From TeachMe
        for m in teachme.misconceptions:
            desc = m.get("description") or m.get("misconception") if isinstance(m, dict) else str(m)
            if desc and desc not in resolved_misconceptions:
                resolved_misconceptions.append(desc)
        for c in teachme.confused_concepts:
            if c not in resolved_weak_concepts:
                resolved_weak_concepts.append(c)

        # From Assessment
        for m in assessment.misconceptions:
            desc = m.get("description") or m.get("misconception") if isinstance(m, dict) else str(m)
            if desc and desc not in resolved_misconceptions:
                resolved_misconceptions.append(desc)
        for w in assessment.weak_concepts:
            if w not in resolved_weak_concepts:
                resolved_weak_concepts.append(w)

        # From Lesson expected misconceptions
        for m in lesson.expected_misconceptions:
            if m and m not in resolved_misconceptions:
                resolved_misconceptions.append(m)

        # Low mastery concepts
        for cid, score in merged_mastery.items():
            if score < 0.60 and cid not in resolved_weak_concepts:
                resolved_weak_concepts.append(cid)

        # Provenance for misconceptions
        if resolved_misconceptions:
            src = NotesContextSource.TEACHME if teachme.misconceptions else (NotesContextSource.ASSESSMENT if assessment.misconceptions else NotesContextSource.LESSON)
            field_provenances["misconceptions"] = FieldProvenance(
                value=resolved_misconceptions,
                source=src,
                priority=SOURCE_PRIORITY_MAP[src],
                confidence=SOURCE_CONFIDENCE_MAP[src],
                status=ContextResolutionStatus.RESOLVED
            )
        else:
            field_provenances["misconceptions"] = FieldProvenance(
                value=[],
                source=NotesContextSource.GENERIC,
                priority=8,
                confidence=0.5,
                status=ContextResolutionStatus.UNKNOWN
            )

        # Calculate composite confidence
        conf_scores = [p.confidence for p in field_provenances.values() if p.status == ContextResolutionStatus.RESOLVED]
        composite_confidence = round(sum(conf_scores) / len(conf_scores), 2) if conf_scores else 0.50

        resolved_ctx = ResolvedContext(
            topic=norm_topic,
            raw_topic=res_raw_topic,
            class_level=res_class_display,
            grade=res_grade,
            subject=resolved_subject,
            curriculum=resolved_curriculum,
            language=norm_lang,
            teaching_method=resolved_teaching_method,
            mastery_state=merged_mastery,
            misconceptions=resolved_misconceptions,
            weak_concepts=resolved_weak_concepts
        )

        provenance_ctx = ProvenanceContext(
            field_sources=field_provenances,
            confidence=composite_confidence,
            conflicts=conflicts
        )

        return resolved_ctx, provenance_ctx

    @staticmethod
    def _pick_highest_priority(candidates: List[CandidateValue]) -> Optional[CandidateValue]:
        """Picks the candidate with the lowest priority number (rank 1 is highest priority)."""
        valid = [c for c in candidates if c.value is not None and str(c.value).strip() != ""]
        if not valid:
            return None
        return min(valid, key=lambda c: c.priority)

    @staticmethod
    def _build_provenance(
        cand: Optional[CandidateValue],
        final_value: Any,
        has_conflict: bool
    ) -> FieldProvenance:
        """Constructs FieldProvenance for a resolved value."""
        if not cand or final_value is None:
            return FieldProvenance(
                value=None,
                source=NotesContextSource.GENERIC,
                priority=8,
                confidence=0.0,
                status=ContextResolutionStatus.UNKNOWN,
                raw_value=None
            )

        status = ContextResolutionStatus.CONFLICTING if has_conflict else ContextResolutionStatus.RESOLVED
        return FieldProvenance(
            value=final_value,
            source=cand.source,
            priority=cand.priority,
            confidence=SOURCE_CONFIDENCE_MAP.get(cand.source, 0.50),
            status=status,
            raw_value=cand.raw_value
        )
