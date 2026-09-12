"""
Explainability Engine for Lesson Planner VNext
==============================================
Implements Section 70:
Every recommendation answers:
1. WHY THIS STAGE?
2. WHY NOW?
3. WHY THIS RESOURCE?
4. WHY THIS DURATION?
5. WHY DID THE PLAN CHANGE?

Pure deterministic templates built from structured metadata.
Zero expensive LLM calls.
"""

from typing import Dict, Any, List, Optional
from ..schemas import (
    RoadmapStage, LearningRoadmap, UniversalResourceCard, PlanRecompileDiff
)


class ExplainabilityEngine:
    """
    Synthesizes transparent, explainable pedagogical rationales for every plan element.
    """

    @classmethod
    def explain_stage(cls, stage: RoadmapStage, roadmap: LearningRoadmap) -> Dict[str, str]:
        why_stage = stage.why_this_stage or f"Addresses core objective: {stage.teaching_goal or stage.title}."
        why_now = stage.why_now or ("Foundational introductory orientation" if stage.sequence == 0 else f"Builds sequentially on concepts established in stage {stage.sequence}.")
        why_duration = f"Allocated {stage.duration_minutes}m based on {stage.pedagogy_method or 'pedagogy policy'} requirements and learner level {roadmap.level}."

        return {
            "why_this_stage": why_stage,
            "why_now": why_now,
            "why_this_duration": why_duration,
            "teaching_method": stage.pedagogy_method or "Active Pedagogy",
            "evidence_expected": stage.evidence_of_learning or "Formative diagnostic check"
        }

    @classmethod
    def explain_resource(cls, card: UniversalResourceCard, stage: RoadmapStage) -> Dict[str, Any]:
        return {
            "title": card.title,
            "why_recommended": card.why_recommended,
            "what_it_covers": card.what_it_covers,
            "exact_section_or_timestamp": card.exact_section or f"{card.timestamp_start}–{card.timestamp_end}",
            "quality_score": card.quality_score,
            "score_breakdown": card.score_breakdown.model_dump(),
            "source_authority": card.source_authority,
            "access_type": card.access_type
        }

    @classmethod
    def explain_recompile(cls, diff: PlanRecompileDiff, roadmap: LearningRoadmap) -> Dict[str, Any]:
        return {
            "reason": diff.reason,
            "evidence_summary": diff.evidence_summary,
            "stages_added": diff.stages_added,
            "stages_compressed": diff.stages_compressed,
            "net_duration_change": f"{diff.net_duration_change}m",
            "requires_teacher_approval": diff.requires_teacher_approval,
            "current_plan_version": f"v{roadmap.version}"
        }

    @classmethod
    def generate_plan_why_report(cls, roadmap: LearningRoadmap) -> Dict[str, Any]:
        return {
            "plan_id": roadmap.id,
            "topic": roadmap.topic,
            "version": roadmap.version,
            "stages": [
                {
                    "stage_id": s.id,
                    "title": s.title,
                    "explanation": cls.explain_stage(s, roadmap)
                }
                for s in roadmap.stages
            ],
            "total_duration": getattr(roadmap, "target_duration_minutes", getattr(roadmap, "duration_minutes", 60))
        }
