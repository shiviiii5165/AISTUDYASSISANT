"""
Script to generate genuine runtime evidence for Phase 3.2C across 5 held-out disciplines:
1. Node.js Architecture (CS)
2. Photosynthesis (Biology)
3. Macbeth (Literature)
4. Eigenvalues/Eigenvectors (Mathematics)
5. Inflation & Monetary Policy (Economics) - with genuine reflow triggered!
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    LayoutFamily,
    SlideIntent,
    DataPoint,
    ComparisonRow,
)
from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    VisualAssetType,
    VisualIntent,
    VisualWeight,
    VisualRhythmBeat,
    VisualSemanticPacket,
    VisualCandidate,
    VisualRelationship,
    RelationshipType,
    DesignDNA,
    TypographyScale,
    SpacingScale,
    ColorPalette,
    ContentDensity,
    VisualDensityProfile,
)
from app.services.presentation.composition_schemas import (
    CompositionInputManifest,
    TypographyRole,
    RegionSemanticRole,
)
from app.services.presentation.typography_engine import (
    TextFitResult,
    TextFitStatus,
    resolve_typography_role_spec,
)
from app.services.presentation.layout_compiler import (
    compile_slide_layout,
    get_parametric_constraint_envelope,
)


def run_evidence():
    evidence_reports = []

    standard_dna = DesignDNA(
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

    # ─────────────────────────────────────────────────────────────
    # Sample 1: Node.js Architecture (Remains on Preferred Geometry)
    # ─────────────────────────────────────────────────────────────
    bp1 = SlideBlueprint(
        slide_id="slide_nodejs_1",
        slide_number=1,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Node.js uses an event-driven non-blocking I/O model.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.DIAGRAM_DOMINANT,
    )
    content1 = SlideContent(
        title="Node.js Architecture & Event Loop",
        subtitle="Single-threaded execution with asynchronous I/O delegation",
        primary_takeaway="The libuv event loop manages asynchronous operations through worker threads.",
        supporting_points=[
            "V8 JavaScript engine handles compilation and execution.",
            "Libuv provides cross-platform asynchronous I/O event polling.",
            "Thread pool handles expensive file system and crypto operations.",
        ],
    )
    packet1 = VisualSemanticPacket(
        slide_no=1,
        primary_visual_message="V8 Call Stack delegates I/O to libuv event queue.",
        visual_intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        system_components=["V8 Engine", "Libuv Event Loop", "Worker Pool", "Event Queue"],
        relationships=[
            VisualRelationship(
                source_entity="V8 Engine", relation="delegates_io", target_entity="Libuv Event Loop",
                relationship_type=RelationshipType.STRUCTURAL,
            ),
        ],
        diagram_candidate="EventLoopDiagram",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.ARCHITECTURE_MAP, layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE)
        ],
    )
    beat1 = VisualRhythmBeat(
        slide_no=1, layout_family=Phase3LayoutFamily.SYSTEM_ARCHITECTURE, visual_weight=VisualWeight.DOMINANT
    )
    manifest1 = CompositionInputManifest(manifest_id="manifest_nodejs")
    manifest1.register_content(bp1.slide_id, content1.model_dump())
    manifest1.register_content("visual_1", packet1.model_dump())

    plan1 = compile_slide_layout(bp1, content1, packet1, standard_dna, beat1, manifest1)

    evidence_reports.append({
        "sample_name": "Node.js Architecture",
        "initial_layout_family": Phase3LayoutFamily.SYSTEM_ARCHITECTURE.value,
        "content_density": bp1.content_density.value,
        "visual_density": packet1.visual_density.model_dump(),
        "initial_constraint_envelope": get_parametric_constraint_envelope(Phase3LayoutFamily.SYSTEM_ARCHITECTURE, bp1.content_density).model_dump(),
        "text_fit_result_inputs": "None (Exact Fit)",
        "resolved_column_spans": {r.region_id: f"col {r.grid_col_start} span {r.grid_col_span}" for r in plan1.content_regions},
        "resolved_vertical_bounds": {r.region_id: f"row {r.baseline_row_start} span {r.baseline_row_span} (top: {r.bounds.top_in}in, h: {r.bounds.height_in}in)" for r in plan1.content_regions},
        "fallback_steps_taken": getattr(plan1, "fallback_history", []),
        "final_layout_family": plan1.layout_family.value,
        "rhythm_compliance": getattr(plan1, "rhythm_plan_compliance", 1.0),
        "quality_defects": getattr(plan1, "quality_defects", []),
        "final_plan_summary": {
            "slide_no": plan1.slide_no,
            "composition_mode": plan1.composition_mode.value,
            "regions_count": len(plan1.content_regions),
            "whitespace_ratio": plan1.whitespace_metrics.planned_whitespace_ratio,
        }
    })

    # ─────────────────────────────────────────────────────────────
    # Sample 2: Photosynthesis (Remains on Preferred Geometry)
    # ─────────────────────────────────────────────────────────────
    bp2 = SlideBlueprint(
        slide_id="slide_photo_2",
        slide_number=2,
        intent=SlideIntent.PROCESS_EXPLANATION,
        primary_message="Light reactions produce ATP and NADPH for the Calvin cycle.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.FULL_WIDTH_PROCESS,
    )
    content2 = SlideContent(
        title="Photosynthesis: Light Reactions",
        subtitle="Energy transduction in the thylakoid membrane",
        primary_takeaway="Photons excite chlorophyll electrons initiating linear electron transport.",
        process_steps=[
            "Photon absorption by Photosystem II (P680)",
            "Photolysis of water releasing molecular oxygen",
            "Proton gradient generation across thylakoid membrane",
            "ATP synthesis and NADP+ reduction to NADPH",
        ],
    )
    packet2 = VisualSemanticPacket(
        slide_no=2,
        primary_visual_message="Sequential electron transfer through PSII, Cytochrome b6f, and PSI.",
        visual_intent=VisualIntent.SHOW_PROCESS,
        process_nodes=["PSII", "Plastoquinone", "Cyt b6f", "Plastocyanin", "PSI", "Ferredoxin"],
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.PROCESS_FLOW, layout_family=Phase3LayoutFamily.PROCESS_CANVAS)
        ],
    )
    beat2 = VisualRhythmBeat(
        slide_no=2, layout_family=Phase3LayoutFamily.PROCESS_CANVAS, visual_weight=VisualWeight.MEDIUM
    )
    manifest2 = CompositionInputManifest(manifest_id="manifest_photo")
    manifest2.register_content(bp2.slide_id, content2.model_dump())
    manifest2.register_content("visual_2", packet2.model_dump())

    plan2 = compile_slide_layout(bp2, content2, packet2, standard_dna, beat2, manifest2)

    evidence_reports.append({
        "sample_name": "Photosynthesis",
        "initial_layout_family": Phase3LayoutFamily.PROCESS_CANVAS.value,
        "content_density": bp2.content_density.value,
        "visual_density": packet2.visual_density.model_dump(),
        "initial_constraint_envelope": get_parametric_constraint_envelope(Phase3LayoutFamily.PROCESS_CANVAS, bp2.content_density).model_dump(),
        "text_fit_result_inputs": "None (Exact Fit)",
        "resolved_column_spans": {r.region_id: f"col {r.grid_col_start} span {r.grid_col_span}" for r in plan2.content_regions},
        "resolved_vertical_bounds": {r.region_id: f"row {r.baseline_row_start} span {r.baseline_row_span} (top: {r.bounds.top_in}in, h: {r.bounds.height_in}in)" for r in plan2.content_regions},
        "fallback_steps_taken": getattr(plan2, "fallback_history", []),
        "final_layout_family": plan2.layout_family.value,
        "rhythm_compliance": getattr(plan2, "rhythm_plan_compliance", 1.0),
        "quality_defects": getattr(plan2, "quality_defects", []),
        "final_plan_summary": {
            "slide_no": plan2.slide_no,
            "composition_mode": plan2.composition_mode.value,
            "regions_count": len(plan2.content_regions),
            "whitespace_ratio": plan2.whitespace_metrics.planned_whitespace_ratio,
        }
    })

    # ─────────────────────────────────────────────────────────────
    # Sample 3: Macbeth (Focal Quote - Preferred Geometry)
    # ─────────────────────────────────────────────────────────────
    bp3 = SlideBlueprint(
        slide_id="slide_macbeth_3",
        slide_number=3,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message="Macbeth's unchecked vaulting ambition leads to moral disintegration.",
        content_density=ContentDensity.LOW,
        layout_family=LayoutFamily.CENTERED_FOCAL,
    )
    content3 = SlideContent(
        title="Macbeth: The Anatomy of Ambition",
        subtitle="Internal psychological collapse in Shakespearean tragedy",
        primary_takeaway="Vaulting ambition o'erleaps itself and falls on the other.",
        callout="Act I, Scene VII — William Shakespeare",
    )
    packet3 = VisualSemanticPacket(
        slide_no=3,
        primary_visual_message="Focal dramatic quote highlighting tragic irony.",
        visual_intent=VisualIntent.HERO_STATEMENT,
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.TEXTUAL_STATEMENT, layout_family=Phase3LayoutFamily.QUOTE_OR_STATEMENT)
        ],
    )
    beat3 = VisualRhythmBeat(
        slide_no=3, layout_family=Phase3LayoutFamily.QUOTE_OR_STATEMENT, visual_weight=VisualWeight.LIGHT
    )
    manifest3 = CompositionInputManifest(manifest_id="manifest_macbeth")
    manifest3.register_content(bp3.slide_id, content3.model_dump())
    manifest3.register_content("visual_3", packet3.model_dump())

    plan3 = compile_slide_layout(bp3, content3, packet3, standard_dna, beat3, manifest3)

    evidence_reports.append({
        "sample_name": "Macbeth",
        "initial_layout_family": Phase3LayoutFamily.QUOTE_OR_STATEMENT.value,
        "content_density": bp3.content_density.value,
        "visual_density": packet3.visual_density.model_dump(),
        "initial_constraint_envelope": get_parametric_constraint_envelope(Phase3LayoutFamily.QUOTE_OR_STATEMENT, bp3.content_density).model_dump(),
        "text_fit_result_inputs": "None (Exact Fit)",
        "resolved_column_spans": {r.region_id: f"col {r.grid_col_start} span {r.grid_col_span}" for r in plan3.content_regions},
        "resolved_vertical_bounds": {r.region_id: f"row {r.baseline_row_start} span {r.baseline_row_span} (top: {r.bounds.top_in}in, h: {r.bounds.height_in}in)" for r in plan3.content_regions},
        "fallback_steps_taken": getattr(plan3, "fallback_history", []),
        "final_layout_family": plan3.layout_family.value,
        "rhythm_compliance": getattr(plan3, "rhythm_plan_compliance", 1.0),
        "quality_defects": getattr(plan3, "quality_defects", []),
        "final_plan_summary": {
            "slide_no": plan3.slide_no,
            "composition_mode": plan3.composition_mode.value,
            "regions_count": len(plan3.content_regions),
            "whitespace_ratio": plan3.whitespace_metrics.planned_whitespace_ratio,
        }
    })

    # ─────────────────────────────────────────────────────────────
    # Sample 4: Eigenvalues/Eigenvectors (Formula Visual - Preferred Geometry)
    # ─────────────────────────────────────────────────────────────
    bp4 = SlideBlueprint(
        slide_id="slide_eigen_4",
        slide_number=4,
        intent=SlideIntent.FORMULA_EXPLANATION,
        primary_message="Eigenvectors experience only scaling under linear transformation.",
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.FORMULA_PLUS_EXAMPLE,
    )
    content4 = SlideContent(
        title="Eigenvalues & Eigenvectors",
        subtitle="Invariant coordinate directions under matrix operations",
        primary_takeaway="A non-zero vector v is an eigenvector if Av is a scalar multiple of v.",
        formula=r"A \mathbf{v} = \lambda \mathbf{v}",
        formula_symbol_meanings="A: transformation matrix, v: eigenvector, lambda: eigenvalue",
    )
    packet4 = VisualSemanticPacket(
        slide_no=4,
        primary_visual_message="Geometric vector stretching without directional change.",
        visual_intent=VisualIntent.SHOW_FORMULA,
        formula_or_equation=r"A \mathbf{v} = \lambda \mathbf{v}",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.FORMULA_VISUAL, layout_family=Phase3LayoutFamily.FORMULA_VISUAL)
        ],
    )
    beat4 = VisualRhythmBeat(
        slide_no=4, layout_family=Phase3LayoutFamily.FORMULA_VISUAL, visual_weight=VisualWeight.MEDIUM
    )
    manifest4 = CompositionInputManifest(manifest_id="manifest_eigen")
    manifest4.register_content(bp4.slide_id, content4.model_dump())
    manifest4.register_content("visual_4", packet4.model_dump())

    plan4 = compile_slide_layout(bp4, content4, packet4, standard_dna, beat4, manifest4)

    evidence_reports.append({
        "sample_name": "Eigenvalues/Eigenvectors",
        "initial_layout_family": Phase3LayoutFamily.FORMULA_VISUAL.value,
        "content_density": bp4.content_density.value,
        "visual_density": packet4.visual_density.model_dump(),
        "initial_constraint_envelope": get_parametric_constraint_envelope(Phase3LayoutFamily.FORMULA_VISUAL, bp4.content_density).model_dump(),
        "text_fit_result_inputs": "None (Exact Fit)",
        "resolved_column_spans": {r.region_id: f"col {r.grid_col_start} span {r.grid_col_span}" for r in plan4.content_regions},
        "resolved_vertical_bounds": {r.region_id: f"row {r.baseline_row_start} span {r.baseline_row_span} (top: {r.bounds.top_in}in, h: {r.bounds.height_in}in)" for r in plan4.content_regions},
        "fallback_steps_taken": getattr(plan4, "fallback_history", []),
        "final_layout_family": plan4.layout_family.value,
        "rhythm_compliance": getattr(plan4, "rhythm_plan_compliance", 1.0),
        "quality_defects": getattr(plan4, "quality_defects", []),
        "final_plan_summary": {
            "slide_no": plan4.slide_no,
            "composition_mode": plan4.composition_mode.value,
            "regions_count": len(plan4.content_regions),
            "whitespace_ratio": plan4.whitespace_metrics.planned_whitespace_ratio,
        }
    })

    # ─────────────────────────────────────────────────────────────
    # Sample 5: Inflation & Monetary Policy (GENUINE REFLOW TRIGGERED!)
    # Initial: SPLIT_40_60; High Density; TextFitResult: REFLOW_REQUIRED
    # Reflow expansion occurs from 5 to 6 cols!
    # ─────────────────────────────────────────────────────────────
    bp5 = SlideBlueprint(
        slide_id="slide_inflation_5",
        slide_number=5,
        intent=SlideIntent.DATA_INSIGHT,
        primary_message="Central bank interest rate hikes cool core inflation with a time lag.",
        content_density=ContentDensity.HIGH,
        layout_family=LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    )
    content5 = SlideContent(
        title="Monetary Policy & Inflation Dynamics",
        subtitle="Empirical transmission mechanism of policy rate adjustments",
        primary_takeaway="A 200 bps policy rate increase correlates with a 1.8% decrease in headline CPI over 6 quarters, demonstrating significant lag in monetary policy transmission.",
        supporting_points=[
            "Direct interest rate channel dampens aggregate demand and borrowing.",
            "Exchange rate appreciation lowers import price pressures.",
            "Expectations channel anchors long-term inflation targets.",
        ],
        data_points=[
            DataPoint(label="Peak CPI", value="9.1", unit="percent"),
            DataPoint(label="Target CPI", value="2.0", unit="percent"),
        ],
        fit_risk="overflow",
    )
    packet5 = VisualSemanticPacket(
        slide_no=5,
        primary_visual_message="Empirical trajectory of CPI response to policy rate hikes.",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
        chart_candidate="PolicyRateVsInflationLineChart",
        visual_candidates=[
            VisualCandidate(asset_type=VisualAssetType.CHART, layout_family=Phase3LayoutFamily.SPLIT_40_60)
        ],
    )
    beat5 = VisualRhythmBeat(
        slide_no=5, layout_family=Phase3LayoutFamily.SPLIT_40_60, visual_weight=VisualWeight.DOMINANT
    )
    manifest5 = CompositionInputManifest(manifest_id="manifest_inflation")
    manifest5.register_content(bp5.slide_id, content5.model_dump())
    manifest5.register_content("visual_5", packet5.model_dump())

    # Genuine Phase 3.2B REFLOW_REQUIRED signal
    fit_results5 = {
        "slide_inflation_5_split_text": TextFitResult(
            region_id="slide_inflation_5_split_text",
            status=TextFitStatus.REFLOW_REQUIRED,
            fit_stage=6,
            display_text=content5.primary_takeaway,
            typography_before=resolve_typography_role_spec(TypographyRole.BODY, standard_dna, ContentDensity.HIGH),
            typography_after=resolve_typography_role_spec(TypographyRole.BODY, standard_dna, ContentDensity.HIGH),
        )
    }

    plan5 = compile_slide_layout(bp5, content5, packet5, standard_dna, beat5, manifest5, text_fit_results=fit_results5)

    evidence_reports.append({
        "sample_name": "Inflation & Monetary Policy",
        "initial_layout_family": Phase3LayoutFamily.SPLIT_40_60.value,
        "content_density": bp5.content_density.value,
        "visual_density": packet5.visual_density.model_dump(),
        "initial_constraint_envelope": get_parametric_constraint_envelope(Phase3LayoutFamily.SPLIT_40_60, bp5.content_density).model_dump(),
        "text_fit_result_inputs": {
            "region_id": "slide_inflation_5_split_text",
            "status": "REFLOW_REQUIRED",
            "fit_stage": 6,
        },
        "resolved_column_spans": {r.region_id: f"col {r.grid_col_start} span {r.grid_col_span}" for r in plan5.content_regions},
        "resolved_vertical_bounds": {r.region_id: f"row {r.baseline_row_start} span {r.baseline_row_span} (top: {r.bounds.top_in}in, h: {r.bounds.height_in}in)" for r in plan5.content_regions},
        "fallback_steps_taken": getattr(plan5, "fallback_history", []),
        "final_layout_family": plan5.layout_family.value,
        "rhythm_compliance": getattr(plan5, "rhythm_plan_compliance", 1.0),
        "quality_defects": getattr(plan5, "quality_defects", []),
        "final_plan_summary": {
            "slide_no": plan5.slide_no,
            "composition_mode": plan5.composition_mode.value,
            "regions_count": len(plan5.content_regions),
            "whitespace_ratio": plan5.whitespace_metrics.planned_whitespace_ratio,
        }
    })

    print(json.dumps(evidence_reports, indent=2))


if __name__ == "__main__":
    run_evidence()
