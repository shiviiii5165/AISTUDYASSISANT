"""
TeachGenie PPT vNext — Phase 3.2C Parametric Layout Compilers & Responsive Reflow Engine
=======================================================================================
Spatial layout compiler layer that consumes:
  - SlideBlueprint (frozen semantic intent)
  - SlideContent (verified structured content)
  - VisualSemanticPacket (semantic visual intent & relationships)
  - DesignDNA (authoritative visual design grammar)
  - VisualRhythmBeat (authoritative deck visual pacing)
  - CompositionInputManifest (immutable content registry)
  - TextFitResult (Phase 3.2B typography fitting signals)

Outputs a deterministic, fully resolved SlideCompositionPlan adhering to:
  1. All 20 Phase3LayoutFamily compilers with parametric constraint envelopes
  2. Safe containment: SAFE_TITLE, SAFE_CONTENT, SAFE_FOOTER, FULL_BLEED
  3. Collision-safe 12-column grid and 30-module baseline geometry
  4. Responsive density adaptation (LOW, MEDIUM, HIGH)
  5. Fallback reflow chains on REFLOW_REQUIRED without content degradation
  6. Zero semantic content invention, zero topic hardcoding
"""
import re
import hashlib
from typing import List, Dict, Tuple, Optional, Any, Set
from pydantic import BaseModel, Field, field_validator, model_validator

from .schemas import (
    SlideBlueprint,
    SlideContent,
    LayoutFamily,
    VisualKind,
)
from .visual_schemas import (
    Phase3LayoutFamily,
    VisualAssetType,
    VisualIntent,
    VisualWeight,
    VisualRhythmBeat,
    VisualSemanticPacket,
    DesignDNA,
    ContentDensity,
    VisualDensityProfile,
    _LEGACY_TO_P3_LAYOUT,
)
from .composition_schemas import (
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    VERTICAL_MODULE_HEIGHT_IN,
    CompositionMode,
    RegionSemanticRole,
    CONTENT_BEARING_ROLES,
    RegionAlignment,
    VerticalAlignment,
    RegionOverflowBehavior,
    SpacingToken,
    TypographyRole,
    FormulaRenderMode,
    RendererCapability,
    SurfaceToken,
    BorderToken,
    ColorToken,
    QuadrantId,
    SourceKind,
    ROLE_MINIMUM_FONT_SIZES,
    LayoutSafeZone,
    ContentBinding,
    CompositionInputManifest,
    ResolvedRegionBounds,
    TypographyRoleSpec,
    ContentRegion,
    WhitespaceMetrics,
    ResponsiveConstraints,
    SlideCompositionPlan,
    ComposedSlideContext,
    FormulaPayload,
)
from .grid_engine import (
    MARGIN_LEFT_IN,
    MARGIN_RIGHT_IN,
    MARGIN_TOP_IN,
    MARGIN_BOTTOM_IN,
    GRID_COLUMNS,
    GRID_GUTTER_IN,
    GRID_COL_WIDTH_IN,
    resolve_column_left_in,
    resolve_column_width_in,
    resolve_row_top_in,
    resolve_row_height_in,
    resolve_region_bounds,
    detect_region_collision,
    calculate_whitespace_metrics,
    LayoutConstraintEnvelope,
)
from .typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)


# ═══════════════════════════════════════════════════════════════
# 1. STRUCTURED COMPOSITION DEFECT CODES (Section 18)
# ═══════════════════════════════════════════════════════════════

DEFECT_LAYOUT_CONSTRAINT_UNSATISFIED    = "LAYOUT_CONSTRAINT_UNSATISFIED"
DEFECT_REFLOW_REQUIRED                 = "REFLOW_REQUIRED"
DEFECT_REFLOW_CHAIN_EXHAUSTED          = "REFLOW_CHAIN_EXHAUSTED"
DEFECT_REGION_COLLISION                = "REGION_COLLISION"
DEFECT_SAFE_ZONE_VIOLATION             = "SAFE_ZONE_VIOLATION"
DEFECT_GRID_SPAN_INVALID               = "GRID_SPAN_INVALID"
DEFECT_VERTICAL_SPAN_INVALID           = "VERTICAL_SPAN_INVALID"
DEFECT_GUTTER_TOO_SMALL                = "GUTTER_TOO_SMALL"
DEFECT_VISUAL_REGION_TOO_SMALL         = "VISUAL_REGION_TOO_SMALL"
DEFECT_TEXT_REGION_TOO_SMALL           = "TEXT_REGION_TOO_SMALL"
DEFECT_SEMANTIC_ROLE_UNSUPPORTED       = "SEMANTIC_ROLE_UNSUPPORTED"
DEFECT_RHYTHM_DEVIATION                = "RHYTHM_DEVIATION"
DEFECT_CARD_GROUPING_INVALID           = "CARD_GROUPING_INVALID"
DEFECT_COMPARISON_STRUCTURE_UNSUPPORTED = "COMPARISON_STRUCTURE_UNSUPPORTED"
DEFECT_PROCESS_STRUCTURE_UNSUPPORTED   = "PROCESS_STRUCTURE_UNSUPPORTED"
DEFECT_FULL_BLEED_TEXT_VIOLATION       = "FULL_BLEED_TEXT_VIOLATION"


# ═══════════════════════════════════════════════════════════════
# 2. PARAMETRIC CONSTRAINT ENVELOPES (Section 3)
# ═══════════════════════════════════════════════════════════════

class ParametricConstraintEnvelope(BaseModel):
    """
    Parametric bounds for layout family compilation.
    Layout families are NOT rigid static templates; they define flexible
    constraint envelopes that adapt to text density, visual requirements,
    and rhythm beat compliance.
    """
    layout_family: Phase3LayoutFamily
    preferred_text_span: int = Field(..., ge=1, le=12)
    min_text_span: int = Field(..., ge=1, le=12)
    max_text_span: int = Field(..., ge=1, le=12)

    preferred_visual_span: int = Field(default=0, ge=0, le=12)
    min_visual_span: int = Field(default=0, ge=0, le=12)
    max_visual_span: int = Field(default=0, ge=0, le=12)

    preferred_visual_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    min_visual_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    max_visual_ratio: float = Field(default=1.0, ge=0.0, le=1.0)

    allowed_vertical_zones: List[LayoutSafeZone] = Field(default_factory=lambda: [LayoutSafeZone.SAFE_CONTENT])
    allowed_alignments: List[RegionAlignment] = Field(default_factory=lambda: [RegionAlignment.LEFT])
    allowed_secondary_regions: List[RegionSemanticRole] = Field(default_factory=list)
    overlay_policy: str = "disallowed"          # "disallowed" | "panel_over_bleed" | "callout_overlay"
    full_bleed_policy: str = "disallowed"       # "disallowed" | "background_visual_only"
    minimum_gutter: float = 0.150
    maximum_gutter: float = 0.500
    fallback_chain: List[Phase3LayoutFamily] = Field(default_factory=list)
    whitespace_target_min: float = 0.20
    whitespace_target_max: float = 0.65


# ═══════════════════════════════════════════════════════════════
# 3. DETERMINISTIC SEMANTIC FALLBACK CHAINS (Section 5)
# ═══════════════════════════════════════════════════════════════

