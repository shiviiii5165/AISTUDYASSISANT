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

from ..schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageReadiness,
    NextBestAction, ClassType, RoadmapStatus, ProductMode,
    CanonicalDomain, TeachingIntent, TopicVolatility, BloomLevel,
    PrerequisiteMasteryState
)
from .classifiers import IntentClassifier, DomainClassifier, TopicVolatilityClassifier
from .knowledge_pack import KnowledgePackService
from .curriculum import CurriculumResolver
from .pedagogy import PedagogyPolicyEngine, ConceptType
from .time_budget import DynamicTimeBudgetEngine
from .canonical_concepts import CanonicalConceptResolver
from .shared_context import LearnerStateRepository

logger = logging.getLogger("teachgenie.lesson_planner.compiler")


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
        for i, (template, dur) in enumerate(zip(stage_templates, durations)):
            stage_id = f"stage_{i+1}_{uuid.uuid4().hex[:6]}"
            
            # Resolve stable canonical concept ID (never ephemeral ad-hoc IDs)
            canonical_concept = CanonicalConceptResolver.resolve_or_create(
                concept_name=f"{topic} {template.archetype.value.replace('_', ' ')}",
                domain=domain
            )
            canonical_id = canonical_concept.canonical_id
            
            # Prerequisite chaining
            prereqs = [stages[i-1].concept_id] if i > 0 else []

            # Check learner state if student_id is provided
            mastery_state = PrerequisiteMasteryState.UNKNOWN
            if student_id:
                state_entry = LearnerStateRepository.get_state(student_id, canonical_id)
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
                concept_id=canonical_id,
                canonical_concept_id=canonical_id,
                title=f"{template.archetype.value.replace('_', ' ').title()}: {topic}",
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
                objectives=curriculum_res.objectives[:2] if i == 0 else curriculum_res.objectives[2:4] or curriculum_res.objectives[:1],
                objective_ids=[o.id for o in curriculum_res.objectives[:2]],
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
            created_at=datetime.now(timezone.utc)
        )

        return roadmap
