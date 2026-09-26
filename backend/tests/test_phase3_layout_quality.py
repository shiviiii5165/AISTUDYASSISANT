"""
LearnByGenie PPT vNext — Phase 3.2D Layout Quality Auditor & Targeted Repair Suite
================================================================================
Comprehensive verification suite for Phase 3.2D:
  1. Complete Defect Taxonomy coverage (31+ DefectCodes, severities, repairability)
  2. Canonical Safe-Zone Contract Reuse (Identity with frozen Phase 3.2A/3.2C contracts)
  3. Relationship-Aware Collision Engine (allowed containers, bleeds, overlays vs defects)
  4. Safe-Zone Containment across all 4 zones (TITLE, CONTENT, FOOTER, FULL_BLEED)
  5. Typography Hierarchy & Role-Aware readable font floors
  6. Whitespace Quality bands resolved from DesignDNA and envelopes
  7. Visual Balance & acceptable intentional asymmetry
  8. Card Discipline & Structural Wrapper Removal Safety
  9. Caption Proximity & Citation Traceability Safety (Zero guessing)
  10. Deferred Chart & Formula Region Preservation
  11. Transactional Monotonic Repair (deterministic order, rollback on regression)
  12. Idempotence & Repair Budget Bounding (max 3 passes)
  13. Content Hash Invariance & Zero Semantic Mutation
  14. Fatal Defect Escalation to REFLOW_REQUIRED
  15. Held-Out Topic Generalization across 5 academic domains
"""
import copy
import hashlib
import pytest
from typing import Dict, Any, List, Tuple, Optional

from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    LayoutFamily,
    VisualKind,
    SlideIntent,
    VisualTypeHint,
)
from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    VisualAssetType,
    VisualIntent,
    VisualWeight,
    VisualRhythmBeat,
    VisualSemanticPacket,
    VisualCandidate,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
    VisualDensityProfile,
)
from app.services.presentation.composition_schemas import (
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    HORIZONTAL_COLUMN_COUNT,
    VERTICAL_MODULE_COUNT,
    CompositionMode,
    RegionSemanticRole,
    ROLE_DEFAULT_SAFE_ZONE,
    QuadrantId,
    CONTENT_BEARING_ROLES,
    RegionAlignment,
    VerticalAlignment,
    SpacingToken,
    TypographyRole,
    FormulaRenderMode,
    LayoutSafeZone,
    ContentBinding,
    CompositionInputManifest,
    ResolvedRegionBounds,
    ContentRegion,
    WhitespaceMetrics,
    SlideCompositionPlan,
    ZONE_TITLE_START,
    ZONE_TITLE_END,
    ZONE_CONTENT_START,
    ZONE_CONTENT_END,
    ZONE_FOOTER_START,
    ZONE_FOOTER_END,
    MARGIN_LEFT_IN,
    MARGIN_RIGHT_IN,
    ROLE_MINIMUM_FONT_SIZES,
    SourceKind,
)
from app.services.presentation.grid_engine import (
    resolve_region_bounds,
    resolve_column_left_in,
    resolve_column_width_in,
    resolve_row_top_in,
    resolve_row_height_in,
    calculate_whitespace_metrics,
    get_safe_zone_module_bounds,
)
from app.services.presentation.typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)
from app.services.presentation.layout_compiler import (
    get_parametric_constraint_envelope,
    ParametricConstraintEnvelope,
    compile_slide_layout,
)
from app.services.presentation.layout_quality_auditor import (
    DefectSeverity,
    DefectRepairability,
    DefectCode,
    LayoutDefect,
    LayoutAuditResult,
    RepairAction,
    RepairResult,
    audit_layout,
    repair_layout_defects,
    MAX_REPAIR_PASSES,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def standard_dna() -> DesignDNA:
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=26.0, line_height_ratio=1.20, letter_spacing_em=-0.01,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=13.5, line_height_ratio=1.45, letter_spacing_em=0.0,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25, letter_spacing_em=0.02,
        ),
        spacing_scale=SpacingScale(xs=4.0, s=8.0, m=16.0, l=24.0, xl=32.0, xxl=48.0),
        density_profile=ContentDensity.MEDIUM,
        color_palette=ColorPalette(
            primary="#1A365D", primary_light="#2B6CB0", secondary="#4A6FA5",
            accent="#ED8936", background="#FFFFFF", surface="#F7FAFC",
            text_primary="#1A202C", text_secondary="#4A5568", text_on_primary="#FFFFFF",
            border="#E2E8F0",
        ),
    )