SEMANTIC_FALLBACK_CHAINS: Dict[Phase3LayoutFamily, List[Phase3LayoutFamily]] = {
    Phase3LayoutFamily.SPLIT_40_60: [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.SPLIT_60_40: [
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.VISUAL_DOMINANT: [
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.FORMULA_VISUAL: [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.DATA_CANVAS: [
        Phase3LayoutFamily.VISUAL_DOMINANT,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.PROCESS_CANVAS: [
        Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.TIMELINE_CANVAS: [
        Phase3LayoutFamily.PROCESS_CANVAS,
        Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.SYSTEM_ARCHITECTURE: [
        Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.DIAGRAM_CANVAS: [
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.CARD_CLUSTER: [
        Phase3LayoutFamily.SUMMARY_GRID,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.SUMMARY_GRID: [
        Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.COMPARISON_TWO_COLUMN: [
        Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.COMPARISON_MATRIX: [
        Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL: [
        Phase3LayoutFamily.VISUAL_DOMINANT,
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.ANNOTATED_VISUAL: [
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.QUOTE_OR_STATEMENT: [
        Phase3LayoutFamily.HERO_CENTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.HERO_CENTER: [
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.HERO_OFFSET: [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.ASYMMETRIC_EDITORIAL: [
        Phase3LayoutFamily.SPLIT_60_40,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    Phase3LayoutFamily.TEXT_DOMINANT: [],  # Terminal fallback
}


TEMPORAL_STRUCTURE_KEYS: Set[str] = {
    "temporal_structure",
    "timeline_sequence",
    "chronological_progression",
    "timeline_structure",
}

TEMPORAL_RELATION_PATTERN: re.Pattern = re.compile(
    r"\b(?:before|after|during|followed\s+by|milestones?|chronolog\w+|phases?|eras?|then|subsequently|prior\s+to|timeline|preceding|succeeding)\b",
    re.IGNORECASE,
)


def extract_distinct_temporal_tokens(text: str) -> Set[str]:
    """
    Extracts distinct canonical dates, eras, quarters, and milestones from text.
    Rejects isolated version numbers (e.g., '3.13', 'v2.0') by requiring explicit
    year, century, era, fiscal quarter, or milestone token format.
    """
    tokens: Set[str] = set()
    if not text:
        return tokens

    # 1. Four-digit Years (1000-2099) not preceded or followed by dots/digits (avoids version strings like 3.13, 2024.1)
    for m in re.finditer(r"(?<![\.\d])(1\d{3}|20\d{2})(?![\.\d])", text):
        tokens.add(f"year:{m.group(1)}")

    # 2. Historical Eras / Centuries (e.g. 1760 BCE, 4th century)
    for m in re.finditer(r"(?:(?<![\.\d])\d{1,4}\s*(?:bce?|ce|ad|bc)|\b\d{1,2}(?:st|nd|rd|th)\s+century)\b", text, re.IGNORECASE):
        tokens.add(f"era:{re.sub(r'\s+', ' ', m.group(0).lower())}")

    # 3. Quarters / Fiscal Years (e.g. Q1, Q2, FY26, FY2026)
    for m in re.finditer(r"\b(?:q[1-4]|quarter\s*[1-4]|fy\s*\d{2,4})\b", text, re.IGNORECASE):
        tokens.add(f"quarter:{re.sub(r'\s+', '', m.group(0).lower())}")

    # 4. Explicit numbered milestones / phases (e.g. Milestone 1, Phase 2)
    for m in re.finditer(r"\b(?:milestone\s*\d+|phase\s*\d+)\b", text, re.IGNORECASE):
        tokens.add(f"milestone:{re.sub(r'\s+', '', m.group(0).lower())}")

    # 5. Full calendar months
    for m in re.finditer(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b", text, re.IGNORECASE):
        tokens.add(f"month:{m.group(0).lower()}")

    return tokens


def has_temporal_semantics(
    packet: VisualSemanticPacket,
    content: Optional[SlideContent] = None,
) -> bool:
    """
    Evaluates whether the slide contains explicit temporal semantics.
    Timeline fallback is NEVER authorized by an isolated single year, quarter,
    version date, or fiscal token (e.g., 'Node.js Architecture 2026',
    'FY26 Security Architecture', 'Python 3.13 in 2026', 'Budget Q2 Analysis').

    Timeline eligibility strictly requires either:
    A. Explicit temporal VisualSemanticPacket structure:
       - packet.visual_intent == VisualIntent.SHOW_TIMELINE
       - packet.visual_structure in ('temporal_structure', 'timeline_sequence', 'chronological_progression')
       - bool(packet.temporal_structure) (non-empty list)
       - packet.relationships containing explicit 'temporal' relationship_type
    OR
    B. Strong ordered temporal evidence:
       - 2+ distinct ordered dates / eras / quarters / milestones
       AND
       - temporal relationship language such as:
         'before', 'after', 'during', 'followed by', 'milestone', 'chronology',
         'phase', 'era', 'then', 'subsequently', 'prior to'
    """
    # ── Criterion A: Explicit temporal VisualSemanticPacket structure ──
    if packet.visual_intent == VisualIntent.SHOW_TIMELINE:
        return True

    struct = getattr(packet, "visual_structure", "") or ""
    if struct in TEMPORAL_STRUCTURE_KEYS:
        return True

    if packet.temporal_structure and len(packet.temporal_structure) > 0:
        return True

    for rel in packet.relationships:
        rtype = str(getattr(rel, "relationship_type", "")).lower()
        if "temporal" in rtype:
            return True

    # ── Criterion B: Strong ordered temporal evidence ──
    texts_to_check: List[str] = []
    if content:
        if getattr(content, "title", None):
            texts_to_check.append(content.title)
        if getattr(content, "subtitle", None):
            texts_to_check.append(content.subtitle)
        if getattr(content, "primary_takeaway", None):
            texts_to_check.append(content.primary_takeaway)
        if getattr(content, "process_steps", None):
            texts_to_check.extend(content.process_steps)
        if getattr(content, "supporting_points", None):
            texts_to_check.extend(content.supporting_points)
        if getattr(content, "example", None):
            texts_to_check.append(content.example)
        if getattr(content, "callout", None):
            texts_to_check.append(content.callout)
    if packet:
        if getattr(packet, "process_nodes", None):
            texts_to_check.extend(packet.process_nodes)
        if getattr(packet, "summary_title", None):
            texts_to_check.append(packet.summary_title)
        if getattr(packet, "primary_insight", None):
            texts_to_check.append(packet.primary_insight)
        for rel in packet.relationships:
            if getattr(rel, "relation", None):
                texts_to_check.append(rel.relation)

    full_text = " ".join(texts_to_check)

    # Must find 2+ distinct temporal tokens
    distinct_tokens = extract_distinct_temporal_tokens(full_text)
    if len(distinct_tokens) < 2:
        return False

    # AND must find temporal relationship language
    has_rel_lang = bool(TEMPORAL_RELATION_PATTERN.search(full_text))
    if not has_rel_lang:
        for rel in packet.relationships:
            if rel.relation and TEMPORAL_RELATION_PATTERN.search(rel.relation):
                has_rel_lang = True
                break

    return has_rel_lang


def get_parametric_constraint_envelope(
    layout: Phase3LayoutFamily,
    content_density: ContentDensity = ContentDensity.MEDIUM,
    visual_density: Optional[VisualDensityProfile] = None,
    design_dna: Optional[DesignDNA] = None,
    packet: Optional[VisualSemanticPacket] = None,
    content: Optional[SlideContent] = None,
) -> ParametricConstraintEnvelope:
    """
    Returns the parametric constraint envelope for any of the 20 layout families,
    dynamically adjusting spans and ratios according to content density, visual
    density, and DesignDNA preferences.
    """
    fallback = list(SEMANTIC_FALLBACK_CHAINS.get(layout, [Phase3LayoutFamily.TEXT_DOMINANT]))
    if layout == Phase3LayoutFamily.PROCESS_CANVAS:
        if packet is not None and has_temporal_semantics(packet, content):
            fallback = [Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.TEXT_DOMINANT]
        else:
            fallback = [Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.TEXT_DOMINANT]
    is_high_density = (content_density == ContentDensity.HIGH)
    is_low_density = (content_density == ContentDensity.LOW)

    # 1. HERO_CENTER
    if layout == Phase3LayoutFamily.HERO_CENTER:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=10 if not is_high_density else 12,
            min_text_span=8,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=4,
            preferred_visual_ratio=0.10,
            min_visual_ratio=0.0,
            max_visual_ratio=0.25,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.CENTER, RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.40,
            whitespace_target_max=0.70,
        )

    # 2. HERO_OFFSET
    elif layout == Phase3LayoutFamily.HERO_OFFSET:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=7 if not is_high_density else 8,
            min_text_span=6,
            max_text_span=9,
            preferred_visual_span=5 if not is_high_density else 4,
            min_visual_span=3,
            max_visual_span=6,
            preferred_visual_ratio=0.40,
            min_visual_ratio=0.25,
            max_visual_ratio=0.55,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.30,
            whitespace_target_max=0.60,
        )

    # 3. SPLIT_40_60
    elif layout == Phase3LayoutFamily.SPLIT_40_60:
        pref_text = 6 if is_high_density else (4 if is_low_density else 5)
        pref_vis = 6 if is_high_density else (8 if is_low_density else 7)
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=4,
            max_text_span=7,
            preferred_visual_span=pref_vis,
            min_visual_span=5,
            max_visual_span=8,
            preferred_visual_ratio=0.58,
            min_visual_ratio=0.45,
            max_visual_ratio=0.70,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 4. SPLIT_60_40
    elif layout == Phase3LayoutFamily.SPLIT_60_40:
        pref_text = 8 if is_high_density else (6 if is_low_density else 7)
        pref_vis = 4 if is_high_density else (6 if is_low_density else 5)
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=6,
            max_text_span=9,
            preferred_visual_span=pref_vis,
            min_visual_span=3,
            max_visual_span=6,
            preferred_visual_ratio=0.40,
            min_visual_ratio=0.25,
            max_visual_ratio=0.50,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 5. VISUAL_DOMINANT
    elif layout == Phase3LayoutFamily.VISUAL_DOMINANT:
        pref_text = 4 if is_high_density else 3
        pref_vis = 8 if is_high_density else 9
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=3,
            max_text_span=5,
            preferred_visual_span=pref_vis,
            min_visual_span=7,
            max_visual_span=9,
            preferred_visual_ratio=0.70,
            min_visual_ratio=0.55,
            max_visual_ratio=0.85,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 6. TEXT_DOMINANT
    elif layout == Phase3LayoutFamily.TEXT_DOMINANT:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12 if is_high_density else 10,
            min_text_span=8,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=3,
            preferred_visual_ratio=0.0,
            min_visual_ratio=0.0,
            max_visual_ratio=0.20,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=[],
            whitespace_target_min=0.25,
            whitespace_target_max=0.55,
        )

    # 7. DIAGRAM_CANVAS
    elif layout == Phase3LayoutFamily.DIAGRAM_CANVAS:
        pref_text = 5 if is_high_density else 4
        pref_vis = 7 if is_high_density else 8
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=3,
            max_text_span=5,
            preferred_visual_span=pref_vis,
            min_visual_span=7,
            max_visual_span=9,
            preferred_visual_ratio=0.65,
            min_visual_ratio=0.50,
            max_visual_ratio=0.80,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 8. FULL_BLEED_IMAGE_WITH_PANEL
    elif layout == Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL:
        pref_panel = 7 if is_high_density else 6
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_panel,
            min_text_span=5,
            max_text_span=8,
            preferred_visual_span=12,  # Background covers full slide
            min_visual_span=12,
            max_visual_span=12,
            preferred_visual_ratio=0.60,
            min_visual_ratio=0.40,
            max_visual_ratio=0.80,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT, LayoutSafeZone.FULL_BLEED],
            allowed_alignments=[RegionAlignment.LEFT],
            overlay_policy="panel_over_bleed",
            full_bleed_policy="background_visual_only",
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.50,
        )

    # 9. CARD_CLUSTER
    elif layout == Phase3LayoutFamily.CARD_CLUSTER:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=6,
            preferred_visual_ratio=0.25,
            min_visual_ratio=0.0,
            max_visual_ratio=0.45,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            allowed_secondary_regions=[RegionSemanticRole.CARD_CONTAINER],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 10. COMPARISON_TWO_COLUMN
    elif layout == Phase3LayoutFamily.COMPARISON_TWO_COLUMN:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,  # 6 cols for Column A, 6 cols for Column B
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=4,
            preferred_visual_ratio=0.15,
            min_visual_ratio=0.0,
            max_visual_ratio=0.35,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            allowed_secondary_regions=[RegionSemanticRole.COMPARISON_COLUMN_A, RegionSemanticRole.COMPARISON_COLUMN_B],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 11. COMPARISON_MATRIX
    elif layout == Phase3LayoutFamily.COMPARISON_MATRIX:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=4,
            preferred_visual_ratio=0.20,
            min_visual_ratio=0.0,
            max_visual_ratio=0.40,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 12. TIMELINE_CANVAS
    elif layout == Phase3LayoutFamily.TIMELINE_CANVAS:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=12,
            min_visual_span=8,
            max_visual_span=12,
            preferred_visual_ratio=0.50,
            min_visual_ratio=0.30,
            max_visual_ratio=0.65,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT, RegionAlignment.CENTER],
            allowed_secondary_regions=[RegionSemanticRole.TIMELINE_NODE],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 13. PROCESS_CANVAS
    elif layout == Phase3LayoutFamily.PROCESS_CANVAS:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=12,
            min_visual_span=8,
            max_visual_span=12,
            preferred_visual_ratio=0.50,
            min_visual_ratio=0.30,
            max_visual_ratio=0.65,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT, RegionAlignment.CENTER],
            allowed_secondary_regions=[RegionSemanticRole.PROCESS_STEP],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 14. DATA_CANVAS
    elif layout == Phase3LayoutFamily.DATA_CANVAS:
        pref_text = 5 if is_high_density else 4
        pref_vis = 7 if is_high_density else 8
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=4,
            max_text_span=6,
            preferred_visual_span=pref_vis,
            min_visual_span=6,
            max_visual_span=8,
            preferred_visual_ratio=0.60,
            min_visual_ratio=0.45,
            max_visual_ratio=0.75,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            allowed_secondary_regions=[RegionSemanticRole.METRIC_CARD, RegionSemanticRole.KEY_INSIGHT_CALLOUT],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 15. FORMULA_VISUAL
    elif layout == Phase3LayoutFamily.FORMULA_VISUAL:
        pref_text = 6 if is_high_density else 5
        pref_vis = 6 if is_high_density else 7
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=4,
            max_text_span=7,
            preferred_visual_span=pref_vis,
            min_visual_span=5,
            max_visual_span=8,
            preferred_visual_ratio=0.50,
            min_visual_ratio=0.35,
            max_visual_ratio=0.65,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT, RegionAlignment.CENTER],
            allowed_secondary_regions=[RegionSemanticRole.FORMULA_DISPLAY],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.55,
        )

    # 16. ANNOTATED_VISUAL
    elif layout == Phase3LayoutFamily.ANNOTATED_VISUAL:
        pref_text = 5 if is_high_density else 4
        pref_vis = 7 if is_high_density else 8
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=3,
            max_text_span=6,
            preferred_visual_span=pref_vis,
            min_visual_span=6,
            max_visual_span=9,
            preferred_visual_ratio=0.60,
            min_visual_ratio=0.45,
            max_visual_ratio=0.75,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            allowed_secondary_regions=[RegionSemanticRole.CAPTION],
            fallback_chain=fallback,
            whitespace_target_min=0.25,
            whitespace_target_max=0.50,
        )

    # 17. QUOTE_OR_STATEMENT
    elif layout == Phase3LayoutFamily.QUOTE_OR_STATEMENT:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=10 if not is_high_density else 12,
            min_text_span=8,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=3,
            preferred_visual_ratio=0.10,
            min_visual_ratio=0.0,
            max_visual_ratio=0.25,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.CENTER, RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.40,
            whitespace_target_max=0.70,
        )

    # 18. SUMMARY_GRID
    elif layout == Phase3LayoutFamily.SUMMARY_GRID:
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=12,
            min_text_span=10,
            max_text_span=12,
            preferred_visual_span=0,
            min_visual_span=0,
            max_visual_span=6,
            preferred_visual_ratio=0.20,
            min_visual_ratio=0.0,
            max_visual_ratio=0.40,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            allowed_secondary_regions=[RegionSemanticRole.CARD_CONTAINER],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.45,
        )

    # 19. ASYMMETRIC_EDITORIAL
    elif layout == Phase3LayoutFamily.ASYMMETRIC_EDITORIAL:
        pref_text = 8 if is_high_density else 7
        pref_vis = 4 if is_high_density else 5
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=6,
            max_text_span=8,
            preferred_visual_span=pref_vis,
            min_visual_span=4,
            max_visual_span=6,
            preferred_visual_ratio=0.40,
            min_visual_ratio=0.25,
            max_visual_ratio=0.55,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.30,
            whitespace_target_max=0.60,
        )

    # 20. SYSTEM_ARCHITECTURE
    elif layout == Phase3LayoutFamily.SYSTEM_ARCHITECTURE:
        pref_text = 5 if is_high_density else 4
        pref_vis = 7 if is_high_density else 8
        return ParametricConstraintEnvelope(
            layout_family=layout,
            preferred_text_span=pref_text,
            min_text_span=3,
            max_text_span=5,
            preferred_visual_span=pref_vis,
            min_visual_span=7,
            max_visual_span=9,
            preferred_visual_ratio=0.67,
            min_visual_ratio=0.50,
            max_visual_ratio=0.80,
            allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
            allowed_alignments=[RegionAlignment.LEFT],
            fallback_chain=fallback,
            whitespace_target_min=0.20,
            whitespace_target_max=0.40,
        )

    # Generic default
    return ParametricConstraintEnvelope(
        layout_family=layout,
        preferred_text_span=6,
        min_text_span=4,
        max_text_span=12,
        preferred_visual_span=6,
        min_visual_span=0,
        max_visual_span=8,
        preferred_visual_ratio=0.50,
        min_visual_ratio=0.0,
        max_visual_ratio=0.80,
        allowed_vertical_zones=[LayoutSafeZone.SAFE_CONTENT],
        allowed_alignments=[RegionAlignment.LEFT],
        fallback_chain=fallback,
        whitespace_target_min=0.25,
        whitespace_target_max=0.55,
    )


# ═══════════════════════════════════════════════════════════════
# 4. COMPILED PLAN & EXTENSION
# ═══════════════════════════════════════════════════════════════

class CompiledSlideCompositionPlan(SlideCompositionPlan):
    """
    Fully compiled spatial composition plan carrying typed defect audit codes,
    reflow fallback history, and rhythm compliance metrics.
    """
    quality_defects: List[str] = Field(default_factory=list)
    fallback_history: List[str] = Field(default_factory=list)
    rhythm_plan_compliance: float = Field(default=1.0, ge=0.0, le=1.0)


# ═══════════════════════════════════════════════════════════════
# 5. REGION BUILDER & GEOMETRY SOLVER
# ═══════════════════════════════════════════════════════════════

class LayoutCompilerContext:
    """Working context for compiling a single slide's composition plan."""
    def __init__(
        self,
        slide_blueprint: SlideBlueprint,
        slide_content: SlideContent,
        visual_semantic_packet: VisualSemanticPacket,
        design_dna: DesignDNA,
        rhythm_beat: Optional[VisualRhythmBeat],
        manifest: CompositionInputManifest,
        text_fit_results: Optional[Dict[str, TextFitResult]] = None,
    ):
        self.blueprint = slide_blueprint
        self.content = slide_content
        self.packet = visual_semantic_packet
        self.dna = design_dna
        self.beat = rhythm_beat
        self.manifest = manifest
        self.fit_results = text_fit_results or {}
        
        # Provenance IDs
        self.slide_source_id = slide_blueprint.slide_id or f"slide_{slide_blueprint.slide_number}"
        self.visual_source_id = f"visual_{slide_blueprint.slide_number}"
        self.evidence_source_id = f"evidence_{slide_blueprint.slide_number}"
        
        # Register in manifest if missing
        if self.slide_source_id not in self.manifest.raw_content_items:
            self.manifest.register_content(self.slide_source_id, self.content.model_dump())
        if self.visual_source_id not in self.manifest.raw_content_items:
            self.manifest.register_content(self.visual_source_id, self.packet.model_dump())
            
        # Audit tracking
        self.quality_defects: List[str] = []
        self.fallback_history: List[str] = []
        self.rhythm_plan_compliance: float = 1.0

    def make_binding(
        self,
        source_kind: SourceKind,
        source_id: str,
        field_path: str,
        is_decorative: bool = False,
    ) -> ContentBinding:
        """Creates a verified typed ContentBinding with full SHA-256 hash."""
        if is_decorative:
            return ContentBinding(is_decorative=True, source_kind=SourceKind.DECORATIVE)
        
        chash = self.manifest.compute_field_hash(source_id, field_path)
        return ContentBinding(
            source_kind=source_kind,
            source_id=source_id,
            field_path=field_path,
            resolved_content_hash=chash,
            content_hash=chash,
            is_decorative=False,
        )

    def resolve_surface_styling(self) -> Tuple[SurfaceToken, BorderToken, float]:
        """Resolves surface token, border token, and corner radius pt from DesignDNA."""
        surface = SurfaceToken.SURFACE_DEFAULT
        if self.dna.surface_strategy == "card_elevation":
            surface = SurfaceToken.SURFACE_ELEVATED
        elif self.dna.surface_strategy == "flat":
            surface = SurfaceToken.SURFACE_DEFAULT
        elif self.dna.surface_strategy == "outlined":
            surface = SurfaceToken.SURFACE_DEFAULT
        elif self.dna.surface_strategy == "glassmorphic":
            surface = SurfaceToken.SURFACE_MUTED

        border = BorderToken.NONE
        if self.dna.stroke_system == "thin_border":
            border = BorderToken.THIN
        elif self.dna.stroke_system == "thick_accent":
            border = BorderToken.THICK
        elif self.dna.stroke_system == "none":
            border = BorderToken.NONE

        corner_radius = 8.0
        if self.dna.corner_radius_system == "sharp":
            corner_radius = 0.0
        elif self.dna.corner_radius_system == "subtle":
            corner_radius = 4.0
        elif self.dna.corner_radius_system == "moderate":
            corner_radius = 8.0
        elif self.dna.corner_radius_system == "rounded":
            corner_radius = 12.0
        elif self.dna.corner_radius_system == "pill":
            corner_radius = 20.0

        return surface, border, corner_radius


def _compile_standard_header_and_footer(
    ctx: LayoutCompilerContext,
    col_start: int = 1,
    col_span: int = 12,
) -> Tuple[ContentRegion, Optional[ContentRegion]]:
    """
    Compiles mandatory Title (rows 3..6) and optional Footer Citation (rows 28..29).
    Title is strictly in SAFE_TITLE (rows 3..7); Footer is strictly in SAFE_FOOTER (rows 28..30).
    """
    # Title region
    title_binding = ctx.make_binding(
        source_kind=SourceKind.SLIDE_CONTENT,
        source_id=ctx.slide_source_id,
        field_path="title",
    )
    title_typo = resolve_typography_role_spec(
        role=TypographyRole.TITLE,
        design_dna=ctx.dna,
        content_density=ctx.blueprint.content_density,
    )
    title_bounds = resolve_region_bounds(col_start, col_span, 3, 4)
    title_region = ContentRegion(
        region_id=f"{ctx.slide_source_id}_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        safe_zone=LayoutSafeZone.SAFE_TITLE,
        binding=title_binding,
        quadrant=QuadrantId.TOP_LEFT,
        grid_col_start=col_start,
        grid_col_span=col_span,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=title_bounds,
        alignment=RegionAlignment.LEFT,
        vertical_alignment=VerticalAlignment.TOP,
        padding_token=SpacingToken.S,
        content_priority=1,
        typography_spec=title_typo,
    )

    # Footer citation region (if citation exists)
    footer_region = None
    if ctx.content.citation_claims:
        footer_binding = ctx.make_binding(
            source_kind=SourceKind.EVIDENCE,
            source_id=ctx.slide_source_id,
            field_path="citation_claims[0]",
        )
        footer_typo = resolve_typography_role_spec(
            role=TypographyRole.CAPTION,
            design_dna=ctx.dna,
            content_density=ctx.blueprint.content_density,
        )
        footer_bounds = resolve_region_bounds(1, 12, 28, 2)
        footer_region = ContentRegion(
            region_id=f"{ctx.slide_source_id}_citation",
            semantic_role=RegionSemanticRole.FOOTER_CITATION,
            safe_zone=LayoutSafeZone.SAFE_FOOTER,
            binding=footer_binding,
            quadrant=QuadrantId.BOTTOM_LEFT,
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=28,
            baseline_row_span=2,
            bounds=footer_bounds,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.BOTTOM,
            padding_token=SpacingToken.XS,
            content_priority=5,
            typography_spec=footer_typo,
        )

    return title_region, footer_region


def _compile_family_regions(
    layout: Phase3LayoutFamily,
    envelope: ParametricConstraintEnvelope,
    ctx: LayoutCompilerContext,
) -> List[ContentRegion]:
    """
    Compiles content regions for any of the 20 Phase3LayoutFamily layouts.
    All content regions are strictly bounded to SAFE_CONTENT (rows 8..27),
    except BLEED_BACKGROUND which is explicitly permitted in FULL_BLEED (rows 1..30).
    """
    regions: List[ContentRegion] = []
    surface, border, corner_radius = ctx.resolve_surface_styling()
    content_density = ctx.blueprint.content_density

    # Title & Citation
    title_reg, footer_reg = _compile_standard_header_and_footer(ctx)
    regions.append(title_reg)
    if footer_reg:
        regions.append(footer_reg)

    # Row capacity for SAFE_CONTENT: rows 8..27 (20 modules = 5.00 in)
    content_row_start = 8
    content_row_span = 19  # rows 8..26 (leaves row 27 as buffer before footer row 28)

    # ─────────────────────────────────────────────────────────────
    # 1. HERO_CENTER
    # ─────────────────────────────────────────────────────────────
    if layout == Phase3LayoutFamily.HERO_CENTER:
        text_span = envelope.preferred_text_span
        col_start = 1 + (12 - text_span) // 2
        body_binding = ctx.make_binding(
            SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway"
        )
        body_typo = resolve_typography_role_spec(TypographyRole.DISPLAY, ctx.dna, content_density)
        b = resolve_region_bounds(col_start, text_span, 10, 14)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_hero_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=body_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=col_start,
            grid_col_span=text_span,
            baseline_row_start=10,
            baseline_row_span=14,
            bounds=b,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.L,
            content_priority=1,
            typography_spec=body_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 2. HERO_OFFSET
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.HERO_OFFSET:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Focal text
        body_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        body_typo = resolve_typography_role_spec(TypographyRole.DISPLAY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_hero_offset_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=body_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=body_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Supporting callout
        sup_field = "supporting_points[0]" if ctx.content.supporting_points else "callout"
        sup_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, sup_field)
        sup_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_hero_offset_sub",
            semantic_role=RegionSemanticRole.SUPPORTING_POINTS,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=sup_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_vis,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=sup_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 3. SPLIT_40_60
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.SPLIT_40_60:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Left Text
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_split_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Right Visual
        vis_field = "diagram_candidate" if ctx.packet.diagram_candidate else "primary_visual_message"
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, vis_field)
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_split_visual",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_vis,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.S,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_MUTED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 4. SPLIT_60_40
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.SPLIT_60_40:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_split60_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_split60_visual",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_vis,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.S,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_MUTED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 5. VISUAL_DOMINANT
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.VISUAL_DOMINANT:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Left overview
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_visdom_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Large Right Visual Canvas
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_visdom_canvas",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_vis,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 6. TEXT_DOMINANT
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.TEXT_DOMINANT:
        t_span = envelope.preferred_text_span
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_textdom_primary",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 7. DIAGRAM_CANVAS
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.DIAGRAM_CANVAS:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_diag_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_diag = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_diag_canvas",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_diag,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_MUTED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 8. FULL_BLEED_IMAGE_WITH_PANEL (Section 9)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL:
        # Background full-bleed decorative region
        bg_binding = ctx.make_binding(SourceKind.DECORATIVE, "", "", is_decorative=True)
        b_bleed = resolve_region_bounds(1, 12, 1, 30, is_full_bleed=True)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_bleed_bg",
            semantic_role=RegionSemanticRole.BLEED_BACKGROUND,
            safe_zone=LayoutSafeZone.FULL_BLEED,
            binding=bg_binding,
            quadrant=QuadrantId.FULL_SPAN,
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=1,
            baseline_row_span=30,
            bounds=b_bleed,
            is_full_bleed=True,
            content_priority=5,
            surface_token=SurfaceToken.SURFACE_MUTED,
        ))
        # Elevated Content Panel (Strictly in SAFE_CONTENT rows 8..26)
        panel_span = envelope.preferred_text_span
        panel_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        panel_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_panel = resolve_region_bounds(1, panel_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_bleed_panel",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=panel_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=panel_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_panel,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.L,
            content_priority=1,
            typography_spec=panel_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=BorderToken.THIN,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 9. CARD_CLUSTER (Section 10)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.CARD_CLUSTER:
        items = ctx.content.supporting_points or ctx.packet.key_entities
        count = min(4, max(2, len(items))) if items else 3
        card_span = 12 // count
        for i in range(count):
            field_path = f"supporting_points[{i}]" if i < len(ctx.content.supporting_points) else "primary_takeaway"
            card_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, field_path)
            card_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
            col_st = 1 + (i * card_span)
            b_card = resolve_region_bounds(col_st, card_span, content_row_start, content_row_span)
            regions.append(ContentRegion(
                region_id=f"{ctx.slide_source_id}_card_{i+1}",
                semantic_role=RegionSemanticRole.CARD_CONTAINER,
                safe_zone=LayoutSafeZone.SAFE_CONTENT,
                binding=card_binding,
                quadrant=QuadrantId.TOP_LEFT if i < count // 2 else QuadrantId.TOP_RIGHT,
                grid_col_start=col_st,
                grid_col_span=card_span,
                baseline_row_start=content_row_start,
                baseline_row_span=content_row_span,
                bounds=b_card,
                alignment=RegionAlignment.LEFT,
                vertical_alignment=VerticalAlignment.TOP,
                padding_token=SpacingToken.M,
                content_priority=2,
                typography_spec=card_typo,
                surface_token=SurfaceToken.SURFACE_ELEVATED,
                border_token=border,
                corner_radius_pt=corner_radius,
            ))

    # ─────────────────────────────────────────────────────────────
    # 10. COMPARISON_TWO_COLUMN (Section 11)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.COMPARISON_TWO_COLUMN:
        # Col A (cols 1..6)
        binding_a = ctx.make_binding(
            SourceKind.SLIDE_CONTENT,
            ctx.slide_source_id,
            "comparison_target_a" if ctx.content.comparison_target_a else "primary_takeaway",
        )
        typo_a = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_a = resolve_region_bounds(1, 6, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_comp_col_a",
            semantic_role=RegionSemanticRole.COMPARISON_COLUMN_A,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=binding_a,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=6,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_a,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=typo_a,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Col B (cols 7..12)
        binding_b = ctx.make_binding(
            SourceKind.SLIDE_CONTENT,
            ctx.slide_source_id,
            "comparison_target_b" if ctx.content.comparison_target_b else (
                "supporting_points[0]" if ctx.content.supporting_points else "callout"
            ),
        )
        typo_b = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_b = resolve_region_bounds(7, 6, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_comp_col_b",
            semantic_role=RegionSemanticRole.COMPARISON_COLUMN_B,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=binding_b,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=7,
            grid_col_span=6,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_b,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=typo_b,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 11. COMPARISON_MATRIX (Section 11)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.COMPARISON_MATRIX:
        rows_count = min(4, max(2, len(ctx.content.comparison_rows))) if ctx.content.comparison_rows else 3
        # Primary container for the matrix
        matrix_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        matrix_typo = resolve_typography_role_spec(TypographyRole.TABLE_HEADER, ctx.dna, content_density)
        b_mat = resolve_region_bounds(1, 12, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_comp_matrix",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=matrix_binding,
            quadrant=QuadrantId.FULL_SPAN,
            grid_col_start=1,
            grid_col_span=12,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_mat,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=matrix_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=BorderToken.THIN,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 12. TIMELINE_CANVAS (Section 12)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.TIMELINE_CANVAS:
        timeline_items = ctx.packet.temporal_structure or ctx.content.supporting_points
        count = min(4, max(3, len(timeline_items))) if timeline_items else 3
        node_span = 12 // count
        for i in range(count):
            field_path = f"supporting_points[{i}]" if i < len(ctx.content.supporting_points) else "primary_takeaway"
            t_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, field_path)
            t_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
            col_st = 1 + (i * node_span)
            b_node = resolve_region_bounds(col_st, node_span, content_row_start, content_row_span)
            regions.append(ContentRegion(
                region_id=f"{ctx.slide_source_id}_timeline_node_{i+1}",
                semantic_role=RegionSemanticRole.TIMELINE_NODE,
                safe_zone=LayoutSafeZone.SAFE_CONTENT,
                binding=t_binding,
                quadrant=QuadrantId.TOP_LEFT if i < count // 2 else QuadrantId.TOP_RIGHT,
                grid_col_start=col_st,
                grid_col_span=node_span,
                baseline_row_start=content_row_start,
                baseline_row_span=content_row_span,
                bounds=b_node,
                alignment=RegionAlignment.CENTER,
                vertical_alignment=VerticalAlignment.MIDDLE,
                padding_token=SpacingToken.S,
                content_priority=2,
                typography_spec=t_typo,
                surface_token=SurfaceToken.SURFACE_ELEVATED,
                border_token=border,
                corner_radius_pt=corner_radius,
            ))

    # ─────────────────────────────────────────────────────────────
    # 13. PROCESS_CANVAS (Section 12)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.PROCESS_CANVAS:
        process_items = ctx.content.process_steps or ctx.packet.process_nodes
        count = min(4, max(3, len(process_items))) if process_items else 3
        step_span = 12 // count
        for i in range(count):
            field_path = f"process_steps[{i}]" if i < len(ctx.content.process_steps) else "primary_takeaway"
            p_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, field_path)
            p_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
            col_st = 1 + (i * step_span)
            b_step = resolve_region_bounds(col_st, step_span, content_row_start, content_row_span)
            regions.append(ContentRegion(
                region_id=f"{ctx.slide_source_id}_process_step_{i+1}",
                semantic_role=RegionSemanticRole.PROCESS_STEP,
                safe_zone=LayoutSafeZone.SAFE_CONTENT,
                binding=p_binding,
                quadrant=QuadrantId.TOP_LEFT if i < count // 2 else QuadrantId.TOP_RIGHT,
                grid_col_start=col_st,
                grid_col_span=step_span,
                baseline_row_start=content_row_start,
                baseline_row_span=content_row_span,
                bounds=b_step,
                alignment=RegionAlignment.LEFT,
                vertical_alignment=VerticalAlignment.TOP,
                padding_token=SpacingToken.S,
                content_priority=2,
                typography_spec=p_typo,
                surface_token=SurfaceToken.SURFACE_ELEVATED,
                border_token=border,
                corner_radius_pt=corner_radius,
            ))

    # ─────────────────────────────────────────────────────────────
    # 14. DATA_CANVAS (Section 14)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.DATA_CANVAS:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Left Metrics / Insights
        metric_field = "data_points[0]" if ctx.content.data_points else "primary_takeaway"
        m_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, metric_field)
        m_typo = resolve_typography_role_spec(TypographyRole.DISPLAY, ctx.dna, content_density)
        b_m = resolve_region_bounds(1, t_span, content_row_start, 8)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_data_metric",
            semantic_role=RegionSemanticRole.METRIC_CARD,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=m_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=8,
            bounds=b_m,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=m_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Left Insight Callout below metric
        callout_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        c_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_c = resolve_region_bounds(1, t_span, 17, 10)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_data_insight",
            semantic_role=RegionSemanticRole.KEY_INSIGHT_CALLOUT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=callout_binding,
            quadrant=QuadrantId.BOTTOM_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=17,
            baseline_row_span=10,
            bounds=b_c,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=2,
            typography_spec=c_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Right Chart Canvas (Reserved bounds for Phase 3.3)
        chart_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        chart_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_chart = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_data_chart_canvas",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=chart_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_chart,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=chart_typo,
            surface_token=SurfaceToken.SURFACE_MUTED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 15. FORMULA_VISUAL (Section 15)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.FORMULA_VISUAL:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Left Explanation
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_formula_expl",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Right Formula Display (Prominent formula bounds, >= 14pt floor)
        form_field = "formula" if ctx.content.formula else "primary_takeaway"
        form_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, form_field)
        form_typo = resolve_typography_role_spec(TypographyRole.FORMULA, ctx.dna, content_density)
        b_form = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_formula_display",
            semantic_role=RegionSemanticRole.FORMULA_DISPLAY,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=form_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_form,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.L,
            content_priority=1,
            typography_spec=form_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=BorderToken.THIN,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 16. ANNOTATED_VISUAL
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.ANNOTATED_VISUAL:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Annotations column
        ann_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        ann_typo = resolve_typography_role_spec(TypographyRole.ANNOTATION, ctx.dna, content_density)
        b_ann = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_ann_list",
            semantic_role=RegionSemanticRole.CAPTION,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=ann_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_ann,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=2,
            typography_spec=ann_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Main visual canvas
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_ann_visual",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_vis,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=1,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 17. QUOTE_OR_STATEMENT
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.QUOTE_OR_STATEMENT:
        quote_span = envelope.preferred_text_span
        col_st = 1 + (12 - quote_span) // 2
        # Large quote statement
        quote_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        quote_typo = resolve_typography_role_spec(TypographyRole.QUOTE, ctx.dna, content_density)
        b_quote = resolve_region_bounds(col_st, quote_span, 10, 11)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_quote_body",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=quote_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=col_st,
            grid_col_span=quote_span,
            baseline_row_start=10,
            baseline_row_span=11,
            bounds=b_quote,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.L,
            content_priority=1,
            typography_spec=quote_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Attribution / Author
        attr_field = "callout" if ctx.content.callout else "subtitle"
        attr_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, attr_field)
        attr_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_attr = resolve_region_bounds(col_st + 1, quote_span - 2, 22, 4)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_quote_attr",
            semantic_role=RegionSemanticRole.CAPTION,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=attr_binding,
            quadrant=QuadrantId.BOTTOM_LEFT,
            grid_col_start=col_st + 1,
            grid_col_span=quote_span - 2,
            baseline_row_start=22,
            baseline_row_span=4,
            bounds=b_attr,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=2,
            typography_spec=attr_typo,
        ))

    # ─────────────────────────────────────────────────────────────
    # 18. SUMMARY_GRID
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.SUMMARY_GRID:
        # 2x2 grid of summary cards
        cell_span = 6
        cell_row_span = 9
        row1_start = 8
        row2_start = 18
        cards_data = [
            (1, cell_span, row1_start, QuadrantId.TOP_LEFT, "primary_takeaway"),
            (7, cell_span, row1_start, QuadrantId.TOP_RIGHT, "supporting_points[0]" if ctx.content.supporting_points else "primary_takeaway"),
            (1, cell_span, row2_start, QuadrantId.BOTTOM_LEFT, "supporting_points[1]" if len(ctx.content.supporting_points) > 1 else "primary_takeaway"),
            (7, cell_span, row2_start, QuadrantId.BOTTOM_RIGHT, "callout" if ctx.content.callout else "primary_takeaway"),
        ]
        for idx, (c_col, c_span, c_row, quad, fld) in enumerate(cards_data):
            c_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, fld)
            c_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
            b_cell = resolve_region_bounds(c_col, c_span, c_row, cell_row_span)
            regions.append(ContentRegion(
                region_id=f"{ctx.slide_source_id}_sum_grid_{idx+1}",
                semantic_role=RegionSemanticRole.CARD_CONTAINER,
                safe_zone=LayoutSafeZone.SAFE_CONTENT,
                binding=c_binding,
                quadrant=quad,
                grid_col_start=c_col,
                grid_col_span=c_span,
                baseline_row_start=c_row,
                baseline_row_span=cell_row_span,
                bounds=b_cell,
                alignment=RegionAlignment.LEFT,
                vertical_alignment=VerticalAlignment.TOP,
                padding_token=SpacingToken.M,
                content_priority=2,
                typography_spec=c_typo,
                surface_token=SurfaceToken.SURFACE_ELEVATED,
                border_token=border,
                corner_radius_pt=corner_radius,
            ))

    # ─────────────────────────────────────────────────────────────
    # 19. ASYMMETRIC_EDITORIAL
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.ASYMMETRIC_EDITORIAL:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_edit_text",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.L,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_vis = resolve_region_bounds(t_span + 1, v_span, content_row_start + 2, content_row_span - 3)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_edit_accent",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start + 2,
            baseline_row_span=content_row_span - 3,
            bounds=b_vis,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))

    # ─────────────────────────────────────────────────────────────
    # 20. SYSTEM_ARCHITECTURE (Section 13)
    # ─────────────────────────────────────────────────────────────
    elif layout == Phase3LayoutFamily.SYSTEM_ARCHITECTURE:
        t_span = envelope.preferred_text_span
        v_span = 12 - t_span
        # Architecture Overview / Components panel
        text_binding = ctx.make_binding(SourceKind.SLIDE_CONTENT, ctx.slide_source_id, "primary_takeaway")
        text_typo = resolve_typography_role_spec(TypographyRole.BODY, ctx.dna, content_density)
        b_text = resolve_region_bounds(1, t_span, content_row_start, content_row_span)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_arch_overview",
            semantic_role=RegionSemanticRole.PRIMARY_TEXT,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=text_binding,
            quadrant=QuadrantId.TOP_LEFT,
            grid_col_start=1,
            grid_col_span=t_span,
            baseline_row_start=content_row_start,
            baseline_row_span=content_row_span,
            bounds=b_text,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            padding_token=SpacingToken.S,
            content_priority=1,
            typography_spec=text_typo,
            surface_token=surface,
            border_token=border,
            corner_radius_pt=corner_radius,
        ))
        # Main Diagram Canvas (cols 5..12, rows 8..21)
        vis_binding = ctx.make_binding(SourceKind.VISUAL_SEMANTIC_PACKET, ctx.visual_source_id, "primary_visual_message")
        vis_typo = resolve_typography_role_spec(TypographyRole.CAPTION, ctx.dna, content_density)
        b_arch = resolve_region_bounds(t_span + 1, v_span, content_row_start, 14)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_arch_canvas",
            semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=vis_binding,
            quadrant=QuadrantId.TOP_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=content_row_start,
            baseline_row_span=14,
            bounds=b_arch,
            alignment=RegionAlignment.CENTER,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.M,
            content_priority=2,
            typography_spec=vis_typo,
            surface_token=SurfaceToken.SURFACE_ELEVATED,
            border_token=BorderToken.THIN,
            corner_radius_pt=corner_radius,
        ))
        # Legend / Interface annotations (cols 5..12, rows 23..26)
        leg_binding = ctx.make_binding(
            SourceKind.SLIDE_CONTENT,
            ctx.slide_source_id,
            "supporting_points[0]" if ctx.content.supporting_points else "primary_takeaway",
        )
        leg_typo = resolve_typography_role_spec(TypographyRole.ANNOTATION, ctx.dna, content_density)
        b_leg = resolve_region_bounds(t_span + 1, v_span, 23, 4)
        regions.append(ContentRegion(
            region_id=f"{ctx.slide_source_id}_arch_legend",
            semantic_role=RegionSemanticRole.CAPTION,
            safe_zone=LayoutSafeZone.SAFE_CONTENT,
            binding=leg_binding,
            quadrant=QuadrantId.BOTTOM_RIGHT,
            grid_col_start=t_span + 1,
            grid_col_span=v_span,
            baseline_row_start=23,
            baseline_row_span=4,
            bounds=b_leg,
            alignment=RegionAlignment.LEFT,
            vertical_alignment=VerticalAlignment.MIDDLE,
            padding_token=SpacingToken.XS,
            content_priority=3,
            typography_spec=leg_typo,
            surface_token=SurfaceToken.SURFACE_MUTED,
            border_token=BorderToken.NONE,
            corner_radius_pt=corner_radius,
        ))

    return regions


