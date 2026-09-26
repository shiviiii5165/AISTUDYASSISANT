"""
LearnByGenie vNEXT Phase 3.1 — Visual Semantic Interpreter
=========================================================
Pure semantic interpreter that converts frozen Phase 1/2 outputs
(SlideBlueprint + SlideContent) into rich VisualSemanticPacket metadata.

Governance:
  - ZERO topic-name branching: all interpretation derives from content
    structure, intent, visual hints, and domain signals.
  - No modification to SlideBlueprint, SlideContent, or any Phase 1/2 contract.
  - Produces typed VisualRelationship / HierarchyNode — no unstructured dicts.
  - Generates ranked VisualCandidate list per slide.
"""
from app.core.logging import logger
from typing import List, Optional, Dict, Any, Tuple

from .schemas import (
    SlideBlueprint,
    SlideContent,
    SlideIntent,
    VisualTypeHint,
    LayoutFamily,
    ContentDensity,
    ComparisonRow,
    ContentOrigin,
    SemanticStatus,
)
from .visual_schemas import (
    VisualIntent,
    VisualAssetType,
    Phase3LayoutFamily,
    RelationshipType,
    VisualRelationship,
    HierarchyNode,
    VisualCandidate,
    VisualDensityProfile,
    VisualSemanticPacket,
    VisualWeight,
    DataGroundingStatus,
    from_legacy_visual_type_hint,
    from_legacy_layout_family,
)


# ═══════════════════════════════════════════════════════════════
# INTENT → VISUAL INTENT MAPPING (semantic, not topic-based)
# ═══════════════════════════════════════════════════════════════

_SLIDE_INTENT_TO_VISUAL_INTENT: Dict[SlideIntent, VisualIntent] = {
    SlideIntent.COVER:                  VisualIntent.HERO_STATEMENT,
    SlideIntent.HOOK:                   VisualIntent.HERO_STATEMENT,
    SlideIntent.CONTEXT:                VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.WHY_IT_MATTERS:         VisualIntent.SHOW_EVIDENCE,
    SlideIntent.AGENDA:                 VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.OBJECTIVES:             VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.PREREQUISITES:          VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.DEFINITION:             VisualIntent.TEXTUAL_SYNTHESIS,
    SlideIntent.MENTAL_MODEL:           VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.CONCEPT_EXPLANATION:    VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.SYSTEM_OVERVIEW:        VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
    SlideIntent.COMPONENT_BREAKDOWN:    VisualIntent.SHOW_HIERARCHY,
    SlideIntent.PROCESS_EXPLANATION:    VisualIntent.SHOW_PROCESS,
    SlideIntent.COMPARISON:             VisualIntent.COMPARE,
    SlideIntent.TRADEOFF:               VisualIntent.COMPARE,
    SlideIntent.WORKED_EXAMPLE:         VisualIntent.SHOW_EXAMPLE,
    SlideIntent.CODE_EXAMPLE:           VisualIntent.SHOW_EXAMPLE,
    SlideIntent.FORMULA_EXPLANATION:    VisualIntent.SHOW_FORMULA,
    SlideIntent.CASE_STUDY:             VisualIntent.SHOW_EVIDENCE,
    SlideIntent.REAL_WORLD_APPLICATION: VisualIntent.SHOW_EXAMPLE,
    SlideIntent.DATA_INSIGHT:           VisualIntent.SHOW_DATA_PATTERN,
    SlideIntent.MISCONCEPTION:          VisualIntent.SHOW_TRANSFORMATION,
    SlideIntent.COMMON_MISTAKES:        VisualIntent.COMPARE,
    SlideIntent.BEST_PRACTICES:         VisualIntent.EXPLAIN_STRUCTURE,
    SlideIntent.DIAGNOSTIC:             VisualIntent.SHOW_DATA_PATTERN,
    SlideIntent.KNOWLEDGE_CHECK:        VisualIntent.TEXTUAL_SYNTHESIS,
    SlideIntent.SUMMARY:                VisualIntent.VISUAL_SUMMARY,
    SlideIntent.REFERENCES:             VisualIntent.TEXTUAL_SYNTHESIS,
    SlideIntent.Q_AND_A:                VisualIntent.HERO_STATEMENT,
}