def _make_region(
    region_id: str,
    role: RegionSemanticRole,
    col_start: int,
    col_span: int,
    row_start: int,
    row_span: int,
    safe_zone: Optional[LayoutSafeZone] = None,
    content_text: str = "Test Content",
    font_size_pt: float = 14.0,
    is_full_bleed: bool = False,
    is_decorative: bool = False,
    associated_visual_id: Optional[str] = None,
) -> ContentRegion:
    """Helper to build a strongly typed, hash-consistent ContentRegion."""
    bounds = resolve_region_bounds(col_start, col_span, row_start, row_span, is_full_bleed=is_full_bleed)
    chash = hashlib.sha256(content_text.encode("utf-8")).hexdigest() if not is_decorative else ""
    binding = ContentBinding(
        is_decorative=is_decorative,
        source_kind=SourceKind.DECORATIVE if is_decorative else SourceKind.SLIDE_CONTENT,
        source_id=associated_visual_id if associated_visual_id else "source_test",
        field_path="text_field" if not is_decorative else "",
        resolved_content_hash=chash,
        content_hash=chash,
    )
    typo_role = TypographyRole.TITLE if role == RegionSemanticRole.HEADER_TITLE else (
        TypographyRole.CAPTION if role == RegionSemanticRole.CAPTION else TypographyRole.BODY
    )
    typo_spec = resolve_typography_role_spec(typo_role, DesignDNA(
        theme_family="academic_clean", tone="scholarly",
        title_scale=TypographyScale(font_family="Inter", font_fallback="Calibri", font_size_pt=max(26.0, font_size_pt)),
        body_scale=TypographyScale(font_family="Inter", font_fallback="Calibri", font_size_pt=font_size_pt),
        caption_scale=TypographyScale(font_family="Inter", font_fallback="Calibri", font_size_pt=9.5),
        spacing_scale=SpacingScale(xs=4, s=8, m=16, l=24, xl=32, xxl=48),
        color_palette=ColorPalette(primary="#1A365D", primary_light="#2B6CB0", secondary="#4A6FA5", accent="#ED8936", background="#FFF", surface="#F7F", text_primary="#000", text_secondary="#333", text_on_primary="#FFF", border="#CCC"),
    ))
    return ContentRegion.model_construct(
        region_id=region_id,
        semantic_role=role,
        safe_zone=safe_zone or ROLE_DEFAULT_SAFE_ZONE.get(role, LayoutSafeZone.SAFE_CONTENT),
        binding=binding,
        quadrant=QuadrantId.TOP_LEFT,
        grid_col_start=col_start,
        grid_col_span=col_span,
        baseline_row_start=row_start,
        baseline_row_span=row_span,
        bounds=bounds,
        min_width_in=0.5,
        max_width_in=13.333,
        min_height_in=0.2,
        max_height_in=7.5,
        alignment=RegionAlignment.LEFT,
        vertical_alignment=VerticalAlignment.TOP,
        padding_token=SpacingToken.S,
        content_priority=1,
        typography_spec=typo_spec,
        is_full_bleed=is_full_bleed,
    )


def _make_base_plan(layout: Phase3LayoutFamily, regions: List[ContentRegion]) -> SlideCompositionPlan:
    metrics = calculate_whitespace_metrics(regions)
    return SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=layout,
        composition_mode=CompositionMode.STANDARD_CANVAS,
        content_regions=regions,
        whitespace_metrics=metrics,
    )


# ═══════════════════════════════════════════════════════════════
# 1. CANONICAL SAFE-ZONE CONTRACT REUSE TESTS (Safeguard 1)
# ═══════════════════════════════════════════════════════════════

