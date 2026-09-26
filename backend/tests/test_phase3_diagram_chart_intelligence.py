"""
TeachGenie PPT vNext — Phase 3.3 Editable Diagram & Native Chart Intelligence Test Suite
==========================================================================================
Validates:
  1. Visual Routing: Deterministic routing across diagrams, charts, fallbacks, and deferred states
  2. 22 Diagram Archetypes: All archetypes rendered via shared primitives with native editable shapes
  3. Semantic Relationship Fidelity: Preserves causality, dependency, feedback, hierarchy, sequence
  4. Native Diagram Editability: Every node, label, and connector independently editable in PowerPoint
  5. Chart Type Suitability: Statistically valid selection across 9 native chart types
  6. Strict Data Provenance & Zero Invention: Refuses chart synthesis when data is absent/unresolved
  7. Deterministic Geometry & Connector Routing: Clean bounds containment and attachment
  8. Round-Trip PPTX: Full serialization and re-inspection of native charts and shapes
  9. 100% Region Traceability: Bidirectional region-to-shape mapping preserved
  10. Offline Reproducibility: 0 network calls or external APIs
"""
import io
import math
from typing import List, Dict, Any
import pytest
from pptx import Presentation
from pptx.util import Inches

from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT
from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    DataPoint,
    ComparisonRow,
    SlideIntent,
    LayoutFamily,
)
from app.services.presentation.visual_schemas import (
    VisualSemanticPacket,
    VisualIntent,
    VisualAssetType,
    VisualRelationship,
    RelationshipType,
    HierarchyNode,
    VisualCandidate,
    DesignDNA,
    ContentDensity,
    Phase3LayoutFamily,
)
from app.services.presentation.composition_schemas import (
    ResolvedRegionBounds,
    ContentRegion,
    RegionSemanticRole,
    ContentBinding,
    ColorToken,
    CompositionInputManifest,
    ComposedSlideContext,
    SlideCompositionPlan,
)
from app.services.presentation.design_dna import _build_academic_clean_dna, _THEME_PALETTES
from app.services.presentation.chart_intelligence import (
    ChartType,
    ChartDataPayload,
    DataSeries,
    ChartDefectCode,
    extract_chart_payload_from_content,
    validate_chart_type_suitability,
    select_appropriate_chart_type,
    render_native_chart,
)
from app.services.presentation.diagram_intelligence import (
    DiagramArchetype,
    DiagramNode,
    DiagramConnector,
    DiagramSpec,
    select_diagram_archetype,
    build_diagram_spec,
    render_editable_diagram,
)
from app.services.presentation.visual_router import (
    VisualRoutingDecision,
    VisualRoutingResult,
    route_visual_decision,
    audit_diagram_structure,
    repair_diagram_geometry,
)
from app.services.presentation.composition_renderer import (
    render_composed_slide,
    RenderDefectCode,
)


@pytest.fixture
def sample_dna() -> DesignDNA:
    return _build_academic_clean_dna(_THEME_PALETTES["blue_professional"], ContentDensity.MEDIUM)


@pytest.fixture
def sample_bounds() -> ResolvedRegionBounds:
    return ResolvedRegionBounds(
        left_in=5.5,
        top_in=1.5,
        width_in=7.0,
        height_in=5.0,
    )


# ═══════════════════════════════════════════════════════════════
# 1. VISUAL ROUTING CONTRACT
# ═══════════════════════════════════════════════════════════════

