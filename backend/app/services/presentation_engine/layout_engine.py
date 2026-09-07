"""
TeachGenie — Layout Engine
===========================
Maps SlidePurpose & ContentPattern → renderer function.
Handles fallback layouts when content doesn't fit a specialized renderer.
Default fallback is strictly plain_concept (clean bullets), never a shape-based pattern.
"""
from app.core.logging import logger
from pptx.slide import Slide
from . import SlideContent, SlidePurpose, ThemeColors
from .tokens import get_theme

from .renderers.cover import render_cover
from .renderers.concept import render_concept
from .renderers.two_column import render_two_column
from .renderers.image_insight import render_image_insight
from .renderers.architecture import render_architecture
from .renderers.process_flow import render_process_flow
from .renderers.timeline import render_timeline
from .renderers.comparison import render_comparison
from .renderers.kpi_metrics import render_kpi_metrics
from .renderers.case_study import render_case_study
from .renderers.quote_insight import render_quote_insight
from .renderers.summary import render_summary
from .renderers.closing import render_closing

# New Pedagogical Component Renderers
from .renderers.definition_box import render_definition_box
from .renderers.contrast_pair import render_contrast_pair
from .renderers.comparison_table import render_comparison_table
from .renderers.numbered_process import render_numbered_process
from .renderers.case_study_block import render_case_study_block
from .renderers.activity_banner import render_activity_banner
from .renderers.worked_example_table import render_worked_example_table
from .renderers.icon_badge_row import render_icon_badge_row
from .renderers.hub_and_spoke import render_hub_and_spoke
from .renderers.illustrated_icon_grid import render_illustrated_icon_grid


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT PATTERN MAP (Direct Lookup Table)
# ═══════════════════════════════════════════════════════════════════════════

CONTENT_PATTERN_MAP = {
    "definition_box":        render_definition_box,
    "contrast_pair":         render_contrast_pair,
    "comparison_table":      render_comparison_table,
    "numbered_process":      render_numbered_process,
    "case_study_block":      render_case_study_block,
    "activity_banner":       render_activity_banner,
    "worked_example_table":  render_worked_example_table,
    "icon_badge_row":        render_icon_badge_row,
    "hub_and_spoke":         render_hub_and_spoke,
    "illustrated_icon_grid": render_illustrated_icon_grid,
    "parallel_comparison":   render_comparison,
    "plain_concept":         render_concept,
}


# ═══════════════════════════════════════════════════════════════════════════
# PURPOSE RENDERER MAP
# ═══════════════════════════════════════════════════════════════════════════

RENDERER_MAP = {
    SlidePurpose.COVER:          render_cover,
    SlidePurpose.SECTION:        render_cover,
    SlidePurpose.CONCEPT:        render_concept,
    SlidePurpose.TWO_COLUMN:     render_two_column,
    SlidePurpose.IMAGE_INSIGHT:  render_image_insight,
    SlidePurpose.ARCHITECTURE:   render_architecture,
    SlidePurpose.PROCESS_FLOW:   render_process_flow,
    SlidePurpose.TIMELINE:       render_timeline,
    SlidePurpose.COMPARISON:     render_comparison,
    SlidePurpose.KPI_METRICS:    render_kpi_metrics,
    SlidePurpose.CASE_STUDY:     render_case_study,
    SlidePurpose.QUOTE_INSIGHT:  render_quote_insight,
    SlidePurpose.SUMMARY:        render_summary,
    SlidePurpose.CLOSING:        render_closing,
}

# Fallback chain: if a specialized layout can't work, use these
FALLBACK_CHAIN = {
    SlidePurpose.ARCHITECTURE:  SlidePurpose.CONCEPT,
    SlidePurpose.PROCESS_FLOW:  SlidePurpose.CONCEPT,
    SlidePurpose.TIMELINE:      SlidePurpose.CONCEPT,
    SlidePurpose.COMPARISON:    SlidePurpose.TWO_COLUMN,
    SlidePurpose.KPI_METRICS:   SlidePurpose.CONCEPT,
    SlidePurpose.CASE_STUDY:    SlidePurpose.TWO_COLUMN,
    SlidePurpose.IMAGE_INSIGHT: SlidePurpose.CONCEPT,
}


