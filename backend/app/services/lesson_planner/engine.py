from typing import List, Dict, Any, Tuple
from .schemas import LearningRoadmap, RoadmapStage, StageStatus, NextBestAction


class TimeBudgetEngine:
    @staticmethod
    def validate_and_adjust_timing(roadmap: LearningRoadmap) -> Tuple[bool, List[str]]:
        """
        Deterministically verifies that sum(stage.duration) <= target_duration.
        Does not use an LLM.
        """
        warnings = []
        total_time = sum(stage.duration_minutes for stage in roadmap.stages)
        target = roadmap.target_duration_minutes

        if total_time > target:
            warnings.append(f"Total time ({total_time}m) exceeds target ({target}m).")
            return False, warnings
        
        # Also validate activities within each stage
        for stage in roadmap.stages:
            stage_time = sum(act.duration_minutes for act in stage.activities)
            if stage_time > stage.duration_minutes:
                warnings.append(f"Stage '{stage.title}' activities time ({stage_time}m) exceeds its allocation ({stage.duration_minutes}m).")
                return False, warnings

        return True, warnings


class PrerequisiteEngine:
    @staticmethod
    def evaluate_readiness(roadmap: LearningRoadmap) -> None:
        """
        Determines which stages are LOCKED vs AVAILABLE based on prerequisite completion.
        Updates the stage statuses in-place.
        """
        # Map concept_id to stage for fast lookup
        concept_to_stage = {stage.concept_id: stage for stage in roadmap.stages}

        for stage in roadmap.stages:
            if stage.status in [StageStatus.MASTERED, StageStatus.TAUGHT]:
                continue
            
            all_prereqs_met = True
            for req_id in stage.prerequisite_ids:
                if req_id in concept_to_stage:
                    req_stage = concept_to_stage[req_id]
                    if req_stage.status not in [StageStatus.MASTERED, StageStatus.TAUGHT]:
                        all_prereqs_met = False
                        break
            
            if all_prereqs_met:
                if stage.status in [StageStatus.LOCKED, StageStatus.BLOCKED]:
                    stage.status = StageStatus.AVAILABLE
            else:
                stage.status = StageStatus.BLOCKED


class LessonHealthValidator:
    @staticmethod
    def evaluate_health(roadmap: LearningRoadmap) -> Dict[str, Any]:
        """
        Computes a transparent health score for the roadmap based on objective alignment,
        timing, source references, and activity balance.
        """
        score = 100
        reasons = []
        warnings = []

        # 1. Timing
        is_timing_valid, timing_warnings = TimeBudgetEngine.validate_and_adjust_timing(roadmap)
        if not is_timing_valid:
            score -= 10
            warnings.extend(timing_warnings)
        else:
            reasons.append("+ Valid timing configuration")

        # 2. Objectives & Checkpoints
        for stage in roadmap.stages:
            if not stage.objective_ids:
                score -= 5
                warnings.append(f"- Stage '{stage.title}' is missing learning objectives.")
            if not stage.checkpoint_questions:
                score -= 5
                warnings.append(f"- Stage '{stage.title}' is missing checkpoint assessment.")
            if not stage.source_refs:
                score -= 2
                warnings.append(f"- Stage '{stage.title}' has no source grounding.")

        # Ensure score stays bounded
        score = max(0, min(100, score))

        if score >= 90:
            reasons.append("+ Strong objective alignment")
            reasons.append("+ Complete source grounding")

        return {
            "score": score,
            "reasons": reasons,
            "warnings": list(set(warnings)) # deduplicate
        }


class StateMachineEngine:
    @staticmethod
    def determine_next_action(roadmap: LearningRoadmap) -> None:
        """
        Deterministically evaluates the roadmap to recommend the Next Best Action.
        """
        # Simple rule engine
        # Are there any blocked stages because a prereq needs review?
        for stage in roadmap.stages:
            if stage.status == StageStatus.NEEDS_REVIEW:
                roadmap.next_best_action = NextBestAction.RETEACH
                return
        
        # Find the first available stage
        for stage in roadmap.stages:
            if stage.status == StageStatus.AVAILABLE:
                roadmap.next_best_action = NextBestAction.TEACH
                return
            if stage.status == StageStatus.IN_PROGRESS:
                roadmap.next_best_action = NextBestAction.TEACH
                return
            if stage.status == StageStatus.ASSESSMENT_PENDING:
                roadmap.next_best_action = NextBestAction.ASSESS
                return
        
        # If all taught/mastered
        roadmap.next_best_action = NextBestAction.ADVANCE
