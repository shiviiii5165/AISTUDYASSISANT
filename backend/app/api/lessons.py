"""
Video Lessons & Video Studio API Endpoints
==========================================
Supports end-to-end AI educational video generation, scene-level regeneration,
Teach Me export to video, and project management.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.core.plan_guards import check_daily_question_limit
from app.services.video.schemas import VideoConfig, VideoQuality, VideoStyle, AspectRatio
from app.services.video.orchestrator import generate_video_pipeline, regenerate_single_scene, PROJECT_STORE
from app.services.knowledge.sources import SourceType
from app.core.logging import logger

router = APIRouter()


class GenerateLessonRequest(BaseModel):
    topic: str
    level: str = "B.Tech"
    duration: str = "5"
    language: str = "hinglish"
    style: str = "academic"
    quality: str = "standard"
    source_type: str = "topic"
    source_ids: Optional[List[str]] = Field(default_factory=list)
    youtube_url: Optional[str] = None
    lesson_session_id: Optional[str] = None


class RegenerateSceneRequest(BaseModel):
    scene_id: str


@router.post("/generate")
async def create_lesson_video(
    request: GenerateLessonRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(check_daily_question_limit),
):
    """
    Starts an asynchronous video generation job using the Production Video Engine.
    """
    try:
        duration_sec = int(request.duration) * 60 if request.duration.isdigit() else 300
        
        try:
            stype = SourceType(request.source_type)
        except Exception:
            stype = SourceType.TOPIC

        try:
            vstyle = VideoStyle(request.style)
        except Exception:
            vstyle = VideoStyle.ACADEMIC

        try:
            vqual = VideoQuality(request.quality)
        except Exception:
            vqual = VideoQuality.STANDARD

        config = VideoConfig(
            topic=request.topic.strip(),
            source_type=stype,
            source_ids=request.source_ids or [],
            youtube_url=request.youtube_url,
            lesson_session_id=request.lesson_session_id,
            duration=duration_sec,
            quality=vqual,
            style=vstyle,
            language=request.language,
            audience=request.level,
        )

        # Initial DB record
        lesson_id = None
        if supabase:
            try:
                res = supabase.table("video_lessons").insert({
                    "user_id": current_user.id,
                    "topic": request.topic,
                    "level": request.level,
                    "duration": str(duration_sec // 60),
                    "language": request.language,
                    "status": "processing",
                }).execute()
                if res.data:
                    lesson_id = res.data[0]["id"]
            except Exception as e:
                print(f"[VideoAPI] DB insert notice: {e}")

        if not lesson_id:
            import uuid
            lesson_id = str(uuid.uuid4())

        # Launch background generation pipeline
        background_tasks.add_task(
            generate_video_pipeline,
            config=config,
            user_id=current_user.id,
            project_id=lesson_id,
        )

        from fastapi import status
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"lesson_id": lesson_id, "project_id": lesson_id, "status": "processing"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to initiate video generation: {str(e)}")


@router.post("/{lesson_id}/regenerate-scene")
async def regenerate_scene_endpoint(
    lesson_id: str,
    request: RegenerateSceneRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """
    Starts an asynchronous background job to regenerate a single scene in the video.
    """
    try:
        background_tasks.add_task(
            regenerate_single_scene,
            project_id=lesson_id,
            scene_id=request.scene_id,
            user_id=current_user.id,
        )
        
        from fastapi import status
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "processing",
                "project_id": lesson_id,
                "scene_id": request.scene_id,
                "message": "Scene regeneration started."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene regeneration failed: {str(e)}")


@router.get("/{lesson_id}")
async def get_lesson_status(
    lesson_id: str,
    current_user=Depends(get_current_user),
):
    """
    Returns full lesson status, video URL, scenes, and transcript.
    """
    # Check in-memory active store first
    if lesson_id in PROJECT_STORE:
        proj = PROJECT_STORE[lesson_id]
        # Enforce ownership on the in-memory branch, matching the Supabase fallback.
        if getattr(proj, "user_id", None) != current_user.id:
            raise HTTPException(status_code=404, detail="Video lesson not found")
        return {
            "status": proj.status,
            "topic": proj.topic,
            "level": proj.config.audience,
            "language": proj.config.language,
            "scene_count": len(proj.storyboard.scenes),
            "total_duration_seconds": proj.config.duration,
            "lesson_json": proj.storyboard.dict(),
            "final_video_url": proj.final_video_url,
            "metrics": proj.metrics.dict(),
        }

    # Fallback to Supabase
    if supabase:
        try:
            res = supabase.table("video_lessons").select("*").eq("id", lesson_id).eq("user_id", current_user.id).single().execute()
            if res.data:
                lesson = res.data
                return {
                    "status": lesson.get("status", "ready"),
                    "topic": lesson.get("topic"),
                    "level": lesson.get("level"),
                    "language": lesson.get("language"),
                    "scene_count": lesson.get("scene_count"),
                    "total_duration_seconds": lesson.get("total_duration_seconds"),
                    "lesson_json": lesson.get("lesson_json"),
                    "error_message": lesson.get("error_message"),
                }
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Video lesson not found")


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

@router.get("/")
async def list_lessons(current_user=Depends(get_current_user)):
    """List recent video lessons for the user."""
    if supabase:
        try:
            res = supabase.table("video_lessons").select("id,topic,level,language,status,scene_count,total_duration_seconds,created_at,storage_path").eq("user_id", current_user.id).order("created_at", desc=True).execute()
            lessons = res.data or []
            for lesson in lessons:
                if lesson.get("status") == "ready" and lesson.get("storage_path"):
                    lesson["download_url"] = _get_signed_url(lesson["storage_path"])
            return lessons
        except Exception:
            pass
    return []


@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: str, current_user=Depends(get_current_user)):
    """Delete a video lesson owned by the current user.

    Reports outcomes honestly: 404 if the lesson does not exist or is not owned
    by the caller, a real 5xx if the database operation genuinely fails, and 200
    only when an owned lesson was actually removed.
    """
    if supabase:
        # Verify existence + ownership before claiming success.
        try:
            res = supabase.table("video_lessons") \
                .select("id") \
                .eq("id", lesson_id) \
                .eq("user_id", current_user.id) \
                .maybe_single() \
                .execute()
        except Exception as e:
            logger.error(f"Lookup failed while deleting lesson {lesson_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not verify lesson before deletion. Please try again.",
            )

        if not res or not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video lesson not found",
            )

        try:
            supabase.table("video_lessons").delete().eq("id", lesson_id).eq("user_id", current_user.id).execute()
        except Exception as e:
            logger.error(f"DB delete failed for lesson {lesson_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete lesson.",
            )

        PROJECT_STORE.pop(lesson_id, None)
        return {"status": "success"}

    # No database configured — operate on the in-memory store only.
    if lesson_id not in PROJECT_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video lesson not found",
        )
    del PROJECT_STORE[lesson_id]
    return {"status": "success"}
