"""
Presentation Orchestrator
=========================
Coordinates the hardened end-to-end presentation lifecycle:
0. Cache Check -> 0.5 Topic Ontology Agent -> 1. Planner Agent (Ontology-Guided) ->
2. Content Agent -> 3. Visual Agent (Stock Photo Pipeline) -> 4. Structural QA Agent ->
4.5 Reviewer / Critic Agent -> 5. Deterministic PPTX Render -> 6. Storage & Cache.

All steps are wrapped in per-step timeouts to prevent indefinite hangs.
Total pipeline execution is hard-capped at PIPELINE_TIMEOUT_SECONDS.
"""
from app.core.logging import logger
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from .schemas import PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind, DiagramSpec, SlideSourceRef
from .cache import get_cached_presentation, save_cached_presentation
from .topic_ontology_agent import generate_topic_ontology, TopicOntologyChecklist
from .planner_agent import plan_presentation
from .content_agent import expand_presentation_content
from .visual_agent import resolve_slide_visuals
from .qa_agent import run_presentation_qa
from .reviewer_agent import run_reviewer_critic
from app.db.supabase_client import supabase

# --- Timeout Configuration (seconds) ---
PIPELINE_TIMEOUT_SECONDS = 120.0
STEP_TIMEOUTS = {
    "ontology": 30.0,
    "planner": 45.0,
    "content": 45.0,
    "visual": 45.0,
    "qa": 30.0,
    "reviewer": 30.0,
}


