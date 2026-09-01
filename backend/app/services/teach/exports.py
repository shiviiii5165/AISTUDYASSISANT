"""
Teach Me Engine — Exports & Existing Systems Integrator
======================================================
Seamlessly converts structured lesson knowledge into:
1. PowerPoint Presentations (via presentation.orchestrator)
2. Educational Videos (via video.orchestrator)
3. Diagnostic Chapter Quizzes
"""
import uuid
from typing import Dict, Any, Optional
from .tools import get_lesson_plan, get_learning_state
from app.db.supabase_client import supabase


async def export_lesson_to_pptx(
    session_id: str,
    user_id: str,
    slide_count: int = 12,
    design: str = "academic",
    theme: str = "blue_professional",
) -> Dict[str, Any]:
    """
    Directly bridges active lesson concepts and grounded knowledge into
    the Advanced Presentation Engine without re-generating information from scratch.
    """
    plan = get_lesson_plan(session_id)
    state = get_learning_state(session_id)
    if not plan:
        raise ValueError(f"Lesson plan for session {session_id} not found.")

    from app.services.presentation.schemas import PresentationConfig, DesignSystem
    from app.services.presentation.orchestrator import generate_presentation_pipeline

    # 1. Formulate PresentationConfig
    count = slide_count if slide_count in [10, 11, 12, 13, 14, 15] else 12
    config = PresentationConfig(
        topic=plan.topic,
        slide_count=count,
        audience=plan.target_level.value if hasattr(plan.target_level, "value") else "university",
        language=plan.language,
        depth=plan.depth.value if hasattr(plan.depth, "value") else "full",
        design=DesignSystem(design) if design in [e.value for e in DesignSystem] else DesignSystem.ACADEMIC_CLEAN,
        theme=theme,
        source_type=plan.source_type.value if hasattr(plan.source_type, "value") else "general",
        source_id=plan.source_ids[0] if plan.source_ids else None,
        enable_diagrams=True,
        enable_images=True,
        enable_speaker_notes=True,
        enable_sources=True,
        enable_examples=True,
    )

    # 2. Run Presentation Pipeline
    spec, pptx_bytes = await generate_presentation_pipeline(config, user_id=user_id)

    # 3. Upload PPTX to Supabase Storage
    deck_id = str(uuid.uuid4())
    file_path = f"{user_id}/{deck_id}.pptx"
    download_url = None

    if supabase:
        try:
            supabase.storage.from_("topic-decks").upload(
                file_path,
                pptx_bytes,
                {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
            )
            url_res = supabase.storage.from_("topic-decks").create_signed_url(file_path, 3600)
            if isinstance(url_res, dict):
                download_url = url_res.get("signedUrl") or url_res.get("signedURL")
            elif hasattr(url_res, "signed_url"):
                download_url = url_res.signed_url
            elif hasattr(url_res, "signedUrl"):
                download_url = url_res.signedUrl

            supabase.table("topic_decks").insert({
                "id": deck_id,
                "user_id": user_id,
                "topic": plan.topic,
                "depth": config.depth,
                "audience": config.audience,
                "status": "ready",
                "storage_path": file_path,
                "slide_count": len(spec.slides),
            }).execute()
        except Exception as e:
            print(f"[TeachExport] PPT Storage note: {e}")

    return {
        "deck_id": deck_id,
        "topic": plan.topic,
        "slide_count": len(spec.slides),
        "download_url": download_url,
        "deck_title": spec.title,
    }


async def export_lesson_to_video(
    session_id: str,
    user_id: str,
    duration: int = 300,
    quality: str = "standard",
    style: str = "academic",
) -> Dict[str, Any]:
    """
    Directly bridges active Teach Me lesson concepts into the Video Generation Engine
    reusing existing learning state without calling a fresh LLM to recreate the lesson.
    """
    plan = get_lesson_plan(session_id)
    if not plan:
        raise ValueError(f"Lesson plan for session {session_id} not found.")

    from app.services.video.schemas import VideoConfig, VideoQuality, VideoStyle
    from app.services.video.orchestrator import generate_video_pipeline

    try:
        vqual = VideoQuality(quality)
    except Exception:
        vqual = VideoQuality.STANDARD

    try:
        vstyle = VideoStyle(style)
    except Exception:
        vstyle = VideoStyle.ACADEMIC

    config = VideoConfig(
        topic=plan.topic,
        source_type=plan.source_type,
        source_ids=plan.source_ids,
        lesson_session_id=session_id,
        duration=duration,
        quality=vqual,
        style=vstyle,
        language=plan.language,
        audience=plan.target_level.value if hasattr(plan.target_level, "value") else "btech",
    )

    project = await generate_video_pipeline(config, user_id=user_id)

    return {
        "project_id": project.id,
        "topic": plan.topic,
        "status": project.status,
        "final_video_url": project.final_video_url,
        "scene_count": len(project.storyboard.scenes),
        "total_duration_seconds": project.config.duration,
        "metrics": project.metrics.dict(),
    }
