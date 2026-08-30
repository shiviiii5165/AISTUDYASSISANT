"""
AI Lesson Planner 2.0 Domain Module
Adaptive Learning Roadmap + Course Intelligence + Stage-Level Resource Orchestration
"""
from .schemas import (
    LearningRoadmap,
    RoadmapStage,
    CourseGraph,
    CourseUnit,
    ConceptNode,
    DependencyEdge,
    LearningObjective,
    BloomLevel,
    StageStatus,
    StageReadiness,
    NextBestAction,
    ResourceType,
    ResourceStatus,
    ResourceRecommendation,
    RoadmapStatus,
    ClassType,
    StageActivity,
    StageDifferentiation,
    SourceReference,
    CourseCoverage,
    SemesterPlan,
    RoadmapEvent
)
from .engine import (
    TimeBudgetEngine,
    PrerequisiteEngine,
    StateMachineEngine,
    ResourceRecommenderEngine,
    LessonHealthValidator,
    RemedialEngine,
    StageOperationsEngine,
    ChangeImpactEngine
)
from .course_intelligence import CourseIntelligenceEngine
from .generator import RoadmapGenerator
from .adapters import (
    PPTAdapter,
    VideoAdapter,
    TeachMeAdapter,
    QuizAdapter,
    NotesAdapter
)

__all__ = [
    "LearningRoadmap",
    "RoadmapStage",
    "CourseGraph",
    "CourseUnit",
    "ConceptNode",
    "DependencyEdge",
    "LearningObjective",
    "BloomLevel",
    "StageStatus",
    "StageReadiness",
    "NextBestAction",
    "ResourceType",
    "ResourceStatus",
    "ResourceRecommendation",
    "RoadmapStatus",
    "ClassType",
    "StageActivity",
    "StageDifferentiation",
    "SourceReference",
    "CourseCoverage",
    "SemesterPlan",
    "RoadmapEvent",
    "TimeBudgetEngine",
    "PrerequisiteEngine",
    "StateMachineEngine",
    "ResourceRecommenderEngine",
    "LessonHealthValidator",
    "RemedialEngine",
    "StageOperationsEngine",
    "ChangeImpactEngine",
    "CourseIntelligenceEngine",
    "RoadmapGenerator",
    "PPTAdapter",
    "VideoAdapter",
    "TeachMeAdapter",
    "QuizAdapter",
    "NotesAdapter"
]
