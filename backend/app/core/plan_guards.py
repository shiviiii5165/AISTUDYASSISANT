from fastapi import Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase_client import supabase

def require_pro(current_user = Depends(get_current_user)):
    """Allow all users for now."""
    return current_user

def check_daily_question_limit(current_user = Depends(get_current_user)):
    """Allow all users for now."""
    return current_user

def check_pdf_upload_limit(current_user = Depends(get_current_user)):
    """Allow all users for now."""
    return current_user

def check_topic_deck_limit(current_user = Depends(get_current_user)):
    """Allow all users for now."""
    return current_user
