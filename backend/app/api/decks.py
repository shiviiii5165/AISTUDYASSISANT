from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro, check_topic_deck_limit
from app.services.deck_service import generate_outline_step, expand_outline_step, quality_review_step, render_deck_step
from app.services.presentation.schemas import PresentationConfig, DesignSystem
from app.services.presentation.orchestrator import generate_presentation_pipeline
import asyncio

router = APIRouter()


class GenerateDeckRequest(BaseModel):
    topic: str
    slide_count: int = 12
    depth: str = "full"
    audience: str = "university"
    design: str = "academic"
    theme: str = "blue_professional"
    source_type: str = "general"
    source_id: Optional[str] = None
    options: Optional[Dict[str, bool]] = None


class ExpandRequest(BaseModel):
    topic: str
    audience: str
    outline_data: Dict[str, Any]
    slide_count: int = 12
    source_type: str = "general"
    source_id: Optional[str] = None


class RenderRequest(BaseModel):
    deck_id: str
    topic: str
    depth: str = "full"
    audience: str = "university"
    design: str = "academic"
    theme: str = "blue_professional"
    expanded_data: Dict[str, Any]


@router.post("/outline")
async def step_outline(
    request: GenerateDeckRequest, 
    current_user = Depends(get_current_user),
    _ = Depends(require_pro),
    __ = Depends(check_topic_deck_limit)
):
    """Step 1: Create DB record and generate N-slide outline (10..15 slides)."""
    try:
        res = supabase.table("topic_decks").insert({
            "user_id": current_user.id,
            "topic": request.topic,
            "depth": request.depth,
            "audience": request.audience,
            "status": "processing"
        }).execute()
        
        deck_id = res.data[0]["id"]
        outline_data = await generate_outline_step(
            topic=request.topic,
            depth=request.depth,
            audience=request.audience,
            slide_count=request.slide_count,
            design=request.design,
            theme=request.theme,
            source_type=request.source_type,
            source_id=request.source_id,
            user_id=current_user.id,
        )
        
        return {"deck_id": deck_id, "outline_data": outline_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.post("/expand")
async def step_expand(
    request: ExpandRequest, 
    current_user = Depends(get_current_user)
):
    """Step 2: Expand outline to full content in 5-slide batches + quality review pass."""
    try:
        expanded_data = await expand_outline_step(
            topic=request.topic,
            audience=request.audience,
            outline_data=request.outline_data,
            slide_count=request.slide_count,
            source_type=request.source_type,
            source_id=request.source_id,
            user_id=current_user.id,
        )
        
        reviewed_data = await quality_review_step(request.topic, request.audience, expanded_data)
        return {"expanded_data": reviewed_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.post("/render")
async def step_render(
    request: RenderRequest, 
    current_user = Depends(get_current_user)
):
    """Step 3: Generate diagrams, resolve visuals, and render PPTX."""
    try:
        storage_path = await render_deck_step(
            deck_id=request.deck_id, 
            user_id=current_user.id, 
            topic=request.topic, 
            depth=request.depth, 
            audience=request.audience, 
            final_deck_json=request.expanded_data,
            design=request.design,
            theme=request.theme,
        )
        
        download_url = _get_signed_url(storage_path)
        
        # Get final slide count
        updated = supabase.table("topic_decks").select("slide_count").eq("id", request.deck_id).single().execute()
        
        return {
            "status": "ready",
            "download_url": download_url,
            "slide_count": updated.data.get("slide_count") if updated.data else 0
        }
    except Exception as e:
        try:
            supabase.table("topic_decks").update({
                "status": "failed",
                "error_message": str(e)[:500]
            }).eq("id", request.deck_id).execute()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e)[:500])


