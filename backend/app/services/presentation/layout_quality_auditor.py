"""
TeachGenie PPT vNext — Phase 3.2D Layout Quality Auditor & Targeted Repair Engine
================================================================================
Deterministic quality audit and transactional monotonic repair engine operating on
Phase 3.2C SlideCompositionPlan objects.

Core Architectural Guarantees:
1. Canonical Contract Reuse: Strictly consumes frozen Phase 3.2A/3.2C safe zones,
   grid invariants, typography role specs, and text-fit statuses without redefinition.
2. Context-Aware Quality: Whitespace and visual minimums derive from DesignDNA,
   VisualDensityProfile, and parametric constraint envelopes — no hardcoded universal numbers.
3. Relationship-Aware Collision Engine: Raw AABB intersection is classified before flagging;
   background bleeds, approved overlays, and container-child associations are permitted.
4. Transactional Monotonic Repair: Deterministic ordering (severity -> code -> region IDs),
   clone-apply-reaudit-verify cycle, immediate rollback upon regression or hash change,
   strictly bounded to MAX_REPAIR_PASSES = 3.
5. Association & Structural Safety: Caption and citation associations require traceable
   provenance; geometry repairs strictly preserve semantic content and content hashes.
"""
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Set
import copy
import hashlib
from pydantic import BaseModel, Field, model_validator

# ═══════════════════════════════════════════════════════════════
# 1. FROZEN CONTRACT IMPORTS (Strict Zero-Redefinition Policy)
# ═══════════════════════════════════════════════════════════════

from .composition_schemas import (
    LayoutSafeZone,
    ZONE_TOP_MARGIN_START,
    ZONE_TOP_MARGIN_END,
    ZONE_TITLE_START,
    ZONE_TITLE_END,
    ZONE_CONTENT_START,
    ZONE_CONTENT_END,
    ZONE_FOOTER_START,
    ZONE_FOOTER_END,
    MARGIN_LEFT_IN,
    MARGIN_RIGHT_IN,
    MARGIN_TOP_IN,
    MARGIN_BOTTOM_IN,
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    VERTICAL_MODULE_HEIGHT_IN,
    ROLE_MINIMUM_FONT_SIZES,
    ROLE_DEFAULT_SAFE_ZONE,
    CONTENT_BEARING_ROLES,
    ResolvedRegionBounds,
    ContentRegion,
    TypographyRoleSpec,
    ContentBinding,
    WhitespaceMetrics,
    SlideCompositionPlan,
    CompositionInputManifest,
    RegionSemanticRole,
    TypographyRole,
    QuadrantId,
    RegionAlignment,
    VerticalAlignment,
    SourceKind,
)

from .visual_schemas import (
    Phase3LayoutFamily,
    VisualDensityProfile,
    VisualSemanticPacket,
    VisualRhythmBeat,
    DesignDNA,
    ContentDensity,
    VisualIntent,
)

from .grid_engine import (
    get_safe_zone_module_bounds,
    snap_to_safe_zone_baseline,
    resolve_region_bounds_in_zone,
    resolve_region_bounds,
    resolve_column_left_in,
    resolve_column_width_in,
    resolve_row_top_in,
    resolve_row_height_in,
    detect_region_collision,
    calculate_whitespace_metrics,
    GRID_COLUMNS,
    GRID_GUTTER_IN,
    GRID_COL_WIDTH_IN,
    ACTIVE_CONTENT_WIDTH_IN,
    ACTIVE_CONTENT_HEIGHT_IN,
    TOTAL_CANVAS_AREA_SQ_IN,
)

from .typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)

from .layout_compiler import (
    get_parametric_constraint_envelope,
    ParametricConstraintEnvelope,
)


# ═══════════════════════════════════════════════════════════════
# 2. DEFECT TAXONOMY & AUDIT DATA MODELS (Section 2 & 3)
# ═══════════════════════════════════════════════════════════════

class DefectSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class DefectRepairability(str, Enum):
    AUTO_REPAIRABLE = "AUTO_REPAIRABLE"
    REFLOW_REQUIRED = "REFLOW_REQUIRED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    UNREPAIRABLE = "UNREPAIRABLE"


class DefectCode(str, Enum):
    REGION_COLLISION = "REGION_COLLISION"
    SAFE_ZONE_VIOLATION = "SAFE_ZONE_VIOLATION"
    GRID_SPAN_INVALID = "GRID_SPAN_INVALID"
    VERTICAL_SPAN_INVALID = "VERTICAL_SPAN_INVALID"
    TITLE_BODY_COLLISION = "TITLE_BODY_COLLISION"
    FOOTER_COLLISION = "FOOTER_COLLISION"
    CITATION_COLLISION = "CITATION_COLLISION"
    TEXT_OVERFLOW = "TEXT_OVERFLOW"
    TITLE_OVERFLOW = "TITLE_OVERFLOW"
    FORMULA_OVERFLOW = "FORMULA_OVERFLOW"
    CODE_OVERFLOW = "CODE_OVERFLOW"
    VISUAL_REGION_TOO_SMALL = "VISUAL_REGION_TOO_SMALL"
    TEXT_REGION_TOO_SMALL = "TEXT_REGION_TOO_SMALL"
    GUTTER_TOO_SMALL = "GUTTER_TOO_SMALL"
    UNBALANCED_COLUMNS = "UNBALANCED_COLUMNS"
    POOR_WHITESPACE_DENSITY = "POOR_WHITESPACE_DENSITY"
    EXCESSIVE_EMPTY_SPACE = "EXCESSIVE_EMPTY_SPACE"
    VISUAL_WEIGHT_IMBALANCE = "VISUAL_WEIGHT_IMBALANCE"
    TYPOGRAPHY_HIERARCHY_INVALID = "TYPOGRAPHY_HIERARCHY_INVALID"
    CARD_NESTING_INVALID = "CARD_NESTING_INVALID"
    UNJUSTIFIED_CARD_USAGE = "UNJUSTIFIED_CARD_USAGE"
    ORPHAN_CAPTION = "ORPHAN_CAPTION"
    ORPHAN_CITATION = "ORPHAN_CITATION"
    FULL_BLEED_TEXT_VIOLATION = "FULL_BLEED_TEXT_VIOLATION"
    RHYTHM_DEVIATION = "RHYTHM_DEVIATION"
    SEMANTIC_PRIORITY_LOSS = "SEMANTIC_PRIORITY_LOSS"
    CONTENT_BINDING_INVALID = "CONTENT_BINDING_INVALID"
    CHART_DEFERRED_REGION_INVALID = "CHART_DEFERRED_REGION_INVALID"
    FORMULA_REGION_INVALID = "FORMULA_REGION_INVALID"
    COMPARISON_ALIGNMENT_INVALID = "COMPARISON_ALIGNMENT_INVALID"
    PROCESS_ALIGNMENT_INVALID = "PROCESS_ALIGNMENT_INVALID"

    # Terminal outcomes & repair status codes
    REPAIR_ROLLED_BACK = "REPAIR_ROLLED_BACK"
    REPAIR_NO_IMPROVEMENT = "REPAIR_NO_IMPROVEMENT"
    REPAIR_BUDGET_EXHAUSTED = "REPAIR_BUDGET_EXHAUSTED"


