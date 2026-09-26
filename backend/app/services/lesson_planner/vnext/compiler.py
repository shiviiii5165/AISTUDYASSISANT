"""
Lesson Compiler for Lesson Planner VNext
========================================
Assembles the complete Evidence-Adaptive Teaching Plan by coordinating:
1. Input Normalization & Classifiers (Intent, Domain, Volatility)
2. Curriculum Resolver (Priority Ladder)
3. Knowledge Pack (Cognitive Brain Artifact)
4. Pedagogy Policy Engine (Stage Templates & Archetypes)
5. Dynamic Time Budget (Reserve Buffer)
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import re
from ..schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageReadiness,
    NextBestAction, ClassType, RoadmapStatus, ProductMode,
    CanonicalDomain, TeachingIntent, TopicVolatility, BloomLevel,
    PrerequisiteMasteryState, LearningObjective
)
from .classifiers import IntentClassifier, DomainClassifier, TopicVolatilityClassifier
from .knowledge_pack import KnowledgePackService
from .curriculum import CurriculumResolver
from .pedagogy import PedagogyPolicyEngine, ConceptType
from .time_budget import DynamicTimeBudgetEngine
from .canonical_concepts import CanonicalConceptResolver
from .shared_context import LearnerStateRepository

logger = logging.getLogger("teachgenie.lesson_planner.compiler")
COMPILER_SEMANTIC_VERSION = "2.2.0"


class LessonCompiler:
    """
    Compiles structured pedagogical stages from curriculum objectives,
    pedagogical policy, and dynamic time budgeting.
    """

    @classmethod
    async def compile_lesson_plan(
        cls,
        topic: str,
        grade: str = "B.Tech",
        subject: str = "General",
        duration_minutes: int = 60,
        language: str = "english",
        mode: ProductMode = ProductMode.TEACHER_CLASSROOM,
        custom_context: Optional[str] = None,
        board: str = "Standard",
        student_id: Optional[str] = None
    ) -> LearningRoadmap:
        """
        Main compilation pipeline for Lesson Planner VNext.
        """
        if isinstance(mode, str):
            try:
                mode = ProductMode(mode)
            except Exception:
                mode = ProductMode.TEACHER_CLASSROOM

        logger.info(f"[LessonCompiler] Compiling VNext Plan for '{topic}' ({grade}, {duration_minutes}m, mode={mode.value})")

        # 1. Classify Intent, Domain, and Volatility
        intent = IntentClassifier.classify(custom_context or topic)
        domain = DomainClassifier.classify(topic)
        volatility = TopicVolatilityClassifier.classify(topic, domain)

        # 2. Retrieve or generate Knowledge Pack (L1 cache hit is instant!)
        pack = await KnowledgePackService.get_or_create_pack(
            topic=topic,
            subject=subject,
            grade=grade,
            curriculum=board,
            language=language,
            custom_context=custom_context
        )

        # 3. Resolve Curriculum Objectives via Authoritative Priority Ladder
        curriculum_res = await CurriculumResolver.resolve(
            topic=topic,
            grade=grade,
            board=board,
            subject=subject,
            uploaded_context=custom_context,
            knowledge_pack=pack
        )

        # 4. Resolve Pedagogy Concept Type & Templates
        concept_type = PedagogyPolicyEngine.detect_concept_type(topic, domain, intent)
        stage_templates = PedagogyPolicyEngine.get_pedagogy_templates(concept_type)

        # 5. Calculate Dynamic Time Budget with 10-20% Reserve Buffer
        durations, reserve_mins = DynamicTimeBudgetEngine.calculate_initial_budget(
            total_duration_minutes=duration_minutes,
            templates=stage_templates,
            reserve_pct=0.10
        )

        # 6. Compile Stage Objects with Canonical Concept Identity & Learner Awareness
        stages: List[RoadmapStage] = []
        is_dp = bool(re.search(r"\b(dp|dynamic[\s-]programming)\b", topic, re.IGNORECASE))
        dp_stage_definitions = [
            {
                "title": "Foundations & Motivation: Overlapping Subproblems & Memoization",
                "focus": "Overlapping subproblems, recursion tree call explosion, and memoization motivation",
                "objectives": [
                    LearningObjective(
                        id="obj_dp_overlap",
                        description="Identify overlapping subproblems in recurrence call trees and formulate top-down memoization",
                        bloom_level=BloomLevel.UNDERSTAND,
                        is_mandatory=True
                    )
                ]
            },
            {
                "title": "Mental Model: Optimal Substructure & State Definition",
                "focus": "Optimal substructure, state formulation, and subproblem independence",
                "objectives": [
                    LearningObjective(
                        id="obj_dp_substruct",
                        description="Define state representation and verify optimal substructure across subproblems",
                        bloom_level=BloomLevel.ANALYZE,
                        is_mandatory=True
                    )
                ]
            },
            {
                "title": "Demonstration: Tabulation, Bottom-Up & Recurrences",
                "focus": "Bottom-up tabulation, iterative table construction, and recurrence relations",
                "objectives": [
                    LearningObjective(
                        id="obj_dp_tab",
                        description="Formulate recurrence relations and construct iterative bottom-up lookup tables",
                        bloom_level=BloomLevel.APPLY,
                        is_mandatory=True
                    )
                ]
            },
            {
                "title": "Guided Practice: 2D DP, Grid Traversal & Knapsack",
                "focus": "Multi-dimensional DP, grid traversal, and 0/1 knapsack state transitions",
                "objectives": [
                    LearningObjective(
                        id="obj_dp_knapsack",
                        description="Apply 2D dynamic programming to grid and 0/1 knapsack state transition problems",
                        bloom_level=BloomLevel.APPLY,
                        is_mandatory=True
                    )
                ]
            },
            {
                "title": "Diagnostic Check: State Invariants, Pitfalls, Complexity & Debugging",
                "focus": "State invariants, state transition mistakes, time/space complexity analysis, and debugging",
                "objectives": [
                    LearningObjective(
                        id="obj_dp_diag",
                        description="Diagnose state transition mistakes, off-by-one boundary errors, and evaluate space optimization",
                        bloom_level=BloomLevel.EVALUATE,
                        is_mandatory=True
                    )
                ]
            }
        ]

        pack_concepts = getattr(pack, "concepts", []) or []

        for i, (template, dur) in enumerate(zip(stage_templates, durations)):
            stage_id = f"stage_{i+1}_{uuid.uuid4().hex[:6]}"
            
            # Determine content semantics (WHAT is taught), decoupled from archetype (HOW it is taught)
            if is_dp:
                dp_def = dp_stage_definitions[i % len(dp_stage_definitions)]
                semantic_stage_title = dp_def["title"]
                stage_focus = dp_def["focus"]
                stage_objectives = dp_def["objectives"]
            elif pack_concepts:
                c_item = pack_concepts[i % len(pack_concepts)]
                c_title = c_item.get("title", "") if isinstance(c_item, dict) else getattr(c_item, "title", "")
                c_desc = c_item.get("description", "") if isinstance(c_item, dict) else getattr(c_item, "description", "")
                semantic_stage_title = f"{c_title}: {topic}" if c_title else f"{topic} Part {i+1}"
                stage_focus = f"{c_title} — {c_desc}"
                stage_objectives = curriculum_res.objectives[i:i+1] if i < len(curriculum_res.objectives) else curriculum_res.objectives[:1]
            else:
                semantic_stage_title = f"{topic}: Core Principles"
                stage_focus = f"{topic} core conceptual foundation"
                stage_objectives = curriculum_res.objectives[:2]

            # Request semantic concept resolution following the 6-tier priority ladder
            resolved_concepts = CanonicalConceptResolver.resolve_stage_semantics(
                topic=topic,
                knowledge_pack=pack,
                objectives=stage_objectives,
                stage_title=semantic_stage_title,
                stage_focus=stage_focus,
                prerequisite_graph=getattr(pack, "concept_dependencies", None),
                domain=domain
            )
            primary_concept_id = resolved_concepts[0] if resolved_concepts else "UNRESOLVED_CANONICAL_CONCEPT"
            
            # Prerequisite chaining
            prereqs = [stages[i-1].concept_id] if i > 0 else []

            # Check learner state if student_id is provided
            mastery_state = PrerequisiteMasteryState.UNKNOWN
            if student_id:
                state_entry = LearnerStateRepository.get_state(student_id, primary_concept_id)
                mastery_state = state_entry.mastery_state

            # Readiness and status derivation
            if mastery_state == PrerequisiteMasteryState.BLOCKING:
                readiness = StageReadiness.BLOCKED
                stage_status = StageStatus.BLOCKED
            elif mastery_state == PrerequisiteMasteryState.WEAK:
                readiness = StageReadiness.REVIEW_RECOMMENDED
                stage_status = StageStatus.NEEDS_REVIEW
            elif mastery_state in [PrerequisiteMasteryState.MASTERED, PrerequisiteMasteryState.LIKELY_MASTERED]:
                readiness = StageReadiness.READY
                stage_status = StageStatus.AVAILABLE
            else:
                # UNKNOWN or default
                readiness = StageReadiness.READY if i == 0 else StageReadiness.PREREQUISITE_REQUIRED
                stage_status = StageStatus.AVAILABLE if i == 0 else StageStatus.LOCKED

            # Why now rationales
            why_now = "Foundational orientation activating prior knowledge" if i == 0 else f"Builds directly on understanding established in {stages[i-1].title}"

            stage = RoadmapStage(
                id=stage_id,
                concept_id=primary_concept_id,
                canonical_concept_id=primary_concept_id,
                canonical_concept_ids=resolved_concepts,
                title=semantic_stage_title,
                description=template.pedagogy_goal,
                sequence=i,
                duration_minutes=dur,
                status=stage_status,
                readiness=readiness,
                mastery=85 if mastery_state == PrerequisiteMasteryState.MASTERED else (0 if mastery_state == PrerequisiteMasteryState.WEAK else 50),
                confidence=0,
                archetype=template.archetype,
                why_this_stage=template.pedagogy_goal,
                why_now=why_now,
                teaching_goal=template.pedagogy_goal,
                pedagogy_method=f"{concept_type.value.capitalize()} Pedagogy Strategy",
                teacher_actions=[template.suggested_teacher_action],
                student_actions=[template.suggested_student_action],
                visual_requirements=[f"System diagram for {topic}"] if template.requires_visual else [],
                assessment_requirement="Formative diagnostic check" if template.archetype.value == "diagnostic_check" else "",
                checkpoint_questions=[pack.assessment_targets[0]] if pack.assessment_targets else [f"Explain how {topic} applies in this scenario"],
                expected_misconceptions=[m.get("title", "") for m in pack.common_misconceptions[:2]],
                objectives=stage_objectives,
                objective_ids=[getattr(o, "id", f"obj_{i}") for o in stage_objectives],
                prerequisite_ids=prereqs,
                next_best_action=NextBestAction.TEACH
            )
            stages.append(stage)

        # 7. Assemble Full LearningRoadmap
        roadmap = LearningRoadmap(
            id=f"plan_{uuid.uuid4().hex[:12]}",
            course_id="vnext_curriculum",
            topic=topic,
            title=f"{topic} — Evidence-Adaptive Teaching Plan",
            description=f"{domain.value.replace('_', ' ').title()} curriculum plan compiled under {mode.value.replace('_', ' ').title()} mode.",
            level=grade,
            language=language,
            class_type=ClassType.INTERACTIVE_LECTURE,
            target_duration_minutes=duration_minutes,
            status=RoadmapStatus.DRAFT,
            mode=mode,
            domain=domain,
            intent=intent,
            volatility=volatility,
            knowledge_pack_id=pack.id,
            adaptive_reserve_minutes=reserve_mins,
            stages=stages,
            next_best_action=NextBestAction.TEACH,
            overall_progress=0,
            health_score=100,
            version=1,
            semantic_version=COMPILER_SEMANTIC_VERSION,
            created_at=datetime.now(timezone.utc)
        )

        return roadmap