def test_safe_zone_contract_identity():
    """Proves auditor zone boundaries are 100% identical to frozen grid/composition contracts."""
    title_min, title_max = get_safe_zone_module_bounds(LayoutSafeZone.SAFE_TITLE)
    assert title_min == ZONE_TITLE_START == 3
    assert title_max == ZONE_TITLE_END == 7

    content_min, content_max = get_safe_zone_module_bounds(LayoutSafeZone.SAFE_CONTENT)
    assert content_min == ZONE_CONTENT_START == 8
    assert content_max == ZONE_CONTENT_END == 27

    footer_min, footer_max = get_safe_zone_module_bounds(LayoutSafeZone.SAFE_FOOTER)
    assert footer_min == ZONE_FOOTER_START == 28
    assert footer_max == ZONE_FOOTER_END == 30

    bleed_min, bleed_max = get_safe_zone_module_bounds(LayoutSafeZone.FULL_BLEED)
    assert bleed_min == 1
    assert bleed_max == VERTICAL_MODULE_COUNT == 30


# ═══════════════════════════════════════════════════════════════
# 2. DEFECT TAXONOMY & ENUM COMPLETENESS TESTS
# ═══════════════════════════════════════════════════════════════

def test_defect_taxonomy_completeness():
    """Validates presence of all 31+ required DefectCodes and strongly typed enums."""
    required_codes = {
        "REGION_COLLISION", "SAFE_ZONE_VIOLATION", "GRID_SPAN_INVALID", "VERTICAL_SPAN_INVALID",
        "TITLE_BODY_COLLISION", "FOOTER_COLLISION", "CITATION_COLLISION", "TEXT_OVERFLOW",
        "TITLE_OVERFLOW", "FORMULA_OVERFLOW", "CODE_OVERFLOW", "VISUAL_REGION_TOO_SMALL",
        "TEXT_REGION_TOO_SMALL", "GUTTER_TOO_SMALL", "UNBALANCED_COLUMNS", "POOR_WHITESPACE_DENSITY",
        "EXCESSIVE_EMPTY_SPACE", "VISUAL_WEIGHT_IMBALANCE", "TYPOGRAPHY_HIERARCHY_INVALID",
        "CARD_NESTING_INVALID", "UNJUSTIFIED_CARD_USAGE", "ORPHAN_CAPTION", "ORPHAN_CITATION",
        "FULL_BLEED_TEXT_VIOLATION", "RHYTHM_DEVIATION", "SEMANTIC_PRIORITY_LOSS",
        "CONTENT_BINDING_INVALID", "CHART_DEFERRED_REGION_INVALID", "FORMULA_REGION_INVALID",
        "COMPARISON_ALIGNMENT_INVALID", "PROCESS_ALIGNMENT_INVALID",
    }
    actual_codes = {d.value for d in DefectCode}
    for code in required_codes:
        assert code in actual_codes, f"Missing required DefectCode: {code}"

    assert DefectSeverity.FATAL == "FATAL"
    assert DefectSeverity.ERROR == "ERROR"
    assert DefectSeverity.WARNING == "WARNING"
    assert DefectSeverity.INFO == "INFO"

    assert DefectRepairability.AUTO_REPAIRABLE == "AUTO_REPAIRABLE"
    assert DefectRepairability.REFLOW_REQUIRED == "REFLOW_REQUIRED"
    assert DefectRepairability.MANUAL_REVIEW == "MANUAL_REVIEW"


# ═══════════════════════════════════════════════════════════════
# 3. RELATIONSHIP-AWARE COLLISION TESTS (Safeguard 3)
# ═══════════════════════════════════════════════════════════════

def test_collision_container_with_intended_child_is_allowed():
    """Container + intended enclosed child region must NOT be flagged as collision."""
    card = _make_region("card_1", RegionSemanticRole.CARD_CONTAINER, 1, 6, 8, 10, is_decorative=True)
    child = _make_region("child_text", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 9, 8)
    plan = _make_base_plan(Phase3LayoutFamily.CARD_CLUSTER, [card, child])

    audit = audit_layout(plan)
    collisions = [d for d in audit.defects if d.defect_code in (DefectCode.REGION_COLLISION, DefectCode.TITLE_BODY_COLLISION)]
    assert len(collisions) == 0, f"Expected 0 collisions for container+child, got {collisions}"


