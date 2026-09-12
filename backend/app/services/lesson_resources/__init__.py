"""
TeachGenie Lesson Planner — Lesson Resources Package
====================================================
"""

from .schemas import (
    ResourceIntentProfile,
    ResourceCandidate,
    ResourceType,
    StageIntent,
    StageActionPriority,
    StageActionRecommendation,
    YouTubeResponseOutput,
    YouTubeItemOutput,
    LearningMaterialsResponseOutput,
    LearningMaterialsCategoriesOutput,
    MaterialItemOutput
)
from .service import StageResourceIntelligenceService
from .action_recommender import StageActionRecommender

__all__ = [
    "ResourceIntentProfile",
    "ResourceCandidate",
    "ResourceType",
    "StageIntent",
    "StageActionPriority",
    "StageActionRecommendation",
    "YouTubeResponseOutput",
    "YouTubeItemOutput",
    "LearningMaterialsResponseOutput",
    "LearningMaterialsCategoriesOutput",
    "MaterialItemOutput",
    "StageResourceIntelligenceService",
    "StageActionRecommender"
]