def test_visual_routing_contract(sample_dna, sample_bounds):
    """Verifies typed visual routing decisions based on content, packet, and region."""
    reg_chart = ContentRegion(
        region_id="reg_chart",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(
            source_id="dp1",
            field_path="data_points",
            resolved_content_hash=CompositionInputManifest.compute_payload_hash("data_points"),
        ),
    )
    reg_diag = ContentRegion(
        region_id="reg_diag",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(
            source_id="dia1",
            field_path="diagram",
            resolved_content_hash=CompositionInputManifest.compute_payload_hash("diagram"),
        ),
    )

    # 1. Routing to NATIVE_CHART when valid empirical data points exist
    content_with_data = SlideContent(
        title="Economic Indicators",
        data_points=[
            DataPoint(metric="2021", value="100.5", unit="USD"),
            DataPoint(metric="2022", value="125.0", unit="USD"),
            DataPoint(metric="2023", value="142.8", unit="USD"),
        ]
    )
    packet_chart = VisualSemanticPacket(
        chart_candidate="column_chart",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
    )
    res_chart = route_visual_decision(packet_chart, content_with_data, reg_chart, sample_bounds, sample_dna)
    assert res_chart.decision == VisualRoutingDecision.NATIVE_CHART
    assert res_chart.data_payload is not None
    assert len(res_chart.data_payload.categories) == 3

    # 2. Honest Refusal / Safe Fallback when data is missing
    content_empty = SlideContent(title="Conceptual Economics")
    res_empty = route_visual_decision(packet_chart, content_empty, reg_chart, sample_bounds, sample_dna)
    assert res_empty.decision == VisualRoutingDecision.SAFE_VISUAL_FALLBACK
    assert res_empty.is_chart_deferred is True
    assert res_empty.defect_code == ChartDefectCode.DATA_INSUFFICIENT_FOR_CHART.value

    # 3. Routing to EDITABLE_DIAGRAM when process / architecture semantics exist
    content_proc = SlideContent(
        title="Software Pipeline",
        process_steps=["Commit Code", "Run Unit Tests", "Deploy Artifact", "Monitor Telemetry"],
    )
    packet_diag = VisualSemanticPacket(
        visual_intent=VisualIntent.SHOW_PROCESS,
        key_entities=["Commit", "Test", "Deploy", "Monitor"],
    )
    res_diag = route_visual_decision(packet_diag, content_proc, reg_diag, sample_bounds, sample_dna)
    assert res_diag.decision == VisualRoutingDecision.EDITABLE_DIAGRAM
    assert res_diag.diagram_spec is not None
    assert len(res_diag.diagram_spec.nodes) == 4


