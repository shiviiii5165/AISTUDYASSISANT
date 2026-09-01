"""
Presentation Orchestrator
=========================
Coordinates the end-to-end presentation lifecycle:
1. Cache Check -> 2. Planner Agent -> 3. Content Agent -> 4. Visual Agent ->
5. QA Agent & Slide Patch -> 6. Deterministic PPTX Render -> 7. Storage & Signed URL.
"""
import asyncio
from typing import Dict, Any, Optional, Callable
from .schemas import PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind, DiagramSpec, SlideSourceRef
from .cache import get_cached_presentation, save_cached_presentation
from .planner_agent import plan_presentation
from .content_agent import expand_presentation_content
from .visual_agent import resolve_slide_visuals
from .qa_agent import run_presentation_qa
from app.db.supabase_client import supabase


async def generate_presentation_pipeline(
    config: PresentationConfig,
    user_id: str,
    on_stage_update: Optional[Callable[[str, int], None]] = None,
) -> tuple[PresentationSpec, bytes]:
    """
    Executes the modular AI presentation generation pipeline.
    Returns (PresentationSpec, pptx_bytes).
    """
    # 0. Check cache for repeated request
    cached_json = await get_cached_presentation(config)
    if cached_json:
        print("[Orchestrator] Cache HIT — using cached presentation specification")
        spec = PresentationSpec(**cached_json)
        # Render PPTX bytes directly
        from .engine.builder import build_presentation_spec
        pptx_bytes = build_presentation_spec(spec)
        return spec, pptx_bytes

    if on_stage_update:
        on_stage_update("planning", 15)

    # 1. PLANNER AGENT
    print(f"[Orchestrator] Step 1: Planning {config.slide_count} slides for '{config.topic}'...")
    outline_data = await plan_presentation(config, user_id=user_id)

    if on_stage_update:
        on_stage_update("content", 45)

    # 2. CONTENT AGENT (Batched in 5s)
    print(f"[Orchestrator] Step 2: Expanding content across 5-slide batches...")
    expanded_slides = await expand_presentation_content(config, user_id=user_id, outline_data=outline_data)

    if on_stage_update:
        on_stage_update("visuals", 70)

    # 3. VISUAL AGENT (Diagrams & Selective AI Images)
    print(f"[Orchestrator] Step 3: Resolving visuals and diagrams...")
    slides_with_visuals = await resolve_slide_visuals(config, expanded_slides)

    if on_stage_update:
        on_stage_update("qa", 85)

    # 4. QA AGENT & TARGETED REPAIR
    print(f"[Orchestrator] Step 4: Running Python QA bounds & repair loop...")
    final_slide_dicts = await run_presentation_qa(config, slides_with_visuals)

    # 5. Build strict PresentationSpec
    structured_slides: list[SlideSpec] = []
    for s in final_slide_dicts:
        # Build VisualSpec
        vspec_data = s.get("visual_spec") or {}
        diagram_spec_data = vspec_data.get("diagram_spec")
        
        # Coerce string -> VisualKind enum safely
        raw_kind = vspec_data.get("kind", "none")
        try:
            kind_enum = VisualKind(raw_kind) if isinstance(raw_kind, str) else raw_kind
        except ValueError:
            kind_enum = VisualKind.NONE

        vspec = VisualSpec(
            kind=kind_enum,
            asset_required=vspec_data.get("asset_required", False),
            image_prompt=vspec_data.get("image_prompt", ""),
            image_bytes=vspec_data.get("image_bytes"),
            diagram_spec=DiagramSpec(**diagram_spec_data) if diagram_spec_data else None,
        )

        # Build SourceRefs
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
    )

    # Enforce exact slide count contract (explicit raise, never use assert in production)
    if len(spec.slides) != config.slide_count:
        raise ValueError(f"Slide count mismatch: got {len(spec.slides)}, expected {config.slide_count}")

    if on_stage_update:
        on_stage_update("rendering", 95)

    # 6. RENDER PPTX VIA DETERMINISTIC PYTHON BUILDER
    from .engine.builder import build_presentation_spec
    pptx_bytes = build_presentation_spec(spec)

    # 7. Cache PresentationSpec for future requests
    # Prepare serializable dict without raw bytes (Pydantic v2 compatible)
    try:
        serializable_dict = spec.model_dump()
    except AttributeError:
        serializable_dict = spec.dict()  # Pydantic v1 fallback
    for s in serializable_dict.get("slides", []):
        if s.get("visual"):
            s["visual"]["image_bytes"] = None
    await save_cached_presentation(config, serializable_dict)

    if on_stage_update:
        on_stage_update("completed", 100)

    return spec, pptx_bytes
