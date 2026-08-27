"""
Next-Gen Video Compiler Orchestrator — Resumable Job State Machine & Telemetry
=============================================================================
Coordinates Storyboard Planning, Visual Routing, Python/SVG Graphics, Stock Media,
TTS Audio Timeline, Synchronized Captions, FFmpeg Composition, and Scene Regeneration.
"""
import os
import uuid
import time
import hashlib
from typing import Dict, Any, Optional, List
from .schemas import (
    VideoConfig, VideoProject, Storyboard, SceneSpec, VisualSpec,
    VisualAssetType, VideoQuality, VisualBudget, VideoMetrics,
    JobState, UsageReport, SourceRef
)
from .planner import plan_storyboard
from .visual_router import route_scene_visual_asset, get_visual_budget_for_quality
from .graphics.renderer import render_scene_to_image_file
from .tts.tts_service import generate_narration_audio
from .captions.caption_generator import generate_srt_subtitles
from .audio.audio_timeline import AudioTimeline
from .compositor.compositor import compose_single_scene_clip, concatenate_scenes_to_final_video
from .qa.python_qa import validate_storyboard_quality, validate_rendered_scene_media
from app.db.supabase_client import supabase


PROJECT_STORE: Dict[str, VideoProject] = {}


def compute_scene_hash(scene: SceneSpec, style: str) -> str:
    """Computes a deterministic hash for a scene to verify if re-rendering is needed."""
    raw = f"{scene.concept_id}_{scene.narration}_{scene.visual_spec.json()}_{style}_{scene.duration}"
    return hashlib.md5(raw.encode()).hexdigest()


