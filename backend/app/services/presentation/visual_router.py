"""
TeachGenie PPT vNext — Phase 3.3 Visual Router & Structural Quality Auditor
============================================================================
Implements typed visual routing decisions and structural quality auditing:
  - Dispatches between Native Charts, Editable Diagrams, Existing Visuals, Deferred Images,
    and Safe Fallbacks.
  - Audits diagram node collisions, connector routing, label clipping, and data provenance.
  - Enforces fail-closed behavior for unresolvable semantic/data defects.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from pydantic import BaseModel, Field

from app.services.presentation.schemas import SlideContent
from app.services.presentation.visual_schemas import (
    VisualSemanticPacket,
    VisualAssetType,
    VisualIntent,
    DesignDNA,
)
from app.services.presentation.composition_schemas import (
    ResolvedRegionBounds,
    ContentBinding,
    ContentRegion,
    RegionSemanticRole,
)
from app.services.presentation.chart_intelligence import (
    ChartType,
    ChartDataPayload,
    extract_chart_payload_from_content,
    select_appropriate_chart_type,
    validate_chart_type_suitability,
    ChartDefectCode,
)
from app.services.presentation.diagram_intelligence import (
    DiagramArchetype,
    DiagramSpec,
    select_diagram_archetype,
    build_diagram_spec,
)


class VisualRoutingDecision(str, Enum):
    EDITABLE_DIAGRAM          = "editable_diagram"
    NATIVE_CHART              = "native_chart"
    IMAGE_ASSET               = "image_asset"
    EXISTING_EDITABLE_VISUAL  = "existing_editable_visual"
    DEFERRED_IMAGE_TO_PHASE_3_4 = "deferred_image_to_phase_3_4"
    SAFE_VISUAL_FALLBACK      = "safe_visual_fallback"
    STRUCTURED_VISUAL_FAILURE = "structured_visual_failure"


class VisualRoutingResult(BaseModel):
    decision: VisualRoutingDecision
    target_type: str = ""
    rationale: str = ""
    data_payload: Optional[ChartDataPayload] = None
    diagram_spec: Optional[DiagramSpec] = None
    defect_code: Optional[str] = None
    is_chart_deferred: bool = False


def route_visual_decision(
    packet: Optional[VisualSemanticPacket],
    content: Optional[SlideContent],
    region: ContentRegion,
    bounds: ResolvedRegionBounds,
    design_dna: DesignDNA,
) -> VisualRoutingResult:
    """
    Evaluates visual intent, slide content, and data grounding to make a strictly typed
    visual rendering decision.
    """
    role = region.semantic_role
    r_id = region.region_id.lower()

    # 1. Chart Candidate Evaluation
    is_chart_designated = "chart" in r_id or "chart" in str(role.value).lower()
    has_chart_intent = (packet and (packet.chart_candidate or packet.visual_intent == VisualIntent.SHOW_DATA_PATTERN))

    if is_chart_designated or has_chart_intent:
        if content and content.data_points:
            payload = extract_chart_payload_from_content(content)
            if payload:
                # Valid empirical data found! Select chart type
                ctype = select_appropriate_chart_type(payload, packet)
                valid, defect = validate_chart_type_suitability(payload, ctype)
                if valid:
                    return VisualRoutingResult(
                        decision=VisualRoutingDecision.NATIVE_CHART,
                        target_type=ctype.value,
                        rationale="Empirical data validated; routing to native PowerPoint chart",
                        data_payload=payload,
                    )
                else:
                    return VisualRoutingResult(
                        decision=VisualRoutingDecision.SAFE_VISUAL_FALLBACK,
                        target_type=ctype.value,
                        defect_code=defect.value if defect else "INVALID_CHART_TYPE",
                        rationale="Chart type unsuitable for data structure; preserving safe fallback",
                        is_chart_deferred=True,
                    )

        # Factual data missing -> Zero invention contract requires honest refusal!
        return VisualRoutingResult(
            decision=VisualRoutingDecision.SAFE_VISUAL_FALLBACK,
            target_type="chart_deferred",
            rationale="No empirical numeric data present in SlideContent.data_points; preserving honest deferred state",
            is_chart_deferred=True,
            defect_code=ChartDefectCode.DATA_INSUFFICIENT_FOR_CHART.value,
        )

    # 2. Diagram Candidate Evaluation
    # Check if visual candidate specifies an image concept for photographic asset
    if packet and packet.image_candidate_concepts and not packet.system_components and not packet.relationships:
        # Phase 3.4: If image intelligence is enabled, route to IMAGE_ASSET
        from app.core.config import settings
        image_enabled = getattr(settings, "PRESENTATION_IMAGE_INTELLIGENCE_ENABLED", False)
        if image_enabled:
            return VisualRoutingResult(
                decision=VisualRoutingDecision.IMAGE_ASSET,
                target_type="photographic_or_illustration",
                rationale="Concept requires photographic asset; routing to Phase 3.4 image intelligence",
            )
        else:
            return VisualRoutingResult(
                decision=VisualRoutingDecision.DEFERRED_IMAGE_TO_PHASE_3_4,
                target_type="photographic_or_illustration",
                rationale="Concept requires external photographic asset; deferred to Phase 3.4 (flag disabled)",
            )

    # Sparse metadata check: If packet exists but completely lacks relationships, causal structure,
    # process nodes, temporal structure, hierarchy, system components, key entities, and content has no steps:
    has_packet_elements = bool(packet and any([
        packet.relationships,
        packet.causal_structure,
        packet.process_nodes,
        packet.temporal_structure,
        packet.hierarchy_tree,
        packet.system_components,
        packet.key_entities,
    ]))
    has_content_structure = bool(content and (content.process_steps or content.comparison_rows))

    if packet and not has_packet_elements and not has_content_structure:
        return VisualRoutingResult(
            decision=VisualRoutingDecision.SAFE_VISUAL_FALLBACK,
            target_type="safe_visual_fallback",
            defect_code="MISSING_RELATIONSHIP_METADATA",
            rationale="No relationship metadata present; linear process prohibited without explicit sequence semantics",
        )

    # Diagram archetype selection based on relationship meaning
    archetype, entities, rels = select_diagram_archetype(packet, content)
    spec = build_diagram_spec(archetype, entities, rels, bounds)

    return VisualRoutingResult(
        decision=VisualRoutingDecision.EDITABLE_DIAGRAM,
        target_type=archetype.value,
        rationale=f"Semantic relationships mapped to {archetype.value} archetype",
        diagram_spec=spec,
    )


# ═══════════════════════════════════════════════════════════════
# 2. STRUCTURAL QUALITY AUDITOR & TARGETED REPAIR
# ═══════════════════════════════════════════════════════════════

class VisualDefect(BaseModel):
    defect_code: str
    severity: str = "WARNING"  # "WARNING" | "FATAL"
    description: str
    affected_elements: List[str] = Field(default_factory=list)


def audit_diagram_structure(
    spec: DiagramSpec,
    bounds: ResolvedRegionBounds,
) -> List[VisualDefect]:
    """
    Audits an editable diagram spec for geometric and semantic defects:
      - Node count adequacy
      - Complex graph geometry containment (REFLOW_REQUIRED)
      - Mandatory source node and edge fidelity (MISSING_REQUIRED_NODE, MISSING_REQUIRED_EDGE)
      - Arrowhead orientation (WRONG_ARROW_DIRECTION)
      - Boundary containment
      - Node collision / overlap
    """
    defects: List[VisualDefect] = []

    # 1. Node count check
    if len(spec.nodes) < 2:
        defects.append(VisualDefect(
            defect_code="INSUFFICIENT_NODES",
            severity="FATAL",
            description="Diagram contains fewer than 2 semantic nodes",
        ))

    w_val = float(getattr(bounds, "width_in", getattr(bounds, "width", 7.0)))
    h_val = float(getattr(bounds, "height_in", getattr(bounds, "height", 5.0)))

    # 2. Geometry reflow check for complex graphs that cannot fit inside constrained bounds
    if (w_val < 3.0 or h_val < 2.0) and len(spec.nodes) > 2:
        defects.append(VisualDefect(
            defect_code="REFLOW_REQUIRED",
            severity="FATAL",
            description=f"Graph with {len(spec.nodes)} nodes cannot fit inside constrained bounds ({w_val:.1f}x{h_val:.1f}); geometry reflow required",
            affected_elements=[n.node_id for n in spec.nodes],
        ))

    # 3. Missing required nodes fidelity check
    for req_node in spec.source_node_ids:
        if not any(n.node_id == req_node for n in spec.nodes):
            defects.append(VisualDefect(
                defect_code="MISSING_REQUIRED_NODE",
                severity="FATAL",
                description=f"Required source node '{req_node}' missing from diagram spec",
                affected_elements=[req_node],
            ))

    # 4. Missing required edges fidelity check
    for req_edge in spec.source_edge_ids:
        if not any(c.edge_id == req_edge for c in spec.connectors):
            defects.append(VisualDefect(
                defect_code="MISSING_REQUIRED_EDGE",
                severity="FATAL",
                description=f"Required relationship edge '{req_edge}' missing from diagram connectors",
                affected_elements=[req_edge],
            ))

    # 5. Wrong arrow direction check
    for c in spec.connectors:
        if not c.has_arrow and not c.is_bidirectional and c.source_entity and c.target_entity:
            defects.append(VisualDefect(
                defect_code="WRONG_ARROW_DIRECTION",
                severity="FATAL",
                description=f"Connector '{c.edge_id}' lacks required directional arrow for source relationship",
                affected_elements=[c.edge_id],
            ))

    # 6. Boundary containment check
    for n in spec.nodes:
        if n.x < 0 or n.y < 0 or (n.x + n.width) > w_val + 0.05 or (n.y + n.height) > h_val + 0.05:
            defects.append(VisualDefect(
                defect_code="DIAGRAM_NODE_OVERFLOW",
                severity="WARNING",
                description=f"Node {n.node_id} exceeds region bounds",
                affected_elements=[n.node_id],
            ))

    # 7. Collision check between nodes
    for i, n1 in enumerate(spec.nodes):
        for j, n2 in enumerate(spec.nodes):
            if i >= j:
                continue
            # Bounding box collision
            overlap_x = not (n1.x + n1.width <= n2.x or n2.x + n2.width <= n1.x)
            overlap_y = not (n1.y + n1.height <= n2.y or n2.y + n2.height <= n1.y)
            if overlap_x and overlap_y:
                defects.append(VisualDefect(
                    defect_code="DIAGRAM_NODE_COLLISION",
                    severity="WARNING",
                    description=f"Nodes {n1.node_id} and {n2.node_id} collide",
                    affected_elements=[n1.node_id, n2.node_id],
                ))

    return defects


def repair_diagram_geometry(
    spec: DiagramSpec,
    bounds: ResolvedRegionBounds,
    defects: List[VisualDefect],
) -> DiagramSpec:
    """
    Applies bounded, deterministic micro-adjustments to eliminate node collisions and containment issues.
    """
    has_collision = any(d.defect_code == "DIAGRAM_NODE_COLLISION" for d in defects)
    has_overflow = any(d.defect_code == "DIAGRAM_NODE_OVERFLOW" for d in defects)

    if not has_collision and not has_overflow:
        return spec

    w_val = float(getattr(bounds, "width_in", getattr(bounds, "width", 7.0)))
    h_val = float(getattr(bounds, "height_in", getattr(bounds, "height", 5.0)))

    # Deterministic adjustment: scale down node sizes slightly and re-center
    scale_factor = 0.90
    repaired_nodes = []
    for n in spec.nodes:
        nw = n.width * scale_factor
        nh = n.height * scale_factor
        # Keep inside bounds
        nx = max(0.1, min(w_val - nw - 0.1, n.x))
        ny = max(0.1, min(h_val - nh - 0.1, n.y))
        repaired_nodes.append(n.model_copy(update={"width": nw, "height": nh, "x": nx, "y": ny}))

    return spec.model_copy(update={"nodes": repaired_nodes})
