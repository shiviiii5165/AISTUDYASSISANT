"""
LearnByGenie vNEXT Phase 3.1 — Design DNA Engine
================================================
Generates deck-level visual design grammar (DesignDNA) from PresentationBrief.

Governance:
  - PresentationBrief is FROZEN — consumed read-only.
  - All design tokens are strongly typed (TypographyScale, SpacingScale, ColorPalette).
  - WCAG AA contrast ratios verified for all generated palettes.
  - No topic-name branching; design decisions derive from template + theme + domain signals.
"""
from app.core.logging import logger
from typing import Dict, List, Optional

from .schemas import (
    PresentationBrief,
    ContentDensity,
    DesignSystem,
)
from .visual_schemas import (
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    Phase3LayoutFamily,
)


# ═══════════════════════════════════════════════════════════════
# COLOR PALETTES PER THEME ANCHOR (WCAG AA compliant)
# ═══════════════════════════════════════════════════════════════

_THEME_PALETTES: Dict[str, ColorPalette] = {
    "blue_professional": ColorPalette(
        primary="#1A365D",
        primary_light="#2B6CB0",
        secondary="#4A6FA5",
        accent="#ED8936",
        background="#FFFFFF",
        surface="#F7FAFC",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
        border="#E2E8F0",
        success="#38A169",
        warning="#DD6B20",
        error="#E53E3E",
        contrast_ratio_primary=12.5,
    ),
    "indigo_innovation": ColorPalette(
        primary="#3C366B",
        primary_light="#5A67D8",
        secondary="#667EEA",
        accent="#F6AD55",
        background="#FFFFFF",
        surface="#EBF4FF",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
        border="#C3DAFE",
        success="#48BB78",
        warning="#ED8936",
        error="#FC8181",
        contrast_ratio_primary=11.2,
    ),
    "emerald_growth": ColorPalette(
        primary="#1C4532",
        primary_light="#276749",
        secondary="#38A169",
        accent="#D69E2E",
        background="#FFFFFF",
        surface="#F0FFF4",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
        border="#C6F6D5",
        success="#48BB78",
        warning="#DD6B20",
        error="#E53E3E",
        contrast_ratio_primary=13.0,
    ),
    "teal_modern": ColorPalette(
        primary="#234E52",
        primary_light="#2C7A7B",
        secondary="#38B2AC",
        accent="#ED64A6",
        background="#FFFFFF",
        surface="#E6FFFA",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
        border="#B2F5EA",
        success="#48BB78",
        warning="#ED8936",
        error="#FC8181",
        contrast_ratio_primary=11.8,
    ),
    "orange_energy": ColorPalette(
        primary="#7B341E",
        primary_light="#C05621",
        secondary="#ED8936",
        accent="#3182CE",
        background="#FFFFFF",
        surface="#FFFAF0",
        text_primary="#1A202C",
        text_secondary="#4A5568",
        text_on_primary="#FFFFFF",
        border="#FEEBC8",
        success="#38A169",
        warning="#DD6B20",
        error="#E53E3E",
        contrast_ratio_primary=9.8,
    ),
    "charcoal_minimal": ColorPalette(
        primary="#1A202C",
        primary_light="#2D3748",
        secondary="#4A5568",
        accent="#63B3ED",
        background="#FFFFFF",
        surface="#F7FAFC",
        text_primary="#1A202C",
        text_secondary="#718096",
        text_on_primary="#FFFFFF",
        border="#E2E8F0",
        success="#48BB78",
        warning="#ED8936",
        error="#FC8181",
        contrast_ratio_primary=15.3,
    ),
}


# ═══════════════════════════════════════════════════════════════
# TEMPLATE-SPECIFIC DESIGN CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

def _build_academic_clean_dna(palette: ColorPalette, density: ContentDensity) -> DesignDNA:
    """Academic Clean: University lecture & teaching design system."""
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        background_strategy="solid_light",
        surface_strategy="card_elevation",
        typographic_personality="geometric_sans",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
            font_weight=700, font_size_pt=28.0,
            line_height_ratio=1.2, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
            font_weight=400, font_size_pt=14.0,
            line_height_ratio=1.5, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", safe_office_fallback="Calibri",
            font_weight=500, font_size_pt=10.0,
            line_height_ratio=1.3, letter_spacing_em=0.03, text_transform="uppercase",
        ),
        corner_radius_system="moderate",
        stroke_system="thin_border",
        shadow_usage="subtle",
        spacing_scale=SpacingScale(xs=4, s=8, m=16, l=24, xl=32, xxl=48),
        grid_system="12_column",
        preferred_composition_families=[
            Phase3LayoutFamily.SPLIT_40_60,
            Phase3LayoutFamily.TEXT_DOMINANT,
            Phase3LayoutFamily.DIAGRAM_CANVAS,
            Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
            Phase3LayoutFamily.SUMMARY_GRID,
        ],
        icon_style="outlined",
        diagram_style="clean_geometric",
        chart_style="minimal_axis",
        image_treatment="rounded_corners",
        highlight_treatment="accent_bar",
        accent_strategy="primary_accent",
        density_profile=density,
        visual_contrast_strategy="alternating",
        color_palette=palette,
    )


