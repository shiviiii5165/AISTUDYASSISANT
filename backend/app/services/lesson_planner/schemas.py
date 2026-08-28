from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class StageStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    MATERIAL_READY = "material_ready"
    TAUGHT = "taught"
    ASSESSMENT_PENDING = "assessment_pending"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class NextBestAction(str, Enum):
    TEACH = "teach"
    PRACTICE = "practice"
    REVIEW = "review"
    RETEACH = "reteach"
    ADVANCE = "advance"
    PREREQUISITE_RECAP = "prerequisite_recap"
    ASSESS = "assess"
    EXTEND = "extend"


class LearningObjective(BaseModel):
    id: str
    description: str
    bloom_level: str  # remember, understand, apply, analyze, evaluate, create


class ConceptNode(BaseModel):
    id: str
    title: str
    description: str
    prerequisite_ids: List[str] = Field(default_factory=list)


class CourseGraph(BaseModel):
    course_id: str
    title: str
    nodes: List[ConceptNode] = Field(default_factory=list)


class StageActivity(BaseModel):
    type: str  # hook, explanation, example, practice, assessment, summary
    description: str
    duration_minutes: int


class RoadmapStage(BaseModel):
    id: str
    concept_id: str
    title: str
    description: str
    objective_ids: List[str] = Field(default_factory=list)
    prerequisite_ids: List[str] = Field(default_factory=list)
    duration_minutes: int
    status: StageStatus = StageStatus.LOCKED
    mastery: int = 0  # 0 to 100
    confidence: int = 0
    readiness: bool = False
    teacher_actions: List[str] = Field(default_factory=list)
    student_actions: List[str] = Field(default_factory=list)
    activities: List[StageActivity] = Field(default_factory=list)
    checkpoint_questions: List[str] = Field(default_factory=list)
    expected_misconceptions: List[str] = Field(default_factory=list)
    recommended_resources: List[str] = Field(default_factory=list)  # ppt, video, quiz, notes
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)


class LearningRoadmap(BaseModel):
    id: str
    course_id: str
    topic: str
    level: str
    language: str
    class_type: str
    target_duration_minutes: int
    stages: List[RoadmapStage] = Field(default_factory=list)
    next_best_action: NextBestAction = NextBestAction.TEACH
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