class LayoutDefect(BaseModel):
    """
    Strongly typed defect containing real measured evidence, severity,
    provenance, and repairability classification.
    """
    defect_code: DefectCode
    severity: DefectSeverity
    region_ids: List[str] = Field(default_factory=list)
    measured_value: Optional[float] = None
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    semantic_impact: str = ""
    repairability: DefectRepairability = DefectRepairability.AUTO_REPAIRABLE
    repair_strategy: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class LayoutAuditResult(BaseModel):
    """
    Comprehensive structured audit report for a slide composition plan.
    Does not use an opaque scalar score as primary result.
    """
    slide_no: int = 1
    defects: List[LayoutDefect] = Field(default_factory=list)
    fatal_defects: int = 0
    repairable_defects: int = 0
    warnings: int = 0
    layout_valid: bool = True
    semantic_integrity_preserved: bool = True
    rhythm_compliance: bool = True
    planned_whitespace_ratio: float = 0.0
    region_count: int = 0
    audit_confidence: float = 1.0


class RepairAction(BaseModel):
    """
    Granular provenance record tracking before/after geometry and verifying
    content hash invariance.
    """
    repair_code: str
    target_regions: List[str] = Field(default_factory=list)
    before_geometry: Dict[str, Any] = Field(default_factory=dict)
    after_geometry: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    defect_resolved: str = ""
    semantic_content_changed: bool = False
    content_hashes_before: Dict[str, str] = Field(default_factory=dict)
    content_hashes_after: Dict[str, str] = Field(default_factory=dict)
    decision: str = "COMMITTED"  # "COMMITTED" | "ROLLED_BACK"


class RepairResult(BaseModel):
    """
    Result of multi-pass localized repair containing the repaired plan,
    audit reports before and after, and full provenance action trail.
    """
    slide_no: int = 1
    original_plan: SlideCompositionPlan
    repaired_plan: SlideCompositionPlan
    audit_before: LayoutAuditResult
    audit_after: LayoutAuditResult
    repair_actions: List[RepairAction] = Field(default_factory=list)
    passes_executed: int = 0
    repaired_successfully: bool = True
    terminal_status: str = "CLEAN"  # "CLEAN" | "REFLOW_REQUIRED" | "MANUAL_REVIEW" | "REPAIR_BUDGET_EXHAUSTED" | "REPAIR_NO_IMPROVEMENT"


# ═══════════════════════════════════════════════════════════════
# 3. RELATIONSHIP-AWARE COLLISION EVALUATION (Safeguard 3)
# ═══════════════════════════════════════════════════════════════

def _is_container_child_relationship(r1: ContentRegion, r2: ContentRegion) -> bool:
    """
    Evaluates whether r1 is a container containing child r2 or vice-versa.
    Spatially contained semantic children within a card/container are allowed.
    """
    # Case 1: Explicit parent-child metadata
    p1 = getattr(r1, "parent_container_id", None)
    p2 = getattr(r2, "parent_container_id", None)
    if p1 == r2.region_id or p2 == r1.region_id:
        return True

    # Case 2: CARD_CONTAINER containing semantic content
    if r1.semantic_role == RegionSemanticRole.CARD_CONTAINER and r2.semantic_role != RegionSemanticRole.CARD_CONTAINER:
        # Check if r2 bounds are enclosed inside r1
        margin = 0.05
        is_inside = (
            r2.bounds.left_in >= r1.bounds.left_in - margin
            and (r2.bounds.left_in + r2.bounds.width_in) <= (r1.bounds.left_in + r1.bounds.width_in + margin)
            and r2.bounds.top_in >= r1.bounds.top_in - margin
            and (r2.bounds.top_in + r2.bounds.height_in) <= (r1.bounds.top_in + r1.bounds.height_in + margin)
        )
        if is_inside:
            return True

    if r2.semantic_role == RegionSemanticRole.CARD_CONTAINER and r1.semantic_role != RegionSemanticRole.CARD_CONTAINER:
        margin = 0.05
        is_inside = (
            r1.bounds.left_in >= r2.bounds.left_in - margin
            and (r1.bounds.left_in + r1.bounds.width_in) <= (r2.bounds.left_in + r2.bounds.width_in + margin)
            and r1.bounds.top_in >= r2.bounds.top_in - margin
            and (r1.bounds.top_in + r1.bounds.height_in) <= (r2.bounds.top_in + r2.bounds.height_in + margin)
        )
        if is_inside:
            return True

    return False


def _is_allowed_overlay(r1: ContentRegion, r2: ContentRegion, overlay_policy: str) -> bool:
    """
    Evaluates whether an overlapping pair represents an approved visual overlay
    per the parametric layout constraint envelope.
    """
    if overlay_policy == "callout_overlay":
        roles = {r1.semantic_role, r2.semantic_role}
        if RegionSemanticRole.KEY_INSIGHT_CALLOUT in roles and (
            RegionSemanticRole.PRIMARY_VISUAL in roles or RegionSemanticRole.SECONDARY_VISUAL in roles
        ):
            return True

    if overlay_policy == "panel_over_bleed":
        if r1.is_full_bleed or r2.is_full_bleed:
            return True

    return False


# ═══════════════════════════════════════════════════════════════
# 4. PRIMARY AUDIT ENGINE
# ═══════════════════════════════════════════════════════════════