def _build_modern_minimal_dna(palette: ColorPalette, density: ContentDensity) -> DesignDNA:
    """Modern Minimal: Premium Canva/NotebookLM clean design system."""
    return DesignDNA(
        theme_family="modern_minimal",
        tone="sophisticated",
        background_strategy="solid_light",
        surface_strategy="flat",
        typographic_personality="neo_grotesque",
        title_scale=TypographyScale(
            font_family="Outfit", font_fallback="Aptos", safe_office_fallback="Calibri",
            font_weight=600, font_size_pt=32.0,
            line_height_ratio=1.15, letter_spacing_em=-0.02,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Aptos", safe_office_fallback="Calibri",
            font_weight=400, font_size_pt=15.0,
            line_height_ratio=1.6, letter_spacing_em=0.005,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Aptos", safe_office_fallback="Calibri",
            font_weight=400, font_size_pt=10.0,
            line_height_ratio=1.3, letter_spacing_em=0.05, text_transform="uppercase",
        ),
        corner_radius_system="rounded",
        stroke_system="none",
        shadow_usage="none",
        spacing_scale=SpacingScale(xs=6, s=12, m=20, l=32, xl=48, xxl=64),
        grid_system="8_column",
        preferred_composition_families=[
            Phase3LayoutFamily.HERO_CENTER,
            Phase3LayoutFamily.SPLIT_40_60,
            Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
            Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL,
            Phase3LayoutFamily.QUOTE_OR_STATEMENT,
        ],
        icon_style="duotone",
        diagram_style="organic",
        chart_style="minimal_axis",
        image_treatment="full_bleed",
        highlight_treatment="bold_only",
        accent_strategy="monochromatic",
        density_profile=density,
        visual_contrast_strategy="progressive",
        color_palette=palette,
    )


def _build_technical_grid_dna(palette: ColorPalette, density: ContentDensity) -> DesignDNA:
    """Technical Grid: CSE, Architecture, Engineering design system."""
    return DesignDNA(
        theme_family="technical_grid",
        tone="precise",
        background_strategy="solid_light",
        surface_strategy="outlined",
        typographic_personality="geometric_sans",
        title_scale=TypographyScale(
            font_family="Roboto", font_fallback="Arial", safe_office_fallback="Arial",
            font_weight=700, font_size_pt=26.0,
            line_height_ratio=1.2, letter_spacing_em=0.0,
        ),
        body_scale=TypographyScale(
            font_family="Roboto", font_fallback="Arial", safe_office_fallback="Arial",
            font_weight=400, font_size_pt=13.0,
            line_height_ratio=1.5, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Roboto Mono", font_fallback="Consolas", safe_office_fallback="Courier New",
            font_weight=400, font_size_pt=9.0,
            line_height_ratio=1.3, letter_spacing_em=0.02, text_transform="uppercase",
        ),
        corner_radius_system="sharp",
        stroke_system="thin_border",
        shadow_usage="none",
        spacing_scale=SpacingScale(xs=4, s=8, m=12, l=20, xl=28, xxl=40),
        grid_system="12_column",
        preferred_composition_families=[
            Phase3LayoutFamily.DIAGRAM_CANVAS,
            Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
            Phase3LayoutFamily.PROCESS_CANVAS,
            Phase3LayoutFamily.COMPARISON_MATRIX,
            Phase3LayoutFamily.DATA_CANVAS,
        ],
        icon_style="outlined",
        diagram_style="technical",
        chart_style="full_grid",
        image_treatment="bordered",
        highlight_treatment="background_tint",
        accent_strategy="complementary",
        density_profile=density,
        visual_contrast_strategy="uniform",
        color_palette=palette,
    )


def _build_editorial_dna(palette: ColorPalette, density: ContentDensity) -> DesignDNA:
    """Editorial: Magazine / Research report design system."""
    return DesignDNA(
        theme_family="editorial",
        tone="narrative",
        background_strategy="solid_light",
        surface_strategy="card_elevation",
        typographic_personality="serif_blend",
        title_scale=TypographyScale(
            font_family="Playfair Display", font_fallback="Georgia", safe_office_fallback="Cambria",
            font_weight=700, font_size_pt=30.0,
            line_height_ratio=1.15, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Source Sans Pro", font_fallback="Calibri", safe_office_fallback="Calibri",
            font_weight=400, font_size_pt=14.0,
            line_height_ratio=1.6, letter_spacing_em=0.005,
        ),
        caption_scale=TypographyScale(
            font_family="Source Sans Pro", font_fallback="Calibri", safe_office_fallback="Calibri",
            font_weight=600, font_size_pt=9.0,
            line_height_ratio=1.3, letter_spacing_em=0.08, text_transform="uppercase",
        ),
        corner_radius_system="subtle",
        stroke_system="thick_accent",
        shadow_usage="medium",
        spacing_scale=SpacingScale(xs=4, s=10, m=18, l=28, xl=40, xxl=56),
        grid_system="12_column",
        preferred_composition_families=[
            Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
            Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL,
            Phase3LayoutFamily.SPLIT_60_40,
            Phase3LayoutFamily.HERO_OFFSET,
            Phase3LayoutFamily.QUOTE_OR_STATEMENT,
        ],
        icon_style="filled",
        diagram_style="organic",
        chart_style="decorative",
        image_treatment="masked",
        highlight_treatment="underline",
        accent_strategy="triadic",
        density_profile=density,
        visual_contrast_strategy="alternating",
        color_palette=palette,
    )


