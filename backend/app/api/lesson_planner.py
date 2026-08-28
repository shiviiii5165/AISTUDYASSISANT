from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user
from app.services.lesson_planner.schemas import LearningRoadmap, RoadmapStage
from app.services.lesson_planner.generator import RoadmapGenerator
from app.services.lesson_planner.engine import TimeBudgetEngine, PrerequisiteEngine, LessonHealthValidator, StateMachineEngine
import json

router = APIRouter()

class GenerateRoadmapRequest(BaseModel):
    topic: str
    level: str = "B.Tech"
    language: str = "hinglish"
    class_type: str = "Interactive Lecture"
    target_duration_minutes: int = 60
    custom_context: Optional[str] = None


@router.post("/generate", response_model=LearningRoadmap)
async def generate_roadmap(
    request: GenerateRoadmapRequest,
    current_user = Depends(get_current_user)
):
    """
    Generates a new Adaptive Learning Roadmap (draft mode).
    """
    roadmap = await RoadmapGenerator.generate_draft_roadmap(
        topic=request.topic,
        level=request.level,
        language=request.language,
        class_type=request.class_type,
        target_duration_minutes=request.target_duration_minutes,
        context=request.custom_context
    )

    # Validate and evaluate initial state
    PrerequisiteEngine.evaluate_readiness(roadmap)
    StateMachineEngine.determine_next_action(roadmap)

    # In a real implementation, we would persist this to supabase.table("learning_roadmaps")
    # For now, we return it. If Supabase is active, do it:
    if supabase:
        try:
            res = supabase.table("learning_roadmaps").insert({
                "id": roadmap.id,
                "user_id": current_user.id,
                "topic": roadmap.topic,
                "level": roadmap.level,
                "language": roadmap.language,
                "class_type": roadmap.class_type,
                "target_duration_minutes": roadmap.target_duration_minutes,
                "next_best_action": roadmap.next_best_action.value,
                "version": roadmap.version
            }).execute()

            for i, stage in enumerate(roadmap.stages):
                supabase.table("roadmap_stages").insert({
                    "id": stage.id,
                    "roadmap_id": roadmap.id,
                    "concept_id": stage.concept_id,
                    "title": stage.title,
                    "description": stage.description,
                    "duration_minutes": stage.duration_minutes,
                    "status": stage.status.value,
                    "stage_json": stage.model_dump_json(),
                    "order_index": i
                }).execute()
        except Exception as e:
            print(f"Failed to save roadmap to DB: {e}")

    return roadmap


class EditStageRequest(BaseModel):
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    expected_version: int


@router.patch("/{roadmap_id}/stages/{stage_id}")
async def edit_roadmap_stage(
    roadmap_id: str,
    stage_id: str,
    request: EditStageRequest,
    current_user = Depends(get_current_user)
):
    """
    Teacher edits a stage. Enforces optimistic locking and recalculates deterministic engine state.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # 1. Optimistic Locking check on Roadmap
    roadmap_res = supabase.table("learning_roadmaps").select("version").eq("id", roadmap_id).eq("user_id", current_user.id).single().execute()
    if not roadmap_res.data:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    current_version = roadmap_res.data.get("version", 1)
    if current_version != request.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch. Server is on version {current_version}, client expected {request.expected_version}"
        )
    
    # 2. Update Stage
    update_data = {}
    if request.duration_minutes is not None:
        update_data["duration_minutes"] = request.duration_minutes
    if request.status is not None:
        update_data["status"] = request.status
        
    supabase.table("roadmap_stages").update(update_data).eq("id", stage_id).eq("roadmap_id", roadmap_id).execute()

    # 3. Bump version
    new_version = current_version + 1
    supabase.table("learning_roadmaps").update({"version": new_version}).eq("id", roadmap_id).execute()

    return {"message": "Stage updated successfully", "new_version": new_version}


@router.get("/{roadmap_id}/health")
async def check_lesson_health(
    roadmap_id: str,
    current_user = Depends(get_current_user)
):
    """
    Runs the deterministic Python validator to score the lesson health.
    """
    if not supabase:
         return {"score": 100, "reasons": [], "warnings": ["DB not connected"]}

    # Reconstruct roadmap
    r_res = supabase.table("learning_roadmaps").select("*").eq("id", roadmap_id).eq("user_id", current_user.id).single().execute()
    s_res = supabase.table("roadmap_stages").select("*").eq("roadmap_id", roadmap_id).order("order_index").execute()

    if not r_res.data:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    stages = []
    for row in s_res.data:
        stage_json = row.get("stage_json", {})
        if isinstance(stage_json, str):
            stage_json = json.loads(stage_json)
        # Overlay DB fields onto the JSON dump
        stage_json["duration_minutes"] = row["duration_minutes"]
        stage_json["status"] = row["status"]
        stages.append(RoadmapStage(**stage_json))
    
    r_data = r_res.data
    roadmap = LearningRoadmap(
        id=r_data["id"],
        course_id=r_data.get("course_id", "default"),
        topic=r_data["topic"],
        level=r_data["level"],
        language=r_data["language"],
        class_type=r_data["class_type"],
        target_duration_minutes=r_data["target_duration_minutes"],
        stages=stages
    )

    health_report = LessonHealthValidator.evaluate_health(roadmap)
    return health_report
