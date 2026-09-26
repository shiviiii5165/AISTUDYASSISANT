"""
Presentation Orchestrator
=========================
Coordinates the hardened end-to-end presentation lifecycle:
0. Cache Check -> 0 Build PresentationBrief (vNEXT) -> 
0.5 Topic Intelligence/Ontology Agent -> 1. Planner Agent (Blueprint-Guided) ->
2. Content Agent -> 3. Visual Agent (Stock Photo Pipeline) -> 4. Structural QA Agent ->
4.5 Reviewer / Critic Agent -> 5. Deterministic PPTX Render -> 6. Storage & Cache.

All steps are wrapped in per-step timeouts to prevent indefinite hangs.
Total pipeline execution is hard-capped at PIPELINE_TIMEOUT_SECONDS.
QA and Reviewer steps degrade gracefully — their failure never kills the pipeline.
"""
from app.core.logging import logger
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from .schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, SlideSelfCheck,
    VisualSpec, VisualKind, DiagramSpec, SlideSourceRef,
    QualityGateError, ContentOrigin, SemanticStatus,
)
from .cache import get_cached_presentation, save_cached_presentation
from .topic_ontology_agent import generate_topic_ontology, TopicOntologyChecklist
from .planner_agent import plan_presentation
from .content_agent import expand_presentation_content
from .visual_agent import resolve_slide_visuals
from .qa_agent import run_presentation_qa
from .reviewer_agent import run_reviewer_critic
from app.db.supabase_client import supabase

# vNEXT Phase 1 imports
from .brief_builder import build_presentation_brief
from .topic_ontology_agent import generate_topic_intelligence
from .planner_agent import plan_presentation_vnext
from .schemas import PipelineProvenance
from .domain_classifier import (
    classify_domain_with_model_fallback,
    MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD,
    CLASSIFICATION_BASIS_MODEL,
)

# --- Timeout Configuration (seconds) ---
PIPELINE_TIMEOUT_SECONDS = 300.0
STEP_TIMEOUTS = {
    "brief": 10.0,     # vNEXT: deterministic brief building
    "domain_refinement": 10.0,  # vNEXT: async model disambiguation for low-confidence
    "ontology": 35.0,
    "topic_intelligence": 50.0,  # vNEXT: expanded intelligence
    "planner": 50.0,
    "content": 90.0,
    "visual": 50.0,
    "qa": 40.0,
    "reviewer": 35.0,
}


async def _run_step(name: str, coro, timeout: float):
    """Execute a pipeline step with a hard timeout. Raises TimeoutError with step context."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"[Orchestrator] Step '{name}' timed out after {timeout}s — aborting step.")
        raise TimeoutError(f"Pipeline step '{name}' exceeded {timeout}s timeout")


async def _run_step_graceful(name: str, coro, timeout: float, fallback):
    """Execute a pipeline step with graceful degradation — returns fallback on any failure."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"[Orchestrator] Step '{name}' timed out after {timeout}s — using fallback (graceful).")
        return fallback
    except Exception as e:
        logger.warning(f"[Orchestrator] Step '{name}' failed ({e}) — using fallback (graceful).")
        return fallback


