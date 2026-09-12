"""
Storyboard Planning & Pedagogical Curriculum Compiler
=====================================================
1. Converts Teach Me LessonPlan/LearningState into a synchronized Storyboard (0 redundant LLM calls).
2. Uses DynamicCurriculumEngine to construct a domain-agnostic Concept Graph for any topic.
3. Compiles a duration-normalized Storyboard via StoryboardCompiler.
4. Grounded in user sources (PDF / Notes / Docs) whenever provided.
"""
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from .schemas import (
    VideoConfig, Storyboard, SceneSpec, VisualSpec,
    VisualAssetType, VideoStyle, VideoQuality, LearningIntent
)
from .pedagogy.intent_parser import LearningIntentParser
from .pedagogy.dynamic_curriculum import DynamicCurriculumEngine
from .pedagogy.story_compiler import StoryboardCompiler
from ..teach.tools import get_lesson_plan, get_learning_state
from ..knowledge.hybrid_search import hybrid_search_evidence
from ..knowledge.sources import EvidenceItem


def build_storyboard_from_teach_me_state(
    session_id: str,
    config: VideoConfig,
) -> Storyboard:
    """
    Directly converts active Teach Me lesson concepts and explanations
    into a Video Storyboard with ZERO redundant LLM calls.
    """
    plan = get_lesson_plan(session_id)
    if not plan:
        raise ValueError(f"Lesson plan for session {session_id} not found.")

    concepts = plan.concepts or []
    target_duration = config.duration
    total_scene_count = len(concepts) + 1
    base_duration = target_duration // total_scene_count
    remainder = target_duration % total_scene_count

    scenes: List[SceneSpec] = []
    
    # 1. Hook / Intro scene
    scenes.append(SceneSpec(
        scene_id="scene_01",
        order=1,
        concept_id="intro",
        purpose="hook",
        duration=base_duration + remainder,
        narration=f"Welcome to this focused masterclass on {plan.topic}. Today we will break down the core mechanisms step by step.",
        visual_type=VisualAssetType.PYTHON_GRAPHICS,
        visual_spec=VisualSpec(title=plan.topic, bullets=[c.name for c in concepts[:4]], theme="blue_professional"),
        caption=f"Overview: {plan.topic}",
    ))

    # 2. Concept scenes
    for idx, c in enumerate(concepts):
        s_dur = base_duration
        scenes.append(SceneSpec(
            scene_id=f"scene_{idx+2:02d}",
            order=idx + 2,
            concept_id=c.id,
            concept_name=c.name,
            purpose="mechanism",
            duration=s_dur,
            narration=c.summary or f"Now let's examine {c.name}, which forms a key pillar of {plan.topic}.",
            visual_type=VisualAssetType.PYTHON_GRAPHICS,
            visual_spec=VisualSpec(
                diagram_type="flow" if "flow" in c.name.lower() or "process" in c.name.lower() else "cards",
                title=c.name,
                bullets=[f"Understanding {c.name}", "Operational principle", "Practical engineering application"],
                nodes=[c.name, "Processing", "Output Result"] if "flow" in c.name.lower() else [],
                theme="blue_professional",
            ),
            caption=c.name,
        ))

    return Storyboard(
        topic=plan.topic,
        style=config.style,
        language=config.language,
        total_duration=target_duration,
        scenes=scenes,
        learning_objectives=[f"Master {c.name}" for c in concepts],
        summary_notes=f"Complete educational breakdown of {plan.topic}.",
    )


async def plan_storyboard(
    config: VideoConfig,
    user_id: str,
) -> Storyboard:
    """
    Plans a complete educational video storyboard with duration normalization
    using the Universal Curriculum and Storyboard Compiler architecture.
    """
    # If Teach Me session ID is provided, reuse existing lesson state directly
    if config.lesson_session_id:
        try:
            return build_storyboard_from_teach_me_state(config.lesson_session_id, config)
        except Exception as e:
            logger.info(f"[StoryboardPlanner] Teach Me reuse fallback: {e}")

    # 1. Targeted RAG retrieval if source files exist
    evidence_items: List[EvidenceItem] = []
    if config.source_ids:
        try:
            evidence_items = await hybrid_search_evidence(
                user_id=user_id,
                query=f"{config.topic} overview mechanisms principles architecture",
                document_ids=config.source_ids,
                top_k=4,
            )
        except Exception as rag_err:
            logger.warning(f"[StoryboardPlanner] RAG retrieval notice: {rag_err}")

    # 2. Build Intent
    intent = LearningIntent(
        raw_prompt=config.topic,
        topic=config.topic,
        domain=config.domain,
        learner_level=config.audience,
        language=config.language,
        duration_seconds=config.duration,
        explanation_depth=config.depth,
        source_type=config.source_type,
        source_ids=config.source_ids,
        custom_context=config.custom_context
    )

    # 3. Build Concept Graph dynamically
    graph = await DynamicCurriculumEngine.build_concept_graph(intent, user_id=user_id)

    # 4. Compile Storyboard
    storyboard = StoryboardCompiler.compile(intent, graph)

    # 5. Attach RAG source citations where applicable
    if evidence_items and storyboard.scenes:
        for s in storyboard.scenes:
            s.source_refs = evidence_items[:2]

    return storyboard