# ═══════════════════════════════════════════════════════════════
# 6. REGION COLLISION & SAFE ZONE VALIDATOR (Section 17)
# ═══════════════════════════════════════════════════════════════

def validate_plan_regions(
    regions: List[ContentRegion],
    layout_family: Phase3LayoutFamily,
) -> List[str]:
    """
    Validates region collisions, safe zones, and geometric invariants.
    Returns list of structured defect codes if violations exist.
    """
    defects: List[str] = []

    # 1. Collision detection across all region pairs
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            r1 = regions[i]
            r2 = regions[j]

            # Authorized full-bleed background overlay
            if (r1.is_full_bleed or r1.semantic_role == RegionSemanticRole.BLEED_BACKGROUND) and \
               (r2.semantic_role != RegionSemanticRole.BLEED_BACKGROUND):
                continue
            if (r2.is_full_bleed or r2.semantic_role == RegionSemanticRole.BLEED_BACKGROUND) and \
               (r1.semantic_role != RegionSemanticRole.BLEED_BACKGROUND):
                continue

            if detect_region_collision(r1.bounds, r2.bounds):
                defects.append(DEFECT_REGION_COLLISION)

    # 2. Safe zone containment and full-bleed text violations
    for r in regions:
        if r.semantic_role in CONTENT_BEARING_ROLES:
            if r.safe_zone == LayoutSafeZone.FULL_BLEED or r.is_full_bleed:
                defects.append(DEFECT_FULL_BLEED_TEXT_VIOLATION)

        if r.safe_zone == LayoutSafeZone.SAFE_TITLE:
            if r.baseline_row_start < 3 or (r.baseline_row_start + r.baseline_row_span - 1 > 7):
                defects.append(DEFECT_SAFE_ZONE_VIOLATION)
        elif r.safe_zone == LayoutSafeZone.SAFE_CONTENT:
            if r.baseline_row_start < 8 or (r.baseline_row_start + r.baseline_row_span - 1 > 27):
                defects.append(DEFECT_SAFE_ZONE_VIOLATION)
        elif r.safe_zone == LayoutSafeZone.SAFE_FOOTER:
            if r.baseline_row_start < 28 or (r.baseline_row_start + r.baseline_row_span - 1 > 30):
                defects.append(DEFECT_SAFE_ZONE_VIOLATION)

        # Dimension checks
        if r.bounds.width_in < 0.5:
            defects.append(DEFECT_TEXT_REGION_TOO_SMALL if r.semantic_role in CONTENT_BEARING_ROLES else DEFECT_VISUAL_REGION_TOO_SMALL)
        if r.bounds.height_in < 0.2:
            defects.append(DEFECT_TEXT_REGION_TOO_SMALL if r.semantic_role in CONTENT_BEARING_ROLES else DEFECT_VISUAL_REGION_TOO_SMALL)

    return list(dict.fromkeys(defects))