async def _generate_presentation_inner(
    config: PresentationConfig,
    user_id: str,
    on_stage_update: Optional[Callable[[str, int], None]] = None,
) -> tuple[PresentationSpec, bytes]:
    """
    Inner pipeline body — all step timeouts enforced here.
    Separated from outer function so the outer can apply a global timeout.
    """
    # Initialize provenance tracking
    provenance = PipelineProvenance(
        planning_engine="VNEXT",
        planning_fallback_used=False,
        planning_fallback_reason="",
        planner_version="vnext_phase1",
        story_grammar_version="1.0",
        blueprint_schema_version="1.0",
        topic_intelligence_version="1.0",
    )

    # 0. Check cache for repeated request
    cached_json = await get_cached_presentation(config)
    if cached_json:
        spec = PresentationSpec(**cached_json)
        # Quality Gate Check on cached spec: ensure cache cannot bypass quality gate
        has_cached_gap = any(
            (
                ((s.content is not None) and (getattr(s.content, "content_origin", None) in (ContentOrigin.CONTENT_SEMANTIC_GAP, "content_semantic_gap")))
                or ((s.content is not None) and (getattr(s.content, "semantic_status", None) in (SemanticStatus.GAP, "gap")))
                or (getattr(s, "fit_risk", None) == "CONTENT_SEMANTIC_GAP")
                or ((s.content is not None) and (getattr(s.content, "fit_risk", None) == "CONTENT_SEMANTIC_GAP"))
                or (isinstance(s.quality_scores, dict) and bool(s.quality_scores.get("hard_fail_reasons")))
                or (hasattr(s.quality_scores, "has_hard_fail") and bool(s.quality_scores.has_hard_fail))
            )
            for s in spec.slides
        )
        if not has_cached_gap:
            logger.info("[Orchestrator] Cache HIT — using valid cached presentation specification")
            from .engine.builder import build_presentation_spec
            pptx_bytes = build_presentation_spec(spec)
            return spec, pptx_bytes
        else:
            logger.warning("[Orchestrator] Cached presentation has unresolved semantic gap; bypassing cache")

    if on_stage_update:
        on_stage_update("brief", 5)

    # 0. vNEXT: BUILD PRESENTATION BRIEF (deterministic intelligence layer)
    logger.info(f"[Orchestrator] Step 0 (vNEXT): Building PresentationBrief for '{config.topic}'...")
    brief = None
    topic_intel = None
    try:
        brief = build_presentation_brief(config)
        logger.info(
            f"[Orchestrator] Brief built: domain={brief.domain}/{brief.subdomain}, "
            f"grammar={brief.primary_story_grammar.value}, "
            f"template={brief.selected_template}({brief.template_selection_source.value}), "
            f"theme={brief.selected_theme}({brief.theme_selection_source.value})"
        )

        # 0.1 vNEXT: Model disambiguation for low-confidence domain classification
        # Only invokes LLM when deterministic confidence is below threshold
        if brief.domain_confidence < MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD:
            logger.info(
                f"[Orchestrator] Low domain confidence ({brief.domain_confidence:.2f}), "
                f"attempting model disambiguation..."
            )
            custom_ctx = config.custom_instructions if hasattr(config, "custom_instructions") else ""
            refined = await _run_step_graceful(
                "domain_refinement",
                classify_domain_with_model_fallback(
                    topic=config.topic,
                    audience=config.audience,
                    custom_context=custom_ctx,
                ),
                STEP_TIMEOUTS["domain_refinement"],
                fallback=None,
            )
            if refined and refined.classification_basis == CLASSIFICATION_BASIS_MODEL:
                # Re-build brief with refined domain
                logger.info(
                    f"[Orchestrator] Model disambiguation refined: "
                    f"{brief.domain} → {refined.domain}/{refined.subdomain}"
                )
                brief = build_presentation_brief(config, domain_classification=refined)

    except Exception as e:
        logger.warning(f"[Orchestrator] Brief building failed ({e}), falling back to legacy path")
        provenance.planning_engine = "LEGACY_FALLBACK"
        provenance.planning_fallback_used = True
        provenance.planning_fallback_reason = "BRIEF_BUILD_FAILED"

    if on_stage_update:
        on_stage_update("ontology", 10)

    # 0.5 TOPIC INTELLIGENCE / ONTOLOGY AGENT
    ontology = None
    if brief:
        # vNEXT path: use expanded TopicIntelligencePack
        logger.info(f"[Orchestrator] Step 0.5 (vNEXT): Generating TopicIntelligencePack...")
        try:
            topic_intel = await _run_step(
                "topic_intelligence",
                generate_topic_intelligence(config, user_id=user_id),
                STEP_TIMEOUTS["topic_intelligence"],
            )
            ontology = topic_intel  # TopicIntelligencePack inherits TopicOntologyChecklist
        except Exception as e:
            logger.warning(f"[Orchestrator] Topic intelligence failed ({e}), falling back to legacy ontology")
            provenance.planning_engine = "LEGACY_FALLBACK"
            provenance.planning_fallback_used = True
            provenance.planning_fallback_reason = "TOPIC_INTELLIGENCE_FAILED"
            brief = None  # Fall back to legacy path

    if ontology is None:
        # Legacy path
        logger.info(f"[Orchestrator] Step 0.5: Establishing Topic Ontology for '{config.topic}'...")
        ontology = await _run_step(
            "ontology",
            generate_topic_ontology(config, user_id=user_id),
            STEP_TIMEOUTS["ontology"],
        )

    if on_stage_update:
        on_stage_update("planning", 25)

    # 1. PLANNER AGENT
    if brief and topic_intel:
        # vNEXT path: Blueprint-driven planning with story grammar
        logger.info(f"[Orchestrator] Step 1 (vNEXT): Blueprint planning {config.slide_count} slides...")
        try:
            outline_data = await _run_step(
                "planner",
                plan_presentation_vnext(brief, topic_intelligence=topic_intel, user_id=user_id),
                STEP_TIMEOUTS["planner"],
            )
        except Exception as e:
            logger.warning(f"[Orchestrator] vNEXT planner failed ({e}), falling back to legacy planner")
            provenance.planning_engine = "LEGACY_FALLBACK"
            provenance.planning_fallback_used = True
            provenance.planning_fallback_reason = "STORY_PLANNING_FAILED"
            outline_data = await _run_step(
                "planner",
                plan_presentation(config, user_id=user_id, ontology=ontology),
                STEP_TIMEOUTS["planner"],
            )
    else:
        # Legacy path
        logger.info(f"[Orchestrator] Step 1: Planning {config.slide_count} slides for '{config.topic}'...")
        if not provenance.planning_fallback_used:
            provenance.planning_engine = "LEGACY_FALLBACK"
            provenance.planning_fallback_used = True
            if not provenance.planning_fallback_reason:
                provenance.planning_fallback_reason = "BRIEF_BUILD_FAILED"
        outline_data = await _run_step(
            "planner",
            plan_presentation(config, user_id=user_id, ontology=ontology),
            STEP_TIMEOUTS["planner"],
        )

    # Attach provenance to outline_data for telemetry
    outline_data["pipeline_provenance"] = provenance.model_dump() if hasattr(provenance, "model_dump") else provenance.dict()
    logger.info(
        f"[Orchestrator] Provenance: engine={provenance.planning_engine}, "
        f"fallback={provenance.planning_fallback_used}, "
        f"reason={provenance.planning_fallback_reason}"
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

    # Phase 2 Content Provenance Telemetry
    if brief and outline_data.get("blueprints"):
        provenance.content_engine = "phase2"
        provenance.content_engine_version = "2.0"
        provenance.content_schema_version = "2.0"
        provenance.content_fallback_used = False
        provenance.content_repair_count = sum(
            1 for s in expanded_slides
            if isinstance(s.get("quality_scores"), dict) and s["quality_scores"].get("hard_fail_reasons")
        )
    else:
        provenance.content_engine = "legacy"
        provenance.content_fallback_used = True
        provenance.content_fallback_reason = "NO_BLUEPRINTS_AVAILABLE"

    outline_data["pipeline_provenance"] = provenance.model_dump() if hasattr(provenance, "model_dump") else provenance.dict()

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

    # 4. STRUCTURAL QA AGENT (Bounds, length, auto-heal) — GRACEFUL: failure uses slides as-is
    logger.info(f"[Orchestrator] Step 4: Running Python QA bounds & repair loop...")
    qa_slides = await _run_step_graceful(
        "qa",
        run_presentation_qa(config, slides_with_visuals),
        STEP_TIMEOUTS["qa"],
        fallback=slides_with_visuals,
    )

    if on_stage_update:
        on_stage_update("review", 90)

    # 4.5 REVIEWER / CRITIC AGENT (Pedagogical depth & variety check) — GRACEFUL
    logger.info(f"[Orchestrator] Step 4.5: Running Reviewer Critic & targeted polish...")
    final_slide_dicts = await _run_step_graceful(
        "reviewer",
        run_reviewer_critic(config, qa_slides, ontology=ontology),
        STEP_TIMEOUTS["reviewer"],
        fallback=qa_slides,
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

        # Parse self_check if present
        sc_data = s.get("self_check")
        self_check_obj = SlideSelfCheck(**sc_data) if sc_data and isinstance(sc_data, dict) else None

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
            section_label=s.get("section_label"),
            self_check=self_check_obj,
            visual=vspec,
            source_refs=source_refs,
            layers=s.get("layers", []),
            steps=s.get("steps", []),
            milestones=s.get("milestones", []),
            columns=s.get("columns", []),
            metrics=s.get("metrics", []),
            quiz_options=s.get("quiz_options", []),
            quiz_answer=s.get("quiz_answer", ""),
            content=s.get("content"),
            quality_scores=s.get("quality_scores"),
            fit_risk=s.get("fit_risk"),
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

    # 5.5 ENFORCE PRE-EXPORT QUALITY GATE
    # Must run before PPTX rendering, storage upload or caching.
    # Block output if any slide has:
    # - unresolved semantic gap;
    # - hard factual failure;
    # - unsupported required claim;
    # - unresolved critical quality failure.
    for slide_idx, slide in enumerate(spec.slides):
        has_semantic_gap = (
            (
                (slide.content is not None)
                and (getattr(slide.content, "content_origin", None) in (ContentOrigin.CONTENT_SEMANTIC_GAP, "content_semantic_gap"))
            )
            or (
                (slide.content is not None)
                and (getattr(slide.content, "semantic_status", None) in (SemanticStatus.GAP, "gap"))
            )
            or (getattr(slide, "fit_risk", None) == "CONTENT_SEMANTIC_GAP")
            or ((slide.content is not None) and (getattr(slide.content, "fit_risk", None) == "CONTENT_SEMANTIC_GAP"))
        )

        hard_fails = []
        if (slide.quality_scores is not None) and isinstance(slide.quality_scores, dict):
            hard_fails = slide.quality_scores.get("hard_fail_reasons", []) or []
        elif (slide.content is not None) and getattr(slide.content, "quality_scores", None):
            qs = getattr(slide.content, "quality_scores")
            if isinstance(qs, dict):
                hard_fails = qs.get("hard_fail_reasons", []) or []

        has_hard_factual_failure = (
            ("FACTUAL_INCONSISTENCY" in hard_fails)
            or ("UNSUPPORTED_CLAIM" in hard_fails)
        )
        has_critical_failure = (
            ("CONTENT_SEMANTIC_GAP" in hard_fails)
            or ("GENERIC_REPAIR_WRAPPER" in hard_fails)
        )

        if has_semantic_gap or has_hard_factual_failure or has_critical_failure:
            reasons = list(hard_fails)
            if has_semantic_gap and ("CONTENT_SEMANTIC_GAP" not in reasons):
                reasons.append("CONTENT_SEMANTIC_GAP")
            err_msg = (
                f"Export blocked by Quality Gate on slide {slide.slide_no or (slide_idx + 1)}: "
                f"unresolved failures {reasons}"
            )
            logger.error(f"[Orchestrator] {err_msg}")
            raise QualityGateError(err_msg)

    # 5.6 ENFORCE CONTENT COMPLETENESS GATE (Pre-export semantic & structural completeness)
    from .content_completeness_gate import audit_deck_content_completeness
    completeness_result = audit_deck_content_completeness(spec)
    if not completeness_result.passed:
        err_msg = f"Export blocked by Content Completeness Gate: {'; '.join(completeness_result.errors)}"
        logger.error(f"[Orchestrator] {err_msg}")
        raise QualityGateError(err_msg)

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
    Hard-capped at PIPELINE_TIMEOUT_SECONDS (240s) to prevent indefinite hangs.
    QA and Reviewer steps degrade gracefully to avoid pipeline-killing timeouts.
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
    except QualityGateError:
        logger.error("[Orchestrator] QualityGateError raised — export strictly blocked, re-raising.")
        raise
    except asyncio.TimeoutError:
        elapsed = time.time() - pipeline_start
        logger.error(f"[Orchestrator] PIPELINE HARD TIMEOUT after {elapsed:.1f}s (limit {PIPELINE_TIMEOUT_SECONDS}s)")
        raise TimeoutError(
            f"Presentation pipeline exceeded hard timeout of {PIPELINE_TIMEOUT_SECONDS}s. "
            f"This is usually caused by slow or unresponsive upstream API providers."
        )