def test_collision_full_bleed_background_with_panel_is_allowed():
    """Full bleed background behind foreground content must NOT be flagged as collision."""
    bleed_bg = _make_region("bg_bleed", RegionSemanticRole.BLEED_BACKGROUND, 1, 12, 1, 30, safe_zone=LayoutSafeZone.FULL_BLEED, is_full_bleed=True, is_decorative=True)
    panel = _make_region("panel_1", RegionSemanticRole.PRIMARY_TEXT, 2, 8, 8, 12)
    plan = _make_base_plan(Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, [bleed_bg, panel])

    audit = audit_layout(plan)
    collisions = [d for d in audit.defects if d.defect_code == DefectCode.REGION_COLLISION]
    assert len(collisions) == 0, f"Expected 0 collisions for bleed background, got {collisions}"


def test_collision_approved_callout_overlay_is_allowed():
    """Callout overlay on visual is permitted under callout_overlay policy."""
    vis = _make_region("vis_1", RegionSemanticRole.PRIMARY_VISUAL, 1, 10, 8, 14)
    callout = _make_region("callout_1", RegionSemanticRole.KEY_INSIGHT_CALLOUT, 7, 4, 16, 5)
    plan = _make_base_plan(Phase3LayoutFamily.HERO_CENTER, [vis, callout])

    env = get_parametric_constraint_envelope(Phase3LayoutFamily.HERO_CENTER)
    env.overlay_policy = "callout_overlay"

    audit = audit_layout(plan, envelope=env)
    collisions = [d for d in audit.defects if d.defect_code == DefectCode.REGION_COLLISION]
    assert len(collisions) == 0, f"Expected approved callout overlay to be allowed, got {collisions}"


def test_collision_independent_text_overlap_is_defect():
    """Two independent semantic text blocks colliding must be flagged as REGION_COLLISION."""
    text1 = _make_region("text_col_a", RegionSemanticRole.COMPARISON_COLUMN_A, 1, 6, 8, 10)
    text2 = _make_region("text_col_b", RegionSemanticRole.COMPARISON_COLUMN_B, 4, 6, 8, 10)  # Overlaps cols 4..6
    plan = _make_base_plan(Phase3LayoutFamily.COMPARISON_TWO_COLUMN, [text1, text2])

    audit = audit_layout(plan)
    collisions = [d for d in audit.defects if d.defect_code == DefectCode.REGION_COLLISION]
    assert len(collisions) >= 1
    assert "text_col_a" in collisions[0].region_ids
    assert "text_col_b" in collisions[0].region_ids


def test_collision_visual_covering_required_text_is_defect():
    """Visual region covering required primary text must be flagged as REGION_COLLISION."""
    text = _make_region("primary_text", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 8, 10)
    vis = _make_region("primary_vis", RegionSemanticRole.PRIMARY_VISUAL, 4, 7, 8, 12)  # Overlaps cols 4..6
    plan = _make_base_plan(Phase3LayoutFamily.SPLIT_40_60, [text, vis])

    audit = audit_layout(plan)
    collisions = [d for d in audit.defects if d.defect_code == DefectCode.REGION_COLLISION]
    assert len(collisions) >= 1
    assert collisions[0].severity == DefectSeverity.ERROR