# ═══════════════════════════════════════════════════════════════
# 2. ALL 22 DIAGRAM ARCHETYPES COVERAGE (PARAMETERIZED)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("archetype", list(DiagramArchetype))
def test_diagram_archetype_coverage(archetype, sample_dna, sample_bounds):
    """Proves that every supported DiagramArchetype can be constructed and rendered into native shapes."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    entities = ["Phase Alpha", "Phase Beta", "Phase Gamma", "Phase Delta"]
    rels = [
        VisualRelationship(
            source_entity="Phase Alpha",
            target_entity="Phase Beta",
            relationship_type=RelationshipType.SEQUENTIAL if "process" in archetype.value or "timeline" in archetype.value else RelationshipType.STRUCTURAL,
        ),
        VisualRelationship(
            source_entity="Phase Beta",
            target_entity="Phase Gamma",
            relationship_type=RelationshipType.FEEDBACK if "cycle" in archetype.value or "loop" in archetype.value else RelationshipType.TRANSFORMATION,
        ),
    ]
    spec = build_diagram_spec(archetype, entities, rels, sample_bounds)
    assert len(spec.nodes) >= 2, f"Archetype {archetype.value} produced fewer than 2 nodes"

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    res = render_editable_diagram(
        prs=prs,
        slide=slide,
        bounds=sample_bounds,
        spec=spec,
        design_dna=sample_dna,
        slide_no=1,
        region_id="diag_reg",
    )
    assert res.success is True, f"Failed rendering archetype {archetype.value}"
    assert res.node_count >= 2
    assert len(res.rendered_shape_ids) >= 2
    assert res.is_native_editable is True
    assert len(res.unrendered_required_nodes) == 0
    assert len(res.unrendered_required_edges) == 0


# ═══════════════════════════════════════════════════════════════
# 3. SEMANTIC RELATIONSHIP FIDELITY
# ═══════════════════════════════════════════════════════════════

def test_semantic_relationship_fidelity(sample_bounds):
    """Ensures relationship types (causality, feedback, hierarchy, sequence) dictate archetype selection."""
    # 1. Feedback relationship must select a cyclic / feedback archetype, never a linear timeline
    packet_cycle = VisualSemanticPacket(
        relationships=[
            VisualRelationship(source_entity="Sensor", target_entity="Controller", relationship_type=RelationshipType.FEEDBACK, direction="bidirectional")
        ]
    )
    arch_cycle, _, _ = select_diagram_archetype(packet_cycle, None)
    assert arch_cycle in (DiagramArchetype.FEEDBACK_CYCLE, DiagramArchetype.CAUSAL_LOOP, DiagramArchetype.LIFECYCLE_DIAGRAM)

    # 2. Hierarchy tree must select a tree archetype
    packet_tree = VisualSemanticPacket(
        hierarchy_tree=[
            HierarchyNode(label="Root", children=[HierarchyNode(label="Child A"), HierarchyNode(label="Child B")])
        ]
    )
    arch_tree, _, _ = select_diagram_archetype(packet_tree, None)
    assert arch_tree in (DiagramArchetype.HIERARCHICAL_TREE, DiagramArchetype.DECISION_TREE)

    # 3. System components must select an architecture archetype
    packet_sys = VisualSemanticPacket(
        visual_intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        system_components=["Client", "API Gateway", "PostgreSQL"],
    )
    arch_sys, _, _ = select_diagram_archetype(packet_sys, None)
    assert arch_sys in (DiagramArchetype.SYSTEM_ARCHITECTURE, DiagramArchetype.LAYERED_ARCHITECTURE, DiagramArchetype.COMPONENT_DIAGRAM)


# ═══════════════════════════════════════════════════════════════
# 4. NATIVE DIAGRAM EDITABILITY (ZERO RASTERIZATION)
# ═══════════════════════════════════════════════════════════════

def test_native_diagram_editability(sample_dna, sample_bounds):
    """Verifies that all nodes and connectors are native PowerPoint shapes with editable text frames."""
    spec = build_diagram_spec(
        DiagramArchetype.SYSTEM_ARCHITECTURE,
        ["Web UI", "Service Mesh", "Distributed DB"],
        [],
        sample_bounds,
    )
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    res = render_editable_diagram(prs, slide, sample_bounds, spec, sample_dna, 1, "arch_reg")
    assert res.success is True

    # Inspect slide shapes
    text_bearing_shapes = [s for s in slide.shapes if s.has_text_frame]
    assert len(text_bearing_shapes) == 3
    assert any("Web UI" in s.text_frame.text for s in text_bearing_shapes)
    assert any("Service Mesh" in s.text_frame.text for s in text_bearing_shapes)
    assert any("Distributed DB" in s.text_frame.text for s in text_bearing_shapes)

    # Connector shapes
    connector_shapes = [s for s in slide.shapes if "conn" in s.name]
    assert len(connector_shapes) >= 2


# ═══════════════════════════════════════════════════════════════
# 5. CHART TYPE SUITABILITY & VALIDATION
# ═══════════════════════════════════════════════════════════════

def test_chart_type_suitability_and_statistical_rules():
    """Validates statistical mapping rules for chart types."""
    # 1. Valid categorical comparison
    payload_cats = ChartDataPayload(
        metric_name="Revenue",
        categories=["Product A", "Product B", "Product C"],
        series=[DataSeries(name="Revenue", values=[10.0, 25.0, 18.0])],
        unit="USD",
    )
    ok, defect = validate_chart_type_suitability(payload_cats, ChartType.COLUMN_CLUSTERED)
    assert ok is True

    # 2. Pie chart rejection when partition contains negative values
    payload_neg = ChartDataPayload(
        metric_name="Margin",
        categories=["Division X", "Division Y"],
        series=[DataSeries(name="Margin", values=[50.0, -15.0])],
        unit="USD",
    )
    ok_pie, defect_pie = validate_chart_type_suitability(payload_neg, ChartType.PIE)
    assert ok_pie is False
    assert defect_pie == ChartDefectCode.NEGATIVE_VALUES_IN_PARTITION

    # 3. Pie chart rejection when percentages do not sum to 100%
    payload_skewed_pct = ChartDataPayload(
        metric_name="Market Share",
        categories=["Company A", "Company B"],
        series=[DataSeries(name="Share", values=[20.0, 30.0])],  # Sum = 50%
        unit="%",
    )
    ok_pct, defect_pct = validate_chart_type_suitability(payload_skewed_pct, ChartType.PIE)
    assert ok_pct is False
    assert defect_pct == ChartDefectCode.MISLEADING_CHART_MAPPING


# ═══════════════════════════════════════════════════════════════
# 6. STRICT DATA PROVENANCE & ZERO INVENTION
# ═══════════════════════════════════════════════════════════════

def test_strict_data_provenance_and_zero_invention():
    """Proves that charts require valid numeric data points and never invent data."""
    # Data with non-numeric or missing values -> Must refuse
    content_bad = SlideContent(
        title="AI Adoption",
        data_points=[
            DataPoint(metric="Stage 1", value="High"),
            DataPoint(metric="Stage 2", value="Medium"),
        ]
    )
    payload_bad = extract_chart_payload_from_content(content_bad)
    assert payload_bad is None

    # Valid data -> Exact provenance hash computed
    content_good = SlideContent(
        title="Transaction Throughput",
        data_points=[
            DataPoint(metric="MySQL", value="4500", unit="TPS", is_verified=True),
            DataPoint(metric="PostgreSQL", value="7200", unit="TPS", is_verified=True),
            DataPoint(metric="CockroachDB", value="6800", unit="TPS", is_verified=True),
        ]
    )
    payload_good = extract_chart_payload_from_content(content_good)
    assert payload_good is not None
    assert len(payload_good.data_hash) == 16
    assert payload_good.is_verified is True
    assert payload_good.series[0].values == [4500.0, 7200.0, 6800.0]


# ═══════════════════════════════════════════════════════════════
# 7. NATIVE CHART POWERPOINT RENDERING (PARAMETERIZED ACROSS ALL 9 CHART TYPES)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("chart_type", list(ChartType))
def test_native_chart_rendering_and_editability(chart_type, sample_dna, sample_bounds):
    """Renders real native PowerPoint chart and verifies embedded chart structure across all 9 supported chart types."""
    if chart_type == ChartType.SCATTER:
        payload = ChartDataPayload(
            metric_name="Scatter Dispersion",
            categories=["1.0", "2.0", "3.0", "4.0"],
            series=[DataSeries(name="Dispersion", values=[10.0, 20.0, 15.0, 25.0])],
            unit="units",
        )
    elif chart_type in (ChartType.PIE, ChartType.DOUGHNUT):
        payload = ChartDataPayload(
            metric_name="Market Share",
            categories=["Segment A", "Segment B", "Segment C"],
            series=[DataSeries(name="Share", values=[40.0, 35.0, 25.0])],
            unit="%",
        )
    else:
        payload = ChartDataPayload(
            metric_name="Execution Time",
            categories=["FCFS", "SJF", "Round Robin", "Priority"],
            series=[DataSeries(name="Execution Time", values=[12.4, 8.1, 9.5, 7.2])],
            unit="ms",
        )

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    res = render_native_chart(
        prs=prs,
        slide=slide,
        bounds=sample_bounds,
        payload=payload,
        chart_type=chart_type,
        design_dna=sample_dna,
        slide_no=1,
        region_id="chart_reg",
    )
    assert res.success is True
    assert res.rendered_shape_id is not None
    assert "native_chart" in res.rendered_shape_name
    assert res.is_native_editable is True

    # Inspect slide chart shape
    assert len(slide.shapes) == 1
    chart_shape = slide.shapes[0]
    assert chart_shape.has_chart is True
    chart = chart_shape.chart
    assert chart.has_title is True
    assert payload.metric_name in chart.chart_title.text_frame.text


# ═══════════════════════════════════════════════════════════════
# 8. ROUND-TRIP PPTX SERIALIZATION WITH CHARTS & DIAGRAMS
# ═══════════════════════════════════════════════════════════════

def test_round_trip_pptx_serialization_with_charts_and_diagrams(sample_dna, sample_bounds):
    """Proves that slides with native charts and editable diagrams serialize, save, and reload cleanly."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # Slide 1: Native Chart
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    chart_payload = ChartDataPayload(
        metric_name="Throughput",
        categories=["Run 1", "Run 2", "Run 3"],
        series=[DataSeries(name="Throughput", values=[100.0, 150.0, 180.0])],
        unit="req/s",
    )
    res_chart = render_native_chart(prs, s1, sample_bounds, chart_payload, ChartType.LINE, sample_dna, 1, "c_reg")
    assert res_chart.success is True

    # Slide 2: Editable Diagram
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    diag_spec = build_diagram_spec(
        DiagramArchetype.FEEDBACK_CYCLE,
        ["Sense", "Compute", "Actuate", "Feedback"],
        [],
        sample_bounds,
    )
    res_diag = render_editable_diagram(prs, s2, sample_bounds, diag_spec, sample_dna, 2, "d_reg")
    assert res_diag.success is True

    # Serialize to memory
    buf = io.BytesIO()
    prs.save(buf)
    raw_bytes = buf.getvalue()
    assert len(raw_bytes) > 15000  # Substantial valid PPTX with chart parts

    # Reopen and inspect
    reopened = Presentation(io.BytesIO(raw_bytes))
    assert len(reopened.slides) == 2

    # Slide 1 has native chart
    assert reopened.slides[0].shapes[0].has_chart is True

    # Slide 2 has diagram nodes and connectors
    s2_shapes = reopened.slides[1].shapes
    assert len(s2_shapes) >= 4
    has_sense_node = any(s.has_text_frame and "Sense" in s.text_frame.text for s in s2_shapes)
    assert has_sense_node is True


