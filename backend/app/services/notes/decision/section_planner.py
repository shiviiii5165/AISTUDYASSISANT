"""
TeachGenie Notes Decision Engine — Deterministic Section Planner
================================================================
Constructs an ordered section blueprint (SectionPlanItem) specifying
required sections and their specific pedagogical targets.
"""
from typing import List, Optional
from app.services.notes.schemas import NoteFormat
from .schemas import SectionPlanItem


class SectionPlanner:
    """Builds an ordered, deterministic sequence of section requirements."""

    @classmethod
    def plan(
        cls,
        selected_formats: List[NoteFormat],
        has_misconceptions: bool,
        misconceptions: List[str],
        class_num: int,
        is_active_mode: bool = False
    ) -> List[SectionPlanItem]:
        """
        Constructs an ordered blueprint:
        1. overview
        2. core_concept
        3. visual / structural representations (flowchart, comparison_table, formula_box, mind_map)
        4. worked_example
        5. common_misconceptions (targeted)
        6. exam_tips (Class >= 9 or exam prep)
        7. thinking_checkpoint (active mode)
        8. quick_summary
        9. checkpoint_practice
        """
        plan: List[SectionPlanItem] = []

        # 1. Overview
        plan.append(SectionPlanItem(type="overview", required=True))

        # 2. Core Concept
        plan.append(SectionPlanItem(type="core_concept", required=True))

        # 3. Format-specific representations
        if NoteFormat.FLOWCHART in selected_formats:
            plan.append(SectionPlanItem(type="flowchart", required=True))

        if NoteFormat.COMPARISON_NOTES in selected_formats:
            plan.append(SectionPlanItem(type="comparison_table", required=True))

        if NoteFormat.FORMULA_SHEET in selected_formats:
            plan.append(SectionPlanItem(type="formula_box", required=True))

        if NoteFormat.MIND_MAP in selected_formats:
            plan.append(SectionPlanItem(type="mind_map", required=True))

        # 4. Worked Example (Standard requirement)
        plan.append(SectionPlanItem(type="worked_example", required=True))

        # 5. Targeted Misconceptions
        if has_misconceptions or NoteFormat.REMEDIAL_NOTES in selected_formats:
            target_str = ", ".join(misconceptions[:2]) if misconceptions else None
            plan.append(SectionPlanItem(
                type="common_misconceptions",
                required=True,
                target=target_str
            ))

        # 6. Exam Tips (Secondary / Senior secondary or Exam Prep)
        if class_num >= 9 or NoteFormat.EXAM_PREPARATION in selected_formats:
            plan.append(SectionPlanItem(type="exam_tips", required=True))

        # 7. Thinking Checkpoints (Active mode only)
        if is_active_mode:
            plan.append(SectionPlanItem(type="thinking_checkpoint", required=True))

        # 8. Quick Summary
        plan.append(SectionPlanItem(type="quick_summary", required=True))

        # 9. Checkpoint Practice
        plan.append(SectionPlanItem(type="checkpoint_practice", required=True))

        return plan
