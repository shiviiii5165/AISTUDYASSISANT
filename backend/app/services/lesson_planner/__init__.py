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
    RoadmapEvent,
    StageAction
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
from .youtube_recommendation import (
    YouTubeRecommendationService,
    YouTubeVideoRecommendation,
    YouTubeRecommendationResponse
)
from .learning_materials import (
    ExtraLearningMaterialsService,
    ExtraLearningMaterialsResponse,
    ExtraLearningMaterialItem,
    ExtraLearningMaterialsCategories
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
    "StageAction",
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
    "NotesAdapter",
    "YouTubeRecommendationService",
    "YouTubeVideoRecommendation",
    "YouTubeRecommendationResponse",
    "ExtraLearningMaterialsService",
    "ExtraLearningMaterialsResponse",
    "ExtraLearningMaterialItem",
    "ExtraLearningMaterialsCategories"
]
