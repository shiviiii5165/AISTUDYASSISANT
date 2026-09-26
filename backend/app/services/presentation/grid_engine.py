"""
LearnByGenie PPT vNext — Phase 3.2A Grid Engine
=============================================
Deterministic 12-column horizontal grid and 30-module vertical baseline engine.
Resolves exact physical dimensions, validates non-bleed safe margins, full-bleed
regions, and provides parametric layout constraint envelopes.
"""
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from .visual_schemas import Phase3LayoutFamily, ContentDensity
from .composition_schemas import (
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    VERTICAL_MODULE_HEIGHT_IN,
    ResolvedRegionBounds,
    ContentRegion,
    WhitespaceMetrics,
    QuadrantId,
    RegionAlignment,
    RegionSemanticRole,
    LayoutSafeZone,
    ZONE_TOP_MARGIN_START,
    ZONE_TOP_MARGIN_END,
    ZONE_TITLE_START,
    ZONE_TITLE_END,
    ZONE_CONTENT_START,
    ZONE_CONTENT_END,
    ZONE_FOOTER_START,
    ZONE_FOOTER_END,
    ZONE_BOTTOM_MARGIN_START,
    ZONE_BOTTOM_MARGIN_END,
)


# ═══════════════════════════════════════════════════════════════
# 1. GRID CONSTANTS & GEOMETRY
# ═══════════════════════════════════════════════════════════════

TOTAL_CANVAS_AREA_SQ_IN: float = SLIDE_WIDTH_IN * SLIDE_HEIGHT_IN  # 99.9975 ~ 100.0 sq in

# Safe Margins (0.8" L/R, 0.6" T/B)
MARGIN_LEFT_IN: float = 0.800
MARGIN_RIGHT_IN: float = 0.800
MARGIN_TOP_IN: float = 0.600
MARGIN_BOTTOM_IN: float = 0.600

ACTIVE_CONTENT_WIDTH_IN: float = SLIDE_WIDTH_IN - MARGIN_LEFT_IN - MARGIN_RIGHT_IN  # 11.733 in
ACTIVE_CONTENT_HEIGHT_IN: float = SLIDE_HEIGHT_IN - MARGIN_TOP_IN - MARGIN_BOTTOM_IN  # 6.300 in

# 12 Horizontal Columns
GRID_COLUMNS: int = HORIZONTAL_COLUMN_COUNT
GRID_GUTTER_IN: float = 0.250
# Single Column Width: (11.733 - 11 * 0.250) / 12 = 8.983 / 12 = 0.7486 in
GRID_COL_WIDTH_IN: float = (ACTIVE_CONTENT_WIDTH_IN - ((GRID_COLUMNS - 1) * GRID_GUTTER_IN)) / GRID_COLUMNS



# ═══════════════════════════════════════════════════════════════
# 2. COORDINATE RESOLUTION & VALIDATION
# ═══════════════════════════════════════════════════════════════

def resolve_column_left_in(col_start: int) -> float:
    """Computes X position in inches for a 1-indexed column start."""
    if not (1 <= col_start <= GRID_COLUMNS):
        raise ValueError(f"col_start must be between 1 and {GRID_COLUMNS}, got {col_start}")
    return round(MARGIN_LEFT_IN + (col_start - 1) * (GRID_COL_WIDTH_IN + GRID_GUTTER_IN), 3)


def resolve_column_width_in(col_span: int) -> float:
    """Computes width in inches for a given column span."""
    if not (1 <= col_span <= GRID_COLUMNS):
        raise ValueError(f"col_span must be between 1 and {GRID_COLUMNS}, got {col_span}")
    return round(col_span * GRID_COL_WIDTH_IN + (col_span - 1) * GRID_GUTTER_IN, 3)


def resolve_row_top_in(row_start: int) -> float:
    """Computes Y position in inches for a 1-indexed baseline row module."""
    if not (1 <= row_start <= VERTICAL_MODULE_COUNT):
        raise ValueError(f"row_start must be between 1 and {VERTICAL_MODULE_COUNT}, got {row_start}")
    return round((row_start - 1) * VERTICAL_MODULE_HEIGHT_IN, 3)


def resolve_row_height_in(row_span: int) -> float:
    """Computes height in inches for a given baseline row span."""
    if not (1 <= row_span <= VERTICAL_MODULE_COUNT):
        raise ValueError(f"row_span must be between 1 and {VERTICAL_MODULE_COUNT}, got {row_span}")
    return round(row_span * VERTICAL_MODULE_HEIGHT_IN, 3)


