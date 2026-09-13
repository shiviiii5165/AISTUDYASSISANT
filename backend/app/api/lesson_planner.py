import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.services.lesson_planner.schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageReadiness,
    NextBestAction, ResourceType, ResourceStatus, ResourceRecommendation,
    RoadmapStatus, ClassType, StageActivity, LearningObjective, BloomLevel,
    StageAction
)
from app.services.lesson_planner.generator import RoadmapGenerator
from app.services.lesson_planner.engine import (
    TimeBudgetEngine, PrerequisiteEngine, LessonHealthValidator, 
    StateMachineEngine, ResourceRecommenderEngine, RemedialEngine,
    StageOperationsEngine, ChangeImpactEngine
)
from app.services.lesson_planner.adapters import (
    PPTAdapter, VideoAdapter, TeachMeAdapter, QuizAdapter, NotesAdapter
)
from app.services.lesson_planner.youtube_recommendation import YouTubeRecommendationService
from app.services.lesson_planner.learning_materials import ExtraLearningMaterialsService
from app.services.lesson_resources.service import StageResourceIntelligenceService

logger = logging.getLogger("teachgenie.api.lesson_planner")
router = APIRouter()

# In-memory store fallback for test suites and offline operation
_MEMORY_ROADMAPS: Dict[str, LearningRoadmap] = {}
# Parallel map of roadmap_id -> owning user_id, since LearningRoadmap carries no
# user_id. Used to enforce ownership on the in-memory cache branch of _get_roadmap.
_MEMORY_ROADMAP_OWNERS: Dict[str, str] = {}


# Request Models
class ParsePromptRequest(BaseModel):
    prompt: str


class GenerateRoadmapRequest(BaseModel):
    topic: str
    level: str = "B.Tech"
    language: str = "hinglish"
    class_type: str = "Interactive Lecture"
    target_duration_minutes: int = 60
    custom_context: Optional[str] = None
    source_refs: Optional[List[Dict[str, Any]]] = None


class EditStageRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[StageStatus] = None
    mastery: Optional[int] = None
    teacher_actions: Optional[List[str]] = None
    student_actions: Optional[List[str]] = None
    checkpoint_questions: Optional[List[str]] = None
    expected_version: int = 1


class ReorderStagesRequest(BaseModel):
    stage_ids: List[str]
    expected_version: int = 1


class MergeStagesRequest(BaseModel):
    stage_id_1: str
    stage_id_2: str
    new_title: Optional[str] = None
    expected_version: int = 1


class SplitStageRequest(BaseModel):
    stage_id: str
    split_title_1: str
    split_title_2: str
    duration_1: int
    duration_2: int
    expected_version: int = 1


class CreateRemedialRequest(BaseModel):
    target_stage_id: str
    weak_prereq_title: Optional[str] = None
    expected_version: int = 1


