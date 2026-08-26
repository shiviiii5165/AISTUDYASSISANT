from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro, check_topic_deck_limit
from app.services.deck_service import generate_outline_step, expand_outline_step, quality_review_step, render_deck_step
import asyncio

router = APIRouter()

class GenerateDeckRequest(BaseModel):
    topic: str
    depth: str = "full"
    audience: str = "university"

class ExpandRequest(BaseModel):
    topic: str
    audience: str
    outline_data: Dict[str, Any]

class RenderRequest(BaseModel):
    deck_id: str
    topic: str
    depth: str
    audience: str
    expanded_data: Dict[str, Any]


@router.post("/outline")
async def step_outline(
    request: GenerateDeckRequest, 
    current_user = Depends(get_current_user),
    _ = Depends(require_pro),
    __ = Depends(check_topic_deck_limit)
):
    """Step 1: Create DB record and generate outline."""
    try:
        res = supabase.table("topic_decks").insert({
            "user_id": current_user.id,
            "topic": request.topic,
            "depth": request.depth,
            "audience": request.audience,
            "status": "processing"
        }).execute()
        
        deck_id = res.data[0]["id"]
        outline_data = await generate_outline_step(request.topic, request.depth, request.audience)
        
        return {"deck_id": deck_id, "outline_data": outline_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.post("/expand")
async def step_expand(
    request: ExpandRequest, 
    current_user = Depends(get_current_user)
):
    """Step 2: Expand outline to full content + quality review pass."""
    try:
        expanded_data = await expand_outline_step(request.topic, request.audience, request.outline_data)
        
        # 🏆 Quality review: AI reviewer improves content before rendering
        reviewed_data = await quality_review_step(request.topic, request.audience, expanded_data)
        
        return {"expanded_data": reviewed_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.post("/render")
async def step_render(
    request: RenderRequest, 
    current_user = Depends(get_current_user)
):
    """Step 3: Generate images in parallel and render PPTX."""
    try:
        storage_path = await render_deck_step(
            request.deck_id, 
            current_user.id, 
            request.topic, 
            request.depth, 
            request.audience, 
            request.expanded_data
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
    res = supabase.table("topic_decks").select("*").eq("id", deck_id).eq("user_id", current_user.id).single().execute()
    
    if not res.data:
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
    return res.data

@router.delete("/{deck_id}")
async def delete_deck(deck_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("topic_decks").select("storage_path").eq("id", deck_id).eq("user_id", current_user.id).single().execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Deck not found")
        
    if res.data.get("storage_path"):
        try:
            supabase.storage.from_("topic-decks").remove([res.data["storage_path"]])
        except Exception as e:
            print(f"Failed to remove file from storage: {e}")
        
    supabase.table("topic_decks").delete().eq("id", deck_id).execute()
    return {"status": "success"}
