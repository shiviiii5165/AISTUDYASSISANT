"""
Dynamic Time Budget & Reallocation Engine for Lesson Planner VNext
==================================================================
Calculates initial stage timing with an adaptive reserve buffer (10–20%).
Enforces strict reallocation rules on adaptation (Section 16):
- NEVER automatically reduce mandatory curriculum objectives, blocking prerequisites,
  required assessments, or teacher-locked stages.
- Compress FIRST: optional examples, repeated explanation, extension activities,
  long recaps, and low-priority enrichment.
"""

import logging
from typing import List, Dict, Any, Tuple
from ..schemas import (
    LearningRoadmap, RoadmapStage, StageArchetype, PlanRecompileDiff
)
from .pedagogy import StageTemplate

logger = logging.getLogger("teachgenie.lesson_planner.time_budget")


class DynamicTimeBudgetEngine:
    """
    Deterministic arithmetic engine for time allocation and adaptive reallocation.
    Zero LLM arithmetic.
    """

    @classmethod
    def calculate_initial_budget(
        cls,
        total_duration_minutes: int,
        templates: List[StageTemplate],
        reserve_pct: float = 0.10
    ) -> Tuple[List[int], int]:
        """
        Distributes lesson time across stages and reserves an adaptive buffer.
        Returns: (stage_durations, reserve_minutes)
        """
        if total_duration_minutes < 15:
            # Minimal micro-lesson: zero reserve
            return [total_duration_minutes], 0

        # Reserve 10-20% buffer (capped at 15 mins)
        reserve_minutes = max(3, min(15, int(round(total_duration_minutes * reserve_pct))))
        instructional_pool = total_duration_minutes - reserve_minutes

        durations: List[int] = []
        allocated = 0
        total_pct = sum(t.default_duration_pct for t in templates) or 1.0

        for i, t in enumerate(templates):
            if i == len(templates) - 1:
                # Final stage takes the remainder of the pool
                rem = instructional_pool - allocated
                durations.append(max(5, rem))
            else:
                portion = int(round((t.default_duration_pct / total_pct) * instructional_pool))
                portion = max(5, portion)
                durations.append(portion)
                allocated += portion

        # Re-check sum
        current_sum = sum(durations) + reserve_minutes
        if current_sum != total_duration_minutes:
            diff = total_duration_minutes - current_sum
            # Adjust the largest instructional stage
            max_idx = durations.index(max(durations))
            durations[max_idx] += diff

        return durations, reserve_minutes

    @classmethod
    def reallocate_time_for_adaptation(
        cls,
        roadmap: LearningRoadmap,
        required_remediation_minutes: int,
        reason: str = "Class misconception remediation"
    ) -> PlanRecompileDiff:
        """
        Deterministically reallocates time to fund an intervention.
        Follows Section 16 Reallocation Rules:
        1. Fund from adaptive reserve first.
        2. If still deficient, compress low-priority / optional stages (EXTENSION, SUMMARY, HOOK).
        3. Never compress locked stages, diagnostic checks, or completed stages.
        """
        needed = required_remediation_minutes
        diff = PlanRecompileDiff(
            reason=reason,
            stages_added=[],
            stages_modified=[],
            stages_compressed=[],
            net_duration_change=0,
            requires_teacher_approval=True
        )

        # 1. Use adaptive reserve
        if roadmap.adaptive_reserve_minutes > 0:
            from_reserve = min(roadmap.adaptive_reserve_minutes, needed)
            roadmap.adaptive_reserve_minutes -= from_reserve
            needed -= from_reserve
            diff.evidence_summary = f"Funded {from_reserve}m from adaptive reserve buffer ({roadmap.adaptive_reserve_minutes}m remaining)."

        if needed <= 0:
            return diff

        # 2. Identify candidate stages to compress (starting from lowest instructional priority)
        # Priority for compression: EXTENSION > SUMMARY > HOOK > WORKED_EXAMPLE
        compress_priority = [
            StageArchetype.EXTENSION,
            StageArchetype.SUMMARY,
            StageArchetype.REFLECTION,
            StageArchetype.HOOK,
            StageArchetype.WORKED_EXAMPLE,
            StageArchetype.EXPLANATION
        ]

        # Protected archetypes that should NEVER be compressed
        protected_archetypes = {
            StageArchetype.DIAGNOSTIC_CHECK,
            StageArchetype.PREREQUISITE_CHECK,
            StageArchetype.REMEDIATION
        }

        locked_stage_ids = {lock.stage_id for lock in roadmap.teacher_locks if lock.is_locked}

        for archetype in compress_priority:
            if needed <= 0:
                break

            for stage in roadmap.stages:
                if needed <= 0:
                    break

                # Protect completed, locked, or protected archetype stages
                if stage.status in ["taught", "mastered"] or stage.is_locked or stage.id in locked_stage_ids:
                    continue
                if stage.archetype in protected_archetypes:
                    continue

                if stage.archetype == archetype:
                    # Can compress down to 5 mins minimum
                    compressible = max(0, stage.duration_minutes - 5)
                    if compressible > 0:
                        reduction = min(compressible, needed)
                        orig_dur = stage.duration_minutes
                        stage.duration_minutes -= reduction
                        needed -= reduction
                        diff.stages_compressed.append({
                            "stage_id": stage.id,
                            "title": stage.title,
                            "before_duration": orig_dur,
                            "after_duration": stage.duration_minutes,
                            "reduced_by": reduction
                        })

        if needed > 0:
            # If still needed, expand lesson total duration if permissible
            roadmap.target_duration_minutes += needed
            diff.net_duration_change = needed

        return diff