def render_slide(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kwargs,
) -> None:
    """
    Render a single slide by checking ContentPattern first, then mapping SlidePurpose.
    Falls back cleanly to plain concept bullets if specialized rendering fails.
    """
    pattern_key = str(content.content_pattern).lower() if content.content_pattern else ""
    if pattern_key in CONTENT_PATTERN_MAP:
        try:
            CONTENT_PATTERN_MAP[pattern_key](slide, content, theme, **kwargs)
            return
        except Exception as e:
            logger.error(f"[WARN] ContentPattern renderer '{pattern_key}' failed: {e}")

    purpose = content.purpose
    renderer = RENDERER_MAP.get(purpose, render_concept)

    try:
        renderer(slide, content, theme, **kwargs)
    except Exception as e:
        logger.error(f"[WARN] Renderer for {purpose.value} failed: {e}")
        # Try fallback
        fallback_purpose = FALLBACK_CHAIN.get(purpose)
        if fallback_purpose:
            fallback_renderer = RENDERER_MAP.get(fallback_purpose, render_concept)
            try:
                fallback_renderer(slide, content, theme, **kwargs)
                logger.info(f"  [OK] Fallback to {fallback_purpose.value} succeeded")
                return
            except Exception as e2:
                logger.error(f"  [WARN] Fallback also failed: {e2}")

        # Ultimate fallback: plain concept slide (clean bullets, no shapes)
        try:
            render_concept(slide, content, theme, **kwargs)
        except Exception:
            pass


def detect_content_pattern_fallback(content: SlideContent) -> str:
    """
    Intelligent deterministic fallback ladder matching slide content signals
    when content_pattern is omitted. The fallback default is strictly 'plain_concept'.
    """
    title_l = (content.title or "").lower()
    bullets_l = " ".join(content.body_bullets or []).lower()
    comb = f"{title_l} {bullets_l}"

    # 1. Definition signals
    if any(w in title_l for w in ["definition", "what is", "glossary", "terminology", "concept:"]):
        return "definition_box"

    # 2. Contrast signals (The Trap vs The Discipline, Common Misconceptions, Anti-patterns)
    if any(w in comb for w in ["trap", "misconception", "pitfall", "anti-pattern", "vs.", "versus", "do's and don'ts"]):
        return "contrast_pair"

    # 3. Process / sequential flow
    if content.steps or any(w in title_l for w in ["step", "lifecycle", "workflow", "pipeline", "phase", "algorithm:"]):
        return "numbered_process"

    # 4. Case Study
    if any(w in title_l for w in ["case study", "real-world", "incident", "failure analysis"]):
        return "case_study_block"

    # 5. Activity / Classroom exercise
    if any(w in title_l for w in ["activity", "exercise", "try this", "discussion prompt", "lab task"]):
        return "activity_banner"

    # 6. Comparison Table (explicit matrix or structured table)
    if content.columns and len(content.columns) >= 2:
        return "comparison_table"

    # 7. Structural CS data concepts (strictly gated to stack, queue, tree, graph, database)
    cs_terms = ["stack", "lifo", "queue", "fifo", "binary tree", "graph topology", "database cylinder"]
    if any(t in comb for t in cs_terms) and any(w in title_l for w in ["structure", "model", "collection", "topology"]):
        return "illustrated_icon_grid"

    # 8. Worked example
    if any(w in title_l for w in ["worked example", "step-by-step trace", "walkthrough", "trace table"]):
        return "worked_example_table"

    # Default fallback: plain text bullets (never a shape or circle-pill)
    return "plain_concept"


def select_layout_for_content(content: SlideContent) -> SlidePurpose:
    """
    Intelligent layout selection based on content structure.
    Used when the LLM didn't specify a purpose, or when auto-adapting.
    """
    if content.layers:
        return SlidePurpose.ARCHITECTURE
    if content.steps:
        return SlidePurpose.PROCESS_FLOW
    if content.milestones:
        return SlidePurpose.TIMELINE
    if content.columns:
        return SlidePurpose.COMPARISON
    if content.metrics:
        return SlidePurpose.KPI_METRICS
    if content.quote:
        return SlidePurpose.QUOTE_INSIGHT

    if content.image_bytes and content.body_bullets:
        return SlidePurpose.IMAGE_INSIGHT

    if content.body_bullets:
        if len(content.body_bullets) > 4 and content.example:
            return SlidePurpose.TWO_COLUMN
        return SlidePurpose.CONCEPT

    return SlidePurpose.CONCEPT
