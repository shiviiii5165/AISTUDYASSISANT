"""
Content Budget & Layout Capacity Engine (Phase 2)
==================================================
Defines layout capacity profiles based on LayoutFamily and VisualTypeHint.
Computes word budgets and evaluates fit_risk when text exceeds capacity.

NEVER silently trims meaningful content into speaker notes.
Overflow resolution order:
  1. Detect budget violation
  2. Remove redundant wording
  3. Compress phrasing without losing meaning
  4. Restructure the structured content fields
  5. Perform targeted BODY_REPAIR
  6. Return FIT_RISK if still unresolved
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from .schemas import (
    SlideBlueprint, SlideIntent, ContentDensity,
    LayoutFamily, VisualTypeHint, LayoutCapacity, TextBudget,
)

logger = logging.getLogger("teachgenie.presentation.content_budget")


# ═══════════════════════════════════════════════════════════════
# Layout Capacity Profiles
# ═══════════════════════════════════════════════════════════════

# Default capacity per LayoutFamily
LAYOUT_CAPACITY_PROFILES: Dict[str, Dict[str, int]] = {
    LayoutFamily.HERO.value: {
        "max_cards": 0, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 60,
    },
    LayoutFamily.CENTERED_FOCAL.value: {
        "max_cards": 0, "max_bullets": 4, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.LEFT_TEXT_RIGHT_VISUAL.value: {
        "max_cards": 0, "max_bullets": 4, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 4, "max_label_length": 35,
    },
    LayoutFamily.LEFT_VISUAL_RIGHT_TEXT.value: {
        "max_cards": 0, "max_bullets": 4, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 4, "max_label_length": 35,
    },
    LayoutFamily.TWO_COLUMN.value: {
        "max_cards": 0, "max_bullets": 3, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 2, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 35,
    },
    LayoutFamily.THREE_CARD.value: {
        "max_cards": 3, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 30,
    },
    LayoutFamily.FOUR_CARD.value: {
        "max_cards": 4, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 25,
    },
    LayoutFamily.DIAGRAM_DOMINANT.value: {
        "max_cards": 0, "max_bullets": 2, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 6, "max_label_length": 40,
    },
    LayoutFamily.FULL_WIDTH_PROCESS.value: {
        "max_cards": 0, "max_bullets": 0, "max_process_steps": 6,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 35,
    },
    LayoutFamily.SPLIT_COMPARISON.value: {
        "max_cards": 0, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 5, "max_table_columns": 3, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 35,
    },
    LayoutFamily.MATRIX.value: {
        "max_cards": 0, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 5, "max_table_columns": 4, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 30,
    },
    LayoutFamily.TIMELINE_LAYOUT.value: {
        "max_cards": 0, "max_bullets": 0, "max_process_steps": 5,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.CODE_PLUS_EXPLANATION.value: {
        "max_cards": 0, "max_bullets": 3, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 8,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.FORMULA_PLUS_EXAMPLE.value: {
        "max_cards": 0, "max_bullets": 3, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.DATA_DASHBOARD.value: {
        "max_cards": 4, "max_bullets": 0, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 8, "max_label_length": 35,
    },
    LayoutFamily.CASE_STUDY_LAYOUT.value: {
        "max_cards": 0, "max_bullets": 4, "max_process_steps": 4,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.SUMMARY_GRID.value: {
        "max_cards": 5, "max_bullets": 5, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
    LayoutFamily.EDITORIAL_ASYMMETRIC.value: {
        "max_cards": 0, "max_bullets": 4, "max_process_steps": 0,
        "max_table_rows": 0, "max_table_columns": 0, "max_code_lines": 0,
        "max_chart_annotations": 0, "max_label_length": 40,
    },
}


# ═══════════════════════════════════════════════════════════════
# Word Budget by Content Density and Intent
# ═══════════════════════════════════════════════════════════════

# Body word ranges by density
DENSITY_BODY_WORD_RANGES: Dict[str, Tuple[int, int]] = {
    ContentDensity.LOW.value:    (20, 45),
    ContentDensity.MEDIUM.value: (45, 80),
    ContentDensity.HIGH.value:   (60, 110),
}

# Special intent overrides
INTENT_BUDGET_OVERRIDES: Dict[str, Dict[str, int]] = {
    SlideIntent.COVER.value: {
        "title_max_words": 10,
        "subtitle_max_words": 22,
        "body_max_words": 0,
        "speaker_note_min_words": 20,
        "speaker_note_max_words": 60,
    },
    SlideIntent.SUMMARY.value: {
        "speaker_note_min_words": 60,
        "speaker_note_max_words": 120,
    },
    SlideIntent.CONCEPT_EXPLANATION.value: {
        "speaker_note_min_words": 70,
        "speaker_note_max_words": 130,
    },
    SlideIntent.SYSTEM_OVERVIEW.value: {
        "speaker_note_min_words": 100,
        "speaker_note_max_words": 170,
    },
    SlideIntent.WORKED_EXAMPLE.value: {
        "speaker_note_min_words": 90,
        "speaker_note_max_words": 170,
    },
    SlideIntent.CODE_EXAMPLE.value: {
        "speaker_note_min_words": 90,
        "speaker_note_max_words": 170,
    },
    SlideIntent.Q_AND_A.value: {
        "speaker_note_min_words": 20,
        "speaker_note_max_words": 60,
    },
}

# Card-level budgets
CARD_HEADLINE_MAX_WORDS = 6
CARD_BODY_MAX_WORDS = 18
PROCESS_STEP_MAX_WORDS = 14
COMPARISON_CELL_MAX_WORDS = 20


def get_layout_capacity(layout_or_bp: Any) -> LayoutCapacity:
    """Compute LayoutCapacity for a given SlideBlueprint or LayoutFamily."""
    if hasattr(layout_or_bp, "layout_family"):
        layout_key = layout_or_bp.layout_family.value if hasattr(layout_or_bp.layout_family, "value") else str(layout_or_bp.layout_family)
    elif hasattr(layout_or_bp, "value"):
        layout_key = layout_or_bp.value
    else:
        layout_key = str(layout_or_bp)

    profile = LAYOUT_CAPACITY_PROFILES.get(layout_key, {})
    return LayoutCapacity(
        max_cards=profile.get("max_cards", 4),
        max_bullets=profile.get("max_bullets", 5),
        max_process_steps=profile.get("max_process_steps", 6),
        max_table_rows=profile.get("max_table_rows", 5),
        max_table_columns=profile.get("max_table_columns", 4),
        max_code_lines=profile.get("max_code_lines", 8),
        max_chart_annotations=profile.get("max_chart_annotations", 6),
        max_label_length=profile.get("max_label_length", 40),
    )


def compute_text_budget(*args, **kwargs) -> TextBudget:
    """Compute a TextBudget for a given blueprint or layout/density/visual/intent tuple."""
    if len(args) == 1 and hasattr(args[0], "text_budget"):
        blueprint = args[0]
        audience_expertise = kwargs.get("audience_expertise", "intermediate")
        base = blueprint.text_budget or TextBudget()
        intent = blueprint.intent.value if hasattr(blueprint.intent, "value") else str(blueprint.intent)
        density = blueprint.content_density.value if hasattr(blueprint.content_density, "value") else str(blueprint.content_density)
    elif len(args) >= 4:
        layout_family, density_val, visual_type, intent_val = args[:4]
        audience_expertise = args[4] if len(args) > 4 else kwargs.get("audience_expertise", "intermediate")
        base = TextBudget()
        intent = intent_val.value if hasattr(intent_val, "value") else str(intent_val)
        density = density_val.value if hasattr(density_val, "value") else str(density_val)
    elif "blueprint" in kwargs:
        blueprint = kwargs["blueprint"]
        audience_expertise = kwargs.get("audience_expertise", "intermediate")
        base = blueprint.text_budget or TextBudget()
        intent = blueprint.intent.value if hasattr(blueprint.intent, "value") else str(blueprint.intent)
        density = blueprint.content_density.value if hasattr(blueprint.content_density, "value") else str(blueprint.content_density)
    else:
        return TextBudget()

    # Density body word ranges
    body_range = DENSITY_BODY_WORD_RANGES.get(density, (45, 80))
    body_min = body_range[0]
    body_max = body_range[1]

    # Intent overrides
    overrides = INTENT_BUDGET_OVERRIDES.get(intent, {})
    title_max = overrides.get("title_max_words", base.title_max_words)
    subtitle_max = overrides.get("subtitle_max_words", base.subtitle_max_words)
    body_max = overrides.get("body_max_words", body_max)
    note_min = overrides.get("speaker_note_min_words", base.speaker_note_min_words)
    note_max = overrides.get("speaker_note_max_words", base.speaker_note_max_words)

    if audience_expertise in ("advanced", "expert", "professional"):
        body_max = int(body_max * 1.15)
    elif audience_expertise in ("beginner", "school"):
        body_max = int(body_max * 0.9)

    return TextBudget(
        title_max_words=title_max,
        subtitle_max_words=subtitle_max,
        body_max_words=body_max,
        card_title_max_words=CARD_HEADLINE_MAX_WORDS,
        card_body_max_words=CARD_BODY_MAX_WORDS,
        example_max_words=overrides.get("example_max_words", base.example_max_words),
        speaker_note_min_words=note_min,
        speaker_note_max_words=note_max,
        body_words_min=body_min,
        body_words_max=body_max,
        title_words_max=title_max,
        subtitle_words_max=subtitle_max,
    )


def count_words(text: str) -> int:
    """Count words in a text string."""
    if not text:
        return 0
    return len(text.split())


def evaluate_budget_compliance(
    content_dict: Any,
    budget: TextBudget,
    capacity: Optional[LayoutCapacity] = None,
) -> Tuple[bool, List[str], str]:
    """Evaluate whether structured content complies with text budget and layout capacity."""
    if capacity is None:
        capacity = get_layout_capacity(LayoutFamily.LEFT_TEXT_RIGHT_VISUAL)

    if hasattr(content_dict, "model_dump"):
        content_dict = content_dict.model_dump()
    elif hasattr(content_dict, "dict"):
        content_dict = content_dict.dict()
    elif not isinstance(content_dict, dict):
        content_dict = {}

    violations = []

    # Title budget
    title = content_dict.get("title", "")
    title_wc = count_words(title)
    if budget.title_max_words > 0 and title_wc > budget.title_max_words:
        violations.append(f"TITLE_OVER_BUDGET: {title_wc}/{budget.title_max_words} words")

    # Subtitle budget
    subtitle = content_dict.get("subtitle", "")
    sub_wc = count_words(subtitle)
    if budget.subtitle_max_words > 0 and sub_wc > budget.subtitle_max_words:
        violations.append(f"SUBTITLE_OVER_BUDGET: {sub_wc}/{budget.subtitle_max_words} words")

    # Body word count (supporting_points + primary_takeaway)
    body_parts = [content_dict.get("primary_takeaway", "")]
    body_parts.extend(content_dict.get("supporting_points", []))
    body_text = " ".join(p for p in body_parts if p)
    body_wc = count_words(body_text)
    if budget.body_max_words > 0 and body_wc > budget.body_max_words:
        violations.append(f"BODY_OVER_BUDGET: {body_wc}/{budget.body_max_words} words")

    # Bullet/supporting point count
    points = content_dict.get("supporting_points", [])
    if len(points) > capacity.max_bullets and capacity.max_bullets > 0:
        violations.append(f"BULLETS_EXCEED_CAPACITY: {len(points)}/{capacity.max_bullets}")

    # Process steps
    steps = content_dict.get("process_steps", [])
    if len(steps) > capacity.max_process_steps and capacity.max_process_steps > 0:
        violations.append(f"STEPS_EXCEED_CAPACITY: {len(steps)}/{capacity.max_process_steps}")

    # Table rows
    comp_rows = content_dict.get("comparison_rows", [])
    if len(comp_rows) > capacity.max_table_rows and capacity.max_table_rows > 0:
        violations.append(f"TABLE_ROWS_EXCEED_CAPACITY: {len(comp_rows)}/{capacity.max_table_rows}")

    # Code lines
    code = content_dict.get("code", "")
    if code:
        code_lines = len(code.strip().split("\n"))
        if code_lines > capacity.max_code_lines and capacity.max_code_lines > 0:
            violations.append(f"CODE_LINES_EXCEED_CAPACITY: {code_lines}/{capacity.max_code_lines}")

    # Speaker notes
    notes = content_dict.get("speaker_notes", "")
    notes_wc = count_words(notes)
    if budget.speaker_note_min_words > 0 and notes_wc < budget.speaker_note_min_words:
        violations.append(f"SPEAKER_NOTES_UNDER_BUDGET: {notes_wc}/{budget.speaker_note_min_words} words")
    if budget.speaker_note_max_words > 0 and notes_wc > budget.speaker_note_max_words:
        violations.append(f"SPEAKER_NOTES_OVER_BUDGET: {notes_wc}/{budget.speaker_note_max_words} words")

    # Card budgets
    for step in content_dict.get("process_steps", []):
        step_wc = count_words(step)
        if step_wc > PROCESS_STEP_MAX_WORDS:
            violations.append(f"PROCESS_STEP_OVER_BUDGET: '{step[:30]}...' {step_wc}/{PROCESS_STEP_MAX_WORDS} words")

    compliant = len(violations) == 0
    fit_risk = ""
    if not compliant:
        fit_risk = f"FIT_RISK: {'; '.join(violations)}"
        logger.debug(f"[ContentBudget] Budget violations detected: {violations}")

    return compliant, violations, fit_risk