# ═══════════════════════════════════════════════════════════════
# 7. PREREQUISITE & SEMANTIC VALIDITY GATES
# ═══════════════════════════════════════════════════════════════

def check_layout_prerequisites(
    layout: Phase3LayoutFamily,
    content: SlideContent,
    packet: VisualSemanticPacket,
) -> Tuple[bool, Optional[str]]:
    """
    Checks if source content supports the semantic structure of a layout family.
    Returns (is_supported, defect_code).
    """
    # 1. Comparison Matrix: requires multiple attributes/entities
    if layout == Phase3LayoutFamily.COMPARISON_MATRIX:
        has_rows = bool(content.comparison_rows and len(content.comparison_rows) >= 2)
        has_targets = bool(packet.comparison_targets and len(packet.comparison_targets) >= 2)
        if not (has_rows or has_targets):
            return False, DEFECT_COMPARISON_STRUCTURE_UNSUPPORTED

    # 2. Card Cluster & Summary Grid: requires grouping
    elif layout in (Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.SUMMARY_GRID):
        items = content.supporting_points or packet.key_entities or content.labels
        if not items or len(items) < 2:
            return False, DEFECT_CARD_GROUPING_INVALID

    # 3. Formula Visual: requires formula source
    elif layout == Phase3LayoutFamily.FORMULA_VISUAL:
        has_form = bool(content.formula and content.formula.strip()) or bool(packet.formula_or_equation and packet.formula_or_equation.strip())
        if not has_form:
            return False, DEFECT_SEMANTIC_ROLE_UNSUPPORTED

    # 4. Process Canvas: requires procedural steps or causal relationships
    elif layout == Phase3LayoutFamily.PROCESS_CANVAS:
        has_steps = bool(content.process_steps and len(content.process_steps) >= 2)
        has_nodes = bool(packet.process_nodes and len(packet.process_nodes) >= 2)
        if not (has_steps or has_nodes):
            return False, DEFECT_PROCESS_STRUCTURE_UNSUPPORTED

    # 4b. Timeline Canvas: requires explicit temporal semantics
    elif layout == Phase3LayoutFamily.TIMELINE_CANVAS:
        if not has_temporal_semantics(packet, content):
            return False, DEFECT_SEMANTIC_ROLE_UNSUPPORTED

    # 5. System Architecture: requires system components or structural relations
    elif layout == Phase3LayoutFamily.SYSTEM_ARCHITECTURE:
        has_comps = bool(packet.system_components and len(packet.system_components) >= 2)
        has_diag = bool(packet.diagram_candidate and packet.diagram_candidate.strip())
        if not (has_comps or has_diag or content.supporting_points):
            return False, DEFECT_SEMANTIC_ROLE_UNSUPPORTED

    return True, None


