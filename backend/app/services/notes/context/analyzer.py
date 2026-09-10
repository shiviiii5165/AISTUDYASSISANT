"""
TeachGenie Notes Context Engine — Main Context Analyzer
======================================================
Coordinates multi-source context collection, normalization, priority-based
resolution, conflict tracking, completeness scoring, and snapshot generation.
Answers: "What does TeachGenie currently know about this note-generation request?"
STRICT BOUNDARY: Does NOT choose format, depth, difficulty, or pedagogy.
"""
import logging
from typing import Dict, Any, Optional, List

from app.db.supabase_client import supabase
from app.services.knowledge.hybrid_search import hybrid_search_evidence
from .schemas import (
    CanonicalNotesContext, RequestContext, ExplicitInputContext,
    StudentContext, CurriculumContext, LessonContext,
    AssessmentContext, TeachMeContext, PPTContext, SourcesContext,
    AnalyzeContextRequest, ContextSnapshot
)
from .normalizer import ContextNormalizer
from .resolver import ContextResolver
from .completeness import CompletenessEvaluator
from .snapshot import ContextSnapshotManager

logger = logging.getLogger("teachgenie.notes.context_analyzer")


class NotesContextAnalyzer:
    """Core Context Engine for the independent TeachGenie Notes Module."""

    @classmethod
    async def analyze_context(
        cls,
        request: AnalyzeContextRequest,
        user_id: str = "anonymous"
    ) -> CanonicalNotesContext:
        """
        Orchestrates full context aggregation, normalization, deterministic resolution,
        conflict preservation, completeness evaluation, and snapshot creation.
        """
        logger.info(f"[NotesContextAnalyzer] Starting context analysis for topic='{request.topic}', user={user_id}")

        # ── 1. Normalize Explicit Input ──
        raw_top, norm_top = ContextNormalizer.normalize_topic(request.topic)
        grade_num, class_disp = ContextNormalizer.normalize_grade(request.class_level)
        norm_curr = ContextNormalizer.normalize_curriculum(request.curriculum)
        norm_lang = ContextNormalizer.normalize_language(request.language)

        explicit_ctx = ExplicitInputContext(
            topic=norm_top or raw_top,
            raw_topic=raw_top,
            class_level=class_disp,
            grade=grade_num,
            subject=request.subject.strip() if request.subject else None,
            curriculum=norm_curr,
            language=norm_lang,
            additional_instructions=request.additional_instructions
        )

        req_ctx = RequestContext(
            user_id=user_id,
            mode=request.mode or "topic"
        )

        # ── 2. Initialize Sub-contexts (from direct payloads if present) ──
        student_ctx = cls._init_student_context(request.student)
        curriculum_ctx = cls._init_curriculum_context(request.curriculum_data, norm_curr)
        lesson_ctx = cls._init_lesson_context(request.lesson)
        assessment_ctx = cls._init_assessment_context(request.assessment)
        teachme_ctx = cls._init_teachme_context(request.teach_me)
        ppt_ctx = cls._init_ppt_context(request.ppt)
        sources_ctx = cls._init_sources_context(request.sources)

        # ── 3. Enrich from Lineage IDs / Existing Store Backends ──
        lineage_ids = request.context or {}

        # Lesson Planner (Roadmap / Stage)
        roadmap_id = lineage_ids.get("roadmapId") or lineage_ids.get("roadmap_id")
        stage_id = lineage_ids.get("stageId") or lineage_ids.get("stage_id")
        if roadmap_id and lesson_ctx.status != "resolved":
            await cls._enrich_from_lesson_planner(lesson_ctx, roadmap_id, stage_id, user_id)

        # TeachMe Session
        teach_session_id = lineage_ids.get("teachSessionId") or lineage_ids.get("teach_session_id")
        if teach_session_id and teachme_ctx.status != "resolved":
            await cls._enrich_from_teachme(teachme_ctx, student_ctx, teach_session_id, user_id)

        # Quiz Assessment
        quiz_id = lineage_ids.get("quizId") or lineage_ids.get("quiz_id")
        if quiz_id and assessment_ctx.status != "resolved":
            await cls._enrich_from_quiz(assessment_ctx, quiz_id, user_id)

        # PPT Deck
        deck_id = lineage_ids.get("deckId") or lineage_ids.get("deck_id")
        if deck_id and ppt_ctx.status != "resolved":
            await cls._enrich_from_deck(ppt_ctx, deck_id, user_id)

        # RAG Grounded Sources
        doc_ids = lineage_ids.get("sourceDocumentIds") or lineage_ids.get("source_document_ids")
        if doc_ids and user_id and sources_ctx.status != "resolved":
            await cls._enrich_from_rag(sources_ctx, explicit_ctx.topic, doc_ids, user_id)

        # ── 4. Deterministic Resolution & Provenance Construction ──
        resolved_ctx, provenance_ctx = ContextResolver.resolve(
            explicit=explicit_ctx,
            lesson=lesson_ctx,
            curriculum=curriculum_ctx,
            student=student_ctx,
            assessment=assessment_ctx,
            teachme=teachme_ctx,
            ppt=ppt_ctx,
            sources=sources_ctx,
            mode=req_ctx.mode
        )

        # ── 5. Completeness Assessment ──
        completeness_ctx = CompletenessEvaluator.evaluate(
            resolved=resolved_ctx,
            explicit=explicit_ctx,
            lesson=lesson_ctx,
            curriculum=curriculum_ctx,
            student=student_ctx,
            assessment=assessment_ctx,
            teachme=teachme_ctx,
            ppt=ppt_ctx
        )

        # ── 6. Assemble CanonicalNotesContext ──
        canonical_ctx = CanonicalNotesContext(
            context_schema_version="1.0",
            request=req_ctx,
            explicit_input=explicit_ctx,
            student=student_ctx,
            curriculum=curriculum_ctx,
            lesson=lesson_ctx,
            assessment=assessment_ctx,
            teach_me=teachme_ctx,
            ppt=ppt_ctx,
            sources=sources_ctx,
            resolved_context=resolved_ctx,
            provenance=provenance_ctx,
            completeness=completeness_ctx
        )

        # ── 7. Create Context Snapshot ──
        snapshot = ContextSnapshotManager.create_snapshot(canonical_ctx, user_id)

        # ── 8. Safe Debug Log Representation (§36) ──
        cls._log_safe_debug_summary(canonical_ctx, snapshot.snapshot_id)

        return canonical_ctx

    # Sub-context initializers for direct payloads
    @staticmethod
    def _init_student_context(payload: Optional[Dict[str, Any]]) -> StudentContext:
        if not payload:
            return StudentContext(status="unknown")
        g_num, c_disp = ContextNormalizer.normalize_grade(payload.get("classLevel") or payload.get("class_level") or payload.get("grade"))
        raw_state = payload.get("currentLearningState") or payload.get("current_learning_state") or {}
        # Normalize mastery in learning state if present
        norm_mastery = {}
        for k, v in raw_state.get("mastery", {}).items():
            val = ContextNormalizer.normalize_mastery(v)
            if val is not None:
                norm_mastery[k.lower()] = val
        raw_state["mastery"] = norm_mastery

        return StudentContext(
            student_id=payload.get("studentId") or payload.get("student_id"),
            class_level=c_disp,
            grade=g_num,
            age_group=payload.get("ageGroup") or payload.get("age_group"),
            language=ContextNormalizer.normalize_language(payload.get("language")),
            learning_preferences=payload.get("learningPreferences") or payload.get("learning_preferences") or [],
            current_learning_state=raw_state,
            status="resolved"
        )

    @staticmethod
    def _init_curriculum_context(payload: Optional[Dict[str, Any]], fallback_board: Optional[str] = None) -> CurriculumContext:
        if not payload:
            if fallback_board:
                return CurriculumContext(board=fallback_board, status="resolved")
            return CurriculumContext(status="unknown")

        board = ContextNormalizer.normalize_curriculum(payload.get("board") or payload.get("curriculum") or fallback_board)
        g_num, _ = ContextNormalizer.normalize_grade(payload.get("grade"))
        return CurriculumContext(
            curriculum_id=payload.get("curriculumId") or payload.get("curriculum_id"),
            board=board,
            subject=payload.get("subject"),
            grade=g_num,
            course=payload.get("course"),
            chapter=payload.get("chapter"),
            unit=payload.get("unit"),
            curriculum_objectives=payload.get("curriculumObjectives") or payload.get("curriculum_objectives") or [],
            syllabus_references=payload.get("syllabusReferences") or payload.get("syllabus_references") or [],
            status="resolved"
        )

    @staticmethod
    def _init_lesson_context(payload: Optional[Dict[str, Any]]) -> LessonContext:
        if not payload:
            return LessonContext(status="unknown")
        return LessonContext(
            roadmap_id=payload.get("roadmapId") or payload.get("roadmap_id"),
            stage_id=payload.get("stageId") or payload.get("stage_id"),
            stage_title=payload.get("stageTitle") or payload.get("stage_title"),
            stage_objective=payload.get("stageObjective") or payload.get("stage_objective"),
            learning_objectives=payload.get("learningObjectives") or payload.get("learning_objectives") or [],
            activities=payload.get("activities") or [],
            teaching_method=payload.get("teachingMethod") or payload.get("teaching_method"),
            teacher_explanation=payload.get("teacherExplanation") or payload.get("teacher_explanation"),
            lesson_sequence=payload.get("lessonSequence") or payload.get("lesson_sequence") or [],
            teacher_instructions=payload.get("teacherInstructions") or payload.get("teacher_instructions") or [],
            expected_misconceptions=payload.get("expectedMisconceptions") or payload.get("expected_misconceptions") or [],
            status="resolved"
        )

    @staticmethod
    def _init_assessment_context(payload: Optional[Dict[str, Any]]) -> AssessmentContext:
        if not payload:
            return AssessmentContext(status="unknown")
        # Normalize mastery values
        norm_mastery = {}
        for k, v in (payload.get("mastery") or {}).items():
            val = ContextNormalizer.normalize_mastery(v)
            if val is not None:
                norm_mastery[k.lower()] = val

        score_val = payload.get("score") if payload.get("score") is not None else payload.get("latestScore")
        norm_score = ContextNormalizer.normalize_mastery(score_val) if score_val is not None else None

        # Normalize misconceptions
        raw_misc = payload.get("misconceptions") or []
        norm_misc = []
        for m in raw_misc:
            if isinstance(m, str):
                norm_misc.append({"concept": "general", "description": m, "severity": "medium", "source": "assessment"})
            elif isinstance(m, dict):
                norm_misc.append(m)

        return AssessmentContext(
            quiz_id=payload.get("quizId") or payload.get("quiz_id"),
            latest_score=norm_score,
            attempts=payload.get("attempts", 1),
            weak_concepts=payload.get("weakConcepts") or payload.get("weak_concepts") or [],
            mastery=norm_mastery,
            misconceptions=norm_misc,
            wrong_answer_patterns=payload.get("wrongAnswerPatterns") or payload.get("wrong_answer_patterns") or [],
            status="resolved"
        )

    @staticmethod
    def _init_teachme_context(payload: Optional[Dict[str, Any]]) -> TeachMeContext:
        if not payload:
            return TeachMeContext(status="unknown")
        raw_misc = payload.get("misconceptions") or []
        norm_misc = []
        for m in raw_misc:
            if isinstance(m, str):
                norm_misc.append({"concept": "general", "description": m, "source": "teachme"})
            elif isinstance(m, dict):
                norm_misc.append(m)

        return TeachMeContext(
            session_id=payload.get("sessionId") or payload.get("session_id"),
            misconceptions=norm_misc,
            confused_concepts=payload.get("confusedConcepts") or payload.get("confused_concepts") or [],
            learner_questions=payload.get("learnerQuestions") or payload.get("questionsAsked") or [],
            interventions=payload.get("interventions") or payload.get("teacherInterventions") or [],
            conversation_signals=payload.get("conversationSignals") or payload.get("conversation_signals") or {},
            summary=payload.get("summary"),
            status="resolved"
        )

    @staticmethod
    def _init_ppt_context(payload: Optional[Dict[str, Any]]) -> PPTContext:
        if not payload:
            return PPTContext(status="unknown")
        return PPTContext(
            deck_id=payload.get("deckId") or payload.get("deck_id"),
            slide_count=payload.get("slideCount") or payload.get("slide_count") or 0,
            slide_topics=payload.get("slideTopics") or payload.get("slide_topics") or [],
            key_points=payload.get("keyPoints") or payload.get("key_points") or [],
            examples=payload.get("examples") or [],
            formulas=payload.get("formulas") or [],
            diagram_ideas=payload.get("diagramIdeas") or payload.get("diagram_ideas") or [],
            summary=payload.get("summary"),
            status="resolved"
        )

    @staticmethod
    def _init_sources_context(payload: Optional[Dict[str, Any]]) -> SourcesContext:
        if not payload:
            return SourcesContext(status="unknown")
        return SourcesContext(
            source_documents=payload.get("sourceDocuments") or payload.get("source_documents") or [],
            evidence=payload.get("evidence") or [],
            metadata=payload.get("metadata") or {},
            status="resolved"
        )

    # Lineage Store Enrichment Handlers
    @classmethod
    async def _enrich_from_lesson_planner(
        cls,
        ctx: LessonContext,
        roadmap_id: str,
        stage_id: Optional[str],
        user_id: str
    ) -> None:
        try:
            from app.api.lesson_planner import _get_roadmap
            roadmap = _get_roadmap(roadmap_id, user_id)
            if roadmap:
                ctx.roadmap_id = roadmap_id
                ctx.stage_id = stage_id
                target_stages = roadmap.stages
                if stage_id:
                    matched = [s for s in roadmap.stages if s.id == stage_id]
                    if matched:
                        target_stages = matched

                for s in target_stages:
                    if stage_id and s.id == stage_id:
                        ctx.stage_title = s.title
                        r_top = getattr(roadmap, 'topic', '') or getattr(roadmap, 'title', '')
                        ctx.stage_topic = f"{s.title} ({r_top})" if r_top and s.title != r_top else s.title
                        ctx.teaching_method = "active"

                    for obj in s.objectives:
                        ctx.learning_objectives.append(obj.description)
                    for act in s.activities:
                        ctx.activities.append(f"{act.type.upper()}: {act.title} - {act.description}")
                    for tact in s.teacher_actions:
                        ctx.teacher_instructions.append(tact)
                    for sact in s.student_actions:
                        ctx.lesson_sequence.append(sact)
                    for misc in s.expected_misconceptions:
                        ctx.expected_misconceptions.append(misc)

                ctx.learning_objectives = list(dict.fromkeys(ctx.learning_objectives))
                ctx.activities = list(dict.fromkeys(ctx.activities))
                ctx.teacher_instructions = list(dict.fromkeys(ctx.teacher_instructions))
                ctx.expected_misconceptions = list(dict.fromkeys(ctx.expected_misconceptions))
                ctx.status = "resolved"
            else:
                ctx.status = "unavailable"
        except Exception as e:
            logger.warning(f"Could not enrich lesson context: {e}")
            ctx.status = "unavailable"

    @classmethod
    async def _enrich_from_teachme(
        cls,
        ctx: TeachMeContext,
        student_ctx: StudentContext,
        session_id: str,
        user_id: str
    ) -> None:
        try:
            from app.services.teach.tools import get_learning_state, get_lesson_plan
            state = get_learning_state(session_id)
            plan = get_lesson_plan(session_id)
            if state:
                ctx.session_id = session_id
                # Mastery
                for cid, score in state.mastery.items():
                    norm_s = ContextNormalizer.normalize_mastery(score)
                    if norm_s is not None:
                        student_ctx.current_learning_state.setdefault("mastery", {})[cid.lower()] = norm_s
                        if norm_s < 0.60 and cid not in ctx.confused_concepts:
                            ctx.confused_concepts.append(cid)

                # Misconceptions
                for m in state.misconceptions:
                    if hasattr(m, "misconception"):
                        ctx.misconceptions.append({"concept": getattr(m, "concept", "general"), "description": m.misconception, "source": "teachme"})
                    elif isinstance(m, str):
                        ctx.misconceptions.append({"concept": "general", "description": m, "source": "teachme"})

                if state.recent_history:
                    turns = [f"{h.get('role', 'user').title()}: {h.get('content', '')[:100]}" for h in state.recent_history[-4:]]
                    ctx.summary = " | ".join(turns)

                ctx.status = "resolved"
            else:
                ctx.status = "unavailable"
        except Exception as e:
            logger.warning(f"Could not enrich TeachMe context: {e}")
            ctx.status = "unavailable"

    @classmethod
    async def _enrich_from_quiz(
        cls,
        ctx: AssessmentContext,
        quiz_id: str,
        user_id: str
    ) -> None:
        if not supabase:
            ctx.status = "unavailable"
            return
        try:
            res = supabase.table("quiz_attempts")\
                .select("score, per_question_results, concept_performance")\
                .eq("quiz_id", quiz_id)\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(2)\
                .execute()

            if res.data:
                ctx.quiz_id = quiz_id
                ctx.attempts = len(res.data)
                for att in res.data:
                    c_perf = att.get("concept_performance") or {}
                    for c_name, c_score in c_perf.items():
                        norm_c = ContextNormalizer.normalize_mastery(c_score)
                        if norm_c is not None:
                            ctx.mastery[c_name.lower()] = norm_c
                            if norm_c < 0.60 and c_name not in ctx.weak_concepts:
                                ctx.weak_concepts.append(c_name)

                    results = att.get("per_question_results") or []
                    for q in results:
                        if q.get("is_correct") is False:
                            ctx.wrong_answer_patterns.append({
                                "question": q.get("question_text") or q.get("question", ""),
                                "student_answer": q.get("student_answer") or q.get("given_answer", ""),
                                "explanation": q.get("explanation", ""),
                            })
                ctx.status = "resolved"
            else:
                ctx.status = "unavailable"
        except Exception as e:
            logger.warning(f"Could not enrich Quiz context: {e}")
            ctx.status = "unavailable"

    @classmethod
    async def _enrich_from_deck(
        cls,
        ctx: PPTContext,
        deck_id: str,
        user_id: str
    ) -> None:
        if not supabase:
            ctx.status = "unavailable"
            return
        try:
            res = supabase.table("topic_decks").select("topic, depth, audience").eq("id", deck_id).eq("user_id", user_id).limit(1).execute()
            if res.data:
                deck = res.data[0]
                ctx.deck_id = deck_id
                ctx.slide_topics = [deck.get("topic", "")]
                ctx.summary = f"Presentation: {deck.get('topic', '')} ({deck.get('depth', '')} depth, {deck.get('audience', '')})"
                ctx.status = "resolved"
            else:
                ctx.status = "unavailable"
        except Exception as e:
            logger.warning(f"Could not enrich Deck context: {e}")
            ctx.status = "unavailable"

    @classmethod
    async def _enrich_from_rag(
        cls,
        ctx: SourcesContext,
        topic: str,
        doc_ids: List[str],
        user_id: str
    ) -> None:
        try:
            query = f"{topic} key concepts definitions formulas principles"
            evidence_items = await hybrid_search_evidence(
                user_id=user_id,
                query=query,
                document_ids=doc_ids,
                top_k=6,
            )
            for ev in evidence_items:
                ctx.evidence.append({
                    "source_name": ev.source_name,
                    "badge": ev.get_citation_badge(),
                    "snippet": ev.text[:300],
                    "page": ev.page or ev.page_number,
                    "slide": ev.slide or ev.slide_number,
                })
            ctx.status = "resolved" if ctx.evidence else "unavailable"
        except Exception as e:
            logger.warning(f"RAG search enrichment failed: {e}")
            ctx.status = "unavailable"

    @staticmethod
    def _log_safe_debug_summary(ctx: CanonicalNotesContext, snapshot_id: str) -> None:
        """Emits privacy-safe diagnostic telemetry following §36 requirements."""
        prov = ctx.provenance.field_sources
        class_src = prov.get("class_level").source.value if prov.get("class_level") else "unknown"
        sub_src = prov.get("subject").source.value if prov.get("subject") else "unknown"
        mast_src = prov.get("mastery_state").source.value if prov.get("mastery_state") else "unknown"
        misc_src = prov.get("misconceptions").source.value if prov.get("misconceptions") else "unknown"
        teach_src = prov.get("teaching_method").source.value if prov.get("teaching_method") else "unknown"

        summary = f"""
------------------------------------------------------------
NOTES CONTEXT ANALYSIS
------------------------------------------------------------
Topic:
    {ctx.resolved_context.topic}
Resolved Class:
    {ctx.resolved_context.class_level}
    Source: {class_src}
Resolved Subject:
    {ctx.resolved_context.subject}
    Source: {sub_src}
Mastery:
    {ctx.resolved_context.mastery_state or 'None'}
    Source: {mast_src}
Misconceptions:
    {ctx.resolved_context.misconceptions or 'None'}
    Source: {misc_src}
Teaching Method:
    {ctx.resolved_context.teaching_method}
    Source: {teach_src}
Conflicts:
    {len(ctx.provenance.conflicts)}
Completeness:
    {ctx.completeness.score}%
Context Schema:
    {ctx.context_schema_version}
Snapshot:
    {snapshot_id}
------------------------------------------------------------"""
        logger.info(summary)
