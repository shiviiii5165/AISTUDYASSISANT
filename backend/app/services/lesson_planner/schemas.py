from typing import List, Dict, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


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


class StageReadiness(str, Enum):
    READY = "ready"
    PREREQUISITE_REQUIRED = "prerequisite_required"
    REVIEW_RECOMMENDED = "review_recommended"
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


class ResourceType(str, Enum):
    PPT = "ppt"
    VIDEO = "video"
    TEACH_ME = "teach_me"
    QUIZ = "quiz"
    NOTES = "notes"
    WORKSHEET = "worksheet"
    HOMEWORK = "homework"
    DIAGRAM = "diagram"


class ResourceStatus(str, Enum):
    NOT_NEEDED = "not_needed"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    SELECTED = "selected"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"


class RoadmapStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ClassType(str, Enum):
    LECTURE = "Lecture"
    INTERACTIVE_LECTURE = "Interactive Lecture"
    TUTORIAL = "Tutorial"
    LAB = "Lab"
    SEMINAR = "Seminar"
    WORKSHOP = "Workshop"
    DISCUSSION = "Discussion"
    FLIPPED_CLASSROOM = "Flipped Classroom"
    ONLINE = "Online"
    HYBRID = "Hybrid"
    REVISION = "Revision"
    EXAM_REVIEW = "Exam Review"
    REMEDIAL = "Remedial"
    PROJECT_BASED = "Project-Based"
    CASE_STUDY = "Case Study"
    VIVA_PREPARATION = "Viva Preparation"


class LearningObjective(BaseModel):
    id: str
    description: str
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class StageActivity(BaseModel):
    id: Optional[str] = None
    type: str  # hook, explanation, example, guided_practice, independent_practice, checkpoint, lab_demo, student_task, debugging, summary
    title: str = ""
    description: str
    duration_minutes: int


class ResourceRecommendation(BaseModel):
    resource_type: ResourceType
    usefulness_score: float = 0.5  # 0.0 to 1.0
    status: ResourceStatus = ResourceStatus.OPTIONAL
    reason: str = ""
    resource_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    lineage_version: int = 1


class StageDifferentiation(BaseModel):
    core: str = ""
    support: str = ""
    extension: str = ""


class SourceReference(BaseModel):
    source_type: str = "general"  # pdf, ppt, notes, youtube, web, syllabus, general
    title: str
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None


class RoadmapStage(BaseModel):
    id: str
    concept_id: str
    title: str
    description: str
    sequence: int = 0
    duration_minutes: int
    status: StageStatus = StageStatus.LOCKED
    readiness: StageReadiness = StageReadiness.BLOCKED
    mastery: int = 0  # 0 to 100
    confidence: int = 0
    
    # Core pedagogy
    objective_ids: List[str] = Field(default_factory=list)
    objectives: List[LearningObjective] = Field(default_factory=list)
    prerequisite_ids: List[str] = Field(default_factory=list)
    
    # Actions & Execution
    teacher_actions: List[str] = Field(default_factory=list)
    student_actions: List[str] = Field(default_factory=list)
    evidence_of_learning: str = ""
    activities: List[StageActivity] = Field(default_factory=list)
    checkpoint_questions: List[str] = Field(default_factory=list)
    expected_misconceptions: List[str] = Field(default_factory=list)
    
    # Differentiation & Resources
    differentiation: StageDifferentiation = Field(default_factory=StageDifferentiation)
    resource_recommendations: List[ResourceRecommendation] = Field(default_factory=list)
    source_refs: List[SourceReference] = Field(default_factory=list)
    
    next_best_action: NextBestAction = NextBestAction.TEACH
    version: int = 1
    is_optional: bool = False
    is_remedial: bool = False


class DependencyEdge(BaseModel):
    source: str
    target: str
    edge_type: str = "prerequisite_of"  # prerequisite_of, depends_on, follows, assesses, supported_by, related_to
    strength: float = 1.0


class ConceptNode(BaseModel):
    id: str
    title: str
    description: str
    unit_id: Optional[str] = None
    prerequisite_ids: List[str] = Field(default_factory=list)
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class CourseUnit(BaseModel):
    id: str
    unit_number: int
    title: str
    description: str = ""
    topics: List[str] = Field(default_factory=list)
    estimated_hours: float = 4.0
    coverage_percentage: int = 0  # 0 to 100


class CourseGraph(BaseModel):
    course_id: str
    title: str
    code: Optional[str] = None
    units: List[CourseUnit] = Field(default_factory=list)
    nodes: List[ConceptNode] = Field(default_factory=list)
    edges: List[DependencyEdge] = Field(default_factory=list)


class CourseCoverage(BaseModel):
    total_units: int = 0
    covered_units: int = 0
    coverage_percentage: int = 0
    unit_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


class LearningRoadmap(BaseModel):
    id: str
    course_id: str = "default_course"
    topic: str
    title: Optional[str] = None
    description: Optional[str] = None
    level: str = "B.Tech"
    language: str = "hinglish"
    class_type: ClassType = ClassType.INTERACTIVE_LECTURE
    target_duration_minutes: int = 60
    status: RoadmapStatus = RoadmapStatus.DRAFT
    
    stages: List[RoadmapStage] = Field(default_factory=list)
    next_best_action: NextBestAction = NextBestAction.TEACH
    overall_progress: int = 0  # 0 to 100
    health_score: int = 100
    
    course_coverage: Optional[CourseCoverage] = None
    version: int = 1
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SemesterScheduledLesson(BaseModel):
    week_number: int
    session_number: int
    date_str: str
    unit_title: str
    topic_title: str
    duration_minutes: int
    is_practical: bool = False
    is_exam: bool = False
    is_holiday: bool = False


class SemesterPlan(BaseModel):
    course_id: str
    total_weeks: int = 14
    classes_per_week: int = 3
    minutes_per_class: int = 60
    scheduled_lessons: List[SemesterScheduledLesson] = Field(default_factory=list)
    coverage_percentage: int = 100


class RoadmapEvent(BaseModel):
    id: Optional[str] = None
    roadmap_id: str
    stage_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
