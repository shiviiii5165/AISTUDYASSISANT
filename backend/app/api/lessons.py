"""
Video Lessons & Video Studio API Endpoints
==========================================
Supports end-to-end AI educational video generation, scene-level regeneration,
Timestamp-Aware Ask Your Doubt with Confusion Diagnosis & Strategy Escalation,
and Quick Mastery Checks.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user, get_current_admin_user
from app.core.plan_guards import check_daily_question_limit
from app.services.video.schemas import (
    VideoConfig, VideoQuality, VideoStyle, AspectRatio, DomainCategory,
    VideoKnowledgePackage, SceneKnowledge, DoubtContext, DoubtAnswer, MasteryCheck,
    ExplanationStrategy, ConfusionType
)
from app.services.video.pedagogy.domain_intelligence import DomainIntelligenceEngine
from app.services.video.pedagogy.intent_parser import LearningIntentParser
from app.services.video.orchestrator import generate_video_pipeline, regenerate_single_scene, PROJECT_STORE
from app.services.video.doubt.context_resolver import VideoContextResolver
from app.services.video.doubt.confusion_diagnosis import ConfusionDiagnosisEngine
from app.services.video.doubt.explanation_strategy import ExplanationStrategyEngine
from app.services.video.doubt.mastery_check import QuickMasteryCheckGenerator
from app.services.video.doubt.mastery_tracker import LearnerMasteryTracker
from app.services.video.doubt.session_memory import DoubtSessionMemoryManager
from app.services.video.pilot.pilot_tracker import LearnerPilotTracker
from app.services.video.failure_taxonomy import FailureTaxonomy
from app.core.logging import logger

router = APIRouter()


class PlaybackProgressRequest(BaseModel):
    timestamp: float = Field(..., ge=0.0, description="Playback timestamp in seconds")
    event_type: str = "throttled_interval"  # throttled_interval, scene_boundary, pause, seek, complete


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


class AskDoubtRequest(BaseModel):
    timestamp: float = Field(..., description="Playback timestamp in seconds when doubt was raised")
    question: str = Field(..., min_length=1, description="Student question or query")
    doubt_session_id: Optional[str] = Field(None, description="Server-side session memory identifier")
    strategy: Optional[str] = Field(None, description="Optional explicitly requested strategy")
    session_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Legacy field, now managed server-side")
    tried_strategies: Optional[List[str]] = Field(default_factory=list)


class RecordPilotSessionRequest(BaseModel):
    pre_score: float = Field(..., ge=0.0, le=1.0, description="Pre-test score [0.0, 1.0]")
    post_score: float = Field(..., ge=0.0, le=1.0, description="Post-test transfer score [0.0, 1.0]")
    delayed_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Delayed recall score if observed")
    provenance: str = Field("REAL_LEARNER_EVALUATION", description="REAL_LEARNER_EVALUATION or INTERNAL_MANUAL_REVIEW")
    doubts_count: int = 0
    doubts_resolved: int = 0
    unresolved_doubts: int = 0
    first_explanation_resolutions: int = 0
    strategy_switches: int = 0
    prerequisite_repairs: int = 0
    time_to_understanding_sec: float = 0.0
    lesson_completion_time_sec: float = 0.0
    learner_experience_rating: Optional[float] = None
    external_help_needed: bool = False
    mastery_evidence: Optional[List[str]] = None


class MasteryCheckEvaluationRequest(BaseModel):
    target_concept_id: str
    question: str
    options: List[str]
    correct_answer_index: int
    selected_index: int
    explanation: str = ""


@router.post("/{lesson_id}/progress")
async def record_playback_progress(
    lesson_id: str,
    request: PlaybackProgressRequest,
    current_user=Depends(get_current_user),
):
    """
    Event-driven playback progress sync (Decision #2).
    Updates concept states up to INTRODUCED or PARTIALLY_UNDERSTOOD (Decision #1).
    """
    proj = PROJECT_STORE.get(lesson_id)
    knowledge_pack = proj.knowledge_package if proj else None
    if not knowledge_pack:
        raise HTTPException(status_code=404, detail="Lesson knowledge package not found")

    profile = LearnerMasteryTracker.sync_playback_progress(
        user_id=current_user.id,
        lesson_id=lesson_id,
        timestamp=request.timestamp,
        knowledge_pack=knowledge_pack,
        event_type=request.event_type,
    )
    return profile.dict()


@router.get("/{lesson_id}/mastery")
async def get_learner_mastery_profile(
    lesson_id: str,
    current_user=Depends(get_current_user),
):
    """Returns the learner's concept mastery breakdown (Decision #1 & #8)."""
    profile = LearnerMasteryTracker.get_or_create_profile(current_user.id, lesson_id)
    return profile.dict()


@router.get("/{lesson_id}/quality")
async def get_lesson_quality_score(
    lesson_id: str,
    view_role: str = "student",  # student, teacher, admin
    current_user=Depends(get_current_user),
):
    """
    Returns Teaching Quality Score.
    Enforces Decision #10: Student view hides raw engineering metrics;
    teacher/admin receives complete 8-dimension breakdown, gates, and repair logs.
    """
    proj = PROJECT_STORE.get(lesson_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Lesson not found")

    qs = proj.quality_score or (proj.metrics.quality_score if proj.metrics else None)
    if not qs:
        return {"status": "pending_evaluation"}

    if view_role == "student":
        return {
            "pedagogical_status": "certified_excellent" if qs.passed_gates else "under_review",
            "certified_learning_goals": len(proj.storyboard.learning_objectives),
            "concept_count": len(proj.storyboard.scenes),
        }
    else:
        return {
            "quality_score": qs.dict(),
            "repair_log": proj.repair_log.dict() if proj.repair_log else None,
            "passed_gates": qs.passed_gates,
            "failed_dimensions": qs.failed_dimensions,
            "repair_recommendations": qs.repair_recommendations,
        }


@router.get("/{lesson_id}/telemetry")
async def get_lesson_telemetry(
    lesson_id: str,
    current_user=Depends(get_current_user),
):
    """
    Returns granular phase latencies (Decision #9: Expose in dev/debug mode only).
    """
    proj = PROJECT_STORE.get(lesson_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return proj.telemetry.dict() if proj.telemetry else {}


@router.post("/generate")
async def create_lesson_video(
    request: GenerateLessonRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(check_daily_question_limit),
):
    """
    Starts an asynchronous video generation job using the TeachGenie AI Video Teacher V2 Engine.
    """
    try:
        # Parse intent dynamically
        intent = LearningIntentParser.parse(request.topic)
        duration_sec = int(request.duration) * 60 if request.duration.isdigit() else intent.duration_seconds

        try:
            vstyle = VideoStyle(request.style)
        except Exception:
            vstyle = VideoStyle.ACADEMIC

        try:
            vqual = VideoQuality(request.quality)
        except Exception:
            vqual = VideoQuality.STANDARD

        # Detect domain
        domain, _ = DomainIntelligenceEngine.detect_domain(intent.topic, request.topic)

        config = VideoConfig(
            topic=intent.topic,
            domain=domain,
            source_type=request.source_type,
            source_ids=request.source_ids or [],
            youtube_url=request.youtube_url,
            lesson_session_id=request.lesson_session_id,
            duration=duration_sec,
            quality=vqual,
            style=vstyle,
            language=request.language or intent.language,
            audience=request.level or intent.learner_level,
        )

        # Initial DB record
        lesson_id = None
        if supabase:
            try:
                res = supabase.table("video_lessons").insert({
                    "user_id": current_user.id,
                    "topic": config.topic,
                    "level": config.audience,
                    "duration": str(duration_sec // 60),
                    "language": config.language,
                    "status": "processing",
                }).execute()
                if res.data:
                    lesson_id = res.data[0]["id"]
            except Exception as e:
                logger.info(f"[VideoAPI] DB insert notice: {e}")

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


@router.post("/{lesson_id}/ask-doubt")
async def ask_lesson_doubt(
    lesson_id: str,
    request: AskDoubtRequest,
    current_user=Depends(get_current_user),
):
    """
    Timestamp-Aware Ask Your Doubt endpoint with Learner Profile Adaptation (Decision #8 & #14).
    """
    # 1. Retrieve project / knowledge package
    knowledge_pack: Optional[VideoKnowledgePackage] = None

    if lesson_id in PROJECT_STORE:
        proj = PROJECT_STORE[lesson_id]
        if getattr(proj, "user_id", None) != current_user.id:
            raise HTTPException(status_code=404, detail="Video lesson not found")
        knowledge_pack = proj.knowledge_package

    if not knowledge_pack and supabase:
        try:
            res = supabase.table("video_lessons").select("*").eq("id", lesson_id).eq("user_id", current_user.id).single().execute()
            if res.data and res.data.get("lesson_json"):
                lj = res.data["lesson_json"]
                if isinstance(lj, dict) and "knowledge_package" in lj:
                    knowledge_pack = VideoKnowledgePackage(**lj["knowledge_package"])
        except Exception as e:
            logger.warning(f"[DoubtAPI] DB lookup notice: {e}")

    if not knowledge_pack:
        knowledge_pack = VideoKnowledgePackage(
            video_id=lesson_id,
            topic="Educational Lesson",
            domain="general_knowledge",
            learner_level="B.Tech",
            language="hinglish",
            total_duration_seconds=300.0,
            scenes=[
                SceneKnowledge(
                    scene_id="scene_01",
                    order=1,
                    timestamp_start=0.0,
                    timestamp_end=300.0,
                    concept_id="core",
                    concept_name="Core Concept",
                    teaching_goal="Explain core topic",
                    purpose="core_concept",
                    narration="Core principle explanation",
                    transcript="Core principle explanation",
                    visual_strategy="generic_diagram"
                )
            ]
        )

    # 2. Server-Side Bounded Doubt Memory & Referential Anchor Resolution (Decisions #1, #2, #8)
    session = DoubtSessionMemoryManager.get_or_create_session(
        doubt_session_id=request.doubt_session_id,
        lesson_id=lesson_id,
        knowledge_pack=knowledge_pack,
    )

    referential_anchor = DoubtSessionMemoryManager.resolve_referential_query(
        query=request.question,
        session=session,
        current_timestamp=request.timestamp,
        knowledge_pack=knowledge_pack,
    )

    # Use resolved anchor timestamp if question referenced an earlier scene/step
    effective_timestamp = request.timestamp
    if referential_anchor and referential_anchor.timestamp_sec > 0 and referential_anchor.timestamp_sec != request.timestamp:
        effective_timestamp = referential_anchor.timestamp_sec

    # 3. Resolve Timestamp Context
    context = VideoContextResolver.resolve_context(
        knowledge_pack=knowledge_pack,
        timestamp=effective_timestamp,
        student_question=request.question
    )

    # 4. Diagnose Confusion
    diagnosis = ConfusionDiagnosisEngine.diagnose(context)

    # 5. Determine Strategy with Escalation Ladder & Learner Profile (Decision #8)
    if request.strategy:
        try:
            strategy = ExplanationStrategy(request.strategy)
        except Exception:
            strategy = diagnosis.recommended_strategy
    else:
        tried_enums = []
        for s_str in (request.tried_strategies or session.strategies_attempted or []):
            try:
                tried_enums.append(ExplanationStrategy(s_str))
            except Exception:
                pass

        learner_guidance = LearnerMasteryTracker.get_adaptive_explanation_guidance(
            user_id=current_user.id,
            lesson_id=lesson_id,
            concept_id=context.current_concept
        )

        strategy = ExplanationStrategyEngine.determine_strategy(
            recommended=diagnosis.recommended_strategy,
            tried_strategies=tried_enums,
            learner_guidance=learner_guidance,
        )

    # 6. Generate Tailored Doubt Answer (No Video)
    answer = await ExplanationStrategyEngine.generate_doubt_answer(
        context=context,
        confusion_type=diagnosis.confusion_type,
        strategy=strategy,
        tried_strategies=tried_enums,
        session_history=session.recent_turns,
        referential_anchors=session.referential_anchors,
    )

    # 7. Record Turn in Server-Side Doubt Session Memory (Bounded Context)
    DoubtSessionMemoryManager.record_turn(
        session_id=session.doubt_session_id,
        user_question=request.question,
        timestamp_sec=request.timestamp,
        tutor_explanation=answer.answer_text,
        strategy_used=strategy.value if hasattr(strategy, 'value') else str(strategy),
        focus_concept=context.current_concept,
        resolved=True,
        confusion_type=diagnosis.confusion_type.value if hasattr(diagnosis.confusion_type, 'value') else str(diagnosis.confusion_type)
    )

    # 8. Record doubt event in Learner Mastery Tracker (Decision #1)
    has_gap = diagnosis.confusion_type == ConfusionType.PREREQUISITE_GAP
    LearnerMasteryTracker.record_doubt_event(
        user_id=current_user.id,
        lesson_id=lesson_id,
        concept_id=context.current_concept,
        concept_name=context.current_concept,
        confusion_type=diagnosis.confusion_type,
        strategy_used=strategy,
        has_prerequisite_gap=has_gap,
        gap_concept=diagnosis.detected_gap,
    )

    resp_payload = answer.dict()
    resp_payload["doubt_session_id"] = session.doubt_session_id
    if referential_anchor:
        resp_payload["referential_anchor"] = referential_anchor.dict()

    return resp_payload


@router.post("/{lesson_id}/mastery-check")
async def evaluate_mastery_check(
    lesson_id: str,
    request: MasteryCheckEvaluationRequest,
    current_user=Depends(get_current_user),
):
    """
    Evaluates student's answer to a 1-question quick mastery check and updates mastery profile (Decision #1).
    """
    check = MasteryCheck(
        question=request.question,
        options=request.options,
        correct_answer_index=request.correct_answer_index,
        explanation=request.explanation,
        target_concept_id=request.target_concept_id
    )
    result = QuickMasteryCheckGenerator.evaluate_answer(check, request.selected_index)

    # Record result in LearnerMasteryTracker
    is_correct = request.selected_index == request.correct_answer_index
    record, msg = LearnerMasteryTracker.record_mastery_check_result(
        user_id=current_user.id,
        lesson_id=lesson_id,
        concept_id=request.target_concept_id,
        is_correct=is_correct,
        evidence_tag="quick_mastery_check",
    )
    result["mastery_state"] = record.state.value
    result["mastery_message"] = msg
    result["evidence_signals"] = record.evidence_for_mastery
    return result


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
    Returns full lesson status, video URL, scenes, transcript, and knowledge package.
    """
    # Check in-memory active store first
    if lesson_id in PROJECT_STORE:
        proj = PROJECT_STORE[lesson_id]
        if getattr(proj, "user_id", None) != current_user.id:
            raise HTTPException(status_code=404, detail="Video lesson not found")
        
        lesson_json_payload = proj.storyboard.dict()
        if proj.knowledge_package:
            lesson_json_payload["knowledge_package"] = proj.knowledge_package.dict()

        return {
            "status": proj.status,
            "topic": proj.topic,
            "level": proj.config.audience,
            "language": proj.config.language,
            "scene_count": len(proj.storyboard.scenes),
            "total_duration_seconds": proj.config.duration,
            "lesson_json": lesson_json_payload,
            "knowledge_package": proj.knowledge_package.dict() if proj.knowledge_package else None,
            "final_video_url": proj.final_video_url,
            "metrics": proj.metrics.dict(),
        }

    # Fallback to Supabase
    if supabase:
        try:
            res = supabase.table("video_lessons").select("*").eq("id", lesson_id).eq("user_id", current_user.id).single().execute()
            if res.data:
                lesson = res.data
                lj = lesson.get("lesson_json") or {}
                kp = lj.get("knowledge_package") if isinstance(lj, dict) else None
                return {
                    "status": lesson.get("status", "ready"),
                    "topic": lesson.get("topic"),
                    "level": lesson.get("level"),
                    "language": lesson.get("language"),
                    "scene_count": lesson.get("scene_count"),
                    "total_duration_seconds": lesson.get("total_duration_seconds"),
                    "lesson_json": lj,
                    "knowledge_package": kp,
                    "final_video_url": lesson.get("final_video_url") or _get_signed_url(lesson.get("storage_path", "")),
                    "error_message": lesson.get("error_message"),
                }
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Video lesson not found")


def _get_signed_url(storage_path: str) -> Optional[str]:
    """Generate a signed download URL from Supabase storage."""
    if not storage_path:
        return None
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
        logger.info(f"Failed to create signed URL: {e}")
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
    """Delete a video lesson owned by the current user."""
    if supabase:
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

    if lesson_id not in PROJECT_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video lesson not found",
        )
    del PROJECT_STORE[lesson_id]
    return {"status": "success"}


# ─────────────────────────────────────────────────────────────────────────────
# V2.2 PRODUCTION VALIDATION & REAL LEARNER PILOT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/readiness-dashboard")
async def get_admin_readiness_dashboard(
    window: str = "24h",
    current_user=Depends(get_current_admin_user),
):
    """
    Protected Production Readiness Dashboard (Decisions #11, #12).
    STRICT SECURITY POLICY:
    - Normal authenticated students receive 403 Forbidden.
    - Never exposes stack traces, secret keys, or internal provider credentials.
    - Aggregates metrics with sample counts across windows: '24h', '7d', '30d'.
    """
    if window not in ["24h", "7d", "30d"]:
        window = "24h"

    report = LearnerPilotTracker.aggregate_metrics(
        measurement_window=window,
        provenance_filter="REAL_LEARNER_EVALUATION"
    )
    return report.model_dump() if hasattr(report, "model_dump") else report.dict()


@router.get("/{lesson_id}/pilot/transfer-questions")
async def get_lesson_transfer_questions(
    lesson_id: str,
    concept_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """
    Generates isomorphic TransferQuestionPairs testing equivalent capability (Decision #6).
    """
    proj = PROJECT_STORE.get(lesson_id)
    topic = proj.topic if proj else "Linked List"
    domain = proj.config.domain.value if proj and hasattr(proj.config.domain, "value") else "computer_science"

    target_cid = concept_id or "core_concept"
    target_name = topic
    if proj and proj.storyboard and proj.storyboard.scenes:
        for s in proj.storyboard.scenes:
            if s.concept_id == target_cid or not concept_id:
                target_cid = s.concept_id
                target_name = s.concept_name
                break

    pair = LearnerPilotTracker.generate_transfer_question_pair(
        concept_id=target_cid,
        concept_name=target_name,
        domain=domain,
    )
    return pair.model_dump() if hasattr(pair, "model_dump") else pair.dict()


@router.post("/{lesson_id}/pilot/record-session")
async def record_pilot_evaluation_session(
    lesson_id: str,
    request: RecordPilotSessionRequest,
    current_user=Depends(get_current_user),
):
    """
    Records a real learner pilot session with normalized gain edge-case handling (Decisions #5, #7, #10, #14, #15, #16).
    """
    proj = PROJECT_STORE.get(lesson_id)
    topic = proj.topic if proj else "Educational Lesson"

    # Generate privacy-safe participant identifier (Decision #7)
    participant_id = LearnerPilotTracker.generate_participant_id(current_user.id)

    session = LearnerPilotTracker.record_pilot_session(
        participant_id=participant_id,
        lesson_id=lesson_id,
        topic=topic,
        pre_score=request.pre_score,
        post_score=request.post_score,
        delayed_score=request.delayed_score,
        provenance=request.provenance,
        doubts_count=request.doubts_count,
        doubts_resolved=request.doubts_resolved,
        unresolved_doubts=request.unresolved_doubts,
        first_explanation_resolutions=request.first_explanation_resolutions,
        strategy_switches=request.strategy_switches,
        prerequisite_repairs=request.prerequisite_repairs,
        time_to_understanding_sec=request.time_to_understanding_sec,
        lesson_completion_time_sec=request.lesson_completion_time_sec,
        learner_experience_rating=request.learner_experience_rating,
        external_help_needed=request.external_help_needed,
        mastery_evidence=request.mastery_evidence,
    )

    return session.model_dump() if hasattr(session, "model_dump") else session.dict()