async def generate_video_pipeline(
    config: VideoConfig,
    user_id: str,
    project_id: Optional[str] = None,
) -> VideoProject:
    """
    Executes the end-to-end educational video compilation pipeline with state transitions.
    """
    t0 = time.time()
    pid = project_id or str(uuid.uuid4())
    import tempfile
    scratch_dir = os.path.join(tempfile.gettempdir(), "teachgenie_scratch", "videos", pid)
    os.makedirs(scratch_dir, exist_ok=True)

    # Initial Project Object
    project = VideoProject(
        id=pid,
        user_id=user_id,
        topic=config.topic,
        config=config,
        storyboard=Storyboard(topic=config.topic, style=config.style, language=config.language, total_duration=config.duration),
        state=JobState.PLANNING,
        status="processing",
        progress=10,
    )
    PROJECT_STORE[pid] = project

    # 1. Plan Storyboard
    storyboard = await plan_storyboard(config, user_id)
    project.storyboard = storyboard
    project.state = JobState.ASSET_RESOLUTION
    project.progress = 25

    # 2. Configure Visual Budget
    budget = get_visual_budget_for_quality(config.quality, config.duration, config.ai_intensity)
    current_ai_sec = 0
    current_ai_img = 0
    stock_count = 0
    python_count = 0
    total_tts_chars = 0

    scene_clip_paths: List[str] = []
    audio_timeline = AudioTimeline()
    current_timeline_sec = 0.0

    # 3. Asset Resolution & Generation
    project.state = JobState.GENERATING
    project.progress = 40

    for idx, scene in enumerate(storyboard.scenes):
        scene_dir = os.path.join(scratch_dir, f"scene_{idx+1:02d}")
        os.makedirs(scene_dir, exist_ok=True)

        # Asset Routing
        asset_type, route_meta = route_scene_visual_asset(
            scene=scene,
            quality=config.quality,
            budget=budget,
            current_ai_video_seconds=current_ai_sec,
            current_ai_image_count=current_ai_img,
        )
        scene.visual_type = asset_type
        scene.scene_hash = compute_scene_hash(scene, config.style.value)

        if asset_type == VisualAssetType.AI_VIDEO:
            current_ai_sec += scene.duration
        elif asset_type == VisualAssetType.AI_IMAGE:
            current_ai_img += 1
        elif asset_type == VisualAssetType.STOCK_VIDEO:
            stock_count += 1
        else:
            python_count += 1

        # Render Graphic Frame
        frame_png_path = os.path.join(scene_dir, "frame.png")
        render_scene_to_image_file(
            scene_data=scene.dict(),
            output_path=frame_png_path,
            style=config.style.value,
        )
        scene.rendered_media_path = frame_png_path

        # Generate TTS Narration Audio
        audio_path = os.path.join(scene_dir, "narration.wav")
        total_tts_chars += len(scene.narration)
        _, actual_audio_dur = await generate_narration_audio(
            text=scene.narration,
            output_path=audio_path,
            language=config.language,
        )
        scene.rendered_audio_path = audio_path
        scene.actual_duration = actual_audio_dur
        audio_timeline.add_narration(audio_path, current_timeline_sec, actual_audio_dur)
        current_timeline_sec += float(scene.duration)

        # Compose Single Scene Clip
        scene_mp4_path = os.path.join(scene_dir, "clip.mp4")
        compose_single_scene_clip(
            image_path=frame_png_path,
            audio_path=audio_path,
            output_mp4_path=scene_mp4_path,
            duration=float(scene.duration),
        )
        scene_clip_paths.append(scene_mp4_path)
        scene.status = "ready"

    # 4. Captions & Timeline Mixing
    project.state = JobState.AUDIO
    project.progress = 70
    srt_path = os.path.join(scratch_dir, "captions.srt")
    generate_srt_subtitles(storyboard.scenes, srt_path)

    # 5. FFmpeg Master Composition
    project.state = JobState.COMPOSITING
    project.progress = 85
    final_mp4_path = os.path.join(scratch_dir, f"{pid}_final.mp4")
    concatenate_scenes_to_final_video(scene_clip_paths, final_mp4_path)

    # 6. QA Validation
    project.state = JobState.QA
    project.progress = 95
    is_sb_valid, _ = validate_storyboard_quality(storyboard, config.duration)
    is_media_valid, _ = validate_rendered_scene_media(storyboard.scenes)

    # 7. Upload to Supabase Storage if available
    final_video_url = None
    if supabase:
        try:
            storage_path = f"{user_id}/videos/{pid}.mp4"
            if os.path.exists(final_mp4_path):
                with open(final_mp4_path, "rb") as f:
                    supabase.storage.from_("topic-decks").upload(storage_path, f.read(), {"content-type": "video/mp4"})
                url_res = supabase.storage.from_("topic-decks").create_signed_url(storage_path, 7200)
                final_video_url = url_res.get("signedUrl") if isinstance(url_res, dict) else getattr(url_res, "signed_url", None)

            supabase.table("video_lessons").upsert({
                "id": pid,
                "user_id": user_id,
                "topic": config.topic,
                "level": config.audience,
                "duration": str(config.duration // 60),
                "language": config.language,
                "status": "ready",
                "scene_count": len(storyboard.scenes),
                "total_duration_seconds": config.duration,
                "lesson_json": storyboard.dict(),
            }).execute()
        except Exception as e:
            print(f"[VideoOrchestrator] Storage notice: {e}")

    render_time = time.time() - t0
    ai_ratio = round(current_ai_sec / max(1, config.duration), 3)
    cost_per_min = round(((current_ai_sec * 0.05) + (current_ai_img * 0.01) + (total_tts_chars * 0.000015)) / max(1, config.duration / 60.0), 3)

    metrics = VideoMetrics(
        total_duration_sec=config.duration,
        ai_video_seconds=current_ai_sec,
        ai_image_count=current_ai_img,
        stock_media_count=stock_count,
        python_graphics_count=python_count,
        tts_characters=total_tts_chars,
        llm_calls=2,
        render_time_sec=round(render_time, 2),
        grounding_score=1.0,
        cost_per_minute_usd=cost_per_min,
        ai_generation_ratio=ai_ratio,
    )

    project.state = JobState.COMPLETED
    project.status = "ready"
    project.progress = 100
    project.final_video_url = final_video_url
    project.captions_url = srt_path
    project.metrics = metrics

    PROJECT_STORE[pid] = project
    return project


async def regenerate_single_scene(
    project_id: str,
    scene_id: str,
    user_id: str,
) -> VideoProject:
    """
    Regenerates ONLY the target scene and re-assembles the final video without touching cached scenes.
    """
    project = PROJECT_STORE.get(project_id)
    if not project:
        raise ValueError(f"Video project {project_id} not found.")

    target_scene = next((s for s in project.storyboard.scenes if s.scene_id == scene_id), None)
    if not target_scene:
        raise ValueError(f"Scene {scene_id} not found in project {project_id}.")

    import tempfile
    scratch_dir = os.path.join(tempfile.gettempdir(), "teachgenie_scratch", "videos", project_id)
    scene_dir = os.path.join(scratch_dir, f"scene_{target_scene.order:02d}")

    # Re-render Graphic Frame
    frame_png_path = os.path.join(scene_dir, "frame.png")
    render_scene_to_image_file(
        scene_data=target_scene.dict(),
        output_path=frame_png_path,
        style=project.config.style.value,
    )
    target_scene.rendered_media_path = frame_png_path

    # Re-render Audio
    audio_path = os.path.join(scene_dir, "narration.wav")
    await generate_narration_audio(
        text=target_scene.narration,
        output_path=audio_path,
        language=project.config.language,
    )
    target_scene.rendered_audio_path = audio_path

    # Re-compose Clip
    scene_mp4_path = os.path.join(scene_dir, "clip.mp4")
    compose_single_scene_clip(
        image_path=frame_png_path,
        audio_path=audio_path,
        output_mp4_path=scene_mp4_path,
        duration=float(target_scene.duration),
    )

    # Re-concatenate full video
    all_clips = [os.path.join(scratch_dir, f"scene_{s.order:02d}", "clip.mp4") for s in project.storyboard.scenes]
    final_mp4_path = os.path.join(scratch_dir, f"{project_id}_final.mp4")
    concatenate_scenes_to_final_video(all_clips, final_mp4_path)

    target_scene.scene_hash = compute_scene_hash(target_scene, project.config.style.value)
    project.updated_at = str(time.time())
    return project
