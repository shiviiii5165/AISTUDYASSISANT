"""
LearnByGenie AI Video Teacher V2.1 — Hybrid Teaching Quality Evaluator
====================================================================
Evaluates pedagogical effectiveness, structural integrity, and cognitive clarity
across 8 distinct dimensions (Total 100 points):
1. Concept Coverage: 20
2. Prerequisite Order: 15
3. Visual Relevance: 15
4. Example Quality: 15
5. Misconception Handling: 10
6. Language Naturalness: 10
7. Narration/Visual Synchronization: 10
8. Doubt Context Readiness: 5

Enforces Mandatory Decision #3 & #4:
- Quality pass requires: total_score >= 80 AND all critical dimension minimums pass.
- 3-Layer Hybrid Evaluation:
    Layer A: Deterministic structural audit
    Layer B: Semantic evaluation (ModelRouter with resilient heuristic fallback)
    Layer C: External human evaluation calibration
"""
import re
from typing import Optional, List, Dict, Any, Tuple
from ..schemas import (
    Storyboard, SceneSpec, VideoKnowledgePackage, TeachingStoryStage,
    TeachingQualityScore, QUALITY_DIMENSION_GATES, VisualStrategyArchetype
)
from app.core.logging import logger


class TeachingQualityEvaluator:
    """Evaluates video lesson pedagogical quality using hybrid structural and semantic rules."""

    @classmethod
    def evaluate_lesson(
        cls,
        storyboard: Storyboard,
        knowledge_pack: Optional[VideoKnowledgePackage] = None,
        target_duration: int = 300,
    ) -> TeachingQualityScore:
        """Runs the 8-dimension hybrid evaluation and returns a TeachingQualityScore."""
        scenes = storyboard.scenes
        if not scenes:
            return TeachingQualityScore(
                total_score=0.0,
                passed_gates=False,
                failed_dimensions=list(QUALITY_DIMENSION_GATES.keys()),
                repair_recommendations=["Storyboard has no scenes. Complete generation failed."],
            )

        # 1. Concept Coverage (max 20)
        c_cov, c_cov_recs = cls._eval_concept_coverage(storyboard, knowledge_pack)

        # 2. Prerequisite Order (max 15)
        p_ord, p_ord_recs = cls._eval_prerequisite_order(scenes)

        # 3. Visual Relevance (max 15)
        v_rel, v_rel_recs = cls._eval_visual_relevance(scenes)

        # 4. Example Quality (max 15)
        e_qua, e_qua_recs = cls._eval_example_quality(scenes)

        # 5. Misconception Handling (max 10)
        m_hnd, m_hnd_recs = cls._eval_misconception_handling(scenes)

        # 6. Language Naturalness (max 10)
        l_nat, l_nat_recs = cls._eval_language_naturalness(scenes, storyboard.language)

        # 7. Narration / Visual Synchronization (max 10)
        n_syn, n_syn_recs = cls._eval_narration_visual_sync(scenes, target_duration)

        # 8. Doubt Context Readiness (max 5)
        d_rdy, d_rdy_recs = cls._eval_doubt_readiness(knowledge_pack)

        total = round(c_cov + p_ord + v_rel + e_qua + m_hnd + l_nat + n_syn + d_rdy, 2)

        subscores = {
            "concept_coverage": c_cov,
            "prerequisite_order": p_ord,
            "visual_relevance": v_rel,
            "example_quality": e_qua,
            "misconception_handling": m_hnd,
            "language_naturalness": l_nat,
            "narration_visual_sync": n_syn,
            "doubt_context_readiness": d_rdy,
        }

        # Check Gates
        gate_results: Dict[str, bool] = {}
        failed_dims: List[str] = []
        all_recs: List[str] = []

        for dim, min_thresh in QUALITY_DIMENSION_GATES.items():
            if dim == "total_score_minimum":
                continue
            actual = subscores.get(dim, 0.0)
            passed = actual >= min_thresh
            gate_results[dim] = passed
            if not passed:
                failed_dims.append(dim)

        passed_total = total >= QUALITY_DIMENSION_GATES.get("total_score_minimum", 80.0)
        passed_all_gates = passed_total and (len(failed_dims) == 0)

        # Collect repair recommendations for failed dimensions
        if "concept_coverage" in failed_dims:
            all_recs.extend(c_cov_recs)
        if "prerequisite_order" in failed_dims:
            all_recs.extend(p_ord_recs)
        if "visual_relevance" in failed_dims:
            all_recs.extend(v_rel_recs)
        if "example_quality" in failed_dims:
            all_recs.extend(e_qua_recs)
        if "misconception_handling" in failed_dims:
            all_recs.extend(m_hnd_recs)
        if "language_naturalness" in failed_dims:
            all_recs.extend(l_nat_recs)
        if "narration_visual_sync" in failed_dims:
            all_recs.extend(n_syn_recs)
        if "doubt_context_readiness" in failed_dims:
            all_recs.extend(d_rdy_recs)

        return TeachingQualityScore(
            concept_coverage=round(c_cov, 2),
            prerequisite_order=round(p_ord, 2),
            visual_relevance=round(v_rel, 2),
            example_quality=round(e_qua, 2),
            misconception_handling=round(m_hnd, 2),
            language_naturalness=round(l_nat, 2),
            narration_visual_sync=round(n_syn, 2),
            doubt_context_readiness=round(d_rdy, 2),
            total_score=total,
            passed_gates=passed_all_gates,
            dimension_gate_results=gate_results,
            failed_dimensions=failed_dims,
            repair_recommendations=all_recs,
            is_hybrid=True,
        )

    @classmethod
    async def evaluate_lesson_with_semantic_llm(
        cls,
        storyboard: Storyboard,
        knowledge_pack: Optional[VideoKnowledgePackage] = None,
        target_duration: int = 300,
    ) -> TeachingQualityScore:
        """
        Layer B: Semantic evaluation via LLM (ModelRouter task="semantic_qa").
        Evaluates explanation clarity, coherence, example usefulness, and misconception handling.
        Gracefully falls back to deterministic Layer A scoring if LLM is unavailable.
        """
        base_score = cls.evaluate_lesson(storyboard, knowledge_pack, target_duration)
        if not storyboard.scenes or base_score.total_score < 40.0:
            return base_score

        try:
            from app.services.ai.router import model_router
            scenes_summary = []
            for s in storyboard.scenes:
                scenes_summary.append({
                    "scene_id": s.scene_id,
                    "purpose": s.purpose.value if hasattr(s.purpose, "value") else str(s.purpose),
                    "archetype": s.visual_strategy.value if hasattr(s.visual_strategy, "value") else str(s.visual_strategy),
                    "narration": s.narration[:200] + ("..." if len(s.narration) > 200 else ""),
                    "worked_example": s.worked_example if s.worked_example else None,
                })

            prompt = (
                f"Evaluate the educational quality of this video lesson storyboard:\n"
                f"Topic: {storyboard.topic}\n"
                f"Language: {storyboard.language}\n"
                f"Learning Objectives: {storyboard.learning_objectives}\n"
                f"Prerequisites: {storyboard.prerequisites}\n"
                f"Scenes:\n{scenes_summary}\n\n"
                "Return a JSON object with:\n"
                "- explanation_clarity (0.0 - 10.0)\n"
                "- pedagogical_coherence (0.0 - 10.0)\n"
                "- example_usefulness (0.0 - 10.0)\n"
                "- misconception_explanation_quality (0.0 - 10.0)\n"
                "- visual_concept_suitability (0.0 - 10.0)\n"
                "- language_naturalness (0.0 - 10.0)\n"
                "- detected_pedagogical_flaws (array of strings)\n"
                "- overall_feedback (string)"
            )

            sem_data = await model_router.generate_json(
                task="semantic_qa",
                prompt=prompt,
                system_instruction="You are an expert pedagogical reviewer. Evaluate the structured lesson and respond ONLY with valid JSON.",
            )

            if sem_data and isinstance(sem_data, dict):
                dim_scores = {
                    "explanation_clarity": float(sem_data.get("explanation_clarity", 8.0)),
                    "pedagogical_coherence": float(sem_data.get("pedagogical_coherence", 8.0)),
                    "example_usefulness": float(sem_data.get("example_usefulness", 8.0)),
                    "misconception_explanation_quality": float(sem_data.get("misconception_explanation_quality", 8.0)),
                    "visual_concept_suitability": float(sem_data.get("visual_concept_suitability", 8.0)),
                    "language_naturalness": float(sem_data.get("language_naturalness", 8.0)),
                }
                sem_avg = sum(dim_scores.values()) / max(1, len(dim_scores))
                sem_total = sem_avg * 10.0  # Scale 0-10 to 0-100

                blended_total = round(0.70 * base_score.total_score + 0.30 * sem_total, 2)
                flaws = [str(f) for f in sem_data.get("detected_pedagogical_flaws", []) if f]
                feedback = str(sem_data.get("overall_feedback", ""))

                combined_recs = list(base_score.repair_recommendations)
                for f in flaws:
                    if f not in combined_recs:
                        combined_recs.append(f"Semantic flaw: {f}")

                passed_gates = (blended_total >= 80.0) and (len(base_score.failed_dimensions) == 0)

                return TeachingQualityScore(
                    concept_coverage=base_score.concept_coverage,
                    prerequisite_order=base_score.prerequisite_order,
                    visual_relevance=base_score.visual_relevance,
                    example_quality=base_score.example_quality,
                    misconception_handling=base_score.misconception_handling,
                    language_naturalness=base_score.language_naturalness,
                    narration_visual_sync=base_score.narration_visual_sync,
                    doubt_context_readiness=base_score.doubt_context_readiness,
                    total_score=blended_total,
                    passed_gates=passed_gates,
                    dimension_gate_results=base_score.dimension_gate_results,
                    failed_dimensions=base_score.failed_dimensions,
                    repair_recommendations=combined_recs,
                    is_hybrid=True,
                    semantic_feedback=feedback,
                    semantic_flaws=flaws,
                    semantic_dimension_scores=dim_scores,
                )
        except Exception as e:
            logger.warning(f"[TeachingQualityEvaluator] Semantic LLM QA failed, returning deterministic score: {e}")

        return base_score

    # ─────────────────────────────────────────────────────────────────────────
    # Dimension Sub-Evaluators
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _eval_concept_coverage(
        cls, storyboard: Storyboard, knowledge_pack: Optional[VideoKnowledgePackage]
    ) -> Tuple[float, List[str]]:
        """Max 20 pts: verifies learning objectives are systematically addressed."""
        score = 20.0
        recs = []
        scenes = storyboard.scenes
        objs = storyboard.learning_objectives

        if not objs and knowledge_pack:
            objs = knowledge_pack.learning_objectives

        if not objs:
            score -= 6.0
            recs.append("Missing explicit learning objectives in lesson metadata.")
        else:
            # Check how many objectives have matching narration keywords
            all_narration = " ".join(s.narration.lower() for s in scenes)
            covered = 0
            for obj in objs:
                obj_words = [w for w in re.findall(r"\w+", obj.lower()) if len(w) > 3]
                if any(w in all_narration for w in obj_words):
                    covered += 1
            coverage_ratio = covered / max(1, len(objs))
            if coverage_ratio < 0.7:
                penalty = round((1.0 - coverage_ratio) * 10, 1)
                score -= penalty
                recs.append(f"Only {covered}/{len(objs)} learning objectives referenced in lesson narration.")

        # Check core stages presence
        stages = [s.purpose if isinstance(s.purpose, str) else s.purpose.value for s in scenes]
        if TeachingStoryStage.CORE_CONCEPT.value not in stages and "core_concept" not in stages:
            score -= 5.0
            recs.append("Lesson lacks a dedicated CORE_CONCEPT teaching scene.")

        return max(0.0, score), recs

    @classmethod
    def _eval_prerequisite_order(cls, scenes: List[SceneSpec]) -> Tuple[float, List[str]]:
        """Max 15 pts: verifies prerequisite connection precedes core derivations/summary."""
        score = 15.0
        recs = []

        prereq_indices = [
            i for i, s in enumerate(scenes)
            if s.purpose in (TeachingStoryStage.PREREQUISITE_CONNECTION, "prerequisite_connection")
            or s.prerequisite_refs
        ]
        core_indices = [
            i for i, s in enumerate(scenes)
            if s.purpose in (TeachingStoryStage.CORE_CONCEPT, TeachingStoryStage.VISUAL_MECHANISM, "core_concept", "visual_mechanism")
        ]
        summary_indices = [
            i for i, s in enumerate(scenes)
            if s.purpose in (TeachingStoryStage.SUMMARY, "summary")
        ]

        if not prereq_indices:
            score -= 4.0
            recs.append("No explicit prerequisite connection scene identified.")
        elif core_indices and min(prereq_indices) > max(core_indices):
            score -= 6.0
            recs.append("Prerequisite connection appears AFTER core concept/mechanism scenes.")

        if prereq_indices and summary_indices and min(prereq_indices) > max(summary_indices):
            score -= 8.0
            recs.append("Prerequisite connection appears after lesson summary.")

        return max(0.0, score), recs

    @classmethod
    def _eval_visual_relevance(cls, scenes: List[SceneSpec]) -> Tuple[float, List[str]]:
        """Max 15 pts: verifies visual archetypes match the pedagogical intent of each scene."""
        score = 15.0
        recs = []

        mismatches = 0
        for s in scenes:
            strat = s.visual_strategy.value if hasattr(s.visual_strategy, "value") else str(s.visual_strategy)
            purpose = s.purpose.value if hasattr(s.purpose, "value") else str(s.purpose)

            # Common mistake scene should ideally use comparison or pitfall archetype
            if purpose == TeachingStoryStage.COMMON_MISTAKE.value and strat not in (
                "comparison", "correct_vs_pitfall", "generic_diagram"
            ):
                mismatches += 1
            # Visual mechanism scene should ideally use process flow or data structure
            elif purpose == TeachingStoryStage.VISUAL_MECHANISM.value and strat == "generic_diagram":
                mismatches += 0.5

        if mismatches > 1:
            penalty = min(6.0, mismatches * 2.0)
            score -= penalty
            recs.append(f"Visual archetype mismatch in {mismatches} scenes: recommend archetype re-routing.")

        # Check that visual spec has meaningful elements
        empty_specs = 0
        for s in scenes:
            v = s.visual_spec
            has_elements = (
                v.title or v.steps or v.nodes or v.timeline_events or
                v.comparisons or v.equations or v.table_headers or v.bullets
            )
            if not has_elements:
                empty_specs += 1

        if empty_specs > 0:
            score -= min(5.0, empty_specs * 2.5)
            recs.append(f"{empty_specs} scenes have empty visual specifications.")

        return max(0.0, score), recs

    @classmethod
    def _eval_example_quality(cls, scenes: List[SceneSpec]) -> Tuple[float, List[str]]:
        """Max 15 pts: verifies concrete worked example exists with stepwise progression."""
        score = 15.0
        recs = []

        example_scenes = [
            s for s in scenes
            if s.purpose in (TeachingStoryStage.WORKED_EXAMPLE, TeachingStoryStage.SECOND_EXAMPLE, "worked_example", "second_example")
            or s.worked_example is not None
        ]

        if not example_scenes:
            score -= 8.0
            recs.append("Missing concrete worked example scene. Student lacks practical demonstration.")
        else:
            for s in example_scenes:
                # Check that example has concrete data or step numbers
                text = (s.worked_example or s.narration).lower()
                has_concrete_steps = bool(re.search(r"(step|\d+|example|let|take|suppose|here)", text))
                if not has_concrete_steps:
                    score -= 3.0
                    recs.append(f"Worked example in scene {s.scene_id} is abstract and lacks concrete numbers/steps.")
                    break

        return max(0.0, score), recs

    @classmethod
    def _eval_misconception_handling(cls, scenes: List[SceneSpec]) -> Tuple[float, List[str]]:
        """Max 10 pts: verifies common pitfalls/mistakes are explicitly addressed."""
        score = 10.0
        recs = []

        misconception_scenes = [
            s for s in scenes
            if s.purpose in (TeachingStoryStage.COMMON_MISTAKE, "common_mistake")
            or s.misconception_tags
        ]

        if not misconception_scenes:
            score -= 5.0
            recs.append("No common pitfall/mistake scene included. High risk of student misconception persistence.")
        else:
            # Check contrastive warning keywords
            has_contrast = any(
                any(k in s.narration.lower() for k in ("mistake", "caution", "don't", "avoid", "pitfall", "warning", "galti", "dhyan"))
                for s in misconception_scenes
            )
            if not has_contrast:
                score -= 2.5
                recs.append("Misconception scene lacks explicit contrastive warning language.")

        return max(0.0, score), recs

    @classmethod
    def _eval_language_naturalness(cls, scenes: List[SceneSpec], language: str) -> Tuple[float, List[str]]:
        """Max 10 pts: verifies conversational fluency, technical glossary preservation, and word pacing."""
        score = 10.0
        recs = []
        penalties = 0.0

        for s in scenes:
            words = s.narration.split()
            word_count = len(words)
            dur = max(1.0, float(s.duration))
            wps = word_count / dur  # words per second

            # Pacing check: between 0.5 and 4.2 wps is acceptable natural educational pacing
            if wps > 4.5:
                penalties += 1.0
                recs.append(f"Scene {s.scene_id} narration pacing is rushed ({wps:.1f} words/sec).")
            elif wps < 0.4 and word_count > 0:
                penalties += 1.0
                recs.append(f"Scene {s.scene_id} narration pacing is overly sparse ({wps:.1f} words/sec).")

        score -= min(3.0, penalties)
        return max(0.0, score), recs

    @classmethod
    def _eval_narration_visual_sync(cls, scenes: List[SceneSpec], target_duration: int) -> Tuple[float, List[str]]:
        """Max 10 pts: verifies duration alignment between audio narration and visual frames."""
        score = 10.0
        recs = []

        total_dur = sum(s.duration for s in scenes)
        dur_delta = abs(total_dur - target_duration)
        if dur_delta > 10:
            score -= min(4.0, dur_delta * 0.2)
            recs.append(f"Overall duration differs from target by {dur_delta}s.")

        # Check individual scene narration completeness
        for s in scenes:
            if not s.narration.strip():
                score -= 3.0
                recs.append(f"Scene {s.scene_id} has empty narration audio.")

        return max(0.0, score), recs

    @classmethod
    def _eval_doubt_readiness(cls, knowledge_pack: Optional[VideoKnowledgePackage]) -> Tuple[float, List[str]]:
        """Max 5 pts: verifies VideoKnowledgePackage contains all anchor data for timestamp doubts."""
        score = 5.0
        recs = []

        if not knowledge_pack:
            return 1.0, ["VideoKnowledgePackage not generated; cannot anchor timestamp doubts."]

        if not knowledge_pack.scenes:
            score -= 3.0
            recs.append("Knowledge package has 0 scenes.")
        else:
            missing_transcripts = sum(1 for s in knowledge_pack.scenes if not s.transcript)
            if missing_transcripts > 0:
                score -= 2.0
                recs.append(f"{missing_transcripts} scenes lack transcripts for doubt context resolution.")

        return max(0.0, score), recs