# ═══════════════════════════════════════════════════════════════
# VISUAL INTENT → ASSET TYPE PREFERENCE ORDER
# ═══════════════════════════════════════════════════════════════

_VISUAL_INTENT_TO_ASSET_PREFERENCES: Dict[VisualIntent, List[VisualAssetType]] = {
    VisualIntent.EXPLAIN_STRUCTURE: [
        VisualAssetType.NATIVE_DIAGRAM, VisualAssetType.ICON_COMPOSITION,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.SHOW_PROCESS: [
        VisualAssetType.PROCESS_FLOW, VisualAssetType.NATIVE_DIAGRAM,
        VisualAssetType.TIMELINE,
    ],
    VisualIntent.SHOW_CAUSALITY: [
        VisualAssetType.NATIVE_DIAGRAM, VisualAssetType.PROCESS_FLOW,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.COMPARE: [
        VisualAssetType.TABLE, VisualAssetType.MATRIX,
        VisualAssetType.NATIVE_DIAGRAM,
    ],
    VisualIntent.SHOW_TIMELINE: [
        VisualAssetType.TIMELINE, VisualAssetType.PROCESS_FLOW,
        VisualAssetType.NATIVE_DIAGRAM,
    ],
    VisualIntent.SHOW_HIERARCHY: [
        VisualAssetType.HIERARCHY, VisualAssetType.NATIVE_DIAGRAM,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.SHOW_DATA_PATTERN: [
        VisualAssetType.CHART, VisualAssetType.TABLE,
        VisualAssetType.NATIVE_DIAGRAM,
    ],
    VisualIntent.SHOW_TRANSFORMATION: [
        VisualAssetType.PROCESS_FLOW, VisualAssetType.NATIVE_DIAGRAM,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.SHOW_SYSTEM_ARCHITECTURE: [
        VisualAssetType.ARCHITECTURE_MAP, VisualAssetType.NATIVE_DIAGRAM,
        VisualAssetType.ICON_COMPOSITION,
    ],
    VisualIntent.SHOW_RELATIONSHIP: [
        VisualAssetType.NATIVE_DIAGRAM, VisualAssetType.ICON_COMPOSITION,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.SHOW_FORMULA: [
        VisualAssetType.FORMULA_VISUAL, VisualAssetType.ANNOTATED_ILLUSTRATION,
        VisualAssetType.TEXTUAL_STATEMENT,
    ],
    VisualIntent.SHOW_EXAMPLE: [
        VisualAssetType.ANNOTATED_ILLUSTRATION, VisualAssetType.TABLE,
        VisualAssetType.ICON_COMPOSITION,
    ],
    VisualIntent.SHOW_EVIDENCE: [
        VisualAssetType.CHART, VisualAssetType.TABLE,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.SHOW_LOCATION: [
        VisualAssetType.AI_ILLUSTRATION, VisualAssetType.ANNOTATED_ILLUSTRATION,
        VisualAssetType.PHOTO,
    ],
    VisualIntent.SHOW_OBJECT: [
        VisualAssetType.PHOTO, VisualAssetType.AI_ILLUSTRATION,
        VisualAssetType.ANNOTATED_ILLUSTRATION,
    ],
    VisualIntent.HERO_STATEMENT: [
        VisualAssetType.TEXTUAL_STATEMENT, VisualAssetType.ICON_COMPOSITION,
        VisualAssetType.AI_ILLUSTRATION,
    ],
    VisualIntent.VISUAL_SUMMARY: [
        VisualAssetType.ICON_COMPOSITION, VisualAssetType.NATIVE_DIAGRAM,
        VisualAssetType.TABLE,
    ],
    VisualIntent.TEXTUAL_SYNTHESIS: [
        VisualAssetType.TEXTUAL_STATEMENT, VisualAssetType.ICON_COMPOSITION,
        VisualAssetType.TABLE,
    ],
}


# ═══════════════════════════════════════════════════════════════
# VISUAL INTENT → LAYOUT PREFERENCE ORDER
# ═══════════════════════════════════════════════════════════════

_VISUAL_INTENT_TO_LAYOUT_PREFERENCES: Dict[VisualIntent, List[Phase3LayoutFamily]] = {
    VisualIntent.EXPLAIN_STRUCTURE: [
        Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.SPLIT_60_40,
    ],
    VisualIntent.SHOW_PROCESS: [
        Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.VISUAL_DOMINANT,
    ],
    VisualIntent.SHOW_CAUSALITY: [
        Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.PROCESS_CANVAS,
    ],
    VisualIntent.COMPARE: [
        Phase3LayoutFamily.COMPARISON_TWO_COLUMN, Phase3LayoutFamily.COMPARISON_MATRIX,
        Phase3LayoutFamily.SPLIT_40_60,
    ],
    VisualIntent.SHOW_TIMELINE: [
        Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.PROCESS_CANVAS,
        Phase3LayoutFamily.VISUAL_DOMINANT,
    ],
    VisualIntent.SHOW_HIERARCHY: [
        Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.VISUAL_DOMINANT,
        Phase3LayoutFamily.SPLIT_40_60,
    ],
    VisualIntent.SHOW_DATA_PATTERN: [
        Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.VISUAL_DOMINANT,
    ],
    VisualIntent.SHOW_TRANSFORMATION: [
        Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.DIAGRAM_CANVAS,
    ],
    VisualIntent.SHOW_SYSTEM_ARCHITECTURE: [
        Phase3LayoutFamily.SYSTEM_ARCHITECTURE, Phase3LayoutFamily.DIAGRAM_CANVAS,
        Phase3LayoutFamily.VISUAL_DOMINANT,
    ],
    VisualIntent.SHOW_RELATIONSHIP: [
        Phase3LayoutFamily.DIAGRAM_CANVAS, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.VISUAL_DOMINANT,
    ],
    VisualIntent.SHOW_FORMULA: [
        Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    VisualIntent.SHOW_EXAMPLE: [
        Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.ANNOTATED_VISUAL,
    ],
    VisualIntent.SHOW_EVIDENCE: [
        Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.ASYMMETRIC_EDITORIAL,
    ],
    VisualIntent.SHOW_LOCATION: [
        Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT,
        Phase3LayoutFamily.SPLIT_40_60,
    ],
    VisualIntent.SHOW_OBJECT: [
        Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT,
        Phase3LayoutFamily.SPLIT_60_40,
    ],
    VisualIntent.HERO_STATEMENT: [
        Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.HERO_OFFSET,
        Phase3LayoutFamily.QUOTE_OR_STATEMENT,
    ],
    VisualIntent.VISUAL_SUMMARY: [
        Phase3LayoutFamily.SUMMARY_GRID, Phase3LayoutFamily.CARD_CLUSTER,
        Phase3LayoutFamily.TEXT_DOMINANT,
    ],
    VisualIntent.TEXTUAL_SYNTHESIS: [
        Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.SPLIT_40_60,
        Phase3LayoutFamily.QUOTE_OR_STATEMENT,
    ],
}


# ═══════════════════════════════════════════════════════════════
# ENTITY / RELATIONSHIP EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════

def _extract_key_entities(
    bp: SlideBlueprint,
    content: Optional[SlideContent],
) -> List[str]:
    """Extract key entities from blueprint canonical concepts and content labels."""
    entities: List[str] = []
    # From blueprint
    if bp.canonical_concepts:
        entities.extend(bp.canonical_concepts)
    if bp.supporting_concepts:
        for sc in bp.supporting_concepts:
            if sc not in entities:
                entities.append(sc)
    # From content labels
    if content and content.labels:
        for label in content.labels:
            if label not in entities:
                entities.append(label)
    return entities


def _extract_relationships(
    bp: SlideBlueprint,
    content: Optional[SlideContent],
    domain: str,
) -> List[VisualRelationship]:
    """Extract typed relationships from content structure.
    No topic-name branching; uses structural signals only."""
    rels: List[VisualRelationship] = []

    # From comparison rows → COMPARATIVE relationships
    if content and content.comparison_rows:
        for row in content.comparison_rows:
            if isinstance(row, ComparisonRow):
                rels.append(VisualRelationship(
                    source_entity=content.comparison_target_a or "Target A",
                    relation=row.dimension,
                    target_entity=content.comparison_target_b or "Target B",
                    relationship_type=RelationshipType.COMPARATIVE,
                    direction="bidirectional",
                    confidence=0.9,
                    visual_importance=0.7,
                ))

    # From process steps → SEQUENTIAL relationships
    if content and content.process_steps and len(content.process_steps) >= 2:
        for i in range(len(content.process_steps) - 1):
            rels.append(VisualRelationship(
                source_entity=content.process_steps[i],
                relation="leads_to",
                target_entity=content.process_steps[i + 1],
                relationship_type=RelationshipType.SEQUENTIAL,
                direction="forward",
                confidence=0.9,
                visual_importance=0.6,
            ))

    # From blueprint supporting concepts → STRUCTURAL relationships
    if bp.primary_message and bp.supporting_concepts:
        primary = bp.primary_message[:60]  # Truncate for entity label
        for concept in bp.supporting_concepts[:4]:
            rels.append(VisualRelationship(
                source_entity=primary,
                relation="supports",
                target_entity=concept,
                relationship_type=RelationshipType.STRUCTURAL,
                direction="forward",
                confidence=0.7,
                visual_importance=0.4,
            ))

    return rels


def _extract_causal_structure(
    content: Optional[SlideContent],
) -> List[VisualRelationship]:
    """Extract causal relationships from content if available."""
    causals: List[VisualRelationship] = []
    if not content:
        return causals

    # Detect causal patterns in supporting points
    causal_keywords = {"causes", "leads to", "results in", "because", "therefore", "consequently"}
    for point in content.supporting_points:
        lower = point.lower()
        for kw in causal_keywords:
            if kw in lower:
                # Split around the causal keyword
                parts = lower.split(kw, 1)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    causals.append(VisualRelationship(
                        source_entity=parts[0].strip()[:50],
                        relation=kw,
                        target_entity=parts[1].strip()[:50],
                        relationship_type=RelationshipType.CAUSAL,
                        direction="forward",
                        confidence=0.7,
                        visual_importance=0.6,
                    ))
                break
    return causals


def _extract_hierarchy(
    bp: SlideBlueprint,
    content: Optional[SlideContent],
) -> List[HierarchyNode]:
    """Build typed hierarchy from content structure."""
    nodes: List[HierarchyNode] = []

    # Only for hierarchy/component-oriented intents
    if bp.intent not in (
        SlideIntent.COMPONENT_BREAKDOWN, SlideIntent.SYSTEM_OVERVIEW,
        SlideIntent.CONCEPT_EXPLANATION, SlideIntent.BEST_PRACTICES,
    ):
        return nodes

    if not content or not content.supporting_points:
        return nodes

    # Build flat hierarchy: primary concept → supporting points
    root = HierarchyNode(
        label=content.title or bp.primary_message[:40],
        level=0,
        parent_label="",
        is_leaf=False,
        visual_weight=1.0,
    )
    for point in content.supporting_points[:6]:
        child = HierarchyNode(
            label=point[:50],
            level=1,
            parent_label=root.label,
            is_leaf=True,
            visual_weight=0.5,
        )
        root.children.append(child)

    nodes.append(root)
    return nodes


def _build_visual_candidates(
    visual_intent: VisualIntent,
    bp: SlideBlueprint,
    content: Optional[SlideContent],
) -> List[VisualCandidate]:
    """Build ranked visual candidate list based on visual intent and content signals."""
    candidates: List[VisualCandidate] = []

    asset_prefs = _VISUAL_INTENT_TO_ASSET_PREFERENCES.get(
        visual_intent,
        [VisualAssetType.TEXTUAL_STATEMENT],
    )
    layout_prefs = _VISUAL_INTENT_TO_LAYOUT_PREFERENCES.get(
        visual_intent,
        [Phase3LayoutFamily.TEXT_DOMINANT],
    )

    for rank, (asset, layout) in enumerate(zip(asset_prefs, layout_prefs)):
        score = max(0.3, 1.0 - (rank * 0.2))
        requires_data = asset in (VisualAssetType.CHART, VisualAssetType.TABLE)
        requires_image = asset in (
            VisualAssetType.PHOTO, VisualAssetType.AI_ILLUSTRATION,
            VisualAssetType.ANNOTATED_ILLUSTRATION,
        )
        complexity = "low" if rank == 0 else ("medium" if rank == 1 else "high")

        candidates.append(VisualCandidate(
            asset_type=asset,
            layout_family=layout,
            suitability_score=score,
            rationale=f"Rank {rank + 1} for {visual_intent.value}: {asset.value} in {layout.value}",
            requires_data=requires_data,
            requires_image=requires_image,
            complexity_estimate=complexity,
        ))

    return candidates


def _compute_visual_density(
    bp: SlideBlueprint,
    content: Optional[SlideContent],
) -> VisualDensityProfile:
    """Compute visual density independently from content density."""
    # Count visual elements
    element_count_score = 0
    if content:
        element_count_score += len(content.supporting_points)
        element_count_score += len(content.process_steps)
        element_count_score += len(content.comparison_rows)
        element_count_score += len(content.data_points)
        if content.formula:
            element_count_score += 2
        if content.code:
            element_count_score += 2

    if element_count_score <= 3:
        el_count = "sparse"
        whitespace = 0.45
    elif element_count_score <= 6:
        el_count = "medium"
        whitespace = 0.35
    else:
        el_count = "dense"
        whitespace = 0.25

    # Decoration level based on visual priority
    if bp.visual_priority >= 0.7:
        decoration = "rich"
    elif bp.visual_priority >= 0.4:
        decoration = "moderate"
    else:
        decoration = "minimal"

    return VisualDensityProfile(
        element_count=el_count,
        whitespace_ratio=whitespace,
        decoration_level=decoration,
        animation_density="subtle",
    )


# ═══════════════════════════════════════════════════════════════
# DATA GROUNDING STATUS DERIVATION
# ═══════════════════════════════════════════════════════════════

def _derive_data_grounding_status(content: Optional[SlideContent]) -> str:
    """Derive data grounding status from Phase 2 content provenance.

    Rules:
      - SOURCE_DOCUMENT origin with GROUNDED status → VERIFIED_DATA or SOURCE_GROUNDED
      - EXTERNAL_SOURCE → SOURCE_GROUNDED
      - MODEL_BACKGROUND → MODEL_BACKGROUND (NOT chart-safe)
      - DETERMINISTIC_STRUCTURE → STRUCTURAL_ONLY
      - No content or GAP status → UNRESOLVED
    """
    if not content:
        return DataGroundingStatus.UNRESOLVED.value

    # If semantic status is GAP, data is unresolved
    if content.semantic_status == SemanticStatus.GAP:
        return DataGroundingStatus.UNRESOLVED.value

    # Map content_origin to grounding status
    origin = content.content_origin

    if origin == ContentOrigin.SOURCE_DOCUMENT:
        # Verified data if it has verified data points
        if content.data_points and any(dp.is_verified for dp in content.data_points):
            return DataGroundingStatus.VERIFIED_DATA.value
        return DataGroundingStatus.SOURCE_GROUNDED.value
    elif origin == ContentOrigin.EXTERNAL_SOURCE:
        return DataGroundingStatus.SOURCE_GROUNDED.value
    elif origin == ContentOrigin.MODEL_BACKGROUND:
        return DataGroundingStatus.MODEL_BACKGROUND.value
    elif origin == ContentOrigin.DETERMINISTIC_STRUCTURE:
        return DataGroundingStatus.STRUCTURAL_ONLY.value
    elif origin == ContentOrigin.CONTENT_SEMANTIC_GAP:
        return DataGroundingStatus.UNRESOLVED.value
    else:
        return DataGroundingStatus.STRUCTURAL_ONLY.value


# ═══════════════════════════════════════════════════════════════
# MAIN INTERPRETER
# ═══════════════════════════════════════════════════════════════

def interpret_slide_visuals(
    blueprint: SlideBlueprint,
    content: Optional[SlideContent],
    domain: str = "general",
    subdomain: str = "",
) -> VisualSemanticPacket:
    """Convert a single SlideBlueprint + SlideContent into a VisualSemanticPacket.

    Pure semantic interpreter — zero topic-name branching.
    Derives visual intent from SlideIntent + VisualTypeHint + content signals.

    Args:
        blueprint: Frozen Phase 1 slide blueprint
        content: Frozen Phase 2 slide content (may be None)
        domain: Classified domain (used for density tuning, not topic branching)
        subdomain: Classified subdomain

    Returns:
        VisualSemanticPacket with typed relationships, hierarchy, and candidates
    """
    # 1. Determine visual intent — prefer VisualTypeHint signal, fall back to SlideIntent
    if blueprint.visual_type != VisualTypeHint.NONE:
        visual_intent = from_legacy_visual_type_hint(blueprint.visual_type)
    else:
        visual_intent = _SLIDE_INTENT_TO_VISUAL_INTENT.get(
            blueprint.intent, VisualIntent.TEXTUAL_SYNTHESIS
        )

    # 2. Override with content-structure signals (zero topic branching)
    if content:
        if content.process_steps and len(content.process_steps) >= 2:
            if visual_intent not in (VisualIntent.SHOW_PROCESS, VisualIntent.SHOW_TIMELINE):
                visual_intent = VisualIntent.SHOW_PROCESS
        elif content.comparison_rows and len(content.comparison_rows) >= 1:
            visual_intent = VisualIntent.COMPARE
        elif content.formula:
            visual_intent = VisualIntent.SHOW_FORMULA
        elif content.data_points and len(content.data_points) >= 2:
            visual_intent = VisualIntent.SHOW_DATA_PATTERN

    # 3. Extract semantic structures
    key_entities = _extract_key_entities(blueprint, content)
    relationships = _extract_relationships(blueprint, content, domain)
    causal_structure = _extract_causal_structure(content)
    hierarchy_tree = _extract_hierarchy(blueprint, content)

    # 4. Extract process/comparison/temporal structures
    process_nodes = []
    comparison_targets = []
    quantitative_vars = []
    temporal_structure = []
    system_components = []
    formula_or_eq = None

    if content:
        process_nodes = list(content.process_steps) if content.process_steps else []
        if content.comparison_target_a and content.comparison_target_b:
            comparison_targets = [content.comparison_target_a, content.comparison_target_b]
        quantitative_vars = [dp.metric for dp in content.data_points if dp.metric]
        formula_or_eq = content.formula if content.formula else None

    # System components from canonical concepts if system-oriented intent
    if blueprint.intent in (SlideIntent.SYSTEM_OVERVIEW, SlideIntent.COMPONENT_BREAKDOWN):
        system_components = list(blueprint.canonical_concepts)

    # 5. Build visual candidates (ranked)
    visual_candidates = _build_visual_candidates(visual_intent, blueprint, content)

    # 6. Compute visual density independently
    visual_density = _compute_visual_density(blueprint, content)

    # 7. Compute visual priority
    visual_priority = blueprint.visual_priority
    if visual_intent in (
        VisualIntent.SHOW_SYSTEM_ARCHITECTURE, VisualIntent.SHOW_PROCESS,
        VisualIntent.SHOW_HIERARCHY, VisualIntent.SHOW_DATA_PATTERN,
    ):
        visual_priority = max(visual_priority, 0.7)
    elif visual_intent in (
        VisualIntent.HERO_STATEMENT, VisualIntent.TEXTUAL_SYNTHESIS,
    ):
        visual_priority = min(visual_priority, 0.4)

    # 8. Build grounding evidence
    grounding_evidence: List[str] = []
    grounding_evidence.append(f"slide_intent={blueprint.intent.value}")
    grounding_evidence.append(f"visual_type_hint={blueprint.visual_type.value}")
    if content:
        grounding_evidence.append(f"semantic_status={content.semantic_status.value}")
    grounding_evidence.append(f"domain={domain}")

    # 9. Build diagram/chart candidates
    diagram_candidate = None
    chart_candidate = None
    if visual_intent in (
        VisualIntent.SHOW_PROCESS, VisualIntent.SHOW_CAUSALITY,
        VisualIntent.SHOW_HIERARCHY, VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
        VisualIntent.EXPLAIN_STRUCTURE, VisualIntent.SHOW_RELATIONSHIP,
    ):
        diagram_candidate = f"{visual_intent.value}_diagram"
    if visual_intent in (VisualIntent.SHOW_DATA_PATTERN, VisualIntent.SHOW_EVIDENCE):
        chart_candidate = "data_visualization"

    # 10. Must-visualize items
    must_visualize = []
    if process_nodes:
        must_visualize.append("process_flow")
    if comparison_targets:
        must_visualize.append("comparison_matrix")
    if hierarchy_tree:
        must_visualize.append("hierarchy_tree")
    if formula_or_eq:
        must_visualize.append("formula")

    # 11. Image candidate concepts
    image_concepts = []
    if visual_intent in (VisualIntent.SHOW_OBJECT, VisualIntent.SHOW_LOCATION):
        image_concepts.extend(key_entities[:3])

    # 12. Annotation candidates
    annotation_candidates = []
    if visual_intent in (VisualIntent.EXPLAIN_STRUCTURE, VisualIntent.SHOW_SYSTEM_ARCHITECTURE):
        annotation_candidates = key_entities[:4]

    # 13. Emphasis targets
    emphasis_targets = []
    if content and content.primary_takeaway:
        emphasis_targets.append(content.primary_takeaway[:60])
    if content and content.callout:
        emphasis_targets.append(content.callout[:60])

    packet = VisualSemanticPacket(
        slide_no=blueprint.slide_number,
        semantic_role=blueprint.semantic_role or blueprint.intent.value,
        primary_visual_message=blueprint.primary_message,
        visual_intent=visual_intent,
        visual_priority=visual_priority,
        key_entities=key_entities,
        relationships=relationships,
        hierarchy_tree=hierarchy_tree,
        process_nodes=process_nodes,
        comparison_targets=comparison_targets,
        quantitative_variables=quantitative_vars,
        temporal_structure=temporal_structure,
        spatial_structure=[],
        system_components=system_components,
        formula_or_equation=formula_or_eq,
        causal_structure=causal_structure,
        data_requirements=[f"data_for_{var}" for var in quantitative_vars],
        image_candidate_concepts=image_concepts,
        diagram_candidate=diagram_candidate,
        chart_candidate=chart_candidate,
        annotation_candidates=annotation_candidates,
        emphasis_targets=emphasis_targets,
        must_visualize=must_visualize,
        must_not_visualize=[],
        visual_candidates=visual_candidates,
        content_density=blueprint.content_density,
        visual_density=visual_density,
        visual_confidence=0.85 if content else 0.6,
        grounding_source="semantic_interpretation",
        grounding_evidence=grounding_evidence,
        data_grounding_status=_derive_data_grounding_status(content),
    )

    logger.debug(
        f"[VisualInterpreter] Slide {blueprint.slide_number}: "
        f"intent={visual_intent.value}, "
        f"candidates={len(visual_candidates)}, "
        f"entities={len(key_entities)}, "
        f"relationships={len(relationships)}"
    )

    return packet


def interpret_deck_visuals(
    blueprints: List[SlideBlueprint],
    contents: List[Optional[SlideContent]],
    domain: str = "general",
    subdomain: str = "",
) -> List[VisualSemanticPacket]:
    """Interpret visual semantics for an entire deck.

    Args:
        blueprints: Frozen Phase 1 slide blueprints
        contents: Frozen Phase 2 slide contents (aligned by index)
        domain: Classified domain
        subdomain: Classified subdomain

    Returns:
        List of VisualSemanticPacket, one per slide
    """
    packets: List[VisualSemanticPacket] = []
    for i, bp in enumerate(blueprints):
        content = contents[i] if i < len(contents) else None
        packet = interpret_slide_visuals(bp, content, domain, subdomain)
        packets.append(packet)

    logger.info(
        f"[VisualInterpreter] Interpreted {len(packets)} slides for domain={domain}"
    )
    return packets