def resolve_region_bounds(
    col_start: int,
    col_span: int,
    row_start: int,
    row_span: int,
    is_full_bleed: bool = False,
) -> ResolvedRegionBounds:
    """
    Deterministically computes exact ResolvedRegionBounds in physical inches.
    Enforces full slide containment and returns validated ResolvedRegionBounds.
    """
    if is_full_bleed:
        return ResolvedRegionBounds(
            left_in=0.0,
            top_in=0.0,
            width_in=SLIDE_WIDTH_IN,
            height_in=SLIDE_HEIGHT_IN,
        )

    # Validate grid spans
    if col_start + col_span - 1 > GRID_COLUMNS:
        raise ValueError(f"col_start ({col_start}) + col_span ({col_span}) - 1 exceeds {GRID_COLUMNS}")
    if row_start + row_span - 1 > VERTICAL_MODULE_COUNT:
        raise ValueError(f"row_start ({row_start}) + row_span ({row_span}) - 1 exceeds {VERTICAL_MODULE_COUNT}")

    left = resolve_column_left_in(col_start)
    width = resolve_column_width_in(col_span)
    top = resolve_row_top_in(row_start)
    height = resolve_row_height_in(row_span)

    return ResolvedRegionBounds(
        left_in=left,
        top_in=top,
        width_in=width,
        height_in=height,
    )


def get_safe_zone_module_bounds(safe_zone: LayoutSafeZone) -> Tuple[int, int]:
    """Returns (start_module, end_module) for a given LayoutSafeZone."""
    if safe_zone == LayoutSafeZone.SAFE_TITLE:
        return (ZONE_TITLE_START, ZONE_TITLE_END)
    elif safe_zone == LayoutSafeZone.SAFE_CONTENT:
        return (ZONE_CONTENT_START, ZONE_CONTENT_END)
    elif safe_zone == LayoutSafeZone.SAFE_FOOTER:
        return (ZONE_FOOTER_START, ZONE_FOOTER_END)
    elif safe_zone == LayoutSafeZone.FULL_BLEED:
        return (1, VERTICAL_MODULE_COUNT)
    return (ZONE_CONTENT_START, ZONE_CONTENT_END)


def snap_to_safe_zone_baseline(
    target_row_start: int,
    target_row_span: int,
    safe_zone: LayoutSafeZone = LayoutSafeZone.SAFE_CONTENT,
) -> Tuple[int, int]:
    """
    Snaps baseline coordinates to the nearest valid baseline position inside the permitted zone.
    Baseline grid = alignment authority; Safe zones = containment authority.
    Semantic text/content regions must never resolve outside their permitted safe zones.
    """
    if safe_zone == LayoutSafeZone.FULL_BLEED:
        row_start = max(1, min(target_row_start, VERTICAL_MODULE_COUNT))
        row_span = max(1, min(target_row_span, VERTICAL_MODULE_COUNT - row_start + 1))
        return (row_start, row_span)

    zone_min, zone_max = get_safe_zone_module_bounds(safe_zone)
    max_span = zone_max - zone_min + 1

    # Clamp span to zone capacity
    span = max(1, min(target_row_span, max_span))

    # Clamp start so [start .. start + span - 1] is within [zone_min .. zone_max]
    if target_row_start < zone_min:
        start = zone_min
    elif target_row_start + span - 1 > zone_max:
        start = zone_max - span + 1
    else:
        start = target_row_start

    return (start, span)


def resolve_region_bounds_in_zone(
    col_start: int,
    col_span: int,
    row_start: int,
    row_span: int,
    safe_zone: LayoutSafeZone = LayoutSafeZone.SAFE_CONTENT,
    is_full_bleed: bool = False,
) -> Tuple[ResolvedRegionBounds, int, int]:
    """
    Snaps baseline coordinates to the nearest valid baseline position inside the permitted zone,
    then resolves exact physical inches bounds.
    Returns (ResolvedRegionBounds, snapped_row_start, snapped_row_span).
    """
    if safe_zone == LayoutSafeZone.FULL_BLEED or is_full_bleed:
        bounds = resolve_region_bounds(col_start, col_span, 1, VERTICAL_MODULE_COUNT, is_full_bleed=True)
        return (bounds, 1, VERTICAL_MODULE_COUNT)

    snapped_start, snapped_span = snap_to_safe_zone_baseline(row_start, row_span, safe_zone)
    bounds = resolve_region_bounds(col_start, col_span, snapped_start, snapped_span, is_full_bleed=False)
    return (bounds, snapped_start, snapped_span)



