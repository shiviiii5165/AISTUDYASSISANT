"""
AI Notes Generator API Router
==============================
Independent top-level endpoints for generating, reading, listing, and deleting
Class 3–12 AI Study Notes from topics or pedagogical lesson/tutoring contexts.

CRITICAL INVARIANT:
This router is mounted at `/api/notes-generator`.
The existing `/api/notes` router is strictly preserved for handwritten OCR image uploads.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.core.dependencies import get_current_user
from app.core.security import limiter
from app.db.supabase_client import supabase
from app.services.notes.schemas import (
    GenerateNotesRequest, NotesDocument,
    AnalyzeContextRequest, AnalyzeContextResponse,
    CanonicalNotesContext
)
from app.services.notes.context import NotesContextAnalyzer, ContextSnapshotManager
from app.services.notes.context_extractor import NotesContextExtractor
from app.services.notes.decision import decide_notes_plan, NotesDecisionEngine
from app.services.notes.generator import NotesGenerator
from app.services.notes.repository import NotesRepository
from app.services.notes.validation import validate_notes, ValidationResult, ValidateNotesRequest
from app.services.notes.generation.engine import ensure_generation_plan
from app.services.notes.generation.schemas import GroundedSources

logger = logging.getLogger("teachgenie.api.notes_generator")
router = APIRouter()


@router.post("/context/analyze", response_model=AnalyzeContextResponse)
@limiter.limit("30/minute")
async def analyze_notes_context(
    request: Request,
    payload: AnalyzeContextRequest,
    current_user=Depends(get_current_user)
):
    """
    Step 1 Context Engine Endpoint:
    Collects, normalizes, prioritizes, and packages available educational context
    into CanonicalNotesContext. Persists immutable ContextSnapshot.
    Strictly deterministic — does NOT invoke LLMs or generate notes.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))

    try:
        ctx = await NotesContextAnalyzer.analyze_context(payload, user_id)
        snapshot = ContextSnapshotManager.create_snapshot(ctx, user_id)
        return AnalyzeContextResponse(
            success=True,
            context=ctx,
            snapshot_id=snapshot.snapshot_id
        )
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error analyzing context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze notes context: {str(e)[:200]}"
        )


@router.post("/decision/analyze")
@limiter.limit("30/minute")
async def analyze_notes_decision(
    request: Request,
    payload: Dict[str, Any],
    current_user=Depends(get_current_user)
):
    """
    Step 2 Decision Engine Endpoint:
    Deterministically evaluates CanonicalNotesContext or raw context payload into
    NotesGenerationPlan answering: 'Given what TeachGenie knows, what does this learner actually need in their notes?'
    Strictly deterministic — does NOT invoke LLMs or generate notes.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))

    try:
        if "resolved_context" in payload and "request" in payload:
            ctx = CanonicalNotesContext(**payload)
        else:
            req_model = AnalyzeContextRequest(**payload)
            ctx = await NotesContextAnalyzer.analyze_context(req_model, user_id)

        plan = decide_notes_plan(ctx)
        return {
            "success": True,
            "plan": plan
        }
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error analyzing notes decision: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze notes decision: {str(e)[:200]}"
        )



@router.post("/generate", response_model=NotesDocument)
@limiter.limit("15/minute")
async def generate_notes(
    request: Request,
    payload: GenerateNotesRequest,
    current_user=Depends(get_current_user)
):
    """
    Generates structured AI study notes from topic or lesson context.
    Executes: Context Extraction -> Decision Engine -> ModelRouter -> Quality Validation -> Persistence.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))

    try:
        # 1. Normalize context following the strict priority order
        ctx = await NotesContextExtractor.extract_canonical_context(payload, user_id)

        # 2. Decision Engine evaluates optimal formats, depth, and difficulty
        decision = NotesDecisionEngine.evaluate(ctx)

        # 3. Primary Generation with Validation & Bounded Repair
        doc = await NotesGenerator.generate(ctx, decision)

        # 4. Save to Repository
        NotesRepository.save_note(doc, user_id)

        return doc

    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error generating notes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study notes: {str(e)[:200]}"
        )


@router.post("/validate", response_model=ValidationResult)
@limiter.limit("30/minute")
async def validate_notes_endpoint(
    request: Request,
    payload: ValidateNotesRequest,
    current_user=Depends(get_current_user)
):
    """
    Step 4 Validation Endpoint.
    Validates a NotesDocument against CanonicalNotesContext, NotesGenerationPlan, and optional GroundedSources.
    """
    try:
        ctx = CanonicalNotesContext(**payload.context)
        plan = ensure_generation_plan(payload.plan)
        doc = NotesDocument(**payload.document)
        sources = GroundedSources(**payload.sources) if payload.sources else None

        result = await validate_notes(context=ctx, plan=plan, document=doc, sources=sources)
        return result
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error validating notes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate notes: {str(e)[:200]}"
        )


@router.get("/{note_id}", response_model=NotesDocument)
async def get_note(
    note_id: str,
    current_user=Depends(get_current_user)
):
    """Retrieves a single note document by ID, strictly enforcing user ownership."""
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    doc = NotesRepository.get_note(note_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note document not found or access denied."
        )
    return doc


@router.get("/")
async def list_notes(
    current_user=Depends(get_current_user)
):
    """Lists all note documents owned by the current authenticated user."""
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    notes = NotesRepository.list_user_notes(user_id)
    return {"notes": notes}


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user=Depends(get_current_user)
):
    """Deletes a note document owned by the user."""
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    success = NotesRepository.delete_note(note_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or could not be deleted."
        )
    return {"message": "Note deleted successfully", "id": note_id}


@router.get("/context/sources")
async def get_available_context_sources(
    current_user=Depends(get_current_user)
):
    """
    Returns available Roadmaps, Stages, and Teach Sessions owned by the student/teacher
    so the frontend can populate the 'Generate from existing lesson' dropdown.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    sources: Dict[str, Any] = {
        "roadmaps": [],
        "teach_sessions": [],
        "quizzes": []
    }

    if supabase:
        try:
            r_res = supabase.table("learning_roadmaps")\
                .select("id, topic, title, level, created_at")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()
            if r_res.data:
                sources["roadmaps"] = r_res.data

            t_res = supabase.table("teach_sessions")\
                .select("id, topic, level, mode, created_at")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()
            if t_res.data:
                sources["teach_sessions"] = t_res.data

            q_res = supabase.table("quizzes")\
                .select("id, title, topic, mode, created_at")\
                .eq("owner_user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()
            if q_res.data:
                sources["quizzes"] = q_res.data

        except Exception as e:
            logger.warning(f"Could not load context sources from Supabase: {e}")

    return sources