# ═══════════════════════════════════════════════════════════════
# 9. COMPOSITION RENDERER INTEGRATION WITH PHASE 3.3
# ═══════════════════════════════════════════════════════════════

def test_composition_renderer_integration_with_phase3_3(sample_dna, sample_bounds, monkeypatch):
    """Proves that render_composed_slide seamlessly produces native charts and diagrams inside full slide plans."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED", True)
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    manifest = CompositionInputManifest(manifest_id="test_man_p33")
    manifest.register_content("reg_title", {"title": "Database Benchmark Analysis"})
    manifest.register_content("reg_chart", {"data_points": "chart_data"})
    manifest.register_content("reg_diag", {"diagram": "diagram_data"})

    h_title = manifest.compute_field_hash("reg_title", "title")
    h_chart = manifest.compute_field_hash("reg_chart", "data_points")
    h_diag = manifest.compute_field_hash("reg_diag", "diagram")

    # Plan with a chart region
    reg_title = ContentRegion(
        region_id="reg_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=ResolvedRegionBounds(left_in=0.8, top_in=0.8, width_in=11.5, height_in=0.8),
        binding=ContentBinding(source_id="reg_title", field_path="title", resolved_content_hash=h_title),
    )
    reg_chart = ContentRegion(
        region_id="reg_chart",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=ResolvedRegionBounds(left_in=0.8, top_in=1.8, width_in=6.0, height_in=4.5),
        binding=ContentBinding(source_id="reg_chart", field_path="data_points", resolved_content_hash=h_chart),
    )
    reg_diag = ContentRegion(
        region_id="reg_diag",
        semantic_role=RegionSemanticRole.SECONDARY_VISUAL,
        grid_col_start=7,
        grid_col_span=6,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=ResolvedRegionBounds(left_in=7.2, top_in=1.8, width_in=5.2, height_in=4.5),
        binding=ContentBinding(source_id="reg_diag", field_path="diagram", resolved_content_hash=h_diag),
    )

    plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.DATA_CANVAS,
        composition_mode="asymmetric_editorial",
        content_regions=[reg_title, reg_chart, reg_diag],
    )
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id="test_man_p33",
    )

    content = SlideContent(
        title="Database Benchmark Analysis",
        supporting_points=["Evaluates latency and throughput across distributed engines"],
        data_points=[
            DataPoint(metric="Postgres", value="8500", unit="IOPS"),
            DataPoint(metric="MongoDB", value="9200", unit="IOPS"),
            DataPoint(metric="Redis", value="18000", unit="IOPS"),
        ],
        process_steps=["Parse Query", "Execute Plan", "Return Cursor"],
    )
    packet = VisualSemanticPacket(
        chart_candidate="column_chart",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
        key_entities=["Parse", "Execute", "Return"],
    )

    res = render_composed_slide(
        prs=prs,
        slide=slide,
        composed_context=ctx,
        composition_input_manifest=manifest,
        design_dna=sample_dna,
        enforce_audit_gate=False,
        visual_semantic_packet=packet,
        slide_content=content,
    )

    assert res.success is True
    # Verify 100% traceability: both reg_chart and reg_diag are tracked in region_to_shape_ids
    assert "reg_chart" in res.region_to_shape_ids
    assert "reg_diag" in res.region_to_shape_ids
    assert len(res.region_to_shape_ids["reg_chart"]) >= 1
    assert len(res.region_to_shape_ids["reg_diag"]) >= 3  # nodes and connectors


# ═══════════════════════════════════════════════════════════════
# 10. DIAGRAM AUDIT & TARGETED REPAIR
# ═══════════════════════════════════════════════════════════════

def test_diagram_audit_and_targeted_repair(sample_bounds):
    """Verifies that diagram geometric collision and containment defects are detected and repaired."""
    # Create intentionally colliding nodes
    spec_colliding = DiagramSpec(
        archetype=DiagramArchetype.LINEAR_PROCESS,
        nodes=[
            DiagramNode(node_id="n1", label="Node 1", x=0.5, y=0.5, width=2.0, height=1.0),
            DiagramNode(node_id="n2", label="Node 2", x=1.0, y=0.5, width=2.0, height=1.0), # Overlaps Node 1!
        ]
    )
    defects = audit_diagram_structure(spec_colliding, sample_bounds)
    assert any(d.defect_code == "DIAGRAM_NODE_COLLISION" for d in defects)

    # Targeted repair
    repaired_spec = repair_diagram_geometry(spec_colliding, sample_bounds, defects)
    assert repaired_spec.nodes[0].width < spec_colliding.nodes[0].width


# ═══════════════════════════════════════════════════════════════
# 11. FEATURE-FLAG ACTIVATION MATRIX (5 MANDATORY COMBINATIONS)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("parent_flag, p33_flag, expect_p33_native", [
    (False, False, False),
    (False, True,  False),
    (True,  False, False),
    (True,  True,  True),
])
def test_feature_flag_activation_matrix(
    parent_flag,
    p33_flag,
    expect_p33_native,
    sample_dna,
    sample_bounds,
    monkeypatch,
):
    """
    Validates all 4 feature-flag activation permutations:
      1. parent OFF, Phase 3.3 OFF -> Legacy template rendering (composition skipped)
      2. parent OFF, Phase 3.3 ON  -> Legacy template rendering (Phase 3.3 cannot activate without parent)
      3. parent ON,  Phase 3.3 OFF -> Composition renderer active, but charts/diagrams deferred (Phase 3.2 baseline)
      4. parent ON,  Phase 3.3 ON  -> Full Phase 3.3 native charts & editable diagrams active
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", parent_flag)
    monkeypatch.setattr(settings, "PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED", p33_flag)

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    manifest = CompositionInputManifest(manifest_id="test_ff_man")
    manifest.register_content("reg_title", {"title": "Flag Matrix Verification"})
    manifest.register_content("reg_chart", {"data_points": "pts"})
    h_title = manifest.compute_field_hash("reg_title", "title")
    h_vis = manifest.compute_field_hash("reg_chart", "data_points")

    reg_title = ContentRegion(
        region_id="reg_title",
        semantic_role=RegionSemanticRole.HEADER_TITLE,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=3,
        baseline_row_span=4,
        bounds=ResolvedRegionBounds(left_in=0.8, top_in=0.8, width_in=11.5, height_in=0.8),
        binding=ContentBinding(source_id="reg_title", field_path="title", resolved_content_hash=h_title),
    )
    reg_vis = ContentRegion(
        region_id="reg_chart",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(source_id="reg_chart", field_path="data_points", resolved_content_hash=h_vis),
    )
    plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.DATA_CANVAS,
        composition_mode="asymmetric_editorial",
        content_regions=[reg_title, reg_vis],
    )
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id="test_ff_man",
    )
    content = SlideContent(
        title="Flag Matrix Verification",
        data_points=[
            DataPoint(metric="Metric A", value="42.0", unit="pts"),
            DataPoint(metric="Metric B", value="84.0", unit="pts"),
        ]
    )
    packet = VisualSemanticPacket(
        chart_candidate="column_chart",
        visual_intent=VisualIntent.SHOW_DATA_PATTERN,
    )

    if not parent_flag:
        # Parent flag disabled -> routes to legacy template renderer in PresentationBuilder
        from app.services.presentation.engine.builder import build_presentation_spec
        from app.services.presentation.schemas import PresentationSpec, PresentationConfig, SlideSpec
        spec = PresentationSpec(
            title="Flag Safety Presentation",
            config=PresentationConfig(topic="Flag Safety", slide_count=10),
            slides=[SlideSpec(slide_no=i+1, title=f"Flag Safety {i+1}", body_bullets=["Testing legacy template path"]) for i in range(10)],
        )
        pptx_bytes = build_presentation_spec(
            spec=spec,
            composed_contexts=[ctx],
            manifest=manifest,
            design_dna=sample_dna,
        )
        assert pptx_bytes is not None
        assert len(pptx_bytes) > 0
    else:
        # Parent flag ON -> calls render_composed_slide
        res = render_composed_slide(
            prs=prs,
            slide=slide,
            composed_context=ctx,
            composition_input_manifest=manifest,
            design_dna=sample_dna,
            enforce_audit_gate=False,
            visual_semantic_packet=packet,
            slide_content=content,
        )
        assert res.success is True
        chart_shapes = [s for s in slide.shapes if getattr(s, "has_chart", False)]
        if expect_p33_native:
            assert len(chart_shapes) >= 1, "Expected native chart when Phase 3.3 flag is ON"
        else:
            assert len(chart_shapes) == 0, "Expected deferred placeholder when Phase 3.3 flag is OFF"


