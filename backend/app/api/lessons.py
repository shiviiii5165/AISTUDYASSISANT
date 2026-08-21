from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.services.lesson_service import generate_lesson

router = APIRouter()

class GenerateLessonRequest(BaseModel):
    topic: str
    level: str = "Class 10"
    duration: str = "5"
    language: str = "hinglish"

@router.post("/generate")
async def create_lesson(
    request: GenerateLessonRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    try:
        # Insert initial record
        res = supabase.table("video_lessons").insert({
            "user_id": current_user.id,
            "topic": request.topic,
            "level": request.level,
            "duration": request.duration,
            "language": request.language,
            "status": "processing"
        }).execute()
        
        lesson_id = res.data[0]["id"]
        
        # Schedule background generation
        background_tasks.add_task(
            generate_lesson,
            request.topic,
            request.level,
            request.duration,
            request.language,
            current_user.id,
            lesson_id
        )
        
        return {"lesson_id": lesson_id, "status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lesson_id}")
async def get_lesson_status(lesson_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("video_lessons").select("*").eq("id", lesson_id).eq("user_id", current_user.id).single().execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    lesson = res.data
    
    return {
        "status": lesson["status"],
        "topic": lesson.get("topic"),
        "level": lesson.get("level"),
        "language": lesson.get("language"),
        "scene_count": lesson.get("scene_count"),
        "total_duration_seconds": lesson.get("total_duration_seconds"),
        "lesson_json": lesson.get("lesson_json"),
        "error_message": lesson.get("error_message")
    }

@router.get("/")
async def list_lessons(current_user = Depends(get_current_user)):
    res = supabase.table("video_lessons").select("id,topic,level,language,status,scene_count,total_duration_seconds,created_at").eq("user_id", current_user.id).order("created_at", desc=True).execute()
    return res.data

@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: str, current_user = Depends(get_current_user)):
    res = supabase.table("video_lessons").select("id").eq("id", lesson_id).eq("user_id", current_user.id).single().execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    supabase.table("video_lessons").delete().eq("id", lesson_id).execute()
    return {"status": "success"}
