"""
LearnByGenie Notes Decision Engine — Adaptive Learning Flow Planner
==================================================================
Synthesizes the authoritative LearningFlowPlan for Step 2.
Determines HOW this specific learner should learn this topic.
Deterministic, policy-driven, zero LLM calls, zero topic whitelisting.
"""
from typing import List, Dict, Any, Optional
import uuid

from app.services.notes.context.schemas import CanonicalNotesContext
from .policies import MasteryBracket, TopicCategory
from .learning_flow_schemas import (
    LearningMode, CognitiveOperation, LearnerKnowledgeState,
    LearnerEntryState, LearningStageItem, LearningCheckpoint,
    AdaptationRule, MasteryCheckPlan, PrerequisiteStrategy,
    ExplanationStrategy, InteractionStrategy, RetrievalStrategy,
    MisconceptionStrategy, ExampleStrategy, PracticeStrategy,
    RevisionStrategy, LearningFlowPlan
)


class LearningFlowPlanner:
    """
    Synthesizes a personalized, machine-readable LearningFlowPlan
    from learner context, assessment signals, lesson state, and topic structure.
    """

    @classmethod
    def plan(
        cls,
        ctx: CanonicalNotesContext,
        mastery_bracket: MasteryBracket,
        avg_mastery: float,
        topic_category: TopicCategory,
        primary_purpose: str,
        exam_state: Optional[str] = None,
        teaching_mode: str = "balanced"
    ) -> LearningFlowPlan:
        # ── 1. Infer Learner Entry State with Provenance ──
        entry_state = cls._derive_entry_state(ctx, mastery_bracket, avg_mastery, exam_state)

        # ── 2. Select Primary Learning Mode ──
        mode = cls._select_learning_mode(entry_state, primary_purpose, teaching_mode)

        # ── 3. Compose Ordered Learning Stages ──
        stages = cls._compose_stages(ctx, entry_state, mode, topic_category)

        # ── 4. Build Checkpoints & Gating ──
        checkpoints = cls._build_checkpoints(ctx, stages, entry_state)

        # ── 5. Build Sub-Strategies ──
        prereq_strat = cls._build_prerequisite_strategy(ctx, entry_state)
        expl_strat = cls._build_explanation_strategy(entry_state)
        interact_strat = cls._build_interaction_strategy(mode, entry_state)
        retrieval_strat = cls._build_retrieval_strategy(mode, entry_state)
        misc_strat = cls._build_misconception_strategy(ctx, entry_state)
        example_strat = cls._build_example_strategy(entry_state, mode)
        practice_strat = cls._build_practice_strategy(entry_state, mode)
        revision_strat = cls._build_revision_strategy(entry_state, mode)
        mastery_check = cls._build_mastery_check(ctx, entry_state, mode)

        # ── 6. Build Adaptation Rules ──
        adaptation_rules = cls._build_adaptation_rules(entry_state)

        # ── 7. Rationale & Evidence ──
        rationale, evidence = cls._compile_rationale_and_evidence(
            entry_state, mode, len(stages), misc_strat.required, prereq_strat.required
        )

        return LearningFlowPlan(
            schema_version="1.0",
            entry_state=entry_state,
            target_state="proficient" if entry_state.mastery != "high" else "advanced",
            learning_mode=mode,
            sequence=stages,
            checkpoints=checkpoints,
            prerequisite_strategy=prereq_strat,
            explanation_strategy=expl_strat,
            interaction_strategy=interact_strat,
            retrieval_strategy=retrieval_strat,
            misconception_strategy=misc_strat,
            example_strategy=example_strat,
            practice_strategy=practice_strat,
            revision_strategy=revision_strat,
            mastery_check=mastery_check,
            exit_condition=f"Demonstrated verified proficiency in {ctx.topic}",
            adaptation_rules=adaptation_rules,
            rationale=rationale,
            confidence=0.95 if entry_state.provenance else 0.80,
            evidence=evidence
        )

    @classmethod
    def _derive_entry_state(
        cls,
        ctx: CanonicalNotesContext,
        mastery_bracket: MasteryBracket,
        avg_mastery: float,
        exam_state: Optional[str]
    ) -> LearnerEntryState:
        provenance: Dict[str, str] = {}

        # 1. Mastery Score & Level
        mastery_val = "unknown"
        mastery_score = None
        if avg_mastery is not None and avg_mastery >= 0.0:
            mastery_score = round(avg_mastery, 3)
            if mastery_bracket == MasteryBracket.LOW:
                mastery_val = "low"
            elif mastery_bracket == MasteryBracket.HIGH:
                mastery_val = "high"
            else:
                mastery_val = "medium"

            if ctx.student_mastery:
                provenance["mastery"] = "ctx.student_mastery"
            elif hasattr(ctx, "assessment") and ctx.assessment and ctx.assessment.mastery:
                provenance["mastery"] = "ctx.assessment.mastery"
            elif hasattr(ctx, "student") and ctx.student and ctx.student.current_learning_state:
                provenance["mastery"] = "ctx.student.current_learning_state"
            else:
                provenance["mastery"] = "inferred_from_grade_baseline"

        # 2. Knowledge State
        if mastery_val == "low":
            knowledge_state = LearnerKnowledgeState.NOVICE.value if avg_mastery < 0.3 else LearnerKnowledgeState.EMERGING.value
        elif mastery_val == "high":
            knowledge_state = LearnerKnowledgeState.ADVANCED.value if avg_mastery > 0.85 else LearnerKnowledgeState.PROFICIENT.value
        elif mastery_val == "medium":
            knowledge_state = LearnerKnowledgeState.DEVELOPING.value
        else:
            knowledge_state = LearnerKnowledgeState.UNKNOWN.value

        # 3. Misconceptions
        all_misconceptions = list(dict.fromkeys(
            ctx.student_misconceptions + ctx.expected_misconceptions +
            ([p.get("concept", "") for p in ctx.quiz_mistakes if isinstance(p, dict) and p.get("concept")] if hasattr(ctx, "quiz_mistakes") and ctx.quiz_mistakes else [])
        ))
        all_misconceptions = [m for m in all_misconceptions if m]

        if len(all_misconceptions) >= 2:
            misc_state = "multiple"
            provenance["misconception_state"] = "multiple_misconceptions_detected"
        elif len(all_misconceptions) == 1:
            misc_state = "confirmed"
            provenance["misconception_state"] = "confirmed_misconception"
        elif hasattr(ctx, "quiz_mistakes") and ctx.quiz_mistakes:
            misc_state = "suspected"
            provenance["misconception_state"] = "quiz_mistakes_signal"
        else:
            misc_state = "none_known"

        # 4. Exam Urgency
        instructions_lower = (ctx.explicit_user_instructions or "").lower()
        exam_in_days = getattr(ctx.resolved_context, "exam_in_days", None) if getattr(ctx, "resolved_context", None) else None
        if "exam tomorrow" in instructions_lower or "test tomorrow" in instructions_lower or "24 hours" in instructions_lower or "2 days" in instructions_lower or (exam_in_days is not None and exam_in_days <= 2) or exam_state == "immediate":
            exam_urgency = "immediate"
            provenance["exam_urgency"] = "immediate_exam"
        elif "exam in 7 days" in instructions_lower or "exam next week" in instructions_lower or (exam_in_days is not None and exam_in_days <= 7) or exam_state == "near":
            exam_urgency = "high"
            provenance["exam_urgency"] = "near_exam"
        elif "exam" in instructions_lower or "test" in instructions_lower or exam_state == "far":
            exam_urgency = "medium"
            provenance["exam_urgency"] = "exam_mentioned"
        else:
            exam_urgency = "none"

        # 5. Engagement State
        teaching_method = "unknown"
        if getattr(ctx, "resolved_context", None) and ctx.resolved_context.teaching_method and ctx.resolved_context.teaching_method != "unknown":
            teaching_method = ctx.resolved_context.teaching_method
        elif hasattr(ctx, "lesson") and ctx.lesson and ctx.lesson.teaching_method and ctx.lesson.teaching_method != "unknown":
            teaching_method = ctx.lesson.teaching_method

        method_lower = (teaching_method or "unknown").lower()
        if any(k in method_lower for k in ["active", "inquiry", "hands-on", "interactive", "flipped", "discussion"]):
            engagement_state = "active"
            provenance["engagement_state"] = "lesson.teaching_method"
        elif any(k in method_lower for k in ["passive", "lecture", "direct_instruction", "reading"]):
            engagement_state = "passive"
            provenance["engagement_state"] = "lesson.teaching_method"
        else:
            engagement_state = "unknown"

        # 6. Prerequisite State
        if ctx.weak_concepts:
            prereq_state = "partial" if len(ctx.weak_concepts) == 1 else "missing"
            provenance["prerequisite_state"] = "ctx.weak_concepts"
        elif mastery_val == "low":
            prereq_state = "partial"
            provenance["prerequisite_state"] = "low_mastery_inference"
        elif mastery_val == "high":
            prereq_state = "adequate"
            provenance["prerequisite_state"] = "high_mastery_inference"
        else:
            prereq_state = "unknown"

        # 7. Prior Exposure
        if mastery_val == "high" or (hasattr(ctx, "assessment") and ctx.assessment and ctx.assessment.attempts > 1):
            prior_exposure = "high"
            provenance["prior_exposure"] = "assessment_attempts_or_mastery"
        elif mastery_val == "low":
            prior_exposure = "low"
            provenance["prior_exposure"] = "low_mastery"
        else:
            prior_exposure = "unknown"

        return LearnerEntryState(
            knowledge_state=knowledge_state,
            mastery=mastery_val,
            mastery_score=mastery_score,
            confidence="low" if mastery_val == "low" else ("high" if mastery_val == "high" else "medium"),
            misconception_state=misc_state,
            prerequisite_state=prereq_state,
            exam_urgency=exam_urgency,
            engagement_state=engagement_state,
            prior_exposure=prior_exposure,
            provenance=provenance
        )

    @classmethod
    def _select_learning_mode(
        cls,
        entry: LearnerEntryState,
        primary_purpose: str,
        teaching_mode: str
    ) -> LearningMode:
        # Remediation takes priority if severe misconception or low mastery
        if entry.misconception_state in ("confirmed", "multiple") or entry.mastery == "low":
            return LearningMode.REMEDIATION

        if entry.exam_urgency in ("immediate", "high") or primary_purpose == "exam_preparation":
            return LearningMode.EXAM_PREPARATION

        if entry.mastery == "high":
            return LearningMode.MASTERY

        if entry.engagement_state == "passive" or teaching_mode == "passive":
            return LearningMode.GUIDED_DISCOVERY

        if entry.engagement_state == "active" or teaching_mode == "active":
            return LearningMode.ACTIVE_RETRIEVAL

        if primary_purpose == "revision":
            return LearningMode.REVISION

        if primary_purpose == "remediation":
            return LearningMode.REMEDIATION

        return LearningMode.MIXED

    @classmethod
    def _compose_stages(
        cls,
        ctx: CanonicalNotesContext,
        entry: LearnerEntryState,
        mode: LearningMode,
        topic_category: TopicCategory
    ) -> List[LearningStageItem]:
        stages: List[LearningStageItem] = []
        topic = ctx.topic
        stage_num = 1

        def _add_stage(name: str, stage_mode: LearningMode, op: CognitiveOperation, goal: str, interactive: bool = False, i_type: Optional[str] = None, scaff: str = "moderate", why: str = ""):
            nonlocal stage_num
            stages.append(LearningStageItem(
                stage_id=f"stg_{stage_num:02d}_{name}",
                stage_name=name,
                mode=stage_mode,
                cognitive_operation=op,
                target_concept=topic,
                instructional_goal=goal,
                is_interactive=interactive,
                interaction_type=i_type,
                scaffolding_level=scaff,
                rationale=why
            ))
            stage_num += 1

        # ── Branch A: Low Mastery / Remediation Flow ──
        if entry.mastery == "low" or entry.misconception_state in ("confirmed", "multiple") or mode == LearningMode.REMEDIATION:
            if entry.prerequisite_state in ("missing", "partial"):
                _add_stage("prerequisite_bridge", LearningMode.REMEDIATION, CognitiveOperation.RECALL,
                           f"Bridge foundational prerequisites required to grasp {topic}.", scaff="guided",
                           why="Learner has missing/partial prerequisite concepts.")

            if entry.misconception_state in ("confirmed", "multiple"):
                _add_stage("misconception_repair", LearningMode.REMEDIATION, CognitiveOperation.DIAGNOSE,
                           f"Scientifically diagnose and debunk confirmed misconceptions in {topic}.", scaff="intensive",
                           why="Learner holds confirmed misconception requiring explicit scientific debunking.")

            _add_stage("intuition_builder", LearningMode.ABSORPTION, CognitiveOperation.EXPLAIN,
                       f"Establish simple, intuitive mental models of {topic} before formal abstraction.", scaff="guided",
                       why="Low mastery requires intuitive scaffolding before formal laws.")

            _add_stage("formal_mechanism", LearningMode.ABSORPTION, CognitiveOperation.RECOGNIZE,
                       f"Explicate formal scientific laws and mechanism boundaries governing {topic}.", scaff="guided",
                       why="Anchor intuitive understanding to formal curriculum standards.")

            _add_stage("visual_model", LearningMode.ABSORPTION, CognitiveOperation.CLASSIFY,
                       f"Provide clear structural diagram/model of {topic}.", scaff="moderate",
                       why="Visual representation assists mental model anchoring.")

            _add_stage("guided_worked_example", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.APPLY,
                       f"Solve a concrete worked problem step-by-step with explicit rationale.", interactive=True, i_type="thinking_checkpoint", scaff="guided",
                       why="Guided problem solving builds initial procedural confidence.")

            _add_stage("easy_retrieval", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Test immediate recall of foundational terms and mechanisms.", interactive=True, i_type="retrieval_question", scaff="moderate",
                       why="Active recall prevents passive illusion of competence.")

            _add_stage("supported_practice", LearningMode.PRACTICE, CognitiveOperation.APPLY,
                       f"Solve scaffolded practice items progressing from recall to simple application.", scaff="guided",
                       why="Practice progression tuned to learner entry ability.")

            _add_stage("mastery_check", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.EXPLAIN,
                       f"Verify whether learner can explain core mechanism independently.", interactive=True, i_type="explain_back", scaff="moderate",
                       why="Check exit criteria to confirm mastery acquisition.")

            _add_stage("revision_synthesis", LearningMode.REVISION, CognitiveOperation.RECALL,
                       f"Provide concise takeaways and key formulas for memory retention.", scaff="minimal",
                       why="Consolidate learned material into high-yield summary.")

        # ── Branch B: High Mastery Flow ──
        elif entry.mastery == "high" or mode == LearningMode.MASTERY:
            _add_stage("diagnostic_retrieval", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Rapid diagnostic retrieval to confirm baseline fluency in {topic}.", interactive=True, i_type="retrieval_question", scaff="minimal",
                       why="High-mastery student verifies baseline rapidly without babying.")

            _add_stage("concept_compression", LearningMode.MASTERY, CognitiveOperation.EXPLAIN,
                       f"Compressed, high-density synthesis of core mechanisms without elementary repetition.", scaff="minimal",
                       why="Avoid repetitive definitions; focus on deep structural properties.")

            _add_stage("edge_cases_and_traps", LearningMode.MASTERY, CognitiveOperation.DIAGNOSE,
                       f"Analyze non-obvious edge cases, boundary failures, and tricky distinctions.", scaff="moderate",
                       why="Challenge high-mastery learners with non-trivial domain limits.")

            _add_stage("guided_discovery", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.PREDICT,
                       f"Predict behavior in complex or novel physical scenarios.", interactive=True, i_type="prediction_prompt", scaff="minimal",
                       why="Foster critical reasoning through prediction rather than exposition.")

            _add_stage("transfer_problem", LearningMode.MASTERY, CognitiveOperation.TRANSFER,
                       f"Worked problem applying {topic} across cross-disciplinary or transfer boundaries.", scaff="moderate",
                       why="High mastery demands transfer across unfamiliar contexts.")

            _add_stage("challenge_practice", LearningMode.PRACTICE, CognitiveOperation.EVALUATE,
                       f"Solve advanced multi-step application and evaluation questions.", scaff="minimal",
                       why="Practice calibrated to advanced cognitive operations.")

            _add_stage("mastery_check", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.TRANSFER,
                       f"Complex self-explanation or error-diagnosis task verifying true expert grasp.", interactive=True, i_type="explain_back", scaff="minimal",
                       why="Rigorous exit verification for high mastery.")

        # ── Branch C: Exam Urgent Flow ──
        elif entry.exam_urgency in ("immediate", "high") or mode == LearningMode.EXAM_PREPARATION:
            _add_stage("rapid_prerequisite_scan", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Rapid scan of critical prerequisites and foundational formulas.", interactive=True, i_type="retrieval_question", scaff="minimal",
                       why="Verify exam-critical prerequisites under tight time constraint.")

            _add_stage("high_yield_synthesis", LearningMode.EXAM_PREPARATION, CognitiveOperation.EXPLAIN,
                       f"High-yield core concept summary focusing on frequently examined mechanisms.", scaff="moderate",
                       why="Optimize cognitive yield per study minute.")

            _add_stage("formula_and_relationships", LearningMode.EXAM_PREPARATION, CognitiveOperation.CLASSIFY,
                       f"Formula sheet, unit relationships, and boundary condition summary.", scaff="minimal",
                       why="Direct reference for quantitative problem solving.")

            _add_stage("common_traps_and_pitfalls", LearningMode.REMEDIATION, CognitiveOperation.DIAGNOSE,
                       f"Catalog of frequent exam traps and common marking deduction triggers.", scaff="guided",
                       why="Prevent costly exam mistakes on known trick questions.")

            _add_stage("exam_worked_problems", LearningMode.EXAM_PREPARATION, CognitiveOperation.APPLY,
                       f"Step-by-step solutions to representative board/exam questions with marking scheme tips.", scaff="moderate",
                       why="Align directly with marking scheme criteria.")

            _add_stage("progressive_timed_practice", LearningMode.PRACTICE, CognitiveOperation.APPLY,
                       f"Timed exam-style practice questions spanning moderate to tricky questions.", scaff="minimal",
                       why="Simulate authentic examination pacing.")

            _add_stage("mastery_check", LearningMode.EXAM_PREPARATION, CognitiveOperation.EVALUATE,
                       f"Timed exit diagnostic checking error-free execution.", interactive=True, i_type="thinking_checkpoint", scaff="minimal",
                       why="Verify readiness for immediate assessment.")

            _add_stage("final_recall_sheet", LearningMode.REVISION, CognitiveOperation.RECALL,
                       f"1-page rapid revision cheat sheet for last-minute review.", scaff="minimal",
                       why="Last-minute memory consolidation before test.")

        # ── Branch D: Active Lesson Flow (Advanced Application & Error Analysis) ──
        elif entry.engagement_state == "active" or mode == LearningMode.ACTIVE_RETRIEVAL:
            _add_stage("diagnostic_retrieval", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Confirm problem-solving fluency in {topic} without repeating elementary definitions.", interactive=True, i_type="retrieval_question", scaff="minimal",
                       why="Active student verifies baseline rapidly.")

            _add_stage("concept_compression", LearningMode.MASTERY, CognitiveOperation.EXPLAIN,
                       f"High-density structural synthesis focusing on advanced invariant properties.", scaff="minimal",
                       why="Skip elementary definitions; focus on non-trivial mathematical/physical invariants.")

            _add_stage("edge_cases_and_traps", LearningMode.MASTERY, CognitiveOperation.DIAGNOSE,
                       f"Error analysis of boundary cases, common exam traps, and non-obvious failure modes.", scaff="moderate",
                       why="Deepen fluency by analyzing tricky edge cases and common errors.")

            _add_stage("transfer_problem", LearningMode.MASTERY, CognitiveOperation.TRANSFER,
                       f"Multi-step problem applying {topic} across novel or cross-domain contexts.", scaff="moderate",
                       why="Push student beyond routine textbook exercises.")

            _add_stage("challenge_practice", LearningMode.PRACTICE, CognitiveOperation.EVALUATE,
                       f"Advanced practice problems demanding multi-step synthesis and evaluation.", scaff="minimal",
                       why="Practice calibrated to active learner readiness.")

            _add_stage("mastery_check", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.EVALUATE,
                       f"Rigorous exit benchmark challenging student to diagnose an intentionally flawed solution.", interactive=True, i_type="thinking_checkpoint", scaff="minimal",
                       why="Verify authentic mastery via critical error diagnosis.")

        # ── Branch E: Passive Lesson Flow (Guided Discovery & Cognitive Activation) ──
        elif entry.engagement_state == "passive" or mode == LearningMode.GUIDED_DISCOVERY:
            _add_stage("inquiry_prompt", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.PREDICT,
                       f"Socratic opening question prompting predictions about {topic}.", interactive=True, i_type="prediction_prompt", scaff="guided",
                       why="Engage active learner curiosity and break passive reception.")

            _add_stage("concept_exploration", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.EXPLAIN,
                       f"Explore observational evidence leading to conceptual conclusions.", interactive=True, i_type="thinking_checkpoint", scaff="moderate",
                       why="Guide student to derive the concept rather than passively read.")

            _add_stage("visual_model", LearningMode.ABSORPTION, CognitiveOperation.CLASSIFY,
                       f"Visual diagram confirming derived relationships.", scaff="minimal",
                       why="Support cognitive consolidation of derived knowledge.")

            _add_stage("guided_worked_problem", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.APPLY,
                       f"Interactive worked problem with pause-and-predict checkpoints.", interactive=True, i_type="thinking_checkpoint", scaff="moderate",
                       why="Maintain high cognitive participation during problem solving.")

            _add_stage("active_retrieval_checkpoint", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Prompt student to articulate core rules from memory.", interactive=True, i_type="retrieval_question", scaff="minimal",
                       why="Active retrieval reinforces derived memory traces.")

            _add_stage("independent_practice", LearningMode.PRACTICE, CognitiveOperation.APPLY,
                       f"Multi-level practice questions challenging understanding.", scaff="moderate",
                       why="Transfer derived concept to novel practice items.")

            _add_stage("mastery_check", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.EXPLAIN,
                       f"Self-explanation challenge explaining the mechanism in own words.", interactive=True, i_type="explain_back", scaff="minimal",
                       why="Verify authentic conceptual understanding through generative explanation.")

        # ── Branch F: Balanced / Mixed Flow (Default) ──
        else:
            _add_stage("concept_intro", LearningMode.ABSORPTION, CognitiveOperation.RECOGNIZE,
                       f"Introduction and intuitive foundation of {topic}.", scaff="moderate",
                       why="Provide balanced introductory scaffolding.")

            _add_stage("formal_mechanism", LearningMode.ABSORPTION, CognitiveOperation.EXPLAIN,
                       f"Scientific explanation of governing mechanisms and boundary rules.", scaff="moderate",
                       why="Core instructional exposition.")

            _add_stage("guided_worked_example", LearningMode.GUIDED_DISCOVERY, CognitiveOperation.APPLY,
                       f"Step-by-step worked problem with reasoning checkpoint.", interactive=True, i_type="thinking_checkpoint", scaff="moderate",
                       why="Bridge theory to quantitative application.")

            _add_stage("retrieval_checkpoint", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.RECALL,
                       f"Checkpoint question testing immediate recall of mechanism rules.", interactive=True, i_type="retrieval_question", scaff="minimal",
                       why="Interrupt passive reading with active retrieval.")

            _add_stage("progressive_practice", LearningMode.PRACTICE, CognitiveOperation.APPLY,
                       f"Tiered practice covering recall, conceptual reasoning, and application.", scaff="moderate",
                       why="Progressive cognitive load practice.")

            _add_stage("mastery_check", LearningMode.ACTIVE_RETRIEVAL, CognitiveOperation.EXPLAIN,
                       f"Explain-back challenge checking exit proficiency.", interactive=True, i_type="explain_back", scaff="minimal",
                       why="Exit verification.")

            _add_stage("revision_synthesis", LearningMode.REVISION, CognitiveOperation.RECALL,
                       f"High-yield revision takeaway points.", scaff="minimal",
                       why="Final retention summary.")

        return stages

    @classmethod
    def _build_checkpoints(
        cls,
        ctx: CanonicalNotesContext,
        stages: List[LearningStageItem],
        entry: LearnerEntryState
    ) -> List[LearningCheckpoint]:
        checkpoints: List[LearningCheckpoint] = []
        topic = ctx.topic

        # Place a diagnostic checkpoint after the first application or discovery stage
        for stg in stages:
            if stg.cognitive_operation in (CognitiveOperation.APPLY, CognitiveOperation.PREDICT) or stg.is_interactive:
                checkpoints.append(LearningCheckpoint(
                    checkpoint_id=f"chk_{stg.stage_id}",
                    after_stage=stg.stage_name,
                    cognitive_operation=stg.cognitive_operation,
                    prompt=f"Explain how the fundamental mechanism of {topic} dictates the outcome in this step.",
                    expected_evidence=f"Clear student articulation linking governing laws to resulting state in {topic}",
                    if_success="Proceed to advanced application and independent practice.",
                    if_failure=f"Activate targeted remediation on {topic} boundary laws.",
                    remediation_action="remediation_bridge"
                ))
                break

        return checkpoints

    @classmethod
    def _build_prerequisite_strategy(
        cls,
        ctx: CanonicalNotesContext,
        entry: LearnerEntryState
    ) -> PrerequisiteStrategy:
        if entry.prerequisite_state in ("missing", "partial") or entry.mastery == "low":
            gap = ctx.weak_concepts[0] if ctx.weak_concepts else f"foundational background for {ctx.topic}"
            return PrerequisiteStrategy(
                required=True,
                gap_identified=gap,
                bridge_action=f"Provide introductory conceptual bridge reviewing {gap} before introducing formal {ctx.topic} laws."
            )
        return PrerequisiteStrategy(required=False)

    @classmethod
    def _build_explanation_strategy(cls, entry: LearnerEntryState) -> ExplanationStrategy:
        if entry.mastery == "high":
            return ExplanationStrategy(depth="concise", analogy_style="minimal", formal_notation=True)
        elif entry.mastery == "low":
            return ExplanationStrategy(depth="scaffolded", analogy_style="concrete", formal_notation=True)
        return ExplanationStrategy(depth="standard", analogy_style="concrete", formal_notation=True)

    @classmethod
    def _build_interaction_strategy(cls, mode: LearningMode, entry: LearnerEntryState) -> InteractionStrategy:
        if mode == LearningMode.GUIDED_DISCOVERY or entry.engagement_state == "active":
            return InteractionStrategy(
                engagement_mode="active",
                interaction_intensity="high",
                cognitive_participation=["prediction", "reasoning", "explanation", "retrieval"]
            )
        elif mode == LearningMode.ABSORPTION or entry.engagement_state == "passive":
            return InteractionStrategy(
                engagement_mode="passive",
                interaction_intensity="none",
                cognitive_participation=["recognition", "recall"]
            )
        return InteractionStrategy(
            engagement_mode="mixed",
            interaction_intensity="medium",
            cognitive_participation=["recall", "explanation", "application"]
        )

    @classmethod
    def _build_retrieval_strategy(cls, mode: LearningMode, entry: LearnerEntryState) -> RetrievalStrategy:
        if mode == LearningMode.EXAM_PREPARATION:
            return RetrievalStrategy(frequency="frequent", formats=["rapid_recall", "fill_the_gap", "formula_reconstruction"])
        elif entry.mastery == "high":
            return RetrievalStrategy(frequency="strategic", formats=["error_diagnosis", "predict_before_reveal"])
        elif entry.mastery == "low":
            return RetrievalStrategy(frequency="strategic", formats=["direct_recall", "guided_check"])
        return RetrievalStrategy(frequency="strategic", formats=["direct_recall", "explain_in_own_words"])

    @classmethod
    def _build_misconception_strategy(
        cls,
        ctx: CanonicalNotesContext,
        entry: LearnerEntryState
    ) -> MisconceptionStrategy:
        all_misconceptions = list(dict.fromkeys(
            ctx.student_misconceptions + ctx.expected_misconceptions +
            ([p.get("concept", "") for p in ctx.quiz_mistakes if isinstance(p, dict) and p.get("concept")] if hasattr(ctx, "quiz_mistakes") and ctx.quiz_mistakes else [])
        ))
        all_misconceptions = [m for m in all_misconceptions if m]

        if all_misconceptions or entry.misconception_state in ("confirmed", "multiple", "suspected"):
            targets = all_misconceptions if all_misconceptions else ["standard textbook simplification"]
            return MisconceptionStrategy(
                required=True,
                has_misconceptions=True,
                remediation_depth="full_semantic_repair",
                target_misconceptions=targets,
                remediation_target_keys=targets
            )
        return MisconceptionStrategy(required=False, has_misconceptions=False, remediation_depth="none")

    @classmethod
    def _build_example_strategy(cls, entry: LearnerEntryState, mode: LearningMode) -> ExampleStrategy:
        if mode == LearningMode.EXAM_PREPARATION or entry.exam_urgency in ("immediate", "high"):
            return ExampleStrategy(style="exam_marking_oriented", scaffolding="moderate")
        elif entry.mastery == "high":
            return ExampleStrategy(style="tricky_edge_case", scaffolding="minimal")
        elif entry.mastery == "low":
            return ExampleStrategy(style="concrete_guided", scaffolding="intensive")
        return ExampleStrategy(style="representative_procedural", scaffolding="moderate")

    @classmethod
    def _build_practice_strategy(cls, entry: LearnerEntryState, mode: LearningMode) -> PracticeStrategy:
        if entry.mastery == "high":
            return PracticeStrategy(
                starting_difficulty="advanced",
                target_difficulty="advanced",
                scaffolding_level="minimal",
                progression=["application", "transfer", "challenge"],
                item_count=3,
                feedback_style="concise_rationale"
            )
        elif entry.mastery == "low":
            return PracticeStrategy(
                starting_difficulty="foundational",
                target_difficulty="basic",
                scaffolding_level="high",
                progression=["recall", "conceptual", "simple_application"],
                item_count=4,
                feedback_style="step_by_step"
            )
        elif mode == LearningMode.EXAM_PREPARATION:
            return PracticeStrategy(
                starting_difficulty="intermediate",
                target_difficulty="advanced",
                scaffolding_level="minimal",
                progression=["recall", "exam_style", "tricky_case"],
                item_count=3,
                feedback_style="marking_scheme"
            )
        return PracticeStrategy(
            starting_difficulty="basic",
            target_difficulty="intermediate",
            scaffolding_level="moderate",
            progression=["recall", "conceptual", "application"],
            item_count=3,
            feedback_style="step_by_step"
        )

    @classmethod
    def _build_revision_strategy(cls, entry: LearnerEntryState, mode: LearningMode) -> RevisionStrategy:
        if entry.exam_urgency in ("immediate", "high") or mode == LearningMode.EXAM_PREPARATION:
            return RevisionStrategy(compression_ratio="high", focus_areas=["formulas", "common_mistakes", "high_yield_takeaways"])
        return RevisionStrategy(compression_ratio="medium", focus_areas=["key_points", "concept_summary"])

    @classmethod
    def _build_mastery_check(
        cls,
        ctx: CanonicalNotesContext,
        entry: LearnerEntryState,
        mode: LearningMode
    ) -> MasteryCheckPlan:
        topic = ctx.topic
        if entry.mastery == "high":
            return MasteryCheckPlan(
                method="transfer_problem",
                target_concepts=[topic],
                cognitive_operation=CognitiveOperation.TRANSFER,
                success_criteria=f"Solve non-standard transfer problem applying {topic} across novel boundary conditions",
                fallback_if_failed="Review edge case assumptions and boundary law derivations"
            )
        elif entry.mastery == "low":
            return MasteryCheckPlan(
                method="self_explanation",
                target_concepts=[topic],
                cognitive_operation=CognitiveOperation.EXPLAIN,
                success_criteria=f"Accurately explain the core operational principle of {topic} in own words without jargon",
                fallback_if_failed="Re-read simple intuition builder and guided worked example"
            )
        return MasteryCheckPlan(
            method="concept_application",
            target_concepts=[topic],
            cognitive_operation=CognitiveOperation.APPLY,
            success_criteria=f"Correctly execute procedural steps to evaluate a standard problem in {topic}",
            fallback_if_failed="Review step-by-step worked example"
        )

    @classmethod
    def _build_adaptation_rules(cls, entry: LearnerEntryState) -> List[AdaptationRule]:
        rules: List[AdaptationRule] = [
            AdaptationRule(
                condition="if prerequisite_failed",
                action="activate_prerequisite_remediation",
                rationale="Restore missing background knowledge before proceeding."
            ),
            AdaptationRule(
                condition="if misconception_detected",
                action="execute_six_part_debunking_sequence",
                rationale="Directly dismantle wrong beliefs with scientific proof."
            ),
            AdaptationRule(
                condition="if retrieval_failed",
                action="revert_to_simpler_retrieval_and_explanation",
                rationale="Lower cognitive load and scaffold core concept."
            ),
            AdaptationRule(
                condition="if application_success",
                action="escalate_to_transfer_or_challenge",
                rationale="Foster higher-order Bloom taxonomy skills."
            ),
            AdaptationRule(
                condition="if high_mastery",
                action="skip_redundant_elementary_definitions",
                rationale="Respect learner expertise and maximize learning velocity."
            ),
            AdaptationRule(
                condition="if exam_imminent",
                action="compress_expository_prose_and_increase_exam_traps",
                rationale="Target score optimization under severe time pressure."
            )
        ]
        return rules

    @classmethod
    def _compile_rationale_and_evidence(
        cls,
        entry: LearnerEntryState,
        mode: LearningMode,
        stage_count: int,
        misc_required: bool,
        prereq_required: bool
    ) -> tuple[str, List[Dict[str, Any]]]:
        evidence: List[Dict[str, Any]] = []

        reasons = [f"Selected primary learning mode: {mode.value.upper()}."]
        if entry.mastery != "unknown":
            reasons.append(f"Learner mastery assessed as {entry.mastery.upper()} (score: {entry.mastery_score}).")
            evidence.append({"dimension": "mastery", "value": entry.mastery, "score": entry.mastery_score})

        if misc_required:
            reasons.append("Remediation stage activated due to confirmed or suspected misconceptions.")
            evidence.append({"dimension": "misconception", "state": entry.misconception_state})

        if prereq_required:
            reasons.append("Prerequisite bridging stage included to repair background conceptual gap.")
            evidence.append({"dimension": "prerequisite", "state": entry.prerequisite_state})

        if entry.exam_urgency != "none":
            reasons.append(f"Exam urgency is {entry.exam_urgency.upper()}; high-yield compression and exam traps prioritized.")
            evidence.append({"dimension": "exam_urgency", "urgency": entry.exam_urgency})

        if entry.engagement_state != "unknown":
            reasons.append(f"Engagement state is {entry.engagement_state.upper()}; matching instructional interaction.")
            evidence.append({"dimension": "engagement", "state": entry.engagement_state})

        reasons.append(f"Planned sequential progression of {stage_count} instructional stages.")
        rationale = " ".join(reasons)

        return rationale, evidence