# ═══════════════════════════════════════════════════════════════
# 8. CORE COMPILER API (Section 1)
# ═══════════════════════════════════════════════════════════════

def compile_slide_layout(
    slide_blueprint: SlideBlueprint,
    slide_content: SlideContent,
    visual_semantic_packet: VisualSemanticPacket,
    design_dna: DesignDNA,
    rhythm_beat: Optional[VisualRhythmBeat],
    composition_input_manifest: CompositionInputManifest,
    text_fit_results: Optional[Dict[str, TextFitResult]] = None,
) -> SlideCompositionPlan:
    """
    Main Phase 3.2C spatial layout compiler.
    Consumes frozen semantic intent and converts it into valid, responsive,
    collision-free composition geometry.
    """
    ctx = LayoutCompilerContext(
        slide_blueprint=slide_blueprint,
        slide_content=slide_content,
        visual_semantic_packet=visual_semantic_packet,
        design_dna=design_dna,
        rhythm_beat=rhythm_beat,
        manifest=composition_input_manifest,
        text_fit_results=text_fit_results,
    )

    # 1. Resolve Initial Layout Family
    initial_family = Phase3LayoutFamily.TEXT_DOMINANT
    if rhythm_beat and rhythm_beat.layout_family:
        initial_family = rhythm_beat.layout_family
    elif visual_semantic_packet.visual_candidates:
        initial_family = visual_semantic_packet.visual_candidates[0].layout_family
    elif slide_blueprint.layout_family:
        if isinstance(slide_blueprint.layout_family, Phase3LayoutFamily):
            initial_family = slide_blueprint.layout_family
        else:
            initial_family = _LEGACY_TO_P3_LAYOUT.get(slide_blueprint.layout_family, Phase3LayoutFamily.TEXT_DOMINANT)

    # 2. Reflow Signal Detection from Phase 3.2B
    requires_reflow = False
    for res in ctx.fit_results.values():
        if res.status == TextFitStatus.REFLOW_REQUIRED or res.status == "reflow_required":
            requires_reflow = True
            break
    if slide_content.fit_risk == "overflow":
        requires_reflow = True

    # 3. Iterative Reflow & Fallback Solver
    candidate_family = initial_family
    current_density = slide_blueprint.content_density
    candidate_envelope = get_parametric_constraint_envelope(
        candidate_family, current_density, visual_semantic_packet.visual_density, design_dna,
        packet=visual_semantic_packet, content=slide_content,
    )
    fallback_steps: List[str] = []

    # Check initial semantic prerequisite and advance fallback chain if unsupported
    supported, defect = check_layout_prerequisites(candidate_family, slide_content, visual_semantic_packet)
    if not supported and defect:
        ctx.quality_defects.append(defect)
        fallback_steps.append(f"{candidate_family.value} -> unsupported structure ({defect})")
        reflow_found = False
        for fallback_fam in candidate_envelope.fallback_chain:
            supp, _ = check_layout_prerequisites(fallback_fam, slide_content, visual_semantic_packet)
            if supp:
                candidate_family = fallback_fam
                candidate_envelope = get_parametric_constraint_envelope(
                    candidate_family, current_density, visual_semantic_packet.visual_density, design_dna,
                    packet=visual_semantic_packet, content=slide_content,
                )
                fallback_steps.append(f"selected supported fallback: {candidate_family.value}")
                reflow_found = True
                break
        if not reflow_found:
            candidate_family = Phase3LayoutFamily.TEXT_DOMINANT
            candidate_envelope = get_parametric_constraint_envelope(
                candidate_family, current_density, visual_semantic_packet.visual_density, design_dna,
                packet=visual_semantic_packet, content=slide_content,
            )
            fallback_steps.append("fallback to text_dominant")

    # If reflow required: attempt expansion then step through fallback chain
    if requires_reflow:
        ctx.quality_defects.append(DEFECT_REFLOW_REQUIRED)
        reflow_success = False

        # Attempt 1: Expand text span within current envelope
        if candidate_envelope.preferred_text_span < candidate_envelope.max_text_span:
            expanded_span = min(candidate_envelope.max_text_span, candidate_envelope.preferred_text_span + 1)
            candidate_envelope.preferred_text_span = expanded_span
            fallback_steps.append(f"{candidate_family.value} expanded to {expanded_span} cols")
            reflow_success = True
        
        # Attempt 2: Fallback chain progression
        if not reflow_success and candidate_envelope.fallback_chain:
            for fallback_fam in candidate_envelope.fallback_chain:
                fallback_steps.append(f"{candidate_family.value} -> {fallback_fam.value}")
                candidate_family = fallback_fam
                candidate_envelope = get_parametric_constraint_envelope(
                    candidate_family, current_density, visual_semantic_packet.visual_density, design_dna,
                    packet=visual_semantic_packet, content=slide_content,
                )
                supp, _ = check_layout_prerequisites(candidate_family, slide_content, visual_semantic_packet)
                if supp:
                    reflow_success = True
                    break

        if not reflow_success:
            ctx.quality_defects.append(DEFECT_REFLOW_CHAIN_EXHAUSTED)

    # 4. Compile Content Regions for the Resolved Family
    compiled_regions = _compile_family_regions(candidate_family, candidate_envelope, ctx)

    # 5. Collision & Safe Zone Validation
    geom_defects = validate_plan_regions(compiled_regions, candidate_family)
    ctx.quality_defects.extend(geom_defects)

    # 6. Calculate Whitespace Metrics
    whitespace_metrics = calculate_whitespace_metrics(
        compiled_regions,
        target_band_min=candidate_envelope.whitespace_target_min,
        target_band_max=candidate_envelope.whitespace_target_max,
    )

    # 7. Rhythm Beat Compliance Evaluation
    compliance = 1.0
    if rhythm_beat:
        if candidate_family == rhythm_beat.layout_family:
            compliance = 1.0
        elif rhythm_beat.visual_weight == VisualWeight.DOMINANT and candidate_family == Phase3LayoutFamily.TEXT_DOMINANT:
            compliance = 0.50
            ctx.quality_defects.append(DEFECT_RHYTHM_DEVIATION)
        else:
            compliance = 0.85
    ctx.rhythm_plan_compliance = compliance

    # 8. Check for Deferred Chart
    has_deferred_chart = bool(
        visual_semantic_packet.chart_candidate or
        (visual_semantic_packet.visual_candidates and
         visual_semantic_packet.visual_candidates[0].asset_type == VisualAssetType.CHART)
    )

    # 9. Map CompositionMode
    mode_map = {
        Phase3LayoutFamily.HERO_CENTER: CompositionMode.FOCAL_HERO,
        Phase3LayoutFamily.HERO_OFFSET: CompositionMode.FOCAL_HERO,
        Phase3LayoutFamily.SPLIT_40_60: CompositionMode.SPLIT_COLUMNS,
        Phase3LayoutFamily.SPLIT_60_40: CompositionMode.SPLIT_COLUMNS,
        Phase3LayoutFamily.VISUAL_DOMINANT: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.TEXT_DOMINANT: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.DIAGRAM_CANVAS: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL: CompositionMode.FULL_BLEED_PANEL,
        Phase3LayoutFamily.CARD_CLUSTER: CompositionMode.CARD_GRID,
        Phase3LayoutFamily.COMPARISON_TWO_COLUMN: CompositionMode.COMPARISON_COLUMNS,
        Phase3LayoutFamily.COMPARISON_MATRIX: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.TIMELINE_CANVAS: CompositionMode.STEP_FLOW,
        Phase3LayoutFamily.PROCESS_CANVAS: CompositionMode.STEP_FLOW,
        Phase3LayoutFamily.DATA_CANVAS: CompositionMode.DATA_DASHBOARD,
        Phase3LayoutFamily.FORMULA_VISUAL: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.ANNOTATED_VISUAL: CompositionMode.STANDARD_CANVAS,
        Phase3LayoutFamily.QUOTE_OR_STATEMENT: CompositionMode.FOCAL_HERO,
        Phase3LayoutFamily.SUMMARY_GRID: CompositionMode.CARD_GRID,
        Phase3LayoutFamily.ASYMMETRIC_EDITORIAL: CompositionMode.ASYMMETRIC_EDITORIAL,
        Phase3LayoutFamily.SYSTEM_ARCHITECTURE: CompositionMode.STANDARD_CANVAS,
    }
    composition_mode = mode_map.get(candidate_family, CompositionMode.STANDARD_CANVAS)

    # 10. Assemble Final SlideCompositionPlan
    rationale_parts = [
        f"Compiled layout {candidate_family.value} (initial: {initial_family.value}).",
        f"Template: {design_dna.theme_family}, Palette: {design_dna.color_palette.primary}.",
    ]
    if fallback_steps:
        rationale_parts.append(f"Reflow fallback steps: {' -> '.join(fallback_steps)}.")
    if ctx.quality_defects:
        rationale_parts.append(f"Defects noted: {', '.join(ctx.quality_defects)}.")

    plan = SlideCompositionPlan(
        slide_no=slide_blueprint.slide_number,
        layout_family=candidate_family,
        composition_mode=composition_mode,
        content_regions=compiled_regions,
        whitespace_metrics=whitespace_metrics,
        visual_weight=candidate_envelope.preferred_visual_ratio,
        hierarchy_levels=3,
        responsive_constraints=ResponsiveConstraints(
            fallback_layout_family=candidate_envelope.fallback_chain[0] if candidate_envelope.fallback_chain else None,
        ),
        composition_confidence=0.95 if not ctx.quality_defects else 0.80,
        planning_rationale=" ".join(rationale_parts),
        template_name=design_dna.theme_family,
        palette_name=design_dna.color_palette.primary,
        formula_render_mode=FormulaRenderMode.UNICODE_TEXT,
        has_deferred_chart=has_deferred_chart,
    )

    # Attach audit properties dynamically to preserve frozen SlideCompositionPlan schema
    object.__setattr__(plan, "quality_defects", ctx.quality_defects)
    object.__setattr__(plan, "fallback_history", fallback_steps)
    object.__setattr__(plan, "rhythm_plan_compliance", ctx.rhythm_plan_compliance)

    return plan