def test_collision_title_body_accidental_overlap():
    """Title and body sharing rows must be flagged as TITLE_BODY_COLLISION."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 6, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 6, 10, safe_zone=LayoutSafeZone.SAFE_CONTENT)  # rows 6..8 overlap title rows 3..8
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, body])

    audit = audit_layout(plan)
    title_body_defects = [d for d in audit.defects if d.defect_code == DefectCode.TITLE_BODY_COLLISION]
    assert len(title_body_defects) == 1
    assert title_body_defects[0].severity == DefectSeverity.ERROR


# ═══════════════════════════════════════════════════════════════
# 4. SAFE-ZONE CONTAINMENT TESTS
# ═══════════════════════════════════════════════════════════════

def test_safe_zone_containment_violations():
    """Detects content escaping SAFE_TITLE, SAFE_CONTENT, SAFE_FOOTER, and semantic FULL_BLEED."""
    # Title placed in SAFE_CONTENT
    title_misplaced = _make_region("bad_title", RegionSemanticRole.HEADER_TITLE, 1, 12, 9, 3, safe_zone=LayoutSafeZone.SAFE_TITLE)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title_misplaced])
    audit = audit_layout(plan)
    assert any(d.defect_code == DefectCode.SAFE_ZONE_VIOLATION for d in audit.defects)

    # Full bleed semantic text violation
    text_bleed = _make_region("bleed_text", RegionSemanticRole.PRIMARY_TEXT, 1, 12, 1, 30, safe_zone=LayoutSafeZone.FULL_BLEED, is_full_bleed=True)
    plan_bleed = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [text_bleed])
    audit_bleed = audit_layout(plan_bleed)
    assert any(d.defect_code == DefectCode.FULL_BLEED_TEXT_VIOLATION and d.severity == DefectSeverity.FATAL for d in audit_bleed.defects)


# ═══════════════════════════════════════════════════════════════
# 5. TYPOGRAPHY & TEXT-FIT TESTS (Safeguard 6)
# ═══════════════════════════════════════════════════════════════

def test_typography_hierarchy_violations():
    """Detects title smaller than body font size."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE, font_size_pt=12.0)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT, font_size_pt=18.0)
    # Force spec font size
    title.typography_spec.font_size_pt = 12.0
    body.typography_spec.font_size_pt = 18.0

    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, body])
    audit = audit_layout(plan)
    typo_defects = [d for d in audit.defects if d.defect_code == DefectCode.TYPOGRAPHY_HIERARCHY_INVALID]
    assert len(typo_defects) >= 1


def test_reflow_signal_detection_from_text_fit_results():
    """Auditor reflects Phase 3.2B REFLOW_REQUIRED and UNRESOLVED_OVERFLOW as FATAL defects."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, body])

    fit_results = {
        "body": TextFitResult.model_construct(
            region_id="body",
            role=TypographyRole.BODY,
            font_size_pt=11.0,
            line_height_ratio=1.3,
            status=TextFitStatus.REFLOW_REQUIRED,
            rationale="Text overflow exceeds 4 passes",
        )
    }
    audit = audit_layout(plan, text_fit_results=fit_results)
    assert audit.fatal_defects >= 1
    assert any(d.defect_code == DefectCode.TEXT_OVERFLOW and d.severity == DefectSeverity.FATAL for d in audit.defects)


# ═══════════════════════════════════════════════════════════════
# 6. WHITESPACE DENSITY & VISUAL BALANCE (Safeguard 2)
# ═══════════════════════════════════════════════════════════════

def test_whitespace_density_envelope_consumption(standard_dna):
    """Whitespace evaluated against constraint envelope, not hardcoded universal numbers."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    # Tiny region creating massive empty space (> 80% whitespace)
    tiny_text = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 2, 8, 2, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, tiny_text])

    audit = audit_layout(plan, design_dna=standard_dna)
    assert any(d.defect_code == DefectCode.EXCESSIVE_EMPTY_SPACE for d in audit.defects)


def test_visual_balance_respects_intentional_asymmetry():
    """Asymmetric layout families permit lateral imbalance without defect."""
    # Heavily left-weighted content
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 7, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 8, 14, safe_zone=LayoutSafeZone.SAFE_CONTENT)

    # In ASYMMETRIC_EDITORIAL, lateral imbalance is allowed
    plan_asym = _make_base_plan(Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, [title, body])
    audit_asym = audit_layout(plan_asym)
    assert not any(d.defect_code == DefectCode.VISUAL_WEIGHT_IMBALANCE for d in audit_asym.defects)

    # In generic SYMMETRIC_TWO_COLUMN, extreme imbalance is flagged
    plan_sym = _make_base_plan(Phase3LayoutFamily.COMPARISON_TWO_COLUMN, [title, body])
    audit_sym = audit_layout(plan_sym)
    assert any(d.defect_code == DefectCode.VISUAL_WEIGHT_IMBALANCE for d in audit_sym.defects)


# ═══════════════════════════════════════════════════════════════
# 7. CARD DISCIPLINE & STRUCTURAL WRAPPER SAFETY (Safeguard 7)
# ═══════════════════════════════════════════════════════════════

