"""
TeachGenie Notes Decision Engine — Deterministic Visual Planner
===============================================================
Constructs VisualPlan blueprint specifying type, requirement, and focus
without generating visual diagrams or prose. Zero LLM calls.
"""
from typing import List, Optional
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.schemas import NoteFormat
from .schemas import VisualPlan
from .policies import TopicCategory


class VisualPlanner:
    """Plans structural visual requirements based on topic nature and format selections."""

    @classmethod
    def plan(
        cls,
        ctx: CanonicalNotesContext,
        topic_category: TopicCategory,
        selected_formats: List[NoteFormat]
    ) -> VisualPlan:
        topic_title = ctx.topic or "Topic"

        # 1. Explicit flowchart request or process topic
        if NoteFormat.FLOWCHART in selected_formats or topic_category == TopicCategory.PROCESS:
            return VisualPlan(
                required=True,
                type="flowchart",
                focus=f"Sequential process stages and transition mechanisms of {topic_title}"
            )

        # 2. Explicit comparison notes or comparison topic
        if NoteFormat.COMPARISON_NOTES in selected_formats or topic_category == TopicCategory.COMPARISON:
            return VisualPlan(
                required=True,
                type="comparison_matrix",
                focus=f"Comparative distinction and feature contrast matrix for {topic_title}"
            )

        # 3. Explicit mind map format
        if NoteFormat.MIND_MAP in selected_formats:
            return VisualPlan(
                required=True,
                type="mind_map",
                focus=f"Classification taxonomy and branch relationships of {topic_title}"
            )

        # 4. Chronological topic
        if topic_category == TopicCategory.CHRONOLOGICAL:
            return VisualPlan(
                required=True,
                type="timeline",
                focus=f"Historical sequence and milestones of {topic_title}"
            )

        # 5. Cause and effect topic
        if topic_category == TopicCategory.CAUSE_EFFECT:
            return VisualPlan(
                required=True,
                type="diagram",
                focus=f"Direct triggers and resulting environmental or system consequences of {topic_title}"
            )

        # 6. Conceptual topic (e.g. Newton's Laws)
        if topic_category == TopicCategory.CONCEPTUAL:
            return VisualPlan(
                required=True,
                type="concept_map",
                focus=f"Core conceptual hierarchy of {topic_title}"
            )

        # 7. PPT diagram ideas signal
        if hasattr(ctx, "ppt") and ctx.ppt and ctx.ppt.diagram_ideas:
            return VisualPlan(
                required=True,
                type="diagram",
                focus=ctx.ppt.diagram_ideas[0]
            )

        # 8. Default: visual is optional
        return VisualPlan(
            required=False,
            type="optional",
            focus=None
        )
