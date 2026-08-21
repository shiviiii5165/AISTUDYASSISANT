from fastapi import Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase_client import supabase

def require_pro(current_user = Depends(get_current_user)):
    """Block free users from Pro-only modes entirely."""
    profile = supabase.table("profiles").select("plan").eq("id", current_user.id).single().execute()
    if profile.data["plan"] != "pro":
        raise HTTPException(
            status_code=403,
            detail={"error": "upgrade_required", "message": "This feature requires Pro. Upgrade to unlock it."}
        )
    return current_user

def check_daily_question_limit(current_user = Depends(get_current_user)):
    """Free users get 20 questions/day. Pro users are unlimited."""
    profile = supabase.table("profiles").select("plan").eq("id", current_user.id).single().execute()
    if profile.data["plan"] == "pro":
        return current_user

    allowed = supabase.rpc("increment_daily_usage", {
        "p_user_id": current_user.id, "p_limit": 20
    }).execute()

    if not allowed.data:
        raise HTTPException(
            status_code=403,
            detail={"error": "daily_limit_reached", "message": "You've used today's 20 free questions. Upgrade to Pro for unlimited access."}
        )
    return current_user

def check_pdf_upload_limit(current_user = Depends(get_current_user)):
    """Free users get 3 PDFs total. Pro users are unlimited."""
    profile = supabase.table("profiles").select("plan").eq("id", current_user.id).single().execute()
    if profile.data["plan"] == "pro":
        return current_user

    count = supabase.table("pdfs").select("id", count="exact").eq("user_id", current_user.id).execute()
    if count.count >= 3:
        raise HTTPException(
            status_code=403,
            detail={"error": "pdf_limit_reached", "message": "Free plan allows 3 PDFs. Upgrade to Pro for unlimited uploads."}
        )
    return current_user

def check_topic_deck_limit(current_user = Depends(get_current_user)):
    """Pro users get 15 decks per month. Free users get 0."""
    profile = supabase.table("profiles").select("plan").eq("id", current_user.id).single().execute()
    if profile.data["plan"] != "pro":
        raise HTTPException(
            status_code=403,
            detail={"error": "upgrade_required", "message": "Topic Decks are a Pro feature."}
        )

    # Check monthly usage
    allowed = supabase.rpc("increment_monthly_deck_usage", {
        "p_user_id": current_user.id, "p_limit": 15
    }).execute()

    if not allowed.data:
        raise HTTPException(
            status_code=403,
            detail={"error": "monthly_limit_reached", "message": "You've reached your monthly limit of 15 Topic Decks."}
        )
    return current_user