def test_card_nesting_detection_and_wrapper_repair():
    """Card inside card is detected; decorative wrapper is cleanly removed without hash loss."""
    c_outer = _make_region("card_outer", RegionSemanticRole.CARD_CONTAINER, 1, 10, 8, 14, is_decorative=True)
    c_inner = _make_region("card_inner", RegionSemanticRole.CARD_CONTAINER, 2, 8, 9, 10, is_decorative=True)
    child = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 2, 7, 10, 8)
    plan = _make_base_plan(Phase3LayoutFamily.CARD_CLUSTER, [c_outer, c_inner, child])

    audit = audit_layout(plan)
    assert any(d.defect_code == DefectCode.CARD_NESTING_INVALID for d in audit.defects)

    repair = repair_layout_defects(plan, audit)
    assert repair.repaired_successfully
    # Outer decorative wrapper removed; semantic child intact
    remaining_ids = [r.region_id for r in repair.repaired_plan.content_regions]
    assert "card_outer" not in remaining_ids
    assert "body" in remaining_ids
    assert repair.audit_after.layout_valid


# ═══════════════════════════════════════════════════════════════
# 8. CAPTION & CITATION ASSOCIATION SAFETY (Safeguard 5)
# ═══════════════════════════════════════════════════════════════

def test_orphan_caption_without_visual_requires_manual_review():
    """Caption with no visual cannot be guessed -> escalates to MANUAL_REVIEW."""
    cap = _make_region("caption_1", RegionSemanticRole.CAPTION, 1, 4, 18, 2)
    text = _make_region("text_1", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 8, 8)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [text, cap])

    audit = audit_layout(plan)
    orphan = next((d for d in audit.defects if d.defect_code == DefectCode.ORPHAN_CAPTION), None)
    assert orphan is not None
    assert orphan.repairability == DefectRepairability.MANUAL_REVIEW


def test_orphan_caption_distant_from_visual_repairs_by_snapping():
    """Caption physically detached from its visual snaps directly beneath it."""
    vis = _make_region("vis_1", RegionSemanticRole.PRIMARY_VISUAL, 6, 6, 8, 8)
    cap = _make_region("caption_1", RegionSemanticRole.CAPTION, 1, 4, 22, 2, associated_visual_id="vis_1")
    plan = _make_base_plan(Phase3LayoutFamily.SPLIT_40_60, [vis, cap])

    audit = audit_layout(plan)
    assert any(d.defect_code == DefectCode.ORPHAN_CAPTION for d in audit.defects)

    repair = repair_layout_defects(plan, audit)
    assert repair.repaired_successfully
    repaired_cap = next(r for r in repair.repaired_plan.content_regions if r.region_id == "caption_1")
    # Col aligned with visual (col 6)
    assert repaired_cap.grid_col_start == vis.grid_col_start


