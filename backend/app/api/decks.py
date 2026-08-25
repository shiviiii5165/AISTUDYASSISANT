from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import require_pro, check_topic_deck_limit
from app.services.deck_service import generate_deck

router = APIRouter()

class GenerateDeckRequest(BaseModel):
    topic: str
    depth: str = "full"
    audience: str = "university"

@router.post("/generate")
async def create_deck(
    request: GenerateDeckRequest, 
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    # Both require pro and check the monthly limit
    _ = Depends(require_pro),
    __ = Depends(check_topic_deck_limit)
):
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
        
        # Schedule background generation
        background_tasks.add_task(
            generate_deck,
            request.topic,
            request.depth,
            request.audience,
            current_user.id,
            deck_id
        )
        
        return {"deck_id": deck_id, "status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{deck_id}")
async def get_deck_status(deck_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("topic_decks").select("*").eq("id", deck_id).eq("user_id", current_user.id).single().execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Deck not found")
        
    deck = res.data
    download_url = None
    
    if deck["status"] == "ready" and deck.get("storage_path"):
        try:
            # Generate a signed URL valid for 1 hour
            # Supabase Python client returns an object with 'signedUrl' (camelCase)
            url_res = supabase.storage.from_("topic-decks").create_signed_url(deck["storage_path"], 3600)
            
            # Handle both dict-style and object-style responses from different supabase-py versions
            if isinstance(url_res, dict):
                download_url = url_res.get("signedUrl") or url_res.get("signedURL")
            elif hasattr(url_res, 'signed_url'):
                download_url = url_res.signed_url
            elif hasattr(url_res, 'signedUrl'):
                download_url = url_res.signedUrl
            else:
                # Fallback: try string conversion
                download_url = str(url_res) if url_res else None
                
        except Exception as e:
            print(f"Failed to create signed URL: {e}")
            # Don't crash — return the deck info without download URL
            download_url = None
        
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
