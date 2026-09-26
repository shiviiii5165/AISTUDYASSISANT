"""
LearnByGenie PPT vNext — Phase 3.2D Quality Audit & Targeted Repair Evidence Generator
===================================================================================
Demonstrates concrete before/after runtime evidence of defect detection and
transactional monotonic repair across 9 canonical scenarios:
  1. Title/Body Collision
  2. Inadequate Gutter (Too Small Gutter)
  3. Text Region Undersizing
  4. Citation Collision & Containment
  5. Whitespace Density & Excessive Emptiness
  6. Orphan Caption Re-anchoring
  7. Card Nesting & Safe Decorative Wrapper Removal
  8. Rollback Safety (Repair rejected due to regression prevention)
  9. Fatal Unrepairable Escalation (REFLOW_REQUIRED)
"""
import sys
import json
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
)
from app.services.presentation.composition_schemas import (
    LayoutSafeZone,
    RegionSemanticRole,
    TypographyRole,
    CompositionMode,
    QuadrantId,
    RegionAlignment,
    VerticalAlignment,
    SpacingToken,
    SourceKind,
    ContentBinding,
    ContentRegion,
    SlideCompositionPlan,
    ZONE_CONTENT_START,
    ZONE_FOOTER_START,
)
from app.services.presentation.grid_engine import (
    resolve_region_bounds,
    calculate_whitespace_metrics,
)
from app.services.presentation.typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)
from app.services.presentation.layout_quality_auditor import (
    DefectSeverity,
    DefectRepairability,
    DefectCode,
    LayoutAuditResult,
    RepairResult,
    audit_layout,
    repair_layout_defects,
)