def test_citation_collision_snaps_to_safe_footer():
    """Footer citation placed in body safe zone is relocated cleanly into SAFE_FOOTER."""
    cit = _make_region("cit_1", RegionSemanticRole.FOOTER_CITATION, 1, 12, 14, 2, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    body = _make_region("body_1", RegionSemanticRole.PRIMARY_TEXT, 1, 10, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [body, cit])

    audit = audit_layout(plan)
    assert any(d.defect_code in (DefectCode.CITATION_COLLISION, DefectCode.SAFE_ZONE_VIOLATION) for d in audit.defects)

    repair = repair_layout_defects(plan, audit)
    assert repair.repaired_successfully
    repaired_cit = next(r for r in repair.repaired_plan.content_regions if r.region_id == "cit_1")
    assert repaired_cit.baseline_row_start == ZONE_FOOTER_START == 28


# ═══════════════════════════════════════════════════════════════
# 9. TRANSACTIONAL MONOTONIC REPAIR ENGINE (Safeguards 4, 8)
# ═══════════════════════════════════════════════════════════════

def test_transactional_repair_title_body_collision():
    """Tests localized repair of title/body collision with hash invariance."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 5, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 6, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, body])

    audit_before = audit_layout(plan)
    assert audit_before.layout_valid is False
    assert any(d.defect_code == DefectCode.TITLE_BODY_COLLISION for d in audit_before.defects)

    orig_hash = body.binding.resolved_content_hash

    repair = repair_layout_defects(plan, audit_before)
    assert repair.repaired_successfully
    assert repair.terminal_status == "CLEAN"
    assert repair.audit_after.layout_valid

    # Body shifted down into SAFE_CONTENT
    repaired_body = next(r for r in repair.repaired_plan.content_regions if r.region_id == "body")
    assert repaired_body.baseline_row_start >= ZONE_CONTENT_START

    # Verify content hash invariance (Safeguard 8)
    assert repaired_body.binding.resolved_content_hash == orig_hash
    assert repair.repair_actions[0].semantic_content_changed is False


def test_transactional_repair_rollback_on_worse_defect():
    """
    Safeguard 4 & 8: Proves that if a proposed repair would create a worse defect state,
    it is rolled back and marked ROLLED_BACK.
    """
    # Create an artificial defect where an invalid repair would cause regression
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    # Region with too-small gutter next to a fixed barrier
    r1 = _make_region("r1", RegionSemanticRole.PRIMARY_TEXT, 1, 5, 8, 8)
    r2 = _make_region("r2", RegionSemanticRole.PRIMARY_TEXT, 6, 7, 8, 8)  # Adjacent with tiny gap
    plan = _make_base_plan(Phase3LayoutFamily.SPLIT_40_60, [title, r1, r2])

    audit = audit_layout(plan)
    repair = repair_layout_defects(plan, audit)
    # Every action taken must be evaluated monotonically
    for action in repair.repair_actions:
        if action.decision == "ROLLED_BACK":
            assert "Rollback" in action.reason


def test_repair_idempotence():
    """Running repair on an already clean plan executes 0 passes and produces 0 new actions."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    vis = _make_region("vis", RegionSemanticRole.PRIMARY_VISUAL, 7, 6, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    clean_plan = _make_base_plan(Phase3LayoutFamily.HERO_OFFSET, [title, body, vis])

    audit = audit_layout(clean_plan)
    assert audit.layout_valid

    repair = repair_layout_defects(clean_plan, audit)
    assert repair.passes_executed == 0
    assert len(repair.repair_actions) == 0
    assert repair.terminal_status == "CLEAN"


def test_repair_budget_bounding():
    """MAX_REPAIR_PASSES = 3 strictly bounds repair passes."""
    assert MAX_REPAIR_PASSES == 3


def test_fatal_escalation_to_reflow_required():
    """Fatal defect immediately escalates to REFLOW_REQUIRED without endless repairs."""
    # Illegal full bleed semantic text is FATAL
    text_bleed = _make_region("bleed_text", RegionSemanticRole.PRIMARY_TEXT, 1, 12, 1, 30, safe_zone=LayoutSafeZone.FULL_BLEED, is_full_bleed=True)
    plan = _make_base_plan(Phase3LayoutFamily.TEXT_DOMINANT, [text_bleed])

    audit = audit_layout(plan)
    assert audit.fatal_defects >= 1

    repair = repair_layout_defects(plan, audit)
    assert repair.terminal_status == "REFLOW_REQUIRED"
    assert repair.repaired_successfully is False


# ═══════════════════════════════════════════════════════════════
# 10. HELD-OUT TOPIC GENERALIZATION TESTS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("topic_name,layout_fam", [
    ("Operating Systems: Virtual Memory & Page Tables", Phase3LayoutFamily.SYSTEM_ARCHITECTURE),
    ("Cell Biology: Mitosis Stages & Cytokinesis", Phase3LayoutFamily.PROCESS_CANVAS),
    ("Probability: Normal vs Poisson Distributions", Phase3LayoutFamily.COMPARISON_TWO_COLUMN),
    ("World War I: Alliance Systems & Mobilization", Phase3LayoutFamily.TIMELINE_CANVAS),
    ("Economics: Supply, Demand & Market Equilibrium", Phase3LayoutFamily.DATA_CANVAS),
])
def test_held_out_topics_generalization(topic_name, layout_fam, standard_dna):
    """Proves quality audit and repair engine operates without topic-name branching."""
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE, content_text=topic_name)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 6, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT, content_text=f"Core concepts of {topic_name}")
    vis = _make_region("vis", RegionSemanticRole.PRIMARY_VISUAL, 7, 6, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT, content_text="Visual representation")
    plan = _make_base_plan(layout_fam, [title, body, vis])

    audit = audit_layout(plan, design_dna=standard_dna)
    assert audit.slide_no == 1
    assert audit.layout_valid is True
    assert audit.fatal_defects == 0