def validate_grid_spans(
    col_start: int,
    col_span: int,
    row_start: int,
    row_span: int,
    is_full_bleed: bool = False,
) -> Tuple[bool, str]:
    """Validates horizontal and vertical grid bounds without throwing."""
    if not (1 <= row_start <= VERTICAL_MODULE_COUNT):
        return False, f"row_start {row_start} out of bounds [1..{VERTICAL_MODULE_COUNT}]"
    if not (1 <= row_span <= VERTICAL_MODULE_COUNT):
        return False, f"row_span {row_span} out of bounds [1..{VERTICAL_MODULE_COUNT}]"
    if row_start + row_span - 1 > VERTICAL_MODULE_COUNT:
        return False, f"Vertical span ({row_start} + {row_span} - 1 = {row_start + row_span - 1}) exceeds {VERTICAL_MODULE_COUNT}"

    if is_full_bleed:
        return True, "Valid full-bleed region"

    if not (1 <= col_start <= GRID_COLUMNS):
        return False, f"col_start {col_start} out of bounds [1..{GRID_COLUMNS}]"
    if not (1 <= col_span <= GRID_COLUMNS):
        return False, f"col_span {col_span} out of bounds [1..{GRID_COLUMNS}]"
    if col_start + col_span - 1 > GRID_COLUMNS:
        return False, f"Column span ({col_start} + {col_span} - 1 = {col_start + col_span - 1}) exceeds {GRID_COLUMNS}"

    return True, "Valid grid placement"


def detect_region_collision(
    r1: ResolvedRegionBounds,
    r2: ResolvedRegionBounds,
    epsilon: float = 0.010,
) -> bool:
    """
    Checks whether two regions overlap spatially.
    Negative gaps or adjacent borders within epsilon are permitted.
    """
    # Overlap occurs if intersection is positive in both dimensions
    no_horizontal_overlap = (
        r1.left_in + r1.width_in <= r2.left_in + epsilon or
        r2.left_in + r2.width_in <= r1.left_in + epsilon
    )
    no_vertical_overlap = (
        r1.top_in + r1.height_in <= r2.top_in + epsilon or
        r2.top_in + r2.height_in <= r1.top_in + epsilon
    )
    return not (no_horizontal_overlap or no_vertical_overlap)


# ═══════════════════════════════════════════════════════════════
# 3. WHITESPACE & AREA OCCUPANCY SOLVER
# ═══════════════════════════════════════════════════════════════