def _build_dna() -> DesignDNA:
    return DesignDNA(
        theme_family="academic_clean",
        tone="scholarly",
        title_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=700,
            font_size_pt=26.0, line_height_ratio=1.20,
        ),
        body_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=400,
            font_size_pt=13.5, line_height_ratio=1.45,
        ),
        caption_scale=TypographyScale(
            font_family="Inter", font_fallback="Calibri", font_weight=500,
            font_size_pt=9.5, line_height_ratio=1.25,
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
    content_text: str = "Evidence payload content",
    is_full_bleed: bool = False,
    is_decorative: bool = False,
    associated_visual_id: Optional[str] = None,
) -> ContentRegion:
    bounds = resolve_region_bounds(col_start, col_span, row_start, row_span, is_full_bleed=is_full_bleed)
    chash = hashlib.sha256(content_text.encode("utf-8")).hexdigest() if not is_decorative else ""
    binding = ContentBinding(
        is_decorative=is_decorative,
        source_kind=SourceKind.DECORATIVE if is_decorative else SourceKind.SLIDE_CONTENT,
        source_id=associated_visual_id if associated_visual_id else "source_evidence",
        field_path="text_field" if not is_decorative else "",
        resolved_content_hash=chash,
        content_hash=chash,
    )
    typo_role = TypographyRole.TITLE if role == RegionSemanticRole.HEADER_TITLE else (
        TypographyRole.CAPTION if role == RegionSemanticRole.CAPTION else TypographyRole.BODY
    )
    typo_spec = resolve_typography_role_spec(typo_role, _build_dna())
    return ContentRegion.model_construct(
        region_id=region_id,
        semantic_role=role,
        safe_zone=safe_zone,
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


def _make_plan(layout: Phase3LayoutFamily, regions: list) -> SlideCompositionPlan:
    metrics = calculate_whitespace_metrics(regions)
    return SlideCompositionPlan.model_construct(
        slide_no=1,
        layout_family=layout,
        composition_mode=CompositionMode.STANDARD_CANVAS,
        content_regions=regions,
        whitespace_metrics=metrics,
    )


def run_evidence():
    dna = _build_dna()
    print("=" * 80)
    print("LEARNBYGENIE PPT VNEXT — PHASE 3.2D AUDITOR & REPAIR RUNTIME EVIDENCE")
    print("=" * 80)

    scenarios = []

    # -------------------------------------------------------------
    # Scenario 1: Title/Body Collision
    # -------------------------------------------------------------
    title = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 5, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 6, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    p1 = _make_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title, body])
    a1 = audit_layout(p1, design_dna=dna)
    r1 = repair_layout_defects(p1, a1, design_dna=dna)
    scenarios.append(("1. Title/Body Collision", p1, a1, r1))

    # -------------------------------------------------------------
    # Scenario 2: Inadequate Gutter (Too Small Gutter)
    # -------------------------------------------------------------
    title2 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    c1 = _make_region("col_left", RegionSemanticRole.PRIMARY_TEXT, 1, 5, 8, 12)
    c2 = _make_region("col_right", RegionSemanticRole.SUPPORTING_POINTS, 6, 7, 8, 12) # Gutter is very small between 5 and 6
    p2 = _make_plan(Phase3LayoutFamily.SPLIT_40_60, [title2, c1, c2])
    a2 = audit_layout(p2, design_dna=dna)
    r2 = repair_layout_defects(p2, a2, design_dna=dna)
    scenarios.append(("2. Inadequate Gutter", p2, a2, r2))

    # -------------------------------------------------------------
    # Scenario 3: Text-Region Undersizing
    # -------------------------------------------------------------
    title3 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    text3 = _make_region("narrow_text", RegionSemanticRole.PRIMARY_TEXT, 1, 2, 8, 12) # Span is 2 cols in SPLIT_40_60
    p3 = _make_plan(Phase3LayoutFamily.SPLIT_40_60, [title3, text3])
    a3 = audit_layout(p3, design_dna=dna)
    r3 = repair_layout_defects(p3, a3, design_dna=dna)
    scenarios.append(("3. Text-Region Undersizing", p3, a3, r3))

    # -------------------------------------------------------------
    # Scenario 4: Citation Collision & Safe Footer Containment
    # -------------------------------------------------------------
    title4 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body4 = _make_region("body", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    cit4 = _make_region("cit_misplaced", RegionSemanticRole.FOOTER_CITATION, 1, 12, 14, 2, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    p4 = _make_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title4, body4, cit4])
    a4 = audit_layout(p4, design_dna=dna)
    r4 = repair_layout_defects(p4, a4, design_dna=dna)
    scenarios.append(("4. Citation Collision & Containment", p4, a4, r4))

    # -------------------------------------------------------------
    # Scenario 5: Poor Whitespace Density (Excessive Emptiness)
    # -------------------------------------------------------------
    title5 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    text5 = _make_region("sparse_text", RegionSemanticRole.PRIMARY_TEXT, 1, 3, 8, 3) # Over 80% whitespace
    p5 = _make_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title5, text5])
    a5 = audit_layout(p5, design_dna=dna)
    r5 = repair_layout_defects(p5, a5, design_dna=dna)
    scenarios.append(("5. Excessive Empty Space", p5, a5, r5))

    # -------------------------------------------------------------
    # Scenario 6: Orphan Caption Re-anchoring
    # -------------------------------------------------------------
    vis6 = _make_region("vis_hero", RegionSemanticRole.PRIMARY_VISUAL, 6, 6, 8, 8)
    cap6 = _make_region("caption_orphan", RegionSemanticRole.CAPTION, 1, 4, 22, 2, associated_visual_id="vis_hero")
    p6 = _make_plan(Phase3LayoutFamily.SPLIT_40_60, [vis6, cap6])
    a6 = audit_layout(p6, design_dna=dna)
    r6 = repair_layout_defects(p6, a6, design_dna=dna)
    scenarios.append(("6. Orphan Caption Re-anchoring", p6, a6, r6))

    # -------------------------------------------------------------
    # Scenario 7: Card Nesting & Structural Wrapper Removal
    # -------------------------------------------------------------
    c_out = _make_region("dec_wrapper", RegionSemanticRole.CARD_CONTAINER, 1, 10, 8, 14, is_decorative=True)
    c_in = _make_region("card_inner", RegionSemanticRole.CARD_CONTAINER, 2, 8, 9, 10, is_decorative=True)
    b7 = _make_region("card_body", RegionSemanticRole.PRIMARY_TEXT, 2, 7, 10, 8)
    p7 = _make_plan(Phase3LayoutFamily.CARD_CLUSTER, [c_out, c_in, b7])
    a7 = audit_layout(p7, design_dna=dna)
    r7 = repair_layout_defects(p7, a7, design_dna=dna)
    scenarios.append(("7. Card Nesting Defect", p7, a7, r7))

    # -------------------------------------------------------------
    # Scenario 8: Rollback Safety (Repair Rolled Back on Regression)
    # -------------------------------------------------------------
    title8 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    r1_8 = _make_region("r1", RegionSemanticRole.PRIMARY_TEXT, 1, 5, 8, 8)
    r2_8 = _make_region("r2", RegionSemanticRole.PRIMARY_TEXT, 6, 7, 8, 8)
    p8 = _make_plan(Phase3LayoutFamily.SPLIT_40_60, [title8, r1_8, r2_8])
    a8 = audit_layout(p8, design_dna=dna)
    r8 = repair_layout_defects(p8, a8, design_dna=dna)
    scenarios.append(("8. Monotonic Rollback Safety", p8, a8, r8))

    # -------------------------------------------------------------
    # Scenario 9: Fatal Unrepairable Escalation (REFLOW_REQUIRED)
    # -------------------------------------------------------------
    title9 = _make_region("title", RegionSemanticRole.HEADER_TITLE, 1, 12, 3, 4, safe_zone=LayoutSafeZone.SAFE_TITLE)
    body9 = _make_region("body_overflow", RegionSemanticRole.PRIMARY_TEXT, 1, 8, 8, 12, safe_zone=LayoutSafeZone.SAFE_CONTENT)
    p9 = _make_plan(Phase3LayoutFamily.TEXT_DOMINANT, [title9, body9])
    fit_fatal = {
        "body_overflow": TextFitResult.model_construct(
            region_id="body_overflow",
            role=TypographyRole.BODY,
            font_size_pt=11.0,
            line_height_ratio=1.2,
            status=TextFitStatus.REFLOW_REQUIRED,
            rationale="Content density exceeds slide capacity floor",
        )
    }
    a9 = audit_layout(p9, design_dna=dna, text_fit_results=fit_fatal)
    r9 = repair_layout_defects(p9, a9, design_dna=dna)
    scenarios.append(("9. Fatal Escalation to REFLOW_REQUIRED", p9, a9, r9))

    # Output concrete evidence for all scenarios
    for name, p_before, audit_bef, repair_res in scenarios:
        print("\n" + "-" * 70)
        print(f"SCENARIO: {name}")
        print("-" * 70)
        print(f"[BEFORE]")
        print(f"  Regions: {[(r.region_id, r.semantic_role.value, f'col={r.grid_col_start}..{r.grid_col_start+r.grid_col_span-1}', f'row={r.baseline_row_start}..{r.baseline_row_start+r.baseline_row_span-1}') for r in p_before.content_regions]}")
        print(f"  Layout Valid: {audit_bef.layout_valid}")
        print(f"[DETECTED DEFECTS ({len(audit_bef.defects)})]")
        for d in audit_bef.defects:
            print(f"  - Code: {d.defect_code.value} | Severity: {d.severity.value} | Repairability: {d.repairability.value} | Msg: {d.message}")

        print(f"[PROPOSED REPAIR & ACTIONS ({len(repair_res.repair_actions)})]")
        for act in repair_res.repair_actions:
            print(f"  - Action: {act.repair_code} on regions {act.target_regions} -> Decision: {act.decision}")
            print(f"    Reason: {act.reason}")
            print(f"    Semantic Content Changed: {act.semantic_content_changed}")

        print(f"[AFTER]")
        print(f"  Terminal Status: {repair_res.terminal_status}")
        print(f"  Passes Executed: {repair_res.passes_executed}")
        print(f"  Repaired Successfully: {repair_res.repaired_successfully}")
        print(f"  Regions: {[(r.region_id, r.semantic_role.value, f'col={r.grid_col_start}..{r.grid_col_start+r.grid_col_span-1}', f'row={r.baseline_row_start}..{r.baseline_row_start+r.baseline_row_span-1}') for r in repair_res.repaired_plan.content_regions]}")

        print(f"[RE-AUDIT]")
        print(f"  Remaining Defects: {len(repair_res.audit_after.defects)}")
        print(f"  Layout Valid: {repair_res.audit_after.layout_valid}")

        print(f"[CONTENT HASH INVARIANCE]")
        before_hashes = {r.region_id: r.binding.resolved_content_hash for r in p_before.content_regions if not r.binding.is_decorative}
        after_hashes = {r.region_id: r.binding.resolved_content_hash for r in repair_res.repaired_plan.content_regions if not r.binding.is_decorative}
        all_match = (before_hashes == after_hashes)
        print(f"  Content Hash Invariance Maintained: {all_match}")
        for r_id, h in after_hashes.items():
            print(f"    Region '{r_id}': {h[:16]}... (preserved)")

    print("\n" + "=" * 80)
    print("PHASE 3.2D RUNTIME EVIDENCE GENERATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_evidence()