async def _background_generate_deck(
    deck_id: str,
    user_id: str,
    config: PresentationConfig
):
    try:
        # Run Pipeline
        spec, pptx_bytes = await generate_presentation_pipeline(config, user_id=user_id)

        # Upload to Supabase Storage
        file_path = f"{user_id}/{deck_id}.pptx"
        try:
            supabase.storage.from_("topic-decks").upload(
                file_path,
                pptx_bytes,
                {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
            )
        except Exception as storage_err:
            print(f"[Decks API] Storage upload note: {storage_err}")

        supabase.table("topic_decks").update({
            "status": "ready",
            "storage_path": file_path,
            "slide_count": len(spec.slides)
        }).eq("id", deck_id).execute()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            supabase.table("topic_decks").update({
                "status": "failed",
                "error_message": str(e)[:500]
            }).eq("id", deck_id).execute()
        except:
            pass

@router.post("/generate-advanced")
async def generate_advanced(
    request: GenerateDeckRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    _ = Depends(require_pro),
    __ = Depends(check_topic_deck_limit)
):
    """One-click advanced presentation generation pipeline mapped to a background queue."""
    try:
        # 1. Create DB record
        res = supabase.table("topic_decks").insert({
            "user_id": current_user.id,
            "topic": request.topic,
            "depth": request.depth,
            "audience": request.audience,
            "status": "processing"
        }).execute()
        deck_id = res.data[0]["id"]

        # 2. Build PresentationConfig
        options = request.options or {}
        config = PresentationConfig(
            topic=request.topic,
            slide_count=request.slide_count if request.slide_count in [10, 11, 12, 13, 14, 15] else 12,
            audience=request.audience,
            language="english",
            depth=request.depth,
            design=DesignSystem(request.design) if request.design in [e.value for e in DesignSystem] else DesignSystem.ACADEMIC_CLEAN,
            theme=request.theme,
            source_type=request.source_type,
            source_id=request.source_id,
            enable_diagrams=options.get("diagrams", True),
            enable_images=options.get("images", True),
            enable_speaker_notes=options.get("speaker_notes", True),
            enable_sources=options.get("sources", True),
            enable_examples=options.get("examples", True),
            enable_quiz=options.get("quiz", False),
        )

        # 3. Queue Background Task
        background_tasks.add_task(_background_generate_deck, deck_id, current_user.id, config)

        from fastapi import status
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "deck_id": deck_id,
                "status": "processing",
                "message": "Generation started in the background. Poll /{deck_id} for status."
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)[:500])


def _get_signed_url(storage_path: str) -> Optional[str]:
    """Generate a signed download URL from Supabase storage."""
    try:
        url_res = supabase.storage.from_("topic-decks").create_signed_url(storage_path, 3600)
        
        if isinstance(url_res, dict):
            return url_res.get("signedUrl") or url_res.get("signedURL")
        elif hasattr(url_res, 'signed_url'):
            return url_res.signed_url
        elif hasattr(url_res, 'signedUrl'):
            return url_res.signedUrl
        else:
            return str(url_res) if url_res else None
    except Exception as e:
        print(f"Failed to create signed URL: {e}")
        return None


@router.get("/{deck_id}")
async def get_deck_status(deck_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("topic_decks").select("*").eq("id", deck_id).eq("user_id", current_user.id).maybe_single().execute()

    if not res or not res.data:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck = res.data
    download_url = None
    
    if deck["status"] == "ready" and deck.get("storage_path"):
        download_url = _get_signed_url(deck["storage_path"])
        
    return {
        "status": deck["status"],
        "slide_count": deck.get("slide_count"),
        "download_url": download_url,
        "error_message": deck.get("error_message")
    }


@router.get("/")
async def list_decks(current_user = Depends(get_current_user)):
    res = supabase.table("topic_decks").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
    decks = res.data or []
    for deck in decks:
        if deck.get("status") == "ready" and deck.get("storage_path"):
            deck["download_url"] = _get_signed_url(deck["storage_path"])
    return decks


@router.delete("/{deck_id}")
async def delete_deck(deck_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("topic_decks").select("storage_path").eq("id", deck_id).eq("user_id", current_user.id).maybe_single().execute()

    if not res or not res.data:
        raise HTTPException(status_code=404, detail="Deck not found")

    if res.data.get("storage_path"):
        try:
            supabase.storage.from_("topic-decks").remove([res.data["storage_path"]])
        except Exception as e:
            print(f"Failed to remove file from storage: {e}")
        
    supabase.table("topic_decks").delete().eq("id", deck_id).execute()
    return {"status": "success"}
