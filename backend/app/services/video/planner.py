"""
Storyboard Planning & Teach Me Storyboard Converter
===================================================
1. Converts Teach Me LessonPlan/LearningState into a synchronized Storyboard (0 redundant LLM calls).
2. Generates grounded multi-source storyboards for Topic/PDF/PPT/Notes/YouTube requests.
3. Enforces deterministic duration calculations in pure Python.
"""
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import (
    VideoConfig, Storyboard, SceneSpec, VisualSpec,
    VisualAssetType, VideoStyle, VideoQuality
)
from ..teach.tools import get_lesson_plan, get_learning_state
from ..knowledge.hybrid_search import hybrid_search_evidence
from ..knowledge.sources import EvidenceItem, SourceType


STORYBOARD_PROMPT = """You are a master educational documentary director and instructional storyboard architect.
Given a topic, target duration, audience level, and source evidence, design a concise, scene-by-scene storyboard.

STORYBOARD RULES:
1. Calculate scene counts so total duration matches the requested duration ({target_duration} seconds).
2. For each scene, specify:
   - "purpose": "hook" | "definition" | "mechanism" | "diagram" | "example" | "summary"
   - "duration": Duration in seconds (usually 15-30s per scene)
   - "narration": 2-4 sentences of natural, engaging teacher script.
   - "caption": 1-line on-screen title
   - "diagram_type": "flow" | "cards" | "architecture" | "comparison" | null
   - "stock_keywords": ["keyword1", "keyword2"]
3. If grounded evidence citations are given, reference them.

Return strict JSON:
{{
  "topic": "{topic}",
  "learning_objectives": ["Objective 1", "Objective 2"],
  "summary_notes": "A 2-paragraph educational synthesis.",
  "scenes": [
    {{
      "scene_id": "scene_1",
      "purpose": "hook",
      "duration": 20,
      "narration": "Have you ever wondered how...",
      "caption": "Introduction",
      "diagram_type": null,
      "stock_keywords": ["network", "technology"]
    }}
  ]
}}
"""


def build_storyboard_from_teach_me_state(
    session_id: str,
    config: VideoConfig,
) -> Storyboard:
    """
    Directly converts active Teach Me lesson concepts and explanations
    into a Video Storyboard with ZERO redundant LLM calls.
    """
    plan = get_lesson_plan(session_id)
    state = get_learning_state(session_id)
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
    Plans a complete educational video storyboard with duration normalization.
    """
    # If Teach Me session ID is provided, reuse existing lesson state directly
    if config.lesson_session_id:
        try:
            return build_storyboard_from_teach_me_state(config.lesson_session_id, config)
        except Exception as e:
            print(f"[StoryboardPlanner] Teach Me reuse fallback: {e}")

    # 1. Targeted RAG retrieval if source files exist
    evidence_items: List[EvidenceItem] = []
    if config.source_ids:
        evidence_items = await hybrid_search_evidence(
            user_id=user_id,
            query=f"{config.topic} overview mechanisms principles architecture",
            document_ids=config.source_ids,
            top_k=4,
        )

    evidence_text = "\n\n".join([f"[{e.get_citation_badge()}]: {e.text[:250]}" for e in evidence_items])

    # 2. Call Planner LLM
    prompt_str = STORYBOARD_PROMPT.format(
        topic=config.topic,
        target_duration=config.duration,
    )
    if evidence_text:
        prompt_str += f"\n\nSource Reference Grounding:\n{evidence_text}"
        
    if config.custom_context:
        prompt_str += (
            "\n\nIMPORTANT INSTRUCTION: Use the following source material to generate the storyboard. "
            "DO NOT fabricate facts beyond this provided context:\n\n"
            f"{config.custom_context}"
        )

    messages = [
        {"role": "system", "content": prompt_str},
        {"role": "user", "content": f"Create a {config.duration}-second storyboard for {config.topic} at {config.audience} level in {config.language}."}
    ]

    try:
        raw_plan = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.3,
            max_tokens=3000,
        )
    except Exception as e:
        print(f"[StoryboardPlanner] LLM provider notice ({e}). Using deterministic storyboard fallback.")
        raw_plan = {
            "topic": config.topic,
            "scenes": [
                {"scene_id": "scene_1", "purpose": "hook", "duration": config.duration // 3, "narration": f"Introduction and fundamentals of {config.topic}.", "caption": f"Overview: {config.topic}"},
                {"scene_id": "scene_2", "purpose": "mechanism", "duration": config.duration // 3, "narration": f"Core operational mechanics and architecture of {config.topic}.", "caption": f"Mechanisms of {config.topic}"},
                {"scene_id": "scene_3", "purpose": "summary", "duration": config.duration - (2 * (config.duration // 3)), "narration": f"Summary and practical real-world takeaways for {config.topic}.", "caption": "Summary"},
            ],
            "learning_objectives": [f"Understand {config.topic}", "Master operational principles"],
            "summary_notes": f"Comprehensive educational breakdown of {config.topic}."
        }

    raw_scenes = raw_plan.get("scenes", [])
    if not raw_scenes:
        # Fallback default scenes
        raw_scenes = [
            {"scene_id": "scene_1", "purpose": "hook", "duration": config.duration // 3, "narration": f"Introduction to {config.topic}.", "caption": "Overview"},
            {"scene_id": "scene_2", "purpose": "mechanism", "duration": config.duration // 3, "narration": f"Key mechanisms of {config.topic}.", "caption": "Mechanisms"},
            {"scene_id": "scene_3", "purpose": "summary", "duration": config.duration - (2 * (config.duration // 3)), "narration": f"Summary of {config.topic}.", "caption": "Summary"},
        ]

    # 3. Construct SceneSpec models & enforce exact duration math in Python
    scenes: List[SceneSpec] = []
    current_sum = 0
    for idx, s in enumerate(raw_scenes):
        dur = int(s.get("duration", config.duration // len(raw_scenes)))
        current_sum += dur
        
        diag_type = s.get("diagram_type")
        spec = VisualSpec(
            diagram_type=diag_type,
            title=s.get("caption", f"Scene {idx+1}"),
            bullets=[s.get("caption", "")] if not diag_type else [],
            stock_keywords=s.get("stock_keywords", []),
        )

        scenes.append(SceneSpec(
            scene_id=s.get("scene_id", f"scene_{idx+1}"),
            order=idx + 1,
            concept_id=s.get("concept_id", f"concept_{idx+1}"),
            purpose=s.get("purpose", "mechanism"),
            duration=dur,
            narration=s.get("narration", ""),
            visual_type=VisualAssetType.PYTHON_GRAPHICS if diag_type else VisualAssetType.STOCK_VIDEO,
            visual_spec=spec,
            caption=s.get("caption", ""),
            source_refs=evidence_items[:2] if evidence_items else [],
        ))

    # Duration normalization
    diff = config.duration - current_sum
    if diff != 0 and scenes:
        scenes[-1].duration = max(5, scenes[-1].duration + diff)

    return Storyboard(
        topic=raw_plan.get("topic", config.topic),
        style=config.style,
        language=config.language,
        total_duration=config.duration,
        scenes=scenes,
        learning_objectives=raw_plan.get("learning_objectives", []),
        summary_notes=raw_plan.get("summary_notes", ""),
    )
