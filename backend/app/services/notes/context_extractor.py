"""
AI Notes Generation Engine — Context Analyzer & Normalization Layer
====================================================================
Normalizes disparate educational sources (Roadmaps, Stages, TeachMe Sessions,
Quizzes, PPT Decks, and Hybrid Vector Search Evidence) into a canonical internal
NotesContext following the strict LearnByGenie Input Priority:

1. Explicit user instruction
2. Current lesson/stage context
3. Curriculum context (Board, Class, Subject)
4. Student learning state (Bayesian mastery, confidence)
5. Assessment / misconception signals
6. PPT / TeachMe supporting context
7. Retrieved educational evidence
8. Generic topic knowledge
"""
import json
import logging
from typing import Optional, List, Dict, Any

from app.db.supabase_client import supabase
from app.services.knowledge.hybrid_search import hybrid_search_evidence
from .schemas import (
    CanonicalNotesContext, GenerateNotesRequest,
    NoteDepth, NoteFormat
)

logger = logging.getLogger("learnbygenie.notes.context_extractor")


class NotesContextExtractor:
    """Extracts and normalizes multi-source educational context for Notes generation."""

    @staticmethod
    async def extract_canonical_context(
        request: GenerateNotesRequest,
        user_id: str
    ) -> CanonicalNotesContext:
        """
        Builds the canonical NotesContext strictly following the priority order.
        Delegates context aggregation, normalization, and resolution to NotesContextAnalyzer.
        Never throws unhandled exceptions if optional context records are missing.
        """
        from .context import NotesContextAnalyzer, AnalyzeContextRequest

        depth_val = None
        if request.requested_depth:
            try:
                depth_val = NoteDepth(request.requested_depth.lower())
            except ValueError:
                depth_val = NoteDepth.STANDARD

        format_val = None
        if request.requested_format:
            try:
                format_val = NoteFormat(request.requested_format.lower())
            except ValueError:
                format_val = None

        analyze_req = AnalyzeContextRequest(
            topic=request.topic,
            class_level=request.class_level,
            subject=request.subject,
            curriculum=request.curriculum,
            language=request.language,
            additional_instructions=request.user_instructions,
            mode=request.mode or "topic",
            context={
                "roadmap_id": request.roadmap_id,
                "stage_id": request.stage_id,
                "teach_session_id": request.teach_session_id,
                "quiz_id": request.quiz_id,
                "deck_id": request.deck_id,
                "source_document_ids": request.source_document_ids,
            }
        )

        canonical_ctx = await NotesContextAnalyzer.analyze_context(analyze_req, user_id)
        canonical_ctx.requested_depth = depth_val
        canonical_ctx.requested_format = format_val
        return canonical_ctx

    @staticmethod
    async def _enrich_from_lesson_planner(
        ctx: CanonicalNotesContext,
        roadmap_id: str,
        stage_id: Optional[str],
        user_id: str
    ) -> None:
        """Pulls objectives, activities, teacher instructions, and expected misconceptions from lesson planner."""
        try:
            # Check in-memory roadmaps first for speed & test suite compatibility
            from app.api.lesson_planner import _get_roadmap
            roadmap = _get_roadmap(roadmap_id, user_id)

            if roadmap:
                ctx.roadmap_title = roadmap.title or roadmap.topic
                if roadmap.level and ctx.class_level == "Class 10":
                    ctx.class_level = roadmap.level

                target_stages = roadmap.stages
                if stage_id:
                    target_stages = [s for s in roadmap.stages if s.id == stage_id] or roadmap.stages

                for s in target_stages:
                    if stage_id and s.id == stage_id:
                        ctx.stage_title = s.title
                        # Stage-specific topic takes priority
                        if not ctx.explicit_user_instructions and s.title:
                            ctx.topic = f"{s.title} ({roadmap.topic})"

                    for obj in s.objectives:
                        ctx.learning_objectives.append(obj.description)
                    for act in s.activities:
                        ctx.lesson_activities.append(f"{act.type.upper()}: {act.title} - {act.description}")
                    for tact in s.teacher_actions:
                        ctx.teacher_instructions.append(tact)
                    for sact in s.student_actions:
                        ctx.teaching_flow.append(sact)
                    for misc in s.expected_misconceptions:
                        ctx.expected_misconceptions.append(misc)

            # Remove duplicates while preserving order
            ctx.learning_objectives = list(dict.fromkeys(ctx.learning_objectives))
            ctx.lesson_activities = list(dict.fromkeys(ctx.lesson_activities))
            ctx.teacher_instructions = list(dict.fromkeys(ctx.teacher_instructions))
            ctx.expected_misconceptions = list(dict.fromkeys(ctx.expected_misconceptions))
        except Exception as e:
            logger.warning(f"Could not enrich context from lesson planner: {e}")

    @staticmethod
    async def _enrich_from_teachme_session(
        ctx: CanonicalNotesContext,
        session_id: str,
        user_id: str
    ) -> None:
        """Pulls student mastery profile, active misconceptions, and dialogue summary from TeachMe."""
        try:
            from app.services.teach.tools import get_learning_state, get_lesson_plan
            state = get_learning_state(session_id)
            plan = get_lesson_plan(session_id)

            if state:
                if state.user_id and state.user_id != user_id and user_id not in ("00000000-0000-0000-0000-000000000001", "anonymous"):
                    logger.warning("Ownership mismatch on teach session context")
                    return

                # Mastery mapping
                for cid, score in state.mastery.items():
                    ctx.student_mastery[cid] = round(score, 2)
                    if score < 0.60:
                        ctx.weak_concepts.append(cid)

                # Misconception items
                for m in state.misconceptions:
                    if hasattr(m, 'misconception'):
                        ctx.student_misconceptions.append(m.misconception)
                    elif isinstance(m, str):
                        ctx.student_misconceptions.append(m)

                # Recent history summary
                if state.recent_history:
                    turns = [f"{h.get('role', 'user').title()}: {h.get('content', '')[:100]}" for h in state.recent_history[-4:]]
                    ctx.teachme_summary = " | ".join(turns)

            if plan and not ctx.learning_objectives:
                for c in plan.concepts:
                    ctx.learning_objectives.append(f"Master {c.name}: {c.summary}")

            ctx.student_misconceptions = list(dict.fromkeys(ctx.student_misconceptions))
            ctx.weak_concepts = list(dict.fromkeys(ctx.weak_concepts))
        except Exception as e:
            logger.warning(f"Could not enrich context from TeachMe: {e}")

    @staticmethod
    async def _enrich_from_quiz(
        ctx: CanonicalNotesContext,
        quiz_id: str,
        user_id: str
    ) -> None:
        """Extracts question mistake patterns and low-scoring concepts from quiz attempts."""
        if not supabase:
            return
        try:
            # Query attempts for this quiz and user
            res = supabase.table("quiz_attempts")\
                .select("score, per_question_results, concept_performance")\
                .eq("quiz_id", quiz_id)\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(2)\
                .execute()

            if res.data:
                for att in res.data:
                    c_perf = att.get("concept_performance") or {}
                    for c_name, c_score in c_perf.items():
                        if isinstance(c_score, (int, float)) and c_score < 60:
                            ctx.weak_concepts.append(c_name)

                    # Question errors
                    results = att.get("per_question_results") or []
                    for q in results:
                        if q.get("is_correct") is False:
                            ctx.quiz_mistakes.append({
                                "question": q.get("question_text") or q.get("question", ""),
                                "student_answer": q.get("student_answer") or q.get("given_answer", ""),
                                "explanation": q.get("explanation", ""),
                            })

            ctx.weak_concepts = list(dict.fromkeys(ctx.weak_concepts))
        except Exception as e:
            logger.warning(f"Could not enrich context from Quiz: {e}")

    @staticmethod
    async def _enrich_from_deck(
        ctx: CanonicalNotesContext,
        deck_id: str,
        user_id: str
    ) -> None:
        """Extracts key themes from generated presentation decks."""
        if not supabase:
            return
        try:
            res = supabase.table("topic_decks").select("topic, depth, audience").eq("id", deck_id).eq("user_id", user_id).limit(1).execute()
            if res.data:
                deck = res.data[0]
                ctx.ppt_summary = f"Presentation: {deck.get('topic', '')} ({deck.get('depth', '')} depth, {deck.get('audience', '')})"
        except Exception as e:
            logger.warning(f"Could not enrich context from Deck: {e}")

    @staticmethod
    async def _enrich_from_rag_evidence(
        ctx: CanonicalNotesContext,
        doc_ids: List[str],
        user_id: str
    ) -> None:
        """Retrieves grounded evidence chunks using existing hybrid search."""
        try:
            query = f"{ctx.topic} key concepts principles definitions formulas"
            evidence_items = await hybrid_search_evidence(
                user_id=user_id,
                query=query,
                document_ids=doc_ids,
                top_k=6,
            )
            for ev in evidence_items:
                ctx.source_evidence.append({
                    "source_name": ev.source_name,
                    "badge": ev.get_citation_badge(),
                    "snippet": ev.text[:300],
                    "page": ev.page or ev.page_number,
                    "slide": ev.slide or ev.slide_number,
                })
        except Exception as e:
            logger.warning(f"RAG search enrichment failed: {e}")