def calculate_whitespace_metrics(
    regions: List[ContentRegion],
    target_band_min: float = 0.20,
    target_band_max: float = 0.65,
) -> WhitespaceMetrics:
    """
    Computes planned geometric region occupancy (bounding-box area coverage)
    and validates role-aware whitespace targets.
    """
    text_roles = {
        RegionSemanticRole.HEADER_TITLE,
        RegionSemanticRole.HEADER_SUBTITLE,
        RegionSemanticRole.PRIMARY_TEXT,
        RegionSemanticRole.SUPPORTING_POINTS,
        RegionSemanticRole.KEY_INSIGHT_CALLOUT,
        RegionSemanticRole.CAPTION,
        RegionSemanticRole.FOOTER_CITATION,
        RegionSemanticRole.CODE_BLOCK,
    }
    visual_roles = {
        RegionSemanticRole.PRIMARY_VISUAL,
        RegionSemanticRole.SECONDARY_VISUAL,
        RegionSemanticRole.FORMULA_DISPLAY,
        RegionSemanticRole.METRIC_CARD,
        RegionSemanticRole.PROCESS_STEP,
        RegionSemanticRole.TIMELINE_NODE,
    }

    text_area = 0.0
    visual_area = 0.0
    occupied_area = 0.0

    # Quadrant tracking (Center point: X=6.666", Y=3.750")
    cx = SLIDE_WIDTH_IN / 2.0
    cy = SLIDE_HEIGHT_IN / 2.0
    quadrant_areas = {
        QuadrantId.TOP_LEFT: 0.0,
        QuadrantId.TOP_RIGHT: 0.0,
        QuadrantId.BOTTOM_LEFT: 0.0,
        QuadrantId.BOTTOM_RIGHT: 0.0,
    }

    for r in regions:
        # Skip bleed backgrounds from content density calculations
        if r.is_full_bleed or r.semantic_role == RegionSemanticRole.BLEED_BACKGROUND:
            continue

        b = r.bounds
        area = b.width_in * b.height_in
        occupied_area += area

        if r.semantic_role in text_roles:
            text_area += area
        elif r.semantic_role in visual_roles:
            visual_area += area
        else:
            text_area += area * 0.5
            visual_area += area * 0.5

        # Quadrant accumulation
        mid_x = b.left_in + (b.width_in / 2.0)
        mid_y = b.top_in + (b.height_in / 2.0)
        if mid_x < cx and mid_y < cy:
            quadrant_areas[QuadrantId.TOP_LEFT] += area
        elif mid_x >= cx and mid_y < cy:
            quadrant_areas[QuadrantId.TOP_RIGHT] += area
        elif mid_x < cx and mid_y >= cy:
            quadrant_areas[QuadrantId.BOTTOM_LEFT] += area
        else:
            quadrant_areas[QuadrantId.BOTTOM_RIGHT] += area

    occupied_ratio = min(1.0, occupied_area / TOTAL_CANVAS_AREA_SQ_IN)
    whitespace_ratio = max(0.0, 1.0 - occupied_ratio)
    text_ratio = min(1.0, text_area / TOTAL_CANVAS_AREA_SQ_IN)
    visual_ratio = min(1.0, visual_area / TOTAL_CANVAS_AREA_SQ_IN)

    # Quadrant weights normalized
    total_q = sum(quadrant_areas.values()) or 1.0
    quadrant_weights = {qid: round(q_area / total_q, 3) for qid, q_area in quadrant_areas.items()}

    is_within_band = (target_band_min <= whitespace_ratio <= target_band_max)

    return WhitespaceMetrics(
        total_canvas_area_sq_in=TOTAL_CANVAS_AREA_SQ_IN,
        region_occupied_area_sq_in=round(occupied_area, 3),
        region_occupied_area_ratio=round(occupied_ratio, 3),
        text_area_ratio=round(text_ratio, 3),
        visual_area_ratio=round(visual_ratio, 3),
        planned_whitespace_ratio=round(whitespace_ratio, 3),
        target_band_min=target_band_min,
        target_band_max=target_band_max,
        is_within_role_band=is_within_band,
        quadrant_weights=quadrant_weights,
    )


# ═══════════════════════════════════════════════════════════════
# 4. PARAMETRIC LAYOUT CONSTRAINT ENVELOPES
# ═══════════════════════════════════════════════════════════════

class LayoutConstraintEnvelope(BaseModel):
    """
    Parametric bounds for layout family compilation.
    Layout families are NOT rigid static templates; they define flexible
    constraint envelopes that adapt to text density and visual requirements.
    """
    layout_family: Phase3LayoutFamily
    preferred_text_col_span: int = Field(..., ge=2, le=12)
    min_text_col_span: int = Field(..., ge=2, le=12)
    max_text_col_span: int = Field(..., ge=2, le=12)
    
    preferred_visual_col_span: int = Field(default=0, ge=0, le=12)
    min_visual_col_span: int = Field(default=0, ge=0, le=12)
    max_visual_col_span: int = Field(default=0, ge=0, le=12)
    
    preferred_visual_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    allowed_alignments: List[RegionAlignment] = Field(default_factory=lambda: [RegionAlignment.LEFT])
    vertical_placement_range: Tuple[int, int] = (8, 27)  # Baseline module range [8..27]
    fallback_chain: List[Phase3LayoutFamily] = Field(default_factory=list)
    whitespace_target_min: float = 0.25
    whitespace_target_max: float = 0.55


