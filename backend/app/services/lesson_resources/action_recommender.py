"""
TeachGenie Lesson Planner — Stage Action Recommender
===================================================
Determines pedagogical prioritization for the 5 Stage Resource actions:
1. PowerPoint (ppt)
2. TeachMe (teach_me)
3. Quiz (quiz)
4. YouTube Recommendations (youtube_recommendations)
5. Learning Materials (extra_learning_materials)

Strict Rule: At most 1 PRIMARY ('Top Pick') and 1-2 RECOMMENDED ('Recommended').
Never visually label all 5 actions as Recommended.
"""

from typing import List, Dict
from .schemas import (
    StageActionPriority,
    StageActionRecommendation,
    ResourceIntentProfile,
    StageIntent
)


class StageActionRecommender:
    """
    Evaluates stage intent, mastery, and objectives to assign calibrated action priorities.
    """

    @classmethod
    def evaluate_actions(cls, profile: ResourceIntentProfile) -> List[StageActionRecommendation]:
        intent = profile.stage_intent
        recs: List[StageActionRecommendation] = []

        if intent == StageIntent.REMEDIAL:
            # Remedial stage: Active dialogue (TeachMe) is primary, followed by targeted video & quiz
            recs = [
                StageActionRecommendation(
                    key="teach_me",
                    priority=StageActionPriority.PRIMARY,
                    badge_label="Top Pick",
                    reason="Interactive dialogue with immediate diagnostic checkpoints to resolve misconceptions."
                ),
                StageActionRecommendation(
                    key="quiz",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="Formative diagnostic check targeting specific weak concepts."
                ),
                StageActionRecommendation(
                    key="youtube_recommendations",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="Curated video walkthrough targeting remedial worked examples."
                ),
                StageActionRecommendation(
                    key="ppt",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Multi-slide concept overview deck."
                ),
                StageActionRecommendation(
                    key="extra_learning_materials",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Academic references and supplementary reading."
                ),
            ]

        elif intent == StageIntent.PRACTICE:
            # Practice stage: Quiz / Coding problems are primary
            primary_materials = profile.is_programming_topic
            recs = [
                StageActionRecommendation(
                    key="quiz",
                    priority=StageActionPriority.PRIMARY,
                    badge_label="Top Pick",
                    reason="Hands-on practice questions and algorithmic problem solving."
                ),
                StageActionRecommendation(
                    key="extra_learning_materials",
                    priority=StageActionPriority.RECOMMENDED if primary_materials else StageActionPriority.AVAILABLE,
                    badge_label="Recommended" if primary_materials else None,
                    reason="Practice problems, coding progression, and official documentation." if primary_materials else "Reference materials and practice questions."
                ),
                StageActionRecommendation(
                    key="teach_me",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="Guided practice with step-by-step Socratic assistance."
                ),
                StageActionRecommendation(
                    key="youtube_recommendations",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Worked tutorial videos."
                ),
                StageActionRecommendation(
                    key="ppt",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Slide deck walkthrough."
                ),
            ]

        elif intent == StageIntent.ASSESSMENT:
            recs = [
                StageActionRecommendation(
                    key="quiz",
                    priority=StageActionPriority.PRIMARY,
                    badge_label="Top Pick",
                    reason="Diagnostic assessment to verify mastery of stage learning objectives."
                ),
                StageActionRecommendation(
                    key="teach_me",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="Interactive review of difficult test questions."
                ),
                StageActionRecommendation(
                    key="youtube_recommendations",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Quick revision lecture."
                ),
                StageActionRecommendation(
                    key="ppt",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Summary slide deck."
                ),
                StageActionRecommendation(
                    key="extra_learning_materials",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Review articles and summary references."
                ),
            ]

        elif intent in (StageIntent.ADVANCED_RESEARCH, StageIntent.DEEP_EXPLANATION):
            recs = [
                StageActionRecommendation(
                    key="extra_learning_materials",
                    priority=StageActionPriority.PRIMARY,
                    badge_label="Top Pick",
                    reason="Verified research papers, canonical standards, and documentation."
                ),
                StageActionRecommendation(
                    key="youtube_recommendations",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="In-depth academic lecture and conference presentation."
                ),
                StageActionRecommendation(
                    key="ppt",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Detailed slide presentation for deep conceptual study."
                ),
                StageActionRecommendation(
                    key="teach_me",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Deep-dive Socratic interrogation."
                ),
                StageActionRecommendation(
                    key="quiz",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Advanced conceptual mastery check."
                ),
            ]

        else:
            # CONCEPT_LEARNING / INTRODUCTION / REVISION default
            recs = [
                StageActionRecommendation(
                    key="teach_me",
                    priority=StageActionPriority.PRIMARY,
                    badge_label="Top Pick",
                    reason="Interactive step-by-step concept introduction."
                ),
                StageActionRecommendation(
                    key="youtube_recommendations",
                    priority=StageActionPriority.RECOMMENDED,
                    badge_label="Recommended",
                    reason="Visual lecture and foundational concept tutorial."
                ),
                StageActionRecommendation(
                    key="ppt",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Structured slide presentation for visual learning."
                ),
                StageActionRecommendation(
                    key="quiz",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Exit ticket check."
                ),
                StageActionRecommendation(
                    key="extra_learning_materials",
                    priority=StageActionPriority.AVAILABLE,
                    badge_label=None,
                    reason="Authoritative encyclopedia and documentation reference."
                ),
            ]

        if profile.is_programming_topic or profile.domain == "computer_science":
            recs.append(StageActionRecommendation(
                key="coding_resources",
                priority=StageActionPriority.RECOMMENDED if intent in (StageIntent.CONCEPT_LEARNING, StageIntent.INTRODUCTION, StageIntent.PRACTICE) else StageActionPriority.AVAILABLE,
                badge_label="Recommended" if intent in (StageIntent.CONCEPT_LEARNING, StageIntent.INTRODUCTION, StageIntent.PRACTICE) else None,
                reason="Official documentation, GeeksforGeeks conceptual guides, and calibrated practice."
            ))

        return recs
