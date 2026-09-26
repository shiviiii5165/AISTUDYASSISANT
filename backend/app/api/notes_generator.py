"""
AI Notes Generator API Router
==============================
Independent top-level endpoints for generating, reading, listing, and deleting
Class 3–12 AI Study Notes from topics or pedagogical lesson/tutoring contexts.

CRITICAL INVARIANT:
This router is mounted at `/api/notes-generator`.
The existing `/api/notes` router is strictly preserved for handwritten OCR image uploads.
"""
import base64
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response

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
from app.services.notes.rendering.pdf_renderer import PDFRenderer
from app.services.notes.rendering.html_builder import HTMLNoteBuilder
from app.services.notes.certification import (
    StudentArtifactCertifier, DocumentQualityResult, CertifyArtifactRequest
)

logger = logging.getLogger("learnbygenie.api.notes_generator")
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
    NotesGenerationPlan answering: 'Given what LearnByGenie knows, what does this learner actually need in their notes?'
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
    Enforces API Security:
    - If snapshot_id is provided, loads the authoritative, immutable context snapshot server-side,
      preventing client-side context tamper or source trust escalation.
    - If plan is omitted or if authoritative derivation is required, derives the trusted plan
      server-side via NotesDecisionEngine.decide(ctx).
    - Ensures arbitrary user-controlled payloads cannot bypass validator gates or escalate unverified sources.
    """
    try:
        # Authoritative context resolution
        if payload.snapshot_id:
            snapshot = ContextSnapshotManager.get_snapshot(payload.snapshot_id)
            if not snapshot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Context snapshot '{payload.snapshot_id}' not found or expired."
                )
            ctx = snapshot.context
        elif payload.context:
            ctx = CanonicalNotesContext(**payload.context)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'snapshot_id' or 'context' payload must be provided for validation."
            )

        # Authoritative plan resolution
        if payload.plan:
            plan = ensure_generation_plan(payload.plan)
        else:
            plan = decide_notes_plan(ctx)

        doc = NotesDocument(**payload.document)
        sources = GroundedSources(**payload.sources) if payload.sources else None

        result = await validate_notes(context=ctx, plan=plan, document=doc, sources=sources)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error validating notes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate notes: {str(e)[:200]}"
        )


@router.post("/{note_id}/export-pdf")
@limiter.limit("20/minute")
async def export_note_pdf(
    request: Request,
    note_id: str,
    certify: bool = True,
    current_user=Depends(get_current_user)
):
    """
    Exports a NoteDocument as a deterministic, publication-grade student PDF.
    Optionally certifies the rendered artifact before returning.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    doc = NotesRepository.get_note(note_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note document not found or access denied."
        )

    try:
        html = HTMLNoteBuilder.build_html(doc)
        pdf_bytes = await PDFRenderer.render_document(doc)

        headers = {
            "Content-Disposition": f'attachment; filename="learnbygenie_notes_{note_id[:8]}.pdf"',
            "Content-Type": "application/pdf"
        }

        if certify:
            qa_result = await StudentArtifactCertifier.certify_artifact(
                document=doc,
                pdf_bytes=pdf_bytes,
                html_content=html
            )
            headers["X-LearnByGenie-Document-Hash"] = qa_result.document_hash
            headers["X-LearnByGenie-PDF-Hash"] = qa_result.pdf_hash
            headers["X-LearnByGenie-Certified"] = qa_result.artifact_status.value
            headers["X-LearnByGenie-Defects"] = str(len(qa_result.artifact_certification.defects))
            # Backward compatibility headers
            headers["X-TeachGenie-Document-Hash"] = qa_result.document_hash
            headers["X-TeachGenie-PDF-Hash"] = qa_result.pdf_hash
            headers["X-TeachGenie-Certified"] = qa_result.artifact_status.value
            headers["X-TeachGenie-Defects"] = str(len(qa_result.artifact_certification.defects))

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error exporting PDF for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export PDF: {str(e)[:200]}"
        )


@router.post("/certify-artifact", response_model=DocumentQualityResult)
@limiter.limit("20/minute")
async def certify_note_artifact(
    request: Request,
    payload: CertifyArtifactRequest,
    current_user=Depends(get_current_user)
):
    """
    Certifies a rendered student artifact (or generates and certifies PDF)
    against the LearnByGenie Quality Gate.
    """
    try:
        doc = NotesDocument(**payload.document)
        pdf_bytes = None
        if payload.pdf_base64:
            pdf_bytes = base64.b64decode(payload.pdf_base64)
        elif payload.html_content:
            pdf_bytes = await PDFRenderer.render_html(payload.html_content)
        else:
            pdf_bytes = await PDFRenderer.render_document(doc)

        ctx = CanonicalNotesContext(**payload.context) if payload.context else None
        plan = ensure_generation_plan(payload.plan) if payload.plan else None

        result = await StudentArtifactCertifier.certify_artifact(
            document=doc,
            pdf_bytes=pdf_bytes,
            html_content=payload.html_content,
            context=ctx,
            plan=plan
        )
        return result
    except Exception as e:
        logger.error(f"[NotesGeneratorAPI] Error certifying artifact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to certify artifact: {str(e)[:200]}"
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