# Helper to persist or retrieve roadmap
def _save_roadmap(roadmap: LearningRoadmap, user_id: str):
    _MEMORY_ROADMAPS[roadmap.id] = roadmap
    _MEMORY_ROADMAP_OWNERS[roadmap.id] = user_id
    if supabase:
        try:
            supabase.table("learning_roadmaps").upsert({
                "id": roadmap.id,
                "user_id": user_id,
                "course_id": roadmap.course_id,
                "topic": roadmap.topic,
                "title": roadmap.title,
                "description": roadmap.description,
                "level": roadmap.level,
                "language": roadmap.language,
                "class_type": roadmap.class_type.value if hasattr(roadmap.class_type, 'value') else str(roadmap.class_type),
                "target_duration_minutes": roadmap.target_duration_minutes,
                "status": roadmap.status.value if hasattr(roadmap.status, 'value') else str(roadmap.status),
                "next_best_action": roadmap.next_best_action.value if hasattr(roadmap.next_best_action, 'value') else str(roadmap.next_best_action),
                "overall_progress": roadmap.overall_progress,
                "health_score": roadmap.health_score,
                "version": roadmap.version,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            for i, stage in enumerate(roadmap.stages):
                supabase.table("roadmap_stages").upsert({
                    "id": stage.id,
                    "roadmap_id": roadmap.id,
                    "concept_id": stage.concept_id,
                    "title": stage.title,
                    "description": stage.description,
                    "duration_minutes": stage.duration_minutes,
                    "status": stage.status.value if hasattr(stage.status, 'value') else str(stage.status),
                    "readiness": stage.readiness.value if hasattr(stage.readiness, 'value') else str(stage.readiness),
                    "mastery": stage.mastery,
                    "confidence": stage.confidence,
                    "stage_json": json.loads(stage.model_dump_json()),
                    "order_index": i,
                    "version": stage.version,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()
        except Exception as e:
            logger.warning(f"Supabase write skipped/failed: {e}")


def _ensure_dev_seed_roadmap():
    dev_user = "00000000-0000-0000-0000-000000000001"
    rm_id = "rm-dbms-demo"
    if rm_id in _MEMORY_ROADMAPS:
        return
    
    stages = [
        RoadmapStage(
            id="stage-1",
            concept_id="c_func_dep",
            title="Functional Dependency & Keys",
            description="Introduction to functional dependencies, Armstrong's axioms, and identifying candidate keys.",
            sequence=0,
            duration_minutes=20,
            status=StageStatus.TAUGHT,
            readiness=StageReadiness.READY,
            mastery=85,
            confidence=90,
            objectives=[
                LearningObjective(id="o1", description="Define functional dependencies and candidate keys", bloom_level=BloomLevel.UNDERSTAND)
            ],
            prerequisite_ids=[],
            checkpoint_questions=["What is a prime attribute?"],
            expected_misconceptions=["Assuming primary keys cannot be composite"]
        ),
        RoadmapStage(
            id="stage-2",
            concept_id="c_dbms_norm",
            title="DBMS Normalization: 1NF to BCNF",
            description="Step-by-step table decomposition: 1NF atomicity, 2NF partial dependencies, 3NF transitive dependencies, and BCNF.",
            sequence=1,
            duration_minutes=25,
            status=StageStatus.IN_PROGRESS,
            readiness=StageReadiness.READY,
            mastery=45,
            confidence=50,
            is_remedial=True,
            objectives=[
                LearningObjective(id="o2", description="Decompose tables into 3NF and BCNF without data loss", bloom_level=BloomLevel.APPLY)
            ],
            prerequisite_ids=["c_func_dep"],
            checkpoint_questions=["How does 2NF differ from 3NF?"],
            expected_misconceptions=["Confusing partial dependency (violates 2NF) with transitive dependency (violates 3NF)"]
        ),
        RoadmapStage(
            id="stage-3",
            concept_id="c_lossless",
            title="Lossless Join & Dependency Preservation",
            description="Verification of lossless join decomposition and testing for functional dependency preservation.",
            sequence=2,
            duration_minutes=15,
            status=StageStatus.LOCKED,
            readiness=StageReadiness.PREREQUISITE_REQUIRED,
            mastery=0,
            confidence=0,
            objectives=[
                LearningObjective(id="o3", description="Prove whether a decomposition is lossless and preserves dependencies", bloom_level=BloomLevel.ANALYZE)
            ],
            prerequisite_ids=["c_dbms_norm"],
            checkpoint_questions=["Does BCNF always preserve dependencies?"],
            expected_misconceptions=["Assuming BCNF decomposition always preserves dependencies"]
        )
    ]
    for s in stages:
        ResourceRecommenderEngine.evaluate_stage_resources(s, ClassType.INTERACTIVE_LECTURE)
    
    rm = LearningRoadmap(
        id=rm_id,
        course_id="course-dbms",
        topic="Database Management Systems",
        title="DBMS Normalization Mastery Roadmap",
        description="Curriculum roadmap for mastering functional dependencies, 1NF, 2NF, 3NF, BCNF, and relational schema decomposition.",
        level="B.Tech",
        language="english",
        class_type=ClassType.INTERACTIVE_LECTURE,
        target_duration_minutes=60,
        status="published",
        stages=stages,
        next_best_action=NextBestAction.PRACTICE,
        overall_progress=35,
        health_score=94,
        version=1
    )
    _save_roadmap(rm, dev_user)


def _get_roadmap(roadmap_id: str, user_id: str) -> Optional[LearningRoadmap]:
    _ensure_dev_seed_roadmap()
    # Check memory first — allow dev user or matching owner
    if roadmap_id in _MEMORY_ROADMAPS:
        if _MEMORY_ROADMAP_OWNERS.get(roadmap_id) == user_id or user_id == "00000000-0000-0000-0000-000000000001":
            return _MEMORY_ROADMAPS[roadmap_id]
        # Owner mismatch (or unknown owner): fall through to the user-scoped
        # Supabase query rather than serving another user's cached roadmap.

    if supabase:
        try:
            r_res = supabase.table("learning_roadmaps").select("*").eq("id", roadmap_id).eq("user_id", user_id).single().execute()
            if r_res.data:
                s_res = supabase.table("roadmap_stages").select("*").eq("roadmap_id", roadmap_id).order("order_index").execute()
                stages = []
                for row in s_res.data:
                    stage_dict = row.get("stage_json") or {}
                    if isinstance(stage_dict, str):
                        stage_dict = json.loads(stage_dict)
                    stage_dict["duration_minutes"] = row["duration_minutes"]
                    stage_dict["status"] = row["status"]
                    stages.append(RoadmapStage(**stage_dict))
                
                r_data = r_res.data
                roadmap = LearningRoadmap(
                    id=r_data["id"],
                    course_id=r_data.get("course_id", "default_course"),
                    topic=r_data["topic"],
                    title=r_data.get("title"),
                    description=r_data.get("description"),
                    level=r_data["level"],
                    language=r_data["language"],
                    class_type=ClassType(r_data.get("class_type", "Interactive Lecture")),
                    target_duration_minutes=r_data["target_duration_minutes"],
                    status=RoadmapStatus(r_data.get("status", "draft")),
                    stages=stages,
                    overall_progress=r_data.get("overall_progress", 0),
                    health_score=r_data.get("health_score", 100),
                    version=r_data.get("version", 1)
                )
                _MEMORY_ROADMAPS[roadmap_id] = roadmap
                _MEMORY_ROADMAP_OWNERS[roadmap_id] = user_id
                return roadmap
        except Exception as e:
            logger.warning(f"Supabase read error: {e}")

    return None


@router.post("/parse")
async def parse_lesson_prompt(
    request: ParsePromptRequest,
    current_user = Depends(get_current_user)
):
    """
    Parses a natural language teacher request into structured parameters.
    """
    parsed = await RoadmapGenerator.parse_natural_language_prompt(request.prompt)
    return parsed


@router.post("/generate", response_model=LearningRoadmap)
async def generate_roadmap(
    request: GenerateRoadmapRequest,
    current_user = Depends(get_current_user)
):
    """
    Generates a full Adaptive Learning Roadmap with Bloom's objectives and deterministic checks.
    """
    roadmap = await RoadmapGenerator.generate_draft_roadmap(
        topic=request.topic,
        level=request.level,
        language=request.language,
        class_type=request.class_type,
        target_duration_minutes=request.target_duration_minutes,
        custom_context=request.custom_context,
        source_refs=request.source_refs
    )

    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap.created_by = user_id
    _save_roadmap(roadmap, user_id)
    return roadmap


@router.get("/")
async def get_roadmaps(current_user = Depends(get_current_user)):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    _ensure_dev_seed_roadmap()
    roadmaps_list = []
    if supabase:
        try:
            res = supabase.table("learning_roadmaps").select("id, topic, description, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
            roadmaps_list = res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch roadmaps: {e}")
    if not roadmaps_list:
        for rid, r in _MEMORY_ROADMAPS.items():
            if _MEMORY_ROADMAP_OWNERS.get(rid) == user_id or user_id == "00000000-0000-0000-0000-000000000001":
                roadmaps_list.append({
                    "id": r.id,
                    "topic": r.topic,
                    "title": r.title or r.topic,
                    "description": r.description or "",
                    "created_at": getattr(r, "created_at", None) or "2026-09-13T00:00:00Z"
                })
    return {"roadmaps": roadmaps_list}


@router.get("/{roadmap_id}", response_model=LearningRoadmap)
async def get_roadmap(
    roadmap_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap


@router.patch("/{roadmap_id}/stages/{stage_id}")
async def edit_roadmap_stage(
    roadmap_id: str,
    stage_id: str,
    request: EditStageRequest,
    current_user = Depends(get_current_user)
):
    """
    Edits a stage with optimistic concurrency control and marks dependent resources stale.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    # Optimistic locking check
    if roadmap.version != request.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch. Server is on version {roadmap.version}, request expected {request.expected_version}."
        )

    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    changed_fields = []
    if request.title is not None and request.title != stage.title:
        stage.title = request.title
        changed_fields.append("title")
    if request.description is not None:
        stage.description = request.description
        changed_fields.append("description")
    if request.duration_minutes is not None and request.duration_minutes != stage.duration_minutes:
        stage.duration_minutes = request.duration_minutes
        changed_fields.append("duration_minutes")
    if request.status is not None and request.status != stage.status:
        StateMachineEngine.transition_stage(stage, request.status)
        changed_fields.append("status")
    if request.mastery is not None:
        stage.mastery = request.mastery
        changed_fields.append("mastery")
    if request.teacher_actions is not None:
        stage.teacher_actions = request.teacher_actions
        changed_fields.append("teacher_actions")
    if request.student_actions is not None:
        stage.student_actions = request.student_actions
        changed_fields.append("student_actions")
    if request.checkpoint_questions is not None:
        stage.checkpoint_questions = request.checkpoint_questions
        changed_fields.append("checkpoint_questions")

    # Change impact analysis
    ChangeImpactEngine.analyze_stage_modification(stage, changed_fields)

    # Recalculate deterministic states
    PrerequisiteEngine.evaluate_readiness(roadmap)
    StateMachineEngine.determine_next_action(roadmap)
    StateMachineEngine.calculate_overall_progress(roadmap)
    LessonHealthValidator.evaluate_health(roadmap)

    # Bump version
    roadmap.version += 1
    stage.version += 1
    _save_roadmap(roadmap, user_id)

    return {
        "message": "Stage updated successfully",
        "new_version": roadmap.version,
        "stage": stage,
        "next_best_action": roadmap.next_best_action.value
    }


@router.post("/{roadmap_id}/stages/reorder")
async def reorder_stages(
    roadmap_id: str,
    request: ReorderStagesRequest,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    if roadmap.version != request.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version conflict")

    success = StageOperationsEngine.reorder_stages(roadmap, request.stage_ids)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid stage IDs for reordering")

    roadmap.version += 1
    _save_roadmap(roadmap, user_id)
    return {"message": "Stages reordered", "new_version": roadmap.version, "stages": roadmap.stages}


@router.post("/{roadmap_id}/stages/merge")
async def merge_stages(
    roadmap_id: str,
    request: MergeStagesRequest,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    if roadmap.version != request.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version conflict")

    merged = StageOperationsEngine.merge_stages(roadmap, request.stage_id_1, request.stage_id_2, request.new_title)
    if not merged:
        raise HTTPException(status_code=400, detail="Failed to merge stages")

    roadmap.version += 1
    _save_roadmap(roadmap, user_id)
    return {"message": "Stages merged successfully", "merged_stage": merged, "new_version": roadmap.version}


@router.post("/{roadmap_id}/stages/split")
async def split_stage(
    roadmap_id: str,
    request: SplitStageRequest,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    if roadmap.version != request.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version conflict")

    parts = StageOperationsEngine.split_stage(
        roadmap, request.stage_id, request.split_title_1, request.split_title_2, request.duration_1, request.duration_2
    )
    if not parts:
        raise HTTPException(status_code=400, detail="Failed to split stage")

    roadmap.version += 1
    _save_roadmap(roadmap, user_id)
    return {"message": "Stage split successfully", "part_1": parts[0], "part_2": parts[1], "new_version": roadmap.version}


@router.post("/{roadmap_id}/remedial")
async def create_remedial_stage(
    roadmap_id: str,
    request: CreateRemedialRequest,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    target = next((s for s in roadmap.stages if s.id == request.target_stage_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target stage not found")

    remedial_stage = RemedialEngine.create_remedial_stage(target, request.weak_prereq_title)
    
    # Insert remedial stage directly before the target stage
    idx = roadmap.stages.index(target)
    roadmap.stages.insert(idx, remedial_stage)
    target.status = StageStatus.BLOCKED
    target.prerequisite_ids.append(remedial_stage.concept_id)

    PrerequisiteEngine.evaluate_readiness(roadmap)
    StateMachineEngine.determine_next_action(roadmap)
    roadmap.version += 1
    _save_roadmap(roadmap, user_id)

    return {
        "message": "Remedial stage inserted successfully",
        "remedial_stage": remedial_stage,
        "new_version": roadmap.version
    }


@router.post("/{roadmap_id}/publish")
async def publish_roadmap(
    roadmap_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    roadmap.status = RoadmapStatus.PUBLISHED
    roadmap.version += 1
    _save_roadmap(roadmap, user_id)
    return {"message": "Roadmap published successfully", "status": roadmap.status.value, "new_version": roadmap.version}


@router.get("/{roadmap_id}/health")
async def check_lesson_health(
    roadmap_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    health_report = LessonHealthValidator.evaluate_health(roadmap)
    return health_report


# Stage Resource Endpoints
@router.post("/{roadmap_id}/stages/{stage_id}/ppt")
async def generate_stage_ppt(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    try:
        ppt_config = PPTAdapter.create_presentation_config(roadmap, stage)
    except Exception as e:
        # Surface a clean error (which passes through CORS middleware) instead of
        # an unhandled 500 that arrives at the browser as a missing-CORS-header error.
        logger.error(f"PPT config build failed for {roadmap_id}/{stage_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not build presentation config: {e}")
    # Update resource recommendation status
    for rec in stage.resource_recommendations:
        if rec.resource_type == ResourceType.PPT:
            rec.status = ResourceStatus.READY
            rec.generated_at = datetime.now(timezone.utc)

    _save_roadmap(roadmap, user_id)
    return {"message": "PPT configuration ready", "config": ppt_config.model_dump() if hasattr(ppt_config, 'model_dump') else str(ppt_config)}


@router.post("/{roadmap_id}/stages/{stage_id}/video")
async def generate_stage_video(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    # Disconnected from Lesson Planner workflow
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Video generation has been removed from the Lesson Planner workflow."
    )


@router.post("/{roadmap_id}/stages/{stage_id}/quiz")
async def generate_stage_quiz(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    try:
        quiz_spec = QuizAdapter.generate_stage_quiz_spec(roadmap, stage)
    except Exception as e:
        logger.error(f"Quiz generation failed for {roadmap_id}/{stage_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate quiz: {e}")
        
    for rec in stage.resource_recommendations:
        if rec.resource_type == ResourceType.QUIZ:
            rec.status = ResourceStatus.READY
            rec.generated_at = datetime.now(timezone.utc)

    _save_roadmap(roadmap, user_id)
    return {"message": "Quiz generated successfully", "quiz": quiz_spec}


@router.post("/{roadmap_id}/stages/{stage_id}/notes")
async def generate_stage_notes(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    # Disconnected from Lesson Planner workflow
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Study notes generation has been removed from the Lesson Planner workflow."
    )


@router.post("/{roadmap_id}/stages/{stage_id}/teach")
async def get_teach_me_brief(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    try:
        brief = TeachMeAdapter.create_teach_me_context(roadmap, stage)
    except Exception as e:
        logger.error(f"Teach Me context build failed for {roadmap_id}/{stage_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not build Teach Me context: {e}")
        
    stage.status = StageStatus.IN_PROGRESS
    _save_roadmap(roadmap, user_id)
    return {"message": "Teach Me context ready", "brief": brief}


@router.get("/{roadmap_id}/stages/{stage_id}/actions")
async def get_stage_actions(
    roadmap_id: str,
    stage_id: str,
    current_user = Depends(get_current_user)
):
    """
    Returns the formal stage actions contract (Active: PPT, TeachMe, Quiz, YouTube Recommendations, Extra Learning Materials).
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if not stage.actions:
        ResourceRecommenderEngine.evaluate_stage_resources(stage)
    return {"stage_id": stage.id, "actions": stage.actions}


@router.get("/{roadmap_id}/stages/{stage_id}/youtube-recommendations")
async def get_stage_youtube_recommendations(
    roadmap_id: str,
    stage_id: str,
    refresh: bool = Query(False),
    current_user = Depends(get_current_user)
):
    """
    Live endpoint returning educational YouTube video recommendations for a lesson stage.
    Powered by StageResourceIntelligenceService with quota protection and durable caching.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    res = await StageResourceIntelligenceService.get_youtube_recommendations(
        topic=roadmap.topic or stage.title,
        stage=stage,
        learner_level=roadmap.level,
        language=roadmap.language,
        refresh=refresh
    )
    return res


@router.get("/{roadmap_id}/stages/{stage_id}/learning-materials")
async def get_stage_learning_materials(
    roadmap_id: str,
    stage_id: str,
    refresh: bool = Query(False),
    current_user = Depends(get_current_user)
):
    """
    Live endpoint returning Learning Materials (Academic References,
    Research Papers, Practice & Coding, and Official Documentation) for a lesson stage.
    Powered by StageResourceIntelligenceService with dynamic categories.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    res = await StageResourceIntelligenceService.get_learning_materials(
        topic=roadmap.topic or stage.title,
        stage=stage,
        learner_level=roadmap.level,
        language=roadmap.language,
        refresh=refresh
    )
    return res


@router.get("/{roadmap_id}/stages/{stage_id}/coding-resources")
async def get_stage_coding_resources(
    roadmap_id: str,
    stage_id: str,
    refresh: bool = Query(False),
    current_user = Depends(get_current_user)
):
    """
    Live endpoint returning authoritative Coding Resources (Official Docs,
    GeeksforGeeks, and LeetCode progression) for a lesson stage.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    stage = next((s for s in roadmap.stages if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    res = await StageResourceIntelligenceService.get_coding_resources(
        topic=roadmap.topic or stage.title,
        stage=stage,
        learner_level=roadmap.level,
        refresh=refresh
    )
    return res


@router.post("/{roadmap_id}/study-pack")
async def generate_study_pack(
    roadmap_id: str,
    current_user = Depends(get_current_user)
):
    """
    Generates all recommended active resources across the entire roadmap (PPT, Quiz).
    Notes and Video are excluded from study-pack generation.
    """
    user_id = str(getattr(current_user, 'id', 'anonymous'))
    roadmap = _get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    pack_results = []
    for stage in roadmap.stages:
        stage_res = {"stage_id": stage.id, "title": stage.title, "generated": []}
        for rec in stage.resource_recommendations:
            if rec.status == ResourceStatus.RECOMMENDED:
                if rec.resource_type == ResourceType.QUIZ:
                    QuizAdapter.generate_stage_quiz_spec(roadmap, stage)
                    rec.status = ResourceStatus.READY
                    stage_res["generated"].append("quiz")
                elif rec.resource_type == ResourceType.PPT:
                    PPTAdapter.create_presentation_config(roadmap, stage)
                    rec.status = ResourceStatus.READY
                    stage_res["generated"].append("ppt")
        pack_results.append(stage_res)

    _save_roadmap(roadmap, user_id)
    return {"message": "Study pack generation completed", "results": pack_results}
