from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, List
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro, check_topic_deck_limit
from app.services.deck_service import generate_deck
import asyncio

router = APIRouter()

class GenerateDeckRequest(BaseModel):
    topic: str
    depth: str = "full"
    audience: str = "university"

@router.post("/generate")
async def create_deck(
    request: GenerateDeckRequest, 
    current_user = Depends(get_current_user),
    _ = Depends(require_pro),
    __ = Depends(check_topic_deck_limit)
):
    """
    Generate a PPT deck. Runs the full pipeline synchronously (inline)
    because Vercel serverless kills background tasks after the response.
    The frontend shows a loading state while waiting.
    """
    try:
        # Insert initial record
        res = supabase.table("topic_decks").insert({
            "user_id": current_user.id,
            "topic": request.topic,
            "depth": request.depth,
            "audience": request.audience,
            "status": "processing"
        }).execute()
        
        deck_id = res.data[0]["id"]
        
        # Run generation SYNCHRONOUSLY (not as background task)
        # This is required for Vercel serverless — background tasks get killed
        await generate_deck(
            request.topic,
            request.depth,
            request.audience,
            current_user.id,
            deck_id
        )
        
        # After generation, fetch the updated record to return the result
        updated = supabase.table("topic_decks").select("*").eq("id", deck_id).single().execute()
        deck = updated.data
        
        download_url = None
        if deck.get("status") == "ready" and deck.get("storage_path"):
            download_url = _get_signed_url(deck["storage_path"])
        
        return {
            "deck_id": deck_id, 
            "status": deck.get("status", "processing"),
            "slide_count": deck.get("slide_count"),
            "download_url": download_url,
            "error_message": deck.get("error_message")
        }
        
    except Exception as e:
        # If we have a deck_id, mark it as failed
        if 'deck_id' in dir():
            try:
                supabase.table("topic_decks").update({
                    "status": "failed",
                    "error_message": str(e)[:500]
                }).eq("id", deck_id).execute()
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
