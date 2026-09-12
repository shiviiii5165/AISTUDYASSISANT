"""
TeachGenie AI Video Teacher V2.1 — Surgical Lesson Repair Engine
================================================================
Performs targeted, surgical repairs only on failed dimensions (Decision #5):
- poor visual relevance -> reroute affected scenes only
- missing worked example -> patch example scenes
- weak misconception handling -> add or modify misconception segment
- bad prerequisite ordering -> reorder affected pedagogical scenes
- language issue -> regenerate narration/localization only

Enforces Decision #6 (Never Assume Repair Improves Quality):
- Measures pre_repair_score and post_repair_score
- If post_repair_score > pre_repair_score: keep repaired version
- Else: preserve better original version and attach QA warning
- Exactly one repair pass allowed.
"""
import copy
import time
from typing import Tuple, List, Optional
from ..schemas import (
    Storyboard, SceneSpec, VideoKnowledgePackage, TeachingStoryStage,
    TeachingQualityScore, RepairLog, VisualStrategyArchetype, VisualSpec,
    ComparisonColumn
)
from .quality_evaluator import TeachingQualityEvaluator
from app.core.logging import logger


class LessonRepairEngine:
    """Performs single-pass targeted repair on underperforming lesson storyboards."""

    @classmethod
    def repair_lesson_if_needed(
        cls,
        storyboard: Storyboard,
        quality_score: TeachingQualityScore,
        knowledge_pack: Optional[VideoKnowledgePackage] = None,
        target_duration: int = 300,
    ) -> Tuple[Storyboard, TeachingQualityScore, Optional[RepairLog]]:
        """
        Runs one surgical repair pass if quality score < 80 or any critical gate fails.
        Guarantees that the repaired version is only kept if post_repair_score > pre_repair_score.
        """
        if quality_score.passed_gates:
            return storyboard, quality_score, None

        pre_score = quality_score.total_score
        failed_dims = quality_score.failed_dimensions
        logger.info(f"[LessonRepairEngine] Initiating targeted repair for failed dimensions: {failed_dims} (pre-score: {pre_score})")

        # Create isolated clone for surgical modification
        candidate = copy.deepcopy(storyboard)
        repair_actions: List[str] = []

        # 1. Surgical Repair: Prerequisite Order
        if "prerequisite_order" in failed_dims:
            reordered, act = cls._repair_prerequisite_order(candidate)
            if act:
                repair_actions.append(act)

        # 2. Surgical Repair: Missing / Weak Worked Example
        if "example_quality" in failed_dims:
            patched, act = cls._repair_example_quality(candidate)
            if act:
                repair_actions.append(act)

        # 3. Surgical Repair: Weak Misconception Handling
        if "misconception_handling" in failed_dims:
            patched, act = cls._repair_misconception_handling(candidate)
            if act:
                repair_actions.append(act)

        # 4. Surgical Repair: Visual Relevance
        if "visual_relevance" in failed_dims:
            rerouted, act = cls._repair_visual_relevance(candidate)
            if act:
                repair_actions.append(act)

        # 5. Surgical Repair: Language Naturalness
        if "language_naturalness" in failed_dims:
            paced, act = cls._repair_language_naturalness(candidate)
            if act:
                repair_actions.append(act)

        # Re-evaluate Post-Repair Quality Score
        post_score_obj = TeachingQualityEvaluator.evaluate_lesson(
            candidate, knowledge_pack, target_duration
        )
        post_score = post_score_obj.total_score
        score_delta = round(post_score - pre_score, 2)

        # Decision #6: Compare scores before accepting repair
        if post_score > pre_score:
            kept_repaired = True
            final_sb = candidate
            final_score_obj = post_score_obj
            warning = None
            logger.info(f"[LessonRepairEngine] Repair successful: score improved from {pre_score} to {post_score} (+{score_delta})")
        else:
            kept_repaired = False
            final_sb = storyboard
            final_score_obj = quality_score
            warning = f"Repair pass produced post-score ({post_score}) <= pre-score ({pre_score}); preserving original lesson."
            logger.warning(f"[LessonRepairEngine] {warning}")

        repair_log = RepairLog(
            repair_timestamp=time.time(),
            pre_repair_score=pre_score,
            post_repair_score=post_score,
            score_delta=score_delta,
            repaired_dimensions=failed_dims,
            repair_actions=repair_actions,
            kept_repaired=kept_repaired,
            warning=warning,
        )

        return final_sb, final_score_obj, repair_log

    # ─────────────────────────────────────────────────────────────────────────
    # Surgical Repair Handlers
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _repair_prerequisite_order(cls, sb: Storyboard) -> Tuple[bool, Optional[str]]:
        """Reorders scenes so prerequisite connection appears early (before core mechanism)."""
        scenes = sb.scenes
        prereq_idx = next(
            (i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.PREREQUISITE_CONNECTION, "prerequisite_connection")),
            None
        )
        core_idx = next(
            (i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.CORE_CONCEPT, "core_concept")),
            None
        )
        if prereq_idx is not None and core_idx is not None and prereq_idx > core_idx:
            # Move prerequisite scene to position immediately preceding core concept
            prereq_scene = scenes.pop(prereq_idx)
            new_core_idx = next(
                (i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.CORE_CONCEPT, "core_concept")),
                0
            )
            scenes.insert(new_core_idx, prereq_scene)
            # Re-index scene order
            for i, s in enumerate(scenes):
                s.order = i + 1
            return True, f"Reordered scene '{prereq_scene.scene_id}' (prerequisite connection) to position {new_core_idx+1} before core concept."
        return False, None

    @classmethod
    def _repair_example_quality(cls, sb: Storyboard) -> Tuple[bool, Optional[str]]:
        """Injects or enriches a concrete worked example with step-by-step numbers."""
        scenes = sb.scenes
        # Look for existing worked example scene or core concept scene
        target = next(
            (s for s in scenes if s.purpose in (TeachingStoryStage.WORKED_EXAMPLE, "worked_example")),
            None
        )
        topic = sb.topic
        concrete_example_text = (
            f"Step 1: Consider a concrete input case for {topic}. "
            "Step 2: Apply the primary operational rule. "
            "Step 3: Verify the output matches our expected invariant."
        )

        if target:
            target.worked_example = concrete_example_text
            target.narration += f" Let's walk through this step-by-step: {concrete_example_text}"
            return True, f"Enriched worked example in scene '{target.scene_id}' with concrete steps."
        else:
            # Find core concept scene and convert following scene or augment it
            core_idx = next((i for i, s in enumerate(scenes) if s.purpose in (TeachingStoryStage.CORE_CONCEPT, "core_concept")), 0)
            if core_idx < len(scenes):
                scenes[core_idx].worked_example = concrete_example_text
                scenes[core_idx].narration += f" For example: {concrete_example_text}"
                return True, f"Injected concrete worked example steps into core scene '{scenes[core_idx].scene_id}'."
        return False, None

    @classmethod
    def _repair_misconception_handling(cls, sb: Storyboard) -> Tuple[bool, Optional[str]]:
        """Injects explicit contrastive pitfall warning into common mistake scene."""
        scenes = sb.scenes
        target = next(
            (s for s in scenes if s.purpose in (TeachingStoryStage.COMMON_MISTAKE, "common_mistake")),
            None
        )
        warning_addition = " Caution: A common mistake here is confusing the order of operations. Avoid changing references prematurely!"
        if target:
            if "mistake" not in target.narration.lower() and "caution" not in target.narration.lower():
                target.narration += warning_addition
            target.misconception_tags.append(f"{sb.topic}_order_confusion")
            return True, f"Injected contrastive warning into misconception scene '{target.scene_id}'."
        else:
            # Tag the last mechanism or worked example scene with misconception contrast
            if scenes:
                scenes[-2].misconception_tags.append("common_pitfall_warning")
                scenes[-2].narration += warning_addition
                return True, f"Injected common pitfall contrast warning into scene '{scenes[-2].scene_id}'."
        return False, None

    @classmethod
    def _repair_visual_relevance(cls, sb: Storyboard) -> Tuple[bool, Optional[str]]:
        """Reroutes mismatched visual archetypes to high-affinity renderer families."""
        scenes = sb.scenes
        repaired_count = 0

        for s in scenes:
            purpose = s.purpose.value if hasattr(s.purpose, "value") else str(s.purpose)
            strat = s.visual_strategy.value if hasattr(s.visual_strategy, "value") else str(s.visual_strategy)

            # If common mistake scene is using generic diagram, switch to comparison
            if purpose == TeachingStoryStage.COMMON_MISTAKE.value and strat == "generic_diagram":
                s.visual_strategy = VisualStrategyArchetype.COMPARISON
                if not s.visual_spec.comparisons:
                    s.visual_spec.comparisons = [
                        ComparisonColumn(header="CORRECT APPROACH", items=["Preserve reference invariant", "Update links in sequence"]),
                        ComparisonColumn(header="COMMON PITFALL", items=["Premature reference overwrite", "State / memory leak"])
                    ]
                repaired_count += 1

            # If visual mechanism is using generic diagram, upgrade to process flow
            elif purpose == TeachingStoryStage.VISUAL_MECHANISM.value and strat == "generic_diagram":
                s.visual_strategy = VisualStrategyArchetype.PROCESS_FLOW
                if not s.visual_spec.steps:
                    s.visual_spec.steps = ["1. Read Current State", "2. Execute Transformation", "3. Validate Post-Condition"]
                repaired_count += 1

            # Ensure visual spec has at least a title if empty
            if not s.visual_spec.title:
                s.visual_spec.title = s.concept_name or s.caption or sb.topic

        if repaired_count > 0:
            return True, f"Rerouted {repaired_count} scenes to high-affinity visual archetypes (Comparison / Process Flow)."
        return False, None

    @classmethod
    def _repair_language_naturalness(cls, sb: Storyboard) -> Tuple[bool, Optional[str]]:
        """Adjusts rushed or sparse narration pacing."""
        scenes = sb.scenes
        adjusted = 0
        for s in scenes:
            words = s.narration.split()
            wps = len(words) / max(1.0, float(s.duration))
            if wps > 4.2:
                # Extend duration to give natural speech cadence
                s.duration = int(len(words) / 2.8) + 1
                adjusted += 1
        if adjusted > 0:
            return True, f"Normalized duration for {adjusted} scenes to achieve natural pacing (2.8 words/sec)."
        return False, None