def get_layout_constraint_envelope(
    layout: Phase3LayoutFamily,
    density: ContentDensity = ContentDensity.MEDIUM,
) -> LayoutConstraintEnvelope:
    """
    Returns the parametric constraint envelope for any of the 20 layout families,
    dynamically adjusting spans according to content density.
    """
    if layout == Phase3LayoutFamily.SPLIT_40_60:
        # Preferred 5 text / 7 visual; adapts to 6/6 under high text density
        pref_text = 6 if density == ContentDensity.HIGH else 5
        pref_vis = 6 if density == ContentDensity.HIGH else 7
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=pref_text,
            min_text_col_span=4,
            max_text_col_span=7,
            preferred_visual_col_span=pref_vis,
            min_visual_col_span=5,
            max_visual_col_span=8,
            preferred_visual_ratio=0.58,
            fallback_chain=[Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.TEXT_DOMINANT],
            whitespace_target_min=0.25,
            whitespace_target_max=0.45,
        )

    elif layout == Phase3LayoutFamily.SPLIT_60_40:
        pref_text = 8 if density == ContentDensity.HIGH else 7
        pref_vis = 4 if density == ContentDensity.HIGH else 5
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=pref_text,
            min_text_col_span=6,
            max_text_col_span=9,
            preferred_visual_col_span=pref_vis,
            min_visual_col_span=3,
            max_visual_col_span=6,
            preferred_visual_ratio=0.40,
            fallback_chain=[Phase3LayoutFamily.TEXT_DOMINANT],
            whitespace_target_min=0.25,
            whitespace_target_max=0.45,
        )

    elif layout == Phase3LayoutFamily.SYSTEM_ARCHITECTURE:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=4,
            min_text_col_span=3,
            max_text_col_span=5,
            preferred_visual_col_span=8,
            min_visual_col_span=7,
            max_visual_col_span=9,
            preferred_visual_ratio=0.67,
            fallback_chain=[Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.SPLIT_40_60],
            whitespace_target_min=0.20,
            whitespace_target_max=0.40,
        )

    elif layout == Phase3LayoutFamily.PROCESS_CANVAS:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=12,
            min_text_col_span=10,
            max_text_col_span=12,
            preferred_visual_col_span=12,
            min_visual_col_span=8,
            max_visual_col_span=12,
            preferred_visual_ratio=0.50,
            fallback_chain=[Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.CARD_CLUSTER],
            whitespace_target_min=0.25,
            whitespace_target_max=0.45,
        )

    elif layout == Phase3LayoutFamily.FORMULA_VISUAL:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=6,
            min_text_col_span=5,
            max_text_col_span=7,
            preferred_visual_col_span=6,
            min_visual_col_span=5,
            max_visual_col_span=7,
            preferred_visual_ratio=0.50,
            fallback_chain=[Phase3LayoutFamily.SPLIT_50_50 if hasattr(Phase3LayoutFamily, 'SPLIT_50_50') else Phase3LayoutFamily.SPLIT_40_60],
            whitespace_target_min=0.30,
            whitespace_target_max=0.50,
        )

    elif layout == Phase3LayoutFamily.HERO_CENTER:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=10,
            min_text_col_span=8,
            max_text_col_span=12,
            preferred_visual_col_span=0,
            min_visual_col_span=0,
            max_visual_col_span=4,
            preferred_visual_ratio=0.10,
            allowed_alignments=[RegionAlignment.CENTER],
            fallback_chain=[Phase3LayoutFamily.TEXT_DOMINANT],
            whitespace_target_min=0.45,
            whitespace_target_max=0.70,
        )

    elif layout == Phase3LayoutFamily.DATA_CANVAS:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=5,
            min_text_col_span=4,
            max_text_col_span=6,
            preferred_visual_col_span=7,
            min_visual_col_span=6,
            max_visual_col_span=8,
            preferred_visual_ratio=0.60,
            fallback_chain=[Phase3LayoutFamily.SPLIT_40_60],
            whitespace_target_min=0.25,
            whitespace_target_max=0.45,
        )

    elif layout == Phase3LayoutFamily.ASYMMETRIC_EDITORIAL:
        return LayoutConstraintEnvelope(
            layout_family=layout,
            preferred_text_col_span=7,
            min_text_col_span=6,
            max_text_col_span=8,
            preferred_visual_col_span=5,
            min_visual_col_span=4,
            max_visual_col_span=6,
            preferred_visual_ratio=0.40,
            fallback_chain=[Phase3LayoutFamily.SPLIT_60_40],
            whitespace_target_min=0.35,
            whitespace_target_max=0.55,
        )

    # General fallback constraint envelope for all other layout families
    return LayoutConstraintEnvelope(
        layout_family=layout,
        preferred_text_col_span=6,
        min_text_col_span=4,
        max_text_col_span=12,
        preferred_visual_col_span=6,
        min_visual_col_span=0,
        max_visual_col_span=8,
        preferred_visual_ratio=0.50,
        fallback_chain=[Phase3LayoutFamily.TEXT_DOMINANT],
        whitespace_target_min=0.25,
        whitespace_target_max=0.55,
    )