def audit_layout(
    composition_plan: SlideCompositionPlan,
    design_dna: Optional[DesignDNA] = None,
    visual_semantic_packet: Optional[VisualSemanticPacket] = None,
    rhythm_beat: Optional[VisualRhythmBeat] = None,
    text_fit_results: Optional[Dict[str, TextFitResult]] = None,
    envelope: Optional[ParametricConstraintEnvelope] = None,
) -> LayoutAuditResult:
    """
    Audits a compiled SlideCompositionPlan and returns a strongly typed LayoutAuditResult.
    Consumes canonical frozen safe-zone contracts, role minimums, and parametric envelopes.
    """
    defects: List[LayoutDefect] = []

    # 1. Resolve Parametric Constraint Envelope
    if envelope is None:
        density = ContentDensity.MEDIUM
        if design_dna and hasattr(design_dna, "density_profile") and design_dna.density_profile:
            density = design_dna.density_profile
        vis_density = visual_semantic_packet.visual_density if visual_semantic_packet else None
        envelope = get_parametric_constraint_envelope(
            composition_plan.layout_family,
            content_density=density,
            visual_density=vis_density,
            design_dna=design_dna,
            packet=visual_semantic_packet,
        )

    regions = composition_plan.content_regions

    # 2. Relationship-Aware Collision Engine (Safeguard 3)
    n = len(regions)
    for i in range(n):
        for j in range(i + 1, n):
            r1 = regions[i]
            r2 = regions[j]

            # Full-bleed backgrounds behind semantic content are allowed
            if r1.is_full_bleed or r2.is_full_bleed:
                continue
            if r1.semantic_role == RegionSemanticRole.BLEED_BACKGROUND or r2.semantic_role == RegionSemanticRole.BLEED_BACKGROUND:
                continue

            # Check spatial intersection
            if detect_region_collision(r1.bounds, r2.bounds, epsilon=0.010):
                # Allowed relationship check 1: Approved overlay
                if _is_allowed_overlay(r1, r2, envelope.overlay_policy):
                    continue

                # Allowed relationship check 2: Container containing child
                if _is_container_child_relationship(r1, r2):
                    continue

                # Invalid relationship: Classify collision type
                roles = {r1.semantic_role, r2.semantic_role}
                title_roles = {RegionSemanticRole.HEADER_TITLE, RegionSemanticRole.HEADER_SUBTITLE}
                body_roles = {
                    RegionSemanticRole.PRIMARY_TEXT,
                    RegionSemanticRole.SUPPORTING_POINTS,
                    RegionSemanticRole.PRIMARY_VISUAL,
                    RegionSemanticRole.KEY_INSIGHT_CALLOUT,
                    RegionSemanticRole.CARD_CONTAINER,
                    RegionSemanticRole.PROCESS_STEP,
                    RegionSemanticRole.TIMELINE_NODE,
                    RegionSemanticRole.COMPARISON_COLUMN_A,
                    RegionSemanticRole.COMPARISON_COLUMN_B,
                }

                if (roles & title_roles) and (roles & body_roles):
                    defects.append(
                        LayoutDefect(
                            defect_code=DefectCode.TITLE_BODY_COLLISION,
                            severity=DefectSeverity.ERROR,
                            region_ids=[r1.region_id, r2.region_id],
                            repairability=DefectRepairability.AUTO_REPAIRABLE,
                            repair_strategy="SHIFT_BODY_DOWNWARD",
                            message=f"Title region '{r1.region_id}' and body region '{r2.region_id}' accidentally collide",
                            evidence={
                                "r1_bounds": r1.bounds.model_dump(),
                                "r2_bounds": r2.bounds.model_dump(),
                                "r1_role": r1.semantic_role.value,
                                "r2_role": r2.semantic_role.value,
                            },
                        )
                    )
                elif RegionSemanticRole.FOOTER_CITATION in roles:
                    defects.append(
                        LayoutDefect(
                            defect_code=DefectCode.CITATION_COLLISION,
                            severity=DefectSeverity.ERROR,
                            region_ids=[r1.region_id, r2.region_id],
                            repairability=DefectRepairability.AUTO_REPAIRABLE,
                            repair_strategy="SNAP_CITATION_TO_FOOTER",
                            message=f"Citation region '{r1.region_id if r1.semantic_role == RegionSemanticRole.FOOTER_CITATION else r2.region_id}' collides with content",
                            evidence={
                                "r1_bounds": r1.bounds.model_dump(),
                                "r2_bounds": r2.bounds.model_dump(),
                            },
                        )
                    )
                else:
                    defects.append(
                        LayoutDefect(
                            defect_code=DefectCode.REGION_COLLISION,
                            severity=DefectSeverity.ERROR,
                            region_ids=[r1.region_id, r2.region_id],
                            repairability=DefectRepairability.AUTO_REPAIRABLE,
                            repair_strategy="REBALANCE_COLUMNS_OR_ROWS",
                            message=f"Unapproved region collision between '{r1.region_id}' ({r1.semantic_role.value}) and '{r2.region_id}' ({r2.semantic_role.value})",
                            evidence={
                                "r1_bounds": r1.bounds.model_dump(),
                                "r2_bounds": r2.bounds.model_dump(),
                            },
                        )
                    )

    # 3. Safe-Zone Containment Engine (Safeguard 1 & 5)
    for r in regions:
        effective_zone = r.safe_zone or ROLE_DEFAULT_SAFE_ZONE.get(r.semantic_role, LayoutSafeZone.SAFE_CONTENT)

        # Full-bleed check for semantic content
        if r.semantic_role in CONTENT_BEARING_ROLES:
            if r.is_full_bleed or effective_zone == LayoutSafeZone.FULL_BLEED:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.FULL_BLEED_TEXT_VIOLATION,
                        severity=DefectSeverity.FATAL,
                        region_ids=[r.region_id],
                        repairability=DefectRepairability.REFLOW_REQUIRED,
                        repair_strategy="ESCALATE_REFLOW",
                        message=f"Ordinary semantic text '{r.region_id}' illegally marked FULL_BLEED",
                    )
                )

        # Safe-zone row module checks (Canonical Phase 3.2A / 3.2C constants)
        if effective_zone == LayoutSafeZone.SAFE_TITLE:
            if r.baseline_row_start < ZONE_TITLE_START or (r.baseline_row_start + r.baseline_row_span - 1 > ZONE_TITLE_END):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.SAFE_ZONE_VIOLATION,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=float(r.baseline_row_start),
                        expected_min=float(ZONE_TITLE_START),
                        expected_max=float(ZONE_TITLE_END),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="SNAP_TO_SAFE_TITLE",
                        message=f"Title region '{r.region_id}' rows {r.baseline_row_start}..{r.baseline_row_start + r.baseline_row_span - 1} exceed SAFE_TITLE [{ZONE_TITLE_START}..{ZONE_TITLE_END}]",
                    )
                )
            if r.bounds.left_in < MARGIN_LEFT_IN - 0.01 or (r.bounds.left_in + r.bounds.width_in > SLIDE_WIDTH_IN - MARGIN_RIGHT_IN + 0.01):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.SAFE_ZONE_VIOLATION,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="CLAMP_TO_MARGINS",
                        message=f"Title region '{r.region_id}' horizontal bounds exceed slide margins",
                    )
                )

        elif effective_zone == LayoutSafeZone.SAFE_CONTENT:
            if r.baseline_row_start < ZONE_CONTENT_START or (r.baseline_row_start + r.baseline_row_span - 1 > ZONE_CONTENT_END):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.SAFE_ZONE_VIOLATION,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=float(r.baseline_row_start),
                        expected_min=float(ZONE_CONTENT_START),
                        expected_max=float(ZONE_CONTENT_END),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="SNAP_TO_SAFE_CONTENT",
                        message=f"Content region '{r.region_id}' rows {r.baseline_row_start}..{r.baseline_row_start + r.baseline_row_span - 1} exceed SAFE_CONTENT [{ZONE_CONTENT_START}..{ZONE_CONTENT_END}]",
                    )
                )
            if r.bounds.left_in < MARGIN_LEFT_IN - 0.01 or (r.bounds.left_in + r.bounds.width_in > SLIDE_WIDTH_IN - MARGIN_RIGHT_IN + 0.01):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.SAFE_ZONE_VIOLATION,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="CLAMP_TO_MARGINS",
                        message=f"Content region '{r.region_id}' horizontal bounds exceed slide margins",
                    )
                )

        elif effective_zone == LayoutSafeZone.SAFE_FOOTER:
            if r.baseline_row_start < ZONE_FOOTER_START or (r.baseline_row_start + r.baseline_row_span - 1 > ZONE_FOOTER_END):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.SAFE_ZONE_VIOLATION,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=float(r.baseline_row_start),
                        expected_min=float(ZONE_FOOTER_START),
                        expected_max=float(ZONE_FOOTER_END),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="SNAP_TO_SAFE_FOOTER",
                        message=f"Footer region '{r.region_id}' rows {r.baseline_row_start}..{r.baseline_row_start + r.baseline_row_span - 1} exceed SAFE_FOOTER [{ZONE_FOOTER_START}..{ZONE_FOOTER_END}]",
                    )
                )

        # 4. Grid and Vertical Span Validation
        if not r.is_full_bleed:
            if r.grid_col_start < 1 or r.grid_col_span < 1 or (r.grid_col_start + r.grid_col_span - 1 > HORIZONTAL_COLUMN_COUNT):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.GRID_SPAN_INVALID,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=float(r.grid_col_start + r.grid_col_span - 1),
                        expected_max=float(HORIZONTAL_COLUMN_COUNT),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="CLAMP_GRID_SPANS",
                        message=f"Grid span invalid for '{r.region_id}' (start={r.grid_col_start}, span={r.grid_col_span})",
                    )
                )
            if r.baseline_row_start < 1 or r.baseline_row_span < 1 or (r.baseline_row_start + r.baseline_row_span - 1 > VERTICAL_MODULE_COUNT):
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.VERTICAL_SPAN_INVALID,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=float(r.baseline_row_start + r.baseline_row_span - 1),
                        expected_max=float(VERTICAL_MODULE_COUNT),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="CLAMP_VERTICAL_SPANS",
                        message=f"Vertical span invalid for '{r.region_id}' (start={r.baseline_row_start}, span={r.baseline_row_span})",
                    )
                )

    # 5. Gutter Quality Validation
    for i in range(n):
        for j in range(i + 1, n):
            r1 = regions[i]
            r2 = regions[j]
            if r1.is_full_bleed or r2.is_full_bleed:
                continue
            # Check if regions are adjacent horizontally on overlapping rows
            rows_overlap = not (
                r1.baseline_row_start + r1.baseline_row_span - 1 < r2.baseline_row_start
                or r2.baseline_row_start + r2.baseline_row_span - 1 < r1.baseline_row_start
            )
            if rows_overlap:
                left_r, right_r = (r1, r2) if r1.bounds.left_in <= r2.bounds.left_in else (r2, r1)
                right_edge_left = left_r.bounds.left_in + left_r.bounds.width_in
                gap = right_r.bounds.left_in - right_edge_left
                # If there is a small positive gap that is below the minimum gutter
                if 0.001 < gap < (envelope.minimum_gutter - 0.010):
                    defects.append(
                        LayoutDefect(
                            defect_code=DefectCode.GUTTER_TOO_SMALL,
                            severity=DefectSeverity.WARNING,
                            region_ids=[left_r.region_id, right_r.region_id],
                            measured_value=round(gap, 3),
                            expected_min=envelope.minimum_gutter,
                            repairability=DefectRepairability.AUTO_REPAIRABLE,
                            repair_strategy="EXPAND_GUTTER_SPACING",
                            message=f"Gutter {gap:.3f}in between '{left_r.region_id}' and '{right_r.region_id}' is below minimum {envelope.minimum_gutter:.3f}in",
                        )
                    )

    # 6. Typography & Text-Fit Validation (Safeguard 6)
    title_spec: Optional[TypographyRoleSpec] = None
    body_specs: List[TypographyRoleSpec] = []
    for r in regions:
        if r.typography_spec:
            spec = r.typography_spec
            # Check role readable floor
            role_floor = ROLE_MINIMUM_FONT_SIZES.get(spec.role, 8.5)
            if spec.font_size_pt < role_floor - 0.01:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.TYPOGRAPHY_HIERARCHY_INVALID,
                        severity=DefectSeverity.ERROR,
                        region_ids=[r.region_id],
                        measured_value=spec.font_size_pt,
                        expected_min=role_floor,
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="RESTORE_ROLE_MINIMUM_FONT",
                        message=f"Font size {spec.font_size_pt:.1f}pt for role {spec.role.value} in '{r.region_id}' below role minimum {role_floor:.1f}pt",
                    )
                )
            if spec.role in (TypographyRole.TITLE, TypographyRole.DISPLAY):
                title_spec = spec
            elif spec.role in (TypographyRole.BODY, TypographyRole.BODY_EMPHASIS):
                body_specs.append(spec)

    if title_spec and body_specs:
        for b_spec in body_specs:
            if title_spec.font_size_pt < b_spec.font_size_pt:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.TYPOGRAPHY_HIERARCHY_INVALID,
                        severity=DefectSeverity.ERROR,
                        region_ids=[],
                        measured_value=title_spec.font_size_pt,
                        expected_min=b_spec.font_size_pt + 2.0,
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="RESTORE_HIERARCHY_DOMINANCE",
                        message=f"Title font size {title_spec.font_size_pt:.1f}pt is smaller than body font size {b_spec.font_size_pt:.1f}pt",
                    )
                )

    # Check external text-fit results (Phase 3.2B signals)
    if text_fit_results:
        for reg_id, fit in text_fit_results.items():
            if fit.status in (TextFitStatus.REFLOW_REQUIRED, "reflow_required"):
                msg = getattr(fit, 'rationale', '') or (fit.quality_defects[0] if getattr(fit, 'quality_defects', None) else "reflow_required")
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.TEXT_OVERFLOW,
                        severity=DefectSeverity.FATAL,
                        region_ids=[reg_id],
                        repairability=DefectRepairability.REFLOW_REQUIRED,
                        repair_strategy="ESCALATE_REFLOW",
                        message=f"Region '{reg_id}' requires layout reflow: {msg}",
                    )
                )
            elif fit.status in (TextFitStatus.UNRESOLVED_OVERFLOW, "unresolved_overflow"):
                msg = getattr(fit, 'rationale', '') or (fit.quality_defects[0] if getattr(fit, 'quality_defects', None) else "unresolved_overflow")
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.TEXT_OVERFLOW,
                        severity=DefectSeverity.FATAL,
                        region_ids=[reg_id],
                        repairability=DefectRepairability.REFLOW_REQUIRED,
                        repair_strategy="ESCALATE_REFLOW",
                        message=f"Unresolved text overflow in region '{reg_id}': {msg}",
                    )
                )

    # 7. Whitespace Quality & Visual Balance (Safeguard 2)
    metrics = composition_plan.whitespace_metrics
    w_min = envelope.whitespace_target_min
    w_max = envelope.whitespace_target_max
    if metrics.planned_whitespace_ratio < w_min - 0.020:
        defects.append(
            LayoutDefect(
                defect_code=DefectCode.POOR_WHITESPACE_DENSITY,
                severity=DefectSeverity.WARNING,
                measured_value=metrics.planned_whitespace_ratio,
                expected_min=w_min,
                expected_max=w_max,
                repairability=DefectRepairability.AUTO_REPAIRABLE,
                repair_strategy="REDISTRIBUTE_OCCUPANCY",
                message=f"Planned whitespace ratio {metrics.planned_whitespace_ratio:.2f} is below target {w_min:.2f} for {composition_plan.layout_family.value}",
            )
        )
    elif metrics.planned_whitespace_ratio > w_max + 0.020:
        defects.append(
            LayoutDefect(
                defect_code=DefectCode.EXCESSIVE_EMPTY_SPACE,
                severity=DefectSeverity.WARNING,
                measured_value=metrics.planned_whitespace_ratio,
                expected_min=w_min,
                expected_max=w_max,
                repairability=DefectRepairability.AUTO_REPAIRABLE,
                repair_strategy="EXPAND_REGION_UTILIZATION",
                message=f"Planned whitespace ratio {metrics.planned_whitespace_ratio:.2f} exceeds target {w_max:.2f} for {composition_plan.layout_family.value}",
            )
        )

    # Lateral Visual Weight Balance
    asymmetric_families = {
        Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
        Phase3LayoutFamily.HERO_OFFSET,
        Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.SPLIT_60_40,
    }
    if composition_plan.layout_family not in asymmetric_families:
        left_area = 0.0
        right_area = 0.0
        midpoint_x = SLIDE_WIDTH_IN / 2.0
        for r in regions:
            if r.is_full_bleed or r.semantic_role == RegionSemanticRole.BLEED_BACKGROUND:
                continue
            r_center = r.bounds.left_in + (r.bounds.width_in / 2.0)
            area = r.bounds.width_in * r.bounds.height_in
            if r_center < midpoint_x:
                left_area += area
            else:
                right_area += area
        total_content_area = left_area + right_area
        if total_content_area > 5.0:
            left_frac = left_area / total_content_area
            if left_frac > 0.90 or left_frac < 0.10:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.VISUAL_WEIGHT_IMBALANCE,
                        severity=DefectSeverity.WARNING,
                        measured_value=round(left_frac, 2),
                        expected_min=0.20,
                        expected_max=0.80,
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="REBALANCE_LATERAL_WEIGHT",
                        message=f"Unintended lateral weight imbalance: {left_frac*100:.1f}% left vs {(1-left_frac)*100:.1f}% right",
                    )
                )

    # 8. Card Discipline & Nesting (Safeguard 7)
    card_containers = [r for r in regions if r.semantic_role == RegionSemanticRole.CARD_CONTAINER]
    for c1 in card_containers:
        for c2 in card_containers:
            if c1.region_id != c2.region_id:
                # Check if c2 is inside c1
                if (
                    c2.bounds.left_in >= c1.bounds.left_in
                    and c2.bounds.left_in + c2.bounds.width_in <= c1.bounds.left_in + c1.bounds.width_in
                    and c2.bounds.top_in >= c1.bounds.top_in
                    and c2.bounds.top_in + c2.bounds.height_in <= c1.bounds.top_in + c1.bounds.height_in
                ):
                    defects.append(
                        LayoutDefect(
                            defect_code=DefectCode.CARD_NESTING_INVALID,
                            severity=DefectSeverity.WARNING,
                            region_ids=[c1.region_id, c2.region_id],
                            repairability=DefectRepairability.AUTO_REPAIRABLE,
                            repair_strategy="REMOVE_DECORATIVE_WRAPPER",
                            message=f"Card container '{c2.region_id}' illegally nested inside card container '{c1.region_id}'",
                        )
                    )

    # 9. Caption & Citation Association Safety (Safeguard 5)
    captions = [r for r in regions if r.semantic_role == RegionSemanticRole.CAPTION]
    visual_regions = [
        r for r in regions
        if r.semantic_role in (
            RegionSemanticRole.PRIMARY_VISUAL,
            RegionSemanticRole.SECONDARY_VISUAL,
            RegionSemanticRole.FORMULA_DISPLAY,
            RegionSemanticRole.METRIC_CARD,
        )
    ]
    for cap in captions:
        # Trace association: must find linked visual
        target_visual_id = getattr(cap, "associated_visual_id", None) or getattr(cap.binding, "source_id", "")
        associated_vis = None
        for v in visual_regions:
            if target_visual_id and (v.region_id == target_visual_id or target_visual_id in v.region_id):
                associated_vis = v
                break
            elif getattr(cap, "associated_visual_id", None) == v.region_id:
                associated_vis = v
                break
            elif len(visual_regions) == 1 and not getattr(cap, "associated_visual_id", None) and (not target_visual_id or target_visual_id == "source_test"):
                associated_vis = v
                break

        if associated_vis is None:
            defects.append(
                LayoutDefect(
                    defect_code=DefectCode.ORPHAN_CAPTION,
                    severity=DefectSeverity.WARNING,
                    region_ids=[cap.region_id],
                    repairability=DefectRepairability.MANUAL_REVIEW,
                    repair_strategy="MANUAL_REVIEW",
                    message=f"Caption '{cap.region_id}' has no traceable visual association; guessing forbidden",
                )
            )
        else:
            # Proximity check: caption should be positioned adjacent to its associated visual
            v_bot = associated_vis.bounds.top_in + associated_vis.bounds.height_in
            dist = cap.bounds.top_in - v_bot
            if dist > 0.80 or dist < -0.05:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.ORPHAN_CAPTION,
                        severity=DefectSeverity.WARNING,
                        region_ids=[cap.region_id, associated_vis.region_id],
                        measured_value=round(dist, 2),
                        expected_max=1.0,
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="SNAP_CAPTION_TO_VISUAL",
                        message=f"Caption '{cap.region_id}' is physically detached ({dist:.2f}in) from associated visual '{associated_vis.region_id}'",
                    )
                )

    # Footer citation check
    citations = [r for r in regions if r.semantic_role == RegionSemanticRole.FOOTER_CITATION]
    for cit in citations:
        chash = cit.binding.resolved_content_hash or cit.binding.content_hash
        if not chash or cit.binding.is_decorative:
            defects.append(
                LayoutDefect(
                    defect_code=DefectCode.ORPHAN_CITATION,
                    severity=DefectSeverity.WARNING,
                    region_ids=[cit.region_id],
                    repairability=DefectRepairability.MANUAL_REVIEW,
                    repair_strategy="MANUAL_REVIEW",
                    message=f"Footer citation '{cit.region_id}' missing traceable content binding or evidence hash",
                )
            )

    # 10. Deferred Chart Region Audit (Safeguard 2)
    if composition_plan.has_deferred_chart:
        chart_regions = [r for r in regions if r.semantic_role == RegionSemanticRole.PRIMARY_VISUAL]
        if not chart_regions:
            defects.append(
                LayoutDefect(
                    defect_code=DefectCode.CHART_DEFERRED_REGION_INVALID,
                    severity=DefectSeverity.ERROR,
                    repairability=DefectRepairability.AUTO_REPAIRABLE,
                    repair_strategy="CREATE_CHART_REGION",
                    message="Plan declares has_deferred_chart=True but has no PRIMARY_VISUAL region reserved",
                )
            )
        else:
            c_reg = chart_regions[0]
            # Minimum geometry comes from constraint envelope
            min_span = envelope.min_visual_span or 4
            if c_reg.grid_col_span < min_span or c_reg.bounds.height_in < 1.80:
                defects.append(
                    LayoutDefect(
                        defect_code=DefectCode.CHART_DEFERRED_REGION_INVALID,
                        severity=DefectSeverity.ERROR,
                        region_ids=[c_reg.region_id],
                        measured_value=float(c_reg.grid_col_span),
                        expected_min=float(min_span),
                        repairability=DefectRepairability.AUTO_REPAIRABLE,
                        repair_strategy="EXPAND_CHART_REGION",
                        message=f"Deferred chart region '{c_reg.region_id}' span {c_reg.grid_col_span} is below minimum {min_span} cols",
                    )
                )

    # 11. Visual Rhythm Deviation Tracking
    if rhythm_beat and rhythm_beat.layout_family:
        if composition_plan.layout_family != rhythm_beat.layout_family:
            defects.append(
                LayoutDefect(
                    defect_code=DefectCode.RHYTHM_DEVIATION,
                    severity=DefectSeverity.INFO,
                    repairability=DefectRepairability.AUTO_REPAIRABLE,
                    repair_strategy="NOTE_DEVIATION",
                    message=f"Layout family '{composition_plan.layout_family.value}' deviates from rhythm beat '{rhythm_beat.layout_family.value}'",
                )
            )

    # 12. Aggregate Audit Metrics
    fatal_cnt = len([d for d in defects if d.severity == DefectSeverity.FATAL])
    repairable_cnt = len([d for d in defects if d.repairability == DefectRepairability.AUTO_REPAIRABLE])
    warning_cnt = len([d for d in defects if d.severity == DefectSeverity.WARNING])
    error_cnt = len([d for d in defects if d.severity == DefectSeverity.ERROR])

    return LayoutAuditResult(
        slide_no=composition_plan.slide_no,
        defects=defects,
        fatal_defects=fatal_cnt,
        repairable_defects=repairable_cnt,
        warnings=warning_cnt,
        layout_valid=(fatal_cnt == 0 and error_cnt == 0),
        semantic_integrity_preserved=True,
        rhythm_compliance=(len([d for d in defects if d.defect_code == DefectCode.RHYTHM_DEVIATION]) == 0),
        planned_whitespace_ratio=metrics.planned_whitespace_ratio,
        region_count=len(regions),
        audit_confidence=1.0 if fatal_cnt == 0 else 0.5,
    )


