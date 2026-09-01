"""
TeachGenie — Layout Engine
===========================
Maps SlidePurpose → renderer function.
Handles fallback layouts when content doesn't fit a specialized renderer.
"""
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


# ═══════════════════════════════════════════════════════════════════════════
# RENDERER MAP
# ═══════════════════════════════════════════════════════════════════════════

RENDERER_MAP = {
    SlidePurpose.COVER:          render_cover,
    SlidePurpose.SECTION:        render_cover,      # section dividers reuse cover with different text
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
    Render a single slide by mapping SlidePurpose → appropriate renderer.
    Falls back through FALLBACK_CHAIN if the specialized renderer fails.
    """
    purpose = content.purpose
    renderer = RENDERER_MAP.get(purpose, render_concept)

    try:
        renderer(slide, content, theme, **kwargs)
    except Exception as e:
        print(f"[WARN] Renderer for {purpose.value} failed: {e}")
        # Try fallback
        fallback_purpose = FALLBACK_CHAIN.get(purpose)
        if fallback_purpose:
            fallback_renderer = RENDERER_MAP.get(fallback_purpose, render_concept)
            try:
                fallback_renderer(slide, content, theme, **kwargs)
                print(f"  [OK] Fallback to {fallback_purpose.value} succeeded")
                return
            except Exception as e2:
                print(f"  [WARN] Fallback also failed: {e2}")

        # Ultimate fallback: concept slide
        try:
            render_concept(slide, content, theme, **kwargs)
        except Exception:
            pass  # slide will be blank but not crash


def select_layout_for_content(content: SlideContent) -> SlidePurpose:
    """
    Intelligent layout selection based on content structure.
    Used when the LLM didn't specify a purpose, or when auto-adapting.
    """
    # If content has structured data, use specialized layouts
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

    # If has image + bullets, use image_insight
    if content.image_bytes and content.body_bullets:
        return SlidePurpose.IMAGE_INSIGHT

    # If has many bullets, use concept
    if content.body_bullets:
        if len(content.body_bullets) > 4 and content.example:
            return SlidePurpose.TWO_COLUMN
        return SlidePurpose.CONCEPT

    return SlidePurpose.CONCEPT
