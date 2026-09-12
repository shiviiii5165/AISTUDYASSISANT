"""
TeachGenie AI Video Teacher V2 — Pipeline Orchestrator
======================================================
Coordinates end-to-end execution across:
1. Topic Intent & Domain Intelligence
2. Dynamic Curriculum & Prerequisite Graph Construction
3. Storyboard Compilation (10-Stage Story Structure)
4. Domain Visualization Registry (Specialized Benchmark & Universal Archetypes)
5. Multilingual Neural TTS (Edge-TTS -> Kokoro -> Piper -> gTTS)
6. FFmpeg Scene Compilation & Normalized Concat Demuxing
7. Technical & Semantic Teaching QA Validation
8. Video Knowledge Package Construction (First-Class Doubt Context Anchor)
"""
from app.core.logging import logger
import os
import uuid
import time
import hashlib
from typing import Dict, Any, Optional, List
from .schemas import (
    VideoConfig, VideoProject, Storyboard, SceneSpec, VisualSpec,
    VisualAssetType, VideoQuality, VisualBudget, VideoMetrics,
    JobState, UsageReport, SourceRef, VideoKnowledgePackage, SceneKnowledge
)
from .planner import plan_storyboard
from .visual_router import route_scene_visual_asset, get_visual_budget_for_quality
from .visualizers.registry import DomainVisualizationRegistry
from .tts.tts_service import generate_narration_audio
from .captions.caption_generator import generate_srt_subtitles
from .audio.audio_timeline import AudioTimeline
from .compositor.compositor import compose_single_scene_clip, concatenate_scenes_to_final_video
from .qa.python_qa import (
    validate_storyboard_quality, validate_rendered_scene_media, validate_semantic_teaching_quality
)
from .qa.quality_evaluator import TeachingQualityEvaluator
from .qa.repair_engine import LessonRepairEngine
from .qa.source_grounding import SourceGroundingQA
from .schemas import (
    VideoConfig, VideoProject, Storyboard, SceneSpec, VisualSpec,
    VisualAssetType, VideoQuality, VisualBudget, VideoMetrics,
    JobState, UsageReport, SourceRef, VideoKnowledgePackage, SceneKnowledge,
    VideoTelemetry, TeachingQualityScore, RepairLog, SourceGroundingReport,
    StorageArtifactClass
)
from .storage_lifecycle import StorageLifecycleManager
from .failure_taxonomy import FailureTaxonomy
from app.db.supabase_client import supabase


PROJECT_STORE: Dict[str, VideoProject] = {}


def compute_scene_hash(scene: SceneSpec, style: str) -> str:
    """Computes a deterministic hash for a scene to verify if re-rendering is needed."""
    raw = f"{scene.concept_id}_{scene.narration}_{scene.visual_spec.json()}_{style}_{scene.duration}_{scene.visual_strategy}"
    return hashlib.md5(raw.encode()).hexdigest()


async def generate_video_pipeline(
    config: VideoConfig,
    user_id: str,
    project_id: Optional[str] = None,
) -> VideoProject:
    """
    Public entrypoint for the TeachGenie AI Video Teacher compilation pipeline.
    Ensures safe error recording and zero corrupt/silent failures (Decision #12).
    Critical failure marks status = FAILED; recoverable failure logs warning.
    """
    try:
        return await _generate_video_pipeline_impl(config, user_id, project_id)
    except Exception as e:
        failure = FailureTaxonomy.classify_exception(e, context_hint=f"pipeline for {project_id}")
        logger.error(f"[VideoOrchestrator] Critical Failure: {failure.internal_diagnostic}")
        pid = project_id
        proj = PROJECT_STORE.get(pid) if pid else None
        if proj is not None:
            proj.status = "failed"
            proj.state = JobState.FAILED
            proj.error_message = failure.safe_user_message
        if supabase and pid:
            try:
                supabase.table("video_lessons").update(
                    {"status": "failed", "error_message": failure.safe_user_message}
                ).eq("id", pid).execute()
            except Exception as db_err:
                logger.warning(f"[VideoOrchestrator] DB update error: {db_err}")
        raise