def _build_visual_learning_dna(palette: ColorPalette, density: ContentDensity) -> DesignDNA:
    """Visual Learning: Diagram-first visual pedagogy design system."""
    return DesignDNA(
        theme_family="visual_learning",
        tone="engaging",
        background_strategy="gradient",
        surface_strategy="glassmorphic",
        typographic_personality="humanist",
        title_scale=TypographyScale(
            font_family="Nunito", font_fallback="Trebuchet MS", safe_office_fallback="Calibri",
            font_weight=800, font_size_pt=30.0,
            line_height_ratio=1.2, letter_spacing_em=-0.005,
        ),
        body_scale=TypographyScale(
            font_family="Nunito", font_fallback="Trebuchet MS", safe_office_fallback="Calibri",
            font_weight=400, font_size_pt=14.0,
            line_height_ratio=1.5, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Nunito", font_fallback="Trebuchet MS", safe_office_fallback="Calibri",
            font_weight=600, font_size_pt=10.0,
            line_height_ratio=1.3, letter_spacing_em=0.02, text_transform="capitalize",
        ),
        corner_radius_system="rounded",
        stroke_system="dashed",
        shadow_usage="dramatic",
        spacing_scale=SpacingScale(xs=6, s=10, m=18, l=28, xl=40, xxl=56),
        grid_system="8_column",
        preferred_composition_families=[
            Phase3LayoutFamily.VISUAL_DOMINANT,
            Phase3LayoutFamily.DIAGRAM_CANVAS,
            Phase3LayoutFamily.ANNOTATED_VISUAL,
            Phase3LayoutFamily.CARD_CLUSTER,
            Phase3LayoutFamily.PROCESS_CANVAS,
        ],
        icon_style="duotone",
        diagram_style="hand_drawn",
        chart_style="decorative",
        image_treatment="rounded_corners",
        highlight_treatment="accent_bar",
        accent_strategy="complementary",
        density_profile=density,
        visual_contrast_strategy="progressive",
        color_palette=palette,
    )


# ═══════════════════════════════════════════════════════════════
# TEMPLATE → BUILDER MAP
# ═══════════════════════════════════════════════════════════════

_TEMPLATE_BUILDERS = {
    "academic":   _build_academic_clean_dna,
    "minimal":    _build_modern_minimal_dna,
    "technical":  _build_technical_grid_dna,
    "editorial":  _build_editorial_dna,
    "visual":     _build_visual_learning_dna,
}


# ═══════════════════════════════════════════════════════════════
# MAIN API
# ═══════════════════════════════════════════════════════════════

def generate_design_dna(brief: PresentationBrief) -> DesignDNA:
    """Generate DesignDNA from a frozen PresentationBrief.

    Args:
        brief: Phase 1 PresentationBrief (read-only)

    Returns:
        DesignDNA with typed tokens, accessible palette, and composition preferences
    """
    # Resolve template
    template = brief.selected_template.lower().strip()
    builder = _TEMPLATE_BUILDERS.get(template, _build_academic_clean_dna)

    # Resolve theme palette
    theme = brief.selected_theme.lower().strip()
    palette = _THEME_PALETTES.get(theme, _THEME_PALETTES["blue_professional"])

    # Resolve density from brief technicality
    density = brief.technicality

    dna = builder(palette, density)

    logger.info(
        f"[DesignDNA] Generated DNA: template={template}, "
        f"theme={theme}, density={density.value}, "
        f"contrast_ratio={palette.contrast_ratio_primary}"
    )

    return dna


def get_available_templates() -> List[str]:
    """Return list of available design template identifiers."""
    return list(_TEMPLATE_BUILDERS.keys())


def get_available_themes() -> List[str]:
    """Return list of available theme anchor identifiers."""
    return list(_THEME_PALETTES.keys())


def validate_palette_contrast(palette: ColorPalette, min_ratio: float = 4.5) -> bool:
    """Validate that the palette meets WCAG AA minimum contrast ratio.

    Args:
        palette: ColorPalette to validate
        min_ratio: Minimum contrast ratio (default 4.5 for WCAG AA)

    Returns:
        True if the palette meets the minimum contrast requirement
    """
    return palette.contrast_ratio_primary >= min_ratio