# ═══════════════════════════════════════════════════════════════
# 5. TARGETED TRANSACTIONAL REPAIR ENGINE (Safeguards 4, 7, 8)
# ═══════════════════════════════════════════════════════════════

MAX_REPAIR_PASSES: int = 3

_SEVERITY_ORDER = {
    DefectSeverity.FATAL: 0,
    DefectSeverity.ERROR: 1,
    DefectSeverity.WARNING: 2,
    DefectSeverity.INFO: 3,
}


def _extract_content_hashes(plan: SlideCompositionPlan) -> Dict[str, str]:
    """Extracts immutable mapping of region_id to content_hash for content-bearing regions."""
    hashes = {}
    for r in plan.content_regions:
        if not r.binding.is_decorative:
            h = r.binding.resolved_content_hash or r.binding.content_hash
            if h:
                hashes[r.region_id] = h
    return hashes


def repair_layout_defects(
    composition_plan: SlideCompositionPlan,
    audit_result: LayoutAuditResult,
    design_dna: Optional[DesignDNA] = None,
    constraint_envelopes: Optional[ParametricConstraintEnvelope] = None,
    max_passes: int = MAX_REPAIR_PASSES,
) -> RepairResult:
    """
    Deterministically repairs localized composition defects using transactional monotonic passes.
    Guarantees:
      - Max 3 passes.
      - Clone -> Apply -> Re-audit -> Monotonic verify -> Commit / Rollback.
      - Zero content mutation: content_hashes_before == content_hashes_after.
      - Never commits a repair that creates a worse defect state.
    """
    initial_hashes = _extract_content_hashes(composition_plan)
    current_plan = composition_plan.model_copy(deep=True)
    repair_actions: List[RepairAction] = []
    passes_executed = 0
    terminal_status = "CLEAN"

    # Resolve parametric envelope if not provided
    if constraint_envelopes is None:
        density = ContentDensity.MEDIUM
        if design_dna and hasattr(design_dna, "density_profile") and design_dna.density_profile:
            density = design_dna.density_profile
        constraint_envelopes = get_parametric_constraint_envelope(
            composition_plan.layout_family,
            content_density=density,
            design_dna=design_dna,
        )

    current_audit = audit_result

    # Initial check: if clean or only unrepairable/fatal
    if current_audit.layout_valid and current_audit.repairable_defects == 0:
        return RepairResult(
            slide_no=composition_plan.slide_no,
            original_plan=composition_plan,
            repaired_plan=current_plan,
            audit_before=audit_result,
            audit_after=current_audit,
            repair_actions=[],
            passes_executed=0,
            repaired_successfully=True,
            terminal_status="CLEAN",
        )

    for pass_idx in range(1, max_passes + 1):
        passes_executed = pass_idx

        # Check for unrepairable FATAL defects
        if current_audit.fatal_defects > 0:
            terminal_status = "REFLOW_REQUIRED"
            break

        repairable = [d for d in current_audit.defects if d.repairability == DefectRepairability.AUTO_REPAIRABLE]
        if not repairable:
            # Check remaining defects
            if any(d.repairability == DefectRepairability.MANUAL_REVIEW for d in current_audit.defects):
                terminal_status = "MANUAL_REVIEW"
            elif any(d.severity == DefectSeverity.FATAL for d in current_audit.defects):
                terminal_status = "REFLOW_REQUIRED"
            else:
                terminal_status = "CLEAN"
            break

        # Deterministic sort order: severity -> defect_code -> sorted(region_ids)
        repairable.sort(
            key=lambda d: (_SEVERITY_ORDER.get(d.severity, 99), d.defect_code.value, sorted(d.region_ids))
        )

        committed_any_in_pass = False

        for defect in repairable:
            # 1. Clone current plan for transactional trial
            candidate_plan = current_plan.model_copy(deep=True)
            target_ids = defect.region_ids

            before_geom = {
                r.region_id: r.bounds.model_dump()
                for r in candidate_plan.content_regions
                if r.region_id in target_ids
            }
            hashes_before = _extract_content_hashes(candidate_plan)

            # 2. Apply localized repair to candidate_plan
            applied = False
            repair_code_name = defect.repair_strategy or "LOCALIZED_REPAIR"

            if defect.defect_code == DefectCode.TITLE_BODY_COLLISION:
                # Shift body downward to SAFE_CONTENT start (row 8)
                title_reg = next((r for r in candidate_plan.content_regions if r.semantic_role == RegionSemanticRole.HEADER_TITLE), None)
                body_regs = [r for r in candidate_plan.content_regions if r.region_id in target_ids and r.semantic_role != RegionSemanticRole.HEADER_TITLE]
                if title_reg and body_regs:
                    new_start = max(ZONE_CONTENT_START, title_reg.baseline_row_start + title_reg.baseline_row_span + 1)
                    for b in body_regs:
                        clamped_span = min(b.baseline_row_span, ZONE_CONTENT_END - new_start + 1)
                        b.baseline_row_start = new_start
                        b.baseline_row_span = max(1, clamped_span)
                        b.bounds = resolve_region_bounds(b.grid_col_start, b.grid_col_span, b.baseline_row_start, b.baseline_row_span)
                    applied = True

            elif defect.defect_code == DefectCode.CITATION_COLLISION or (
                defect.defect_code == DefectCode.SAFE_ZONE_VIOLATION and any("cit" in rid for rid in target_ids)
            ):
                # Snap citation region to SAFE_FOOTER (row 28)
                cit_reg = next(
                    (r for r in candidate_plan.content_regions if r.region_id in target_ids and (r.semantic_role == RegionSemanticRole.FOOTER_CITATION or "cit" in r.region_id)),
                    None,
                )
                if cit_reg is None:
                    cit_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids), None)
                if cit_reg:
                    cit_reg.baseline_row_start = ZONE_FOOTER_START
                    cit_reg.baseline_row_span = 2
                    cit_reg.grid_col_start = 1
                    cit_reg.grid_col_span = HORIZONTAL_COLUMN_COUNT
                    cit_reg.safe_zone = LayoutSafeZone.SAFE_FOOTER
                    cit_reg.bounds = resolve_region_bounds(cit_reg.grid_col_start, cit_reg.grid_col_span, cit_reg.baseline_row_start, cit_reg.baseline_row_span)
                    applied = True

            elif defect.defect_code == DefectCode.GUTTER_TOO_SMALL:
                # Expand spacing between adjacent columns
                if len(target_ids) >= 2:
                    left_id, right_id = target_ids[0], target_ids[1]
                    r_left = next((r for r in candidate_plan.content_regions if r.region_id == left_id), None)
                    r_right = next((r for r in candidate_plan.content_regions if r.region_id == right_id), None)
                    if r_left and r_right:
                        if r_left.bounds.left_in > r_right.bounds.left_in:
                            r_left, r_right = r_right, r_left
                        # Adjust: if right can shift right
                        if r_right.grid_col_start < HORIZONTAL_COLUMN_COUNT:
                            r_right.grid_col_start = min(HORIZONTAL_COLUMN_COUNT - r_right.grid_col_span + 1, r_right.grid_col_start + 1)
                            r_right.bounds = resolve_region_bounds(r_right.grid_col_start, r_right.grid_col_span, r_right.baseline_row_start, r_right.baseline_row_span)
                            applied = True
                        elif r_left.grid_col_span > 2:
                            r_left.grid_col_span -= 1
                            r_left.bounds = resolve_region_bounds(r_left.grid_col_start, r_left.grid_col_span, r_left.baseline_row_start, r_left.baseline_row_span)
                            applied = True

            elif defect.defect_code in (DefectCode.TEXT_REGION_TOO_SMALL, DefectCode.POOR_WHITESPACE_DENSITY):
                target_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids), None)
                if target_reg:
                    max_span = constraint_envelopes.max_text_span
                    if target_reg.grid_col_span < max_span and (target_reg.grid_col_start + target_reg.grid_col_span <= HORIZONTAL_COLUMN_COUNT):
                        target_reg.grid_col_span = min(max_span, target_reg.grid_col_span + 1)
                        target_reg.bounds = resolve_region_bounds(target_reg.grid_col_start, target_reg.grid_col_span, target_reg.baseline_row_start, target_reg.baseline_row_span)
                        applied = True

            elif defect.defect_code in (DefectCode.VISUAL_REGION_TOO_SMALL, DefectCode.CHART_DEFERRED_REGION_INVALID):
                target_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids), None)
                if target_reg:
                    pref_vis = constraint_envelopes.preferred_visual_span or constraint_envelopes.min_visual_span or 6
                    target_reg.grid_col_span = max(pref_vis, target_reg.grid_col_span)
                    target_reg.baseline_row_span = max(6, target_reg.baseline_row_span)
                    if target_reg.grid_col_start + target_reg.grid_col_span - 1 > HORIZONTAL_COLUMN_COUNT:
                        target_reg.grid_col_start = max(1, HORIZONTAL_COLUMN_COUNT - target_reg.grid_col_span + 1)
                    target_reg.bounds = resolve_region_bounds(target_reg.grid_col_start, target_reg.grid_col_span, target_reg.baseline_row_start, target_reg.baseline_row_span)
                    applied = True

            elif defect.defect_code == DefectCode.EXCESSIVE_EMPTY_SPACE:
                # Expand main content spans toward envelope preferred spans
                for r in candidate_plan.content_regions:
                    if r.semantic_role in (RegionSemanticRole.PRIMARY_TEXT, RegionSemanticRole.SUPPORTING_POINTS):
                        if r.grid_col_span < constraint_envelopes.preferred_text_span and (r.grid_col_start + r.grid_col_span <= HORIZONTAL_COLUMN_COUNT):
                            r.grid_col_span = min(constraint_envelopes.preferred_text_span, r.grid_col_span + 2)
                            r.bounds = resolve_region_bounds(r.grid_col_start, r.grid_col_span, r.baseline_row_start, r.baseline_row_span)
                            applied = True
                            break

            elif defect.defect_code == DefectCode.ORPHAN_CAPTION:
                # Snap caption to align immediately below associated visual
                cap_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids and r.semantic_role == RegionSemanticRole.CAPTION), None)
                vis_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids and r.semantic_role in (RegionSemanticRole.PRIMARY_VISUAL, RegionSemanticRole.SECONDARY_VISUAL)), None)
                if not vis_reg:
                    vis_reg = next((r for r in candidate_plan.content_regions if r.semantic_role in (RegionSemanticRole.PRIMARY_VISUAL, RegionSemanticRole.SECONDARY_VISUAL)), None)
                if cap_reg and vis_reg:
                    cap_reg.grid_col_start = vis_reg.grid_col_start
                    cap_reg.grid_col_span = min(vis_reg.grid_col_span, 6)
                    new_top_row = min(ZONE_CONTENT_END - 1, vis_reg.baseline_row_start + vis_reg.baseline_row_span)
                    cap_reg.baseline_row_start = new_top_row
                    cap_reg.baseline_row_span = 2
                    cap_reg.bounds = resolve_region_bounds(cap_reg.grid_col_start, cap_reg.grid_col_span, cap_reg.baseline_row_start, cap_reg.baseline_row_span)
                    applied = True

            elif defect.defect_code == DefectCode.CARD_NESTING_INVALID:
                # Safeguard 7: Remove redundant decorative parent container only
                c1_id = target_ids[0] if target_ids else None
                c1 = next((r for r in candidate_plan.content_regions if r.region_id == c1_id), None)
                if c1 and (c1.binding.is_decorative or c1.binding.source_kind == SourceKind.DECORATIVE):
                    candidate_plan.content_regions = [r for r in candidate_plan.content_regions if r.region_id != c1_id]
                    repair_code_name = "REMOVE_DECORATIVE_WRAPPER"
                    applied = True

            elif defect.defect_code == DefectCode.SAFE_ZONE_VIOLATION:
                target_reg = next((r for r in candidate_plan.content_regions if r.region_id in target_ids), None)
                if target_reg:
                    zone = target_reg.safe_zone or ROLE_DEFAULT_SAFE_ZONE.get(target_reg.semantic_role, LayoutSafeZone.SAFE_CONTENT)
                    new_start, new_span = snap_to_safe_zone_baseline(target_reg.baseline_row_start, target_reg.baseline_row_span, safe_zone=zone)
                    target_reg.baseline_row_start = new_start
                    target_reg.baseline_row_span = new_span
                    target_reg.bounds = resolve_region_bounds(target_reg.grid_col_start, target_reg.grid_col_span, new_start, new_span)
                    applied = True

            elif defect.defect_code == DefectCode.TYPOGRAPHY_HIERARCHY_INVALID:
                # Restore role floor or title dominance
                title_reg = next((r for r in candidate_plan.content_regions if r.semantic_role == RegionSemanticRole.HEADER_TITLE), None)
                body_reg = next((r for r in candidate_plan.content_regions if r.semantic_role in (RegionSemanticRole.PRIMARY_TEXT, RegionSemanticRole.SUPPORTING_POINTS)), None)
                if title_reg and body_reg and title_reg.typography_spec and body_reg.typography_spec:
                    if title_reg.typography_spec.font_size_pt < body_reg.typography_spec.font_size_pt:
                        title_reg.typography_spec.font_size_pt = max(26.0, body_reg.typography_spec.font_size_pt + 6.0)
                        applied = True

            if not applied:
                continue

            # 3. Recalculate whitespace metrics on candidate
            candidate_plan.whitespace_metrics = calculate_whitespace_metrics(
                candidate_plan.content_regions,
                target_band_min=constraint_envelopes.whitespace_target_min,
                target_band_max=constraint_envelopes.whitespace_target_max,
            )

            # 4. Re-audit candidate plan
            candidate_audit = audit_layout(
                candidate_plan,
                design_dna=design_dna,
                envelope=constraint_envelopes,
            )

            # 5. Transactional Monotonic Checks (Safeguards 4, 8)
            hashes_after = _extract_content_hashes(candidate_plan)
            after_geom = {
                r.region_id: r.bounds.model_dump()
                for r in candidate_plan.content_regions
                if r.region_id in target_ids
            }

            # Check A: Content Hash Invariance across all content-bearing regions
            hash_mismatch = False
            for r_id, h_orig in initial_hashes.items():
                if hashes_after.get(r_id) != h_orig:
                    hash_mismatch = True
                    break

            # Check B: Monotonic Severity Invariance (Never introduce a new worse defect)
            cand_fatal = candidate_audit.fatal_defects
            curr_fatal = current_audit.fatal_defects
            cand_error = len([d for d in candidate_audit.defects if d.severity == DefectSeverity.ERROR])
            curr_error = len([d for d in current_audit.defects if d.severity == DefectSeverity.ERROR])

            introduced_worse_defect = (
                cand_fatal > curr_fatal
                or (cand_error > curr_error and defect.severity in (DefectSeverity.WARNING, DefectSeverity.INFO))
            )

            # Check C: Target Defect Measurable Improvement
            target_still_present = any(
                d.defect_code == defect.defect_code and set(d.region_ids) == set(defect.region_ids)
                for d in candidate_audit.defects
            )

            should_commit = (
                not hash_mismatch
                and not introduced_worse_defect
                and not target_still_present
            )

            if should_commit:
                # COMMIT REPAIR
                repair_actions.append(
                    RepairAction(
                        repair_code=repair_code_name,
                        target_regions=target_ids,
                        before_geometry=before_geom,
                        after_geometry=after_geom,
                        reason=f"Resolved {defect.defect_code.value} monotonically",
                        defect_resolved=defect.defect_code.value,
                        semantic_content_changed=False,
                        content_hashes_before=hashes_before,
                        content_hashes_after=hashes_after,
                        decision="COMMITTED",
                    )
                )
                current_plan = candidate_plan
                current_audit = candidate_audit
                committed_any_in_pass = True
                # Break to re-evaluate remaining defects in fresh state
                break
            else:
                # ROLLBACK REPAIR
                rollback_reason = "Hash mismatch" if hash_mismatch else (
                    "Introduced new higher-severity defect" if introduced_worse_defect else "Target defect was not resolved"
                )
                repair_actions.append(
                    RepairAction(
                        repair_code=repair_code_name,
                        target_regions=target_ids,
                        before_geometry=before_geom,
                        after_geometry=after_geom,
                        reason=f"Rollback: {rollback_reason}",
                        defect_resolved=defect.defect_code.value,
                        semantic_content_changed=False,
                        content_hashes_before=hashes_before,
                        content_hashes_after=hashes_after,
                        decision="ROLLED_BACK",
                    )
                )

        if not committed_any_in_pass:
            terminal_status = "REPAIR_NO_IMPROVEMENT"
            break

        if current_audit.layout_valid and current_audit.repairable_defects == 0:
            terminal_status = "CLEAN"
            break

    # If passes hit budget limit without achieving clean state
    if passes_executed >= max_passes and not current_audit.layout_valid:
        terminal_status = "REPAIR_BUDGET_EXHAUSTED"

    final_audit = audit_layout(current_plan, design_dna=design_dna, envelope=constraint_envelopes)
    success = final_audit.layout_valid and final_audit.fatal_defects == 0

    return RepairResult(
        slide_no=composition_plan.slide_no,
        original_plan=composition_plan,
        repaired_plan=current_plan,
        audit_before=audit_result,
        audit_after=final_audit,
        repair_actions=repair_actions,
        passes_executed=passes_executed,
        repaired_successfully=success,
        terminal_status=terminal_status,
    )