async def _run_step(name: str, coro, timeout: float):
    """Execute a pipeline step with a hard timeout. Raises TimeoutError with step context."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"[Orchestrator] Step '{name}' timed out after {timeout}s — aborting step.")
        raise TimeoutError(f"Pipeline step '{name}' exceeded {timeout}s timeout")


async def _generate_presentation_inner(
    config: PresentationConfig,
    user_id: str,
    on_stage_update: Optional[Callable[[str, int], None]] = None,
) -> tuple[PresentationSpec, bytes]:
    """
    Inner pipeline body — all step timeouts enforced here.
    Separated from outer function so the outer can apply a global timeout.
    """
    # 0. Check cache for repeated request
    cached_json = await get_cached_presentation(config)
    if cached_json:
        logger.info("[Orchestrator] Cache HIT — using cached presentation specification")
        spec = PresentationSpec(**cached_json)
        from .engine.builder import build_presentation_spec
        pptx_bytes = build_presentation_spec(spec)
        return spec, pptx_bytes

    if on_stage_update:
        on_stage_update("ontology", 10)

    # 0.5 TOPIC ONTOLOGY AGENT (Checklist for complete coverage)
    logger.info(f"[Orchestrator] Step 0.5: Establishing Topic Ontology for '{config.topic}'...")
    ontology = await _run_step(
        "ontology",
        generate_topic_ontology(config, user_id=user_id),
        STEP_TIMEOUTS["ontology"],
    )

    if on_stage_update:
        on_stage_update("planning", 25)

    # 1. PLANNER AGENT (Ontology-Guided Mapping & Slide Count Flex)
    logger.info(f"[Orchestrator] Step 1: Planning {config.slide_count} slides for '{config.topic}'...")
    outline_data = await _run_step(
        "planner",
        plan_presentation(config, user_id=user_id, ontology=ontology),
        STEP_TIMEOUTS["planner"],
    )

    if on_stage_update:
        on_stage_update("content", 50)

    # 2. CONTENT AGENT (Single Batched Request with image_query generation)
    logger.info(f"[Orchestrator] Step 2: Expanding content with concrete image queries...")
    expanded_slides = await _run_step(
        "content",
        expand_presentation_content(config, user_id=user_id, outline_data=outline_data),
        STEP_TIMEOUTS["content"],
    )

    if on_stage_update:
        on_stage_update("visuals", 70)

    # 3. VISUAL AGENT (Stock Photo Router & Deterministic Diagrams)
    logger.info(f"[Orchestrator] Step 3: Resolving stock photos and diagrams...")
    slides_with_visuals = await _run_step(
        "visual",
        resolve_slide_visuals(config, expanded_slides),
        STEP_TIMEOUTS["visual"],
    )

    if on_stage_update:
        on_stage_update("qa", 80)

    # 4. STRUCTURAL QA AGENT (Bounds, length, auto-heal)
    logger.info(f"[Orchestrator] Step 4: Running Python QA bounds & repair loop...")
    qa_slides = await _run_step(
        "qa",
        run_presentation_qa(config, slides_with_visuals),
        STEP_TIMEOUTS["qa"],
    )

    if on_stage_update:
        on_stage_update("review", 90)

    # 4.5 REVIEWER / CRITIC AGENT (Pedagogical depth & variety check)
    logger.info(f"[Orchestrator] Step 4.5: Running Reviewer Critic & targeted polish...")
    final_slide_dicts = await _run_step(
        "reviewer",
        run_reviewer_critic(config, qa_slides, ontology=ontology),
        STEP_TIMEOUTS["reviewer"],
    )

    # 5. Build strict PresentationSpec
    structured_slides: list[SlideSpec] = []
    for s in final_slide_dicts:
        vspec_data = s.get("visual_spec") or {}
        diagram_spec_data = vspec_data.get("diagram_spec")
        
        raw_kind = vspec_data.get("kind", "none")
        try:
            kind_enum = VisualKind(raw_kind) if isinstance(raw_kind, str) else raw_kind
        except ValueError:
            kind_enum = VisualKind.NONE

        img_bytes = vspec_data.get("image_bytes") or s.get("image_bytes")

        vspec = VisualSpec(
            kind=kind_enum,
            asset_required=vspec_data.get("asset_required", False),
            image_prompt=vspec_data.get("image_prompt", s.get("image_query", "")),
            image_bytes=img_bytes,
            diagram_spec=DiagramSpec(**diagram_spec_data) if diagram_spec_data else None,
        )

        source_refs = [SlideSourceRef(**r) for r in s.get("source_refs", [])]

        slide_obj = SlideSpec(
            slide_no=s.get("slide_no", 1),
            type=s.get("type", "concept"),
            title=s.get("title", ""),
            subtitle=s.get("subtitle", ""),
            key_message=s.get("key_message", ""),
            body_bullets=s.get("body_bullets", []),
            example=s.get("example", ""),
            speaker_notes=s.get("speaker_notes", ""),
            image_query=s.get("image_query", ""),
            content_pattern=s.get("content_pattern"),
            visual=vspec,
            source_refs=source_refs,
            layers=s.get("layers", []),
            steps=s.get("steps", []),
            milestones=s.get("milestones", []),
            columns=s.get("columns", []),
            metrics=s.get("metrics", []),
            quiz_options=s.get("quiz_options", []),
            quiz_answer=s.get("quiz_answer", ""),
        )
        structured_slides.append(slide_obj)

    spec = PresentationSpec(
        title=outline_data.get("deck_title", config.topic),
        subtitle=outline_data.get("subtitle", ""),
        config=config,
        key_takeaways=outline_data.get("key_takeaways", []),
        slides=structured_slides,
        expansion_reason=outline_data.get("expansion_reason", ""),
    )

    if on_stage_update:
        on_stage_update("rendering", 95)

    # 6. RENDER PPTX VIA DETERMINISTIC PYTHON BUILDER
    from .engine.builder import build_presentation_spec
    pptx_bytes = build_presentation_spec(spec)

    # 7. Cache PresentationSpec for future requests
    try:
        serializable_dict = spec.model_dump()
    except AttributeError:
        serializable_dict = spec.dict()
    for s in serializable_dict.get("slides", []):
        if s.get("visual"):
            s["visual"]["image_bytes"] = None
    await save_cached_presentation(config, serializable_dict)

    if on_stage_update:
        on_stage_update("completed", 100)

    return spec, pptx_bytes


async def generate_presentation_pipeline(
    config: PresentationConfig,
    user_id: str,
    on_stage_update: Optional[Callable[[str, int], None]] = None,
) -> tuple[PresentationSpec, bytes]:
    """
    Executes the modular AI presentation generation pipeline.
    Returns (PresentationSpec, pptx_bytes).
    Hard-capped at PIPELINE_TIMEOUT_SECONDS (120s) to prevent indefinite hangs.
    """
    pipeline_start = time.time()
    try:
        result = await asyncio.wait_for(
            _generate_presentation_inner(config, user_id, on_stage_update),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        elapsed = time.time() - pipeline_start
        logger.info(f"[Orchestrator] Pipeline completed in {elapsed:.2f}s")
        return result
    except asyncio.TimeoutError:
        elapsed = time.time() - pipeline_start
        logger.error(f"[Orchestrator] PIPELINE HARD TIMEOUT after {elapsed:.1f}s (limit {PIPELINE_TIMEOUT_SECONDS}s)")
        raise TimeoutError(
            f"Presentation pipeline exceeded hard timeout of {PIPELINE_TIMEOUT_SECONDS}s. "
            f"This is usually caused by slow or unresponsive upstream API providers."
        )