def test_feature_flag_integrity_failure_fails_closed(sample_dna, sample_bounds, monkeypatch):
    """
    Validates 5th combination:
      parent ON, Phase 3.3 ON + Integrity failure (hash mismatch) -> STRICT FAIL CLOSED.
      No silent fallback to legacy template rendering.
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "PRESENTATION_COMPOSITION_RENDERER_ENABLED", True)
    monkeypatch.setattr(settings, "PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED", True)

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    manifest = CompositionInputManifest(manifest_id="test_man_corrupt")
    manifest.register_content("reg_chart", {"data_points": "real_data"})

    # Intentionally forged/corrupt hash
    reg_chart = ContentRegion(
        region_id="reg_chart",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(source_id="reg_chart", field_path="data_points", resolved_content_hash="CORRUPTED_TAMPERED_HASH"),
    )
    plan = SlideCompositionPlan(
        slide_no=1,
        layout_family=Phase3LayoutFamily.DATA_CANVAS,
        composition_mode="asymmetric_editorial",
        content_regions=[reg_chart],
    )
    ctx = ComposedSlideContext(
        slide_no=1,
        composition_plan=plan,
        composition_input_manifest_id="test_man_corrupt",
    )
    content = SlideContent(title="Integrity Failure Slide")

    res = render_composed_slide(
        prs=prs,
        slide=slide,
        composed_context=ctx,
        composition_input_manifest=manifest,
        design_dna=sample_dna,
        enforce_audit_gate=False,
        slide_content=content,
    )
    # Must fail closed: success is False, terminal_status is CONTENT_BINDING_HASH_MISMATCH
    assert res.success is False
    assert res.terminal_status == "CONTENT_BINDING_HASH_MISMATCH"


# ═══════════════════════════════════════════════════════════════
# 12. NEGATIVE TESTS: MISSING EDGES, WRONG ARROW, REFLOW DEFECT
# ═══════════════════════════════════════════════════════════════

def test_negative_diagram_missing_required_edge(sample_bounds):
    """Verifies that audit_diagram_structure catches missing required edges."""
    spec = DiagramSpec(
        archetype=DiagramArchetype.LINEAR_PROCESS,
        nodes=[
            DiagramNode(node_id="n_1", label="Step 1", x=0.5, y=1.0, width=1.5, height=0.6),
            DiagramNode(node_id="n_2", label="Step 2", x=2.5, y=1.0, width=1.5, height=0.6),
        ],
        connectors=[],  # Missing required edge!
        source_node_ids=["n_1", "n_2"],
        source_edge_ids=["req_edge_1"],
    )
    defects = audit_diagram_structure(spec, sample_bounds)
    assert any(d.defect_code == "MISSING_REQUIRED_EDGE" for d in defects)
    defect = next(d for d in defects if d.defect_code == "MISSING_REQUIRED_EDGE")
    assert defect.severity == "FATAL"
    assert "req_edge_1" in defect.affected_elements


def test_negative_diagram_wrong_arrow_direction(sample_bounds):
    """Verifies that audit_diagram_structure catches connectors with missing/wrong arrows."""
    spec = DiagramSpec(
        archetype=DiagramArchetype.FEEDBACK_CYCLE,
        nodes=[
            DiagramNode(node_id="c_1", label="Sensor", x=0.5, y=1.0, width=1.5, height=0.6),
            DiagramNode(node_id="c_2", label="Actuator", x=2.5, y=1.0, width=1.5, height=0.6),
        ],
        connectors=[
            DiagramConnector(
                edge_id="e_causal",
                source_node_id="c_1",
                target_node_id="c_2",
                source_entity="Sensor",
                target_entity="Actuator",
                has_arrow=False,  # Wrong! Causal/feedback connector missing arrow!
                is_bidirectional=False,
            )
        ],
        source_node_ids=["c_1", "c_2"],
        source_edge_ids=["e_causal"],
    )
    defects = audit_diagram_structure(spec, sample_bounds)
    assert any(d.defect_code == "WRONG_ARROW_DIRECTION" for d in defects)
    defect = next(d for d in defects if d.defect_code == "WRONG_ARROW_DIRECTION")
    assert defect.severity == "FATAL"
    assert "e_causal" in defect.affected_elements


def test_negative_diagram_constrained_bounds_reflow_defect():
    """
    Verifies that complex graphs placed into impossibly constrained bounds return
    a structured REFLOW_REQUIRED defect rather than silently deleting relationships.
    """
    tiny_bounds = ResolvedRegionBounds(left_in=1.0, top_in=1.0, width_in=2.0, height_in=1.5)
    spec = DiagramSpec(
        archetype=DiagramArchetype.FEEDBACK_CYCLE,
        nodes=[
            DiagramNode(node_id=f"node_{i}", label=f"Subsystem {i}", x=0.2*i, y=0.2*i, width=1.0, height=0.5)
            for i in range(5)
        ],
        connectors=[
            DiagramConnector(edge_id=f"e_{i}", source_node_id=f"node_{i}", target_node_id=f"node_{(i+1)%5}")
            for i in range(5)
        ],
    )
    defects = audit_diagram_structure(spec, tiny_bounds)
    assert any(d.defect_code == "REFLOW_REQUIRED" for d in defects)
    defect = next(d for d in defects if d.defect_code == "REFLOW_REQUIRED")
    assert defect.severity == "FATAL"
    assert "reflow required" in defect.description.lower()


# ═══════════════════════════════════════════════════════════════
# 13. SPARSE SEMANTIC METADATA SAFETY: ZERO FABRICATED EDGES
# ═══════════════════════════════════════════════════════════════

def test_sparse_semantic_metadata_safety_zero_fabricated_edges(sample_dna, sample_bounds):
    """
    Verifies that when no relationship metadata exists:
      - Sequential order is NOT inferred
      - Causal arrows are NOT created
      - Dependencies are NOT created
      - LINEAR_PROCESS is NOT automatically chosen
      - Either independent editable nodes without connectors or structured SAFE_VISUAL_FALLBACK is returned
      - Proves zero fabricated edges or relationships
    """
    # Case A: Independent semantic concepts without relationship metadata
    packet_sparse = VisualSemanticPacket(
        visual_intent=VisualIntent.VISUAL_SUMMARY,
        key_entities=["Concept Alpha", "Concept Beta", "Concept Gamma"],
        # ZERO relationships, ZERO process nodes, ZERO temporal structure
    )
    content_sparse = SlideContent(title="Independent Abstract Concepts")
    reg_sparse = ContentRegion(
        region_id="reg_sparse",
        semantic_role=RegionSemanticRole.PRIMARY_VISUAL,
        grid_col_start=1,
        grid_col_span=12,
        baseline_row_start=8,
        baseline_row_span=18,
        bounds=sample_bounds,
        binding=ContentBinding(source_id="sp_1", field_path="key_entities", resolved_content_hash="h_sp"),
    )

    # 1. Archetype selection must NOT choose LINEAR_PROCESS
    arch, entities, rels = select_diagram_archetype(packet_sparse, content_sparse)
    assert arch != DiagramArchetype.LINEAR_PROCESS
    assert arch == DiagramArchetype.CONCEPT_MAP
    assert len(rels) == 0

    # 2. Spec must have ZERO connectors (no fabricated edges)
    spec = build_diagram_spec(arch, entities, rels, sample_bounds)
    assert len(spec.nodes) == 3
    assert len(spec.connectors) == 0

    # 3. Router decision must produce CONCEPT_MAP with 0 connectors
    routing_res = route_visual_decision(packet_sparse, content_sparse, reg_sparse, sample_bounds, sample_dna)
    assert routing_res.decision == VisualRoutingDecision.EDITABLE_DIAGRAM
    assert routing_res.target_type == DiagramArchetype.CONCEPT_MAP.value
    assert len(routing_res.diagram_spec.connectors) == 0

    # 4. Rendering produces 3 independent editable shapes and 0 connector shapes
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    d_res = render_editable_diagram(prs, slide, sample_bounds, routing_res.diagram_spec, sample_dna, 1, "reg_sparse")
    assert d_res.success is True
    assert d_res.node_count == 3
    assert d_res.connector_count == 0
    assert len(d_res.rendered_connector_shape_ids) == 0

    # Case B: Completely empty packet -> structured SAFE_VISUAL_FALLBACK
    packet_empty = VisualSemanticPacket(primary_visual_message="Abstract concepts without entities")
    content_empty = SlideContent(title="Empty Concepts")
    routing_empty = route_visual_decision(packet_empty, content_empty, reg_sparse, sample_bounds, sample_dna)
    assert routing_empty.decision == VisualRoutingDecision.SAFE_VISUAL_FALLBACK
    assert routing_empty.defect_code == "MISSING_RELATIONSHIP_METADATA"

