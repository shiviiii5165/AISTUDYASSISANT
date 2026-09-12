"""
Domain Visualization Registry
=============================
Unified routing dispatcher between Specialized Quality Overrides and Universal Archetypes.
Ensures the system NEVER fails for any topic.
"""
from typing import Dict, Type
from app.core.logging import logger
from ..schemas import SceneSpec, VisualStrategyArchetype
from .base import BaseVisualizer
from .archetypes.flow_process import FlowProcessVisualizer
from .archetypes.timeline import TimelineVisualizer
from .archetypes.comparison import ComparisonVisualizer
from .archetypes.hierarchy import HierarchyVisualizer
from .archetypes.concept_map import ConceptMapVisualizer
from .archetypes.equation import EquationVisualizer
from .archetypes.graph_plot import GraphPlotVisualizer
from .archetypes.table_chart import TableChartVisualizer
from .archetypes.generic_diagram import GenericDiagramVisualizer
from .specialized.linked_list import LinkedListVisualizer


class DomainVisualizationRegistry:
    """Dispatches rendering requests to specialized or archetype visualizers."""

    # 1. Specialized Topic Registry (Optional high-value overrides)
    SPECIALIZED_REGISTRY: Dict[str, Type[BaseVisualizer]] = {
        "linked list": LinkedListVisualizer,
        "singly linked list": LinkedListVisualizer,
        "doubly linked list": LinkedListVisualizer,
    }

    # 2. Universal Visual Archetype Map
    ARCHETYPE_MAP: Dict[VisualStrategyArchetype, Type[BaseVisualizer]] = {
        VisualStrategyArchetype.PROCESS_FLOW: FlowProcessVisualizer,
        VisualStrategyArchetype.SCIENTIFIC_PROCESS: FlowProcessVisualizer,
        VisualStrategyArchetype.STEP_SEQUENCE: FlowProcessVisualizer,
        VisualStrategyArchetype.ALGORITHM_TRACE: FlowProcessVisualizer,
        VisualStrategyArchetype.TIMELINE: TimelineVisualizer,
        VisualStrategyArchetype.CAUSE_EFFECT: TimelineVisualizer,
        VisualStrategyArchetype.COMPARISON: ComparisonVisualizer,
        VisualStrategyArchetype.HIERARCHY: HierarchyVisualizer,
        VisualStrategyArchetype.SYSTEM_ARCHITECTURE: HierarchyVisualizer,
        VisualStrategyArchetype.CONCEPT_MAP: ConceptMapVisualizer,
        VisualStrategyArchetype.NETWORK: ConceptMapVisualizer,
        VisualStrategyArchetype.MATHEMATICAL_DERIVATION: EquationVisualizer,
        VisualStrategyArchetype.FORMULA_VISUALIZATION: EquationVisualizer,
        VisualStrategyArchetype.GRAPH_PLOT: GraphPlotVisualizer,
        VisualStrategyArchetype.TABLE: TableChartVisualizer,
        VisualStrategyArchetype.CHART: TableChartVisualizer,
        VisualStrategyArchetype.GENERIC_DIAGRAM: GenericDiagramVisualizer,
        VisualStrategyArchetype.TEXTUAL_EXPLAINER: GenericDiagramVisualizer,
        VisualStrategyArchetype.REAL_WORLD_EXAMPLE: GenericDiagramVisualizer,
    }

    @classmethod
    def get_visualizer(cls, topic: str, archetype: VisualStrategyArchetype) -> Type[BaseVisualizer]:
        """
        Dispatches according to strict production routing order:
        1. Check if specialized visualizer exists for topic
        2. Else map to generic archetype visualizer
        3. Fallback safely to GenericDiagramVisualizer
        """
        clean_topic = topic.lower().strip()

        # 1. Specialized override
        for key, vis_cls in cls.SPECIALIZED_REGISTRY.items():
            if key in clean_topic or clean_topic in key:
                logger.debug(f"[VisualRegistry] Dispatched to specialized visualizer: {vis_cls.__name__}")
                return vis_cls

        # 2. Archetype map
        if archetype in cls.ARCHETYPE_MAP:
            return cls.ARCHETYPE_MAP[archetype]

        # 3. Guaranteed fallback
        return GenericDiagramVisualizer

    @classmethod
    def render_scene_media(cls, scene: SceneSpec, topic: str, output_path: str, style: str = "academic") -> str:
        """Renders scene media with failsafe fallback guarantees."""
        visualizer_cls = cls.get_visualizer(topic, scene.visual_strategy)
        try:
            return visualizer_cls.render_scene(scene, output_path, style=style)
        except Exception as e:
            logger.warning(f"[VisualRegistry] Visualizer {visualizer_cls.__name__} notice: {e}. Using Generic fallback.")
            return GenericDiagramVisualizer.render_scene(scene, output_path, style=style)