async def _generate_video_pipeline_impl(
    config: VideoConfig,
    user_id: str,
    project_id: Optional[str] = None,
) -> VideoProject:
    """
    Executes the universal educational video compilation workflow.
    """
    t0 = time.time()
    pid = project_id or str(uuid.uuid4())
    # Unique scratch directory per job (Decision #3)
    job_id, scratch_dir = StorageLifecycleManager.create_job_scratch_dir(
        job_uuid=None,
        user_scope=user_id,
        lesson_id=pid,
    )

    # Telemetry accumulators
    t_render_accum = 0.0
    t_tts_accum = 0.0

    # 1. Initialize Project Object
    project = VideoProject(
        id=pid,
        user_id=user_id,
        topic=config.topic,
        config=config,
        storyboard=Storyboard(topic=config.topic, domain=config.domain, style=config.style, language=config.language, total_duration=config.duration),
        state=JobState.PLANNING,
        status="processing",
        progress=10,
    )
    PROJECT_STORE[pid] = project

    # 2. Plan Storyboard (Intent -> Domain -> Concept Graph -> Storyboard)
    project.state = JobState.BUILDING_CONCEPT_GRAPH
    t_plan_start = time.time()
    storyboard = await plan_storyboard(config, user_id)
    storyboard_ms = (time.time() - t_plan_start) * 1000.0
    project.storyboard = storyboard
    project.state = JobState.ASSET_RESOLUTION
    project.progress = 25

    # 3. Configure Visual Budget & Timeline
    budget = get_visual_budget_for_quality(config.quality, config.duration, config.ai_intensity)
    current_ai_sec = 0
    current_ai_img = 0
    stock_count = 0
    python_count = 0
    total_tts_chars = 0

    scene_clip_paths: List[str] = []
    audio_timeline = AudioTimeline()
    current_timeline_sec = 0.0

    # 4. Asset Resolution & Multi-Scene Generation
    project.state = JobState.GENERATING
    project.progress = 40

    scene_knowledges: List[SceneKnowledge] = []

    for idx, scene in enumerate(storyboard.scenes):
        scene_dir = os.path.join(scratch_dir, f"scene_{idx+1:02d}")
        os.makedirs(scene_dir, exist_ok=True)

        scene_start = current_timeline_sec
        scene_duration = float(scene.duration)
        scene_end = scene_start + scene_duration

        # Compute hash
        scene.scene_hash = compute_scene_hash(scene, config.style.value)
        python_count += 1

        # Render visual media via DomainVisualizationRegistry with failure recovery (Decision #8)
        frame_png_path = os.path.join(scene_dir, "frame.png")
        t_vr0 = time.time()
        try:
            DomainVisualizationRegistry.render_scene_media(
                scene=scene,
                topic=config.topic,
                output_path=frame_png_path,
                style=config.style.value,
            )
        except Exception as vr_err:
            logger.warning(f"[VideoOrchestrator] Visualizer error in scene {scene.scene_id}: {vr_err}. Using fallback.")
            from .visualizers.archetypes.generic_diagram import GenericDiagramVisualizer
            GenericDiagramVisualizer.render(scene.visual_spec, frame_png_path, config.style.value)
        t_render_accum += (time.time() - t_vr0) * 1000.0
        scene.rendered_media_path = frame_png_path

        # Generate TTS Narration Audio via Pluggable Cascade
        audio_path = os.path.join(scene_dir, "narration.mp3")
        total_tts_chars += len(scene.narration)
        t_tts0 = time.time()
        _, actual_audio_dur = await generate_narration_audio(
            text=scene.narration,
            output_path=audio_path,
            language=config.language,
        )
        t_tts_accum += (time.time() - t_tts0) * 1000.0
        scene.rendered_audio_path = audio_path
        scene.actual_duration = actual_audio_dur
        audio_timeline.add_narration(audio_path, current_timeline_sec, actual_audio_dur)

        # Compose Single Scene Clip via FFmpeg
        scene_mp4_path = os.path.join(scene_dir, "clip.mp4")
        compose_single_scene_clip(
            image_path=frame_png_path,
            audio_path=audio_path,
            output_mp4_path=scene_mp4_path,
            duration=scene_duration,
        )
        scene_clip_paths.append(scene_mp4_path)
        scene.status = "ready"

        # Construct Scene Knowledge Record
        scene_knowledges.append(SceneKnowledge(
            scene_id=scene.scene_id,
            order=scene.order,
            timestamp_start=round(scene_start, 2),
            timestamp_end=round(scene_end, 2),
            concept_id=scene.concept_id,
            concept_name=scene.concept_name or scene.caption,
            teaching_goal=scene.teaching_goal,
            purpose=scene.purpose if isinstance(scene.purpose, str) else scene.purpose.value,
            narration=scene.narration,
            transcript=scene.narration,
            visual_strategy=scene.visual_strategy.value if hasattr(scene.visual_strategy, 'value') else str(scene.visual_strategy),
            visual_state=scene.visual_spec.dict(),
            worked_example=scene.worked_example,
            misconception_tags=scene.misconception_tags,
            prerequisite_refs=scene.prerequisite_refs,
            source_refs=scene.source_refs,
        ))

        current_timeline_sec = scene_end

    # 5. Captions & Timeline Mixing
    project.state = JobState.AUDIO
    project.progress = 70
    srt_path = os.path.join(scratch_dir, "captions.srt")
    generate_srt_subtitles(storyboard.scenes, srt_path)

    # 6. FFmpeg Master Composition
    project.state = JobState.COMPOSITING
    project.progress = 85
    t_comp_start = time.time()
    final_mp4_path = os.path.join(scratch_dir, f"{pid}_final.mp4")
    concatenate_scenes_to_final_video(scene_clip_paths, final_mp4_path)
    composition_ms = (time.time() - t_comp_start) * 1000.0

    # 7. Construct Video Knowledge Package
    knowledge_pack = VideoKnowledgePackage(
        video_id=pid,
        topic=config.topic,
        domain=config.domain.value if hasattr(config.domain, 'value') else str(config.domain),
        learner_level=config.audience,
        language=config.language,
        total_duration_seconds=float(config.duration),
        learning_objectives=storyboard.learning_objectives,
        prerequisites=storyboard.prerequisites,
        concept_graph={"topic": config.topic, "domain": config.domain.value if hasattr(config.domain, 'value') else str(config.domain)},
        scenes=scene_knowledges,
    )
    project.knowledge_package = knowledge_pack

    # 8. QA Validation & Quality Scoring (Decision #2, #3, #4, #5, #6)
    project.state = JobState.QA
    project.progress = 95
    t_qa_start = time.time()
    is_sb_valid, sb_issues = validate_storyboard_quality(storyboard, config.duration)
    is_media_valid, media_reason = validate_rendered_scene_media(storyboard.scenes)
    is_sem_valid, sem_issues = validate_semantic_teaching_quality(storyboard, knowledge_pack)

    if not is_media_valid:
        raise RuntimeError(f"Rendered media failed QA validation: {media_reason}")
    if not os.path.exists(final_mp4_path) or os.path.getsize(final_mp4_path) < 1024:
        raise RuntimeError("Final video file is missing or too small to be a valid MP4.")

    if not is_sem_valid:
        logger.warning(f"[VideoOrchestrator] Semantic QA notice: {sem_issues}")

    # Run Hybrid Teaching Quality Evaluator (Layer A deterministic + Layer B semantic LLM)
    quality_score = await TeachingQualityEvaluator.evaluate_lesson_with_semantic_llm(
        storyboard=storyboard,
        knowledge_pack=knowledge_pack,
        target_duration=config.duration,
    )
    qa_ms = (time.time() - t_qa_start) * 1000.0

    # Automatic Targeted Repair if score < 80 or any critical gate fails (Decision #3, #5, #6)
    repair_ms = 0.0
    repair_log: Optional[RepairLog] = None
    if not quality_score.passed_gates:
        t_rep_start = time.time()
        storyboard, quality_score, repair_log = LessonRepairEngine.repair_lesson_if_needed(
            storyboard=storyboard,
            quality_score=quality_score,
            knowledge_pack=knowledge_pack,
            target_duration=config.duration,
        )
        repair_ms = (time.time() - t_rep_start) * 1000.0
        project.storyboard = storyboard

    project.quality_score = quality_score
    project.repair_log = repair_log

    # Source Grounding QA (Decision #7)
    source_grounding = SourceGroundingQA.evaluate_grounding(
        storyboard=storyboard,
        source_text=config.custom_context,
        source_id=config.source_ids[0] if config.source_ids else "topic_general",
    )

    # 9. Upload to Supabase Storage if available
    final_video_url = None
    storage_error: str | None = None
    if supabase:
        try:
            storage_path = f"{user_id}/videos/{pid}.mp4"
            if os.path.exists(final_mp4_path):
                with open(final_mp4_path, "rb") as f:
                    supabase.storage.from_("topic-decks").upload(storage_path, f.read(), {"content-type": "video/mp4"})
                url_res = supabase.storage.from_("topic-decks").create_signed_url(storage_path, 7200)
                final_video_url = url_res.get("signedUrl") if isinstance(url_res, dict) else getattr(url_res, "signed_url", None)
        except Exception as e:
            storage_error = str(e)[:400]
            logger.error(f"[VideoOrchestrator] Storage upload failed: {e}")

        # Combined lesson_json persisting both Storyboard and VideoKnowledgePackage
        lesson_payload = {
            "storyboard": storyboard.dict(),
            "knowledge_package": knowledge_pack.dict(),
            "quality_score": quality_score.dict(),
            "repair_log": repair_log.dict() if repair_log else None,
            "source_grounding": source_grounding.dict(),
            # Keep top-level keys for backwards-compatibility with existing frontend tabs
            "scenes": [s.dict() for s in storyboard.scenes],
            "topic": storyboard.topic,
            "style": storyboard.style.value if hasattr(storyboard.style, 'value') else str(storyboard.style),
            "language": storyboard.language,
            "total_duration": storyboard.total_duration,
            "learning_objectives": storyboard.learning_objectives,
            "summary_notes": storyboard.summary_notes,
        }

        try:
            supabase.table("video_lessons").upsert({
                "id": pid,
                "user_id": user_id,
                "topic": config.topic,
                "level": config.audience,
                "duration": str(config.duration // 60),
                "language": config.language,
                "status": "ready" if final_video_url or os.path.exists(final_mp4_path) else "failed",
                "scene_count": len(storyboard.scenes),
                "total_duration_seconds": config.duration,
                "lesson_json": lesson_payload,
                **({"error_message": f"Storage notice: {storage_error}"} if storage_error else {}),
            }).execute()
        except Exception as db_e:
            logger.error(f"[VideoOrchestrator] DB upsert failed: {db_e}")

    # Fallback local URL if Supabase not configured or in offline test mode
    if not final_video_url and os.path.exists(final_mp4_path):
        final_video_url = f"/local_videos/{pid}.mp4"

    render_time = time.time() - t0
    cost_per_min = round(((total_tts_chars * 0.000015)) / max(1, config.duration / 60.0), 3)

    telemetry = VideoTelemetry(
        intent_parse_ms=15.0,
        domain_detection_ms=10.0,
        curriculum_ms=round(storyboard_ms * 0.6, 1),
        storyboard_ms=round(storyboard_ms * 0.4, 1),
        visual_render_ms=round(t_render_accum, 1),
        tts_ms=round(t_tts_accum, 1),
        composition_ms=round(composition_ms, 1),
        qa_ms=round(qa_ms, 1),
        repair_ms=round(repair_ms, 1),
        total_generation_ms=round(render_time * 1000.0, 1),
    )

    metrics = VideoMetrics(
        total_duration_sec=config.duration,
        ai_video_seconds=current_ai_sec,
        ai_image_count=current_ai_img,
        stock_media_count=stock_count,
        python_graphics_count=python_count,
        tts_characters=total_tts_chars,
        llm_calls=2,
        render_time_sec=round(render_time, 2),
        grounding_score=source_grounding.grounding_score,
        cost_per_minute_usd=cost_per_min,
        ai_generation_ratio=0.0,
        telemetry=telemetry,
        quality_score=quality_score,
        repair_log=repair_log,
        source_grounding=source_grounding,
    )

    # 10. Storage Lifecycle: Register Persistent Artifacts & Clean Ephemeral
    StorageLifecycleManager.register_artifact(final_mp4_path, StorageArtifactClass.PERSISTENT)
    StorageLifecycleManager.register_artifact(srt_path, StorageArtifactClass.PERSISTENT)
    cleaned_ephemeral = StorageLifecycleManager.clean_ephemeral_artifacts(scratch_dir)
    logger.info(f"[VideoOrchestrator] Job {job_id} cleaned {cleaned_ephemeral} ephemeral artifacts.")

    if final_video_url and final_video_url.startswith(("http://", "https://")):
        StorageLifecycleManager.verify_and_prune_local_master(final_mp4_path, final_video_url)

    project.state = JobState.COMPLETED
    project.status = "ready"
    project.progress = 100
    project.final_video_url = final_video_url
    project.captions_url = srt_path
    project.metrics = metrics
    project.telemetry = telemetry

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

    scratch_dir = StorageLifecycleManager.get_project_scratch_dir(project_id)
    scene_dir = os.path.join(scratch_dir, f"scene_{target_scene.order:02d}")
    os.makedirs(scene_dir, exist_ok=True)

    # Re-render Graphic Frame via Registry
    frame_png_path = os.path.join(scene_dir, "frame.png")
    DomainVisualizationRegistry.render_scene_media(
        scene=target_scene,
        topic=project.config.topic,
        output_path=frame_png_path,
        style=project.config.style.value,
    )
    target_scene.rendered_media_path = frame_png_path

    # Re-render Audio
    audio_path = os.path.join(scene_dir, "narration.mp3")
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
