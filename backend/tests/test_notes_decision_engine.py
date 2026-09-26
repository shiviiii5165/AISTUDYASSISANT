"""
LearnByGenie Notes Decision Engine — Comprehensive Test Suite
===========================================================
Tests all Step 2 requirements of the Notes Intelligence Layer:
1. Topic Only Uses Neutral Defaults
2. Low Mastery Changes Plan
3. Medium Mastery Changes Plan
4. High Mastery Changes Plan
5. Missing Mastery Does Not Assume Medium
6. Misconception Adds Remediation
7. Weak Concept Creates Targeted Focus
8. Process Topic Selects Flowchart
9. Comparison Topic Selects Comparison
10. Formula Topic Selects Formula Sheet
11. Passive Lesson Strategy
12. Active Lesson Strategy
13. Unknown Teaching Method Uses Neutral Strategy
14. Exam Near Prioritizes Revision
15. User Intent Overrides Default Heuristics
16. Combined Exam and Low Mastery
17. Decision Determinism
18. Decision Explainability
19. Same Topic Different Student Profiles
20. Missing Context Truthfulness
21. Curriculum Constraint
22. Lesson Objective Constraint
23. Visual Plan
24. Section Plan
25. Backward Compatibility

Plus Golden Tests:
- Mandatory Golden Test (Newton's Laws of Motion Case A vs Case B)
- Active vs Passive Golden Test
- Misconception Golden Test
- Topic Format Golden Test
- API Endpoint POST /api/notes-generator/decision/analyze
"""
import copy
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user
from app.services.notes.schemas import (
    CanonicalNotesContext,
    NoteFormat,
    NoteDepth,
    NoteDifficulty,
    DecisionOutput
)
from app.services.notes.context import NotesContextAnalyzer, AnalyzeContextRequest
from app.services.notes.decision import (
    decide_notes_plan,
    NotesDecisionEngine,
    NotesGenerationPlan,
    PurposeType,
    TopicCategory
)
import asyncio


def make_context(
    topic: str,
    class_level: str = "Class 10",
    subject: str = "General",
    curriculum: str = "CBSE",
    language: str = "english",
    student_mastery: dict = None,
    student_misconceptions: list = None,
    weak_concepts: list = None,
    lesson_teaching_method: str = None,
    learning_objectives: list = None,
    explicit_user_instructions: str = None,
    **kwargs
) -> CanonicalNotesContext:
    lesson_dict = {}
    if lesson_teaching_method:
        lesson_dict["teachingMethod"] = lesson_teaching_method
    if learning_objectives:
        lesson_dict["learningObjectives"] = learning_objectives

    assessment_dict = {}
    if student_mastery:
        assessment_dict["mastery"] = student_mastery
    if weak_concepts:
        assessment_dict["weakConcepts"] = weak_concepts
    if student_misconceptions:
        assessment_dict["misconceptions"] = student_misconceptions

    teachme_dict = {}
    if student_misconceptions:
        teachme_dict["misconceptions"] = student_misconceptions

    student_dict = {}

    req = AnalyzeContextRequest(
        topic=topic,
        class_level=class_level,
        subject=subject,
        curriculum=curriculum,
        language=language,
        additional_instructions=explicit_user_instructions,
        lesson=lesson_dict or None,
        assessment=assessment_dict or None,
        teach_me=teachme_dict or None,
        student=student_dict or None,
        **kwargs
    )
    return asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="test-usr"))


class MockUser:
    def __init__(self, user_id: str = "usr_decision_test_1"):
        self.id = user_id
        self.email = "tester@teachgenie.ai"


@pytest.fixture
def auth_client():
    mock_u = MockUser()
    app.dependency_overrides[get_current_user] = lambda: mock_u
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()



# ============================================================================
# 25 REQUIRED ARCHITECTURAL TESTS
# ============================================================================

def test_1_topic_only_uses_neutral_defaults():
    """TEST 1: When only topic is provided, engine uses neutral defaults without inventing data."""
    ctx = CanonicalNotesContext(
        topic="Photosynthesis"
    )
    plan = decide_notes_plan(ctx)

    assert plan.purpose.primary == PurposeType.LEARNING.value
    assert plan.teaching_strategy.mode == "balanced"
    assert plan.remediation_plan.required is False
    assert plan.remediation_plan.priority == "none"
    assert plan.visual_plan.type == "flowchart"  # Photosynthesis is a biological process
    assert plan.evidence["mastery"] is None


def test_2_low_mastery_changes_plan():
    """TEST 2: Low mastery (< 0.40) selects foundational difficulty, guided/intensive scaffolding, and remediation."""
    ctx = CanonicalNotesContext(
        topic="Fractions",
        class_level="Class 6",
        student_mastery={"Fractions": 0.25}
    )
    plan = decide_notes_plan(ctx)

    assert plan.difficulty == NoteDifficulty.FOUNDATIONAL
    assert plan.teaching_strategy.scaffolding in ["guided", "intensive"]
    assert plan.remediation_plan.required is True
    assert plan.remediation_plan.priority == "high"
    assert plan.practice_plan.difficulty == "foundational"
    assert "step_by_step_scaffolding" in plan.teaching_strategy.features
    assert NoteFormat.REMEDIAL_NOTES in plan.formats


def test_3_medium_mastery_changes_plan():
    """TEST 3: Medium mastery (0.40 <= m < 0.75) selects standard difficulty and intermediate practice."""
    ctx = CanonicalNotesContext(
        topic="Fractions",
        class_level="Class 6",
        student_mastery={"Fractions": 0.60}
    )
    plan = decide_notes_plan(ctx)

    assert plan.difficulty == NoteDifficulty.STANDARD
    assert plan.teaching_strategy.scaffolding == "moderate"
    assert plan.practice_plan.difficulty == "intermediate"
    assert plan.practice_plan.types == ["recall", "application"]


def test_4_high_mastery_changes_plan():
    """TEST 4: High mastery (>= 0.75) selects advanced focus, concise depth, and tricky cases."""
    ctx = CanonicalNotesContext(
        topic="Thermodynamics",
        class_level="Class 11",
        student_mastery={"Thermodynamics": 0.85}
    )
    plan = decide_notes_plan(ctx)

    assert plan.difficulty == NoteDifficulty.ADVANCED
    assert plan.depth == NoteDepth.CONCISE
    assert plan.teaching_strategy.scaffolding == "minimal"
    assert plan.practice_plan.difficulty == "advanced"
    assert "tricky_cases" in plan.practice_plan.types
    assert "minimize_repetitive_definitions" in plan.constraints


def test_5_missing_mastery_does_not_assume_medium():
    """TEST 5: Missing mastery must remain UNKNOWN and not assume 0.50 medium."""
    ctx = CanonicalNotesContext(
        topic="Gravitation",
        class_level="Class 9"
    )
    plan = decide_notes_plan(ctx)

    assert plan.evidence["mastery"] is None
    # Verify it doesn't log or trace a fabricated mastery score
    trace_items = [t for t in plan.decision_trace if t.decision == "difficulty"]
    assert len(trace_items) > 0
    # The trace should rely on class level, not an invented mastery score
    assert not any(e.get("field") == "mastery" for e in trace_items[0].evidence)


def test_6_misconception_adds_remediation():
    """TEST 6: Misconceptions trigger targeted remediation and correction requirements."""
    ctx = CanonicalNotesContext(
        topic="Electric Current",
        class_level="Class 10",
        student_misconceptions=["Current gets consumed by the resistor"]
    )
    plan = decide_notes_plan(ctx)

    assert plan.remediation_plan.required is True
    assert plan.remediation_plan.include_misconception_correction is True
    assert "Current gets consumed by the resistor" in plan.remediation_plan.target_concepts
    # Misconceptions section exists in section blueprint
    misc_sections = [s for s in plan.section_plan if s.type == "common_misconceptions"]
    assert len(misc_sections) == 1
    assert misc_sections[0].target is not None
    assert "Current gets consumed" in misc_sections[0].target


def test_7_weak_concept_creates_targeted_focus():
    """TEST 7: Weak concepts create targeted reinforcement without generic unrelated additions."""
    ctx = CanonicalNotesContext(
        topic="Optics",
        class_level="Class 10",
        weak_concepts=["Total Internal Reflection"]
    )
    plan = decide_notes_plan(ctx)

    assert "Total Internal Reflection" in plan.weak_concepts_to_reinforce
    assert any("total_internal_reflection" in c.lower() for c in plan.constraints)


def test_8_process_topic_selects_flowchart():
    """TEST 8: Process topics automatically select flowchart format and visual plan."""
    ctx = CanonicalNotesContext(
        topic="Water Cycle",
        class_level="Class 6"
    )
    plan = decide_notes_plan(ctx)

    assert NoteFormat.FLOWCHART in plan.formats
    assert plan.visual_plan.required is True
    assert plan.visual_plan.type == "flowchart"


def test_9_comparison_topic_selects_comparison():
    """TEST 9: Comparison topics automatically select comparison notes and comparison matrix visual."""
    ctx = CanonicalNotesContext(
        topic="Mitosis vs Meiosis",
        class_level="Class 11",
        subject="Biology"
    )
    plan = decide_notes_plan(ctx)

    assert NoteFormat.COMPARISON_NOTES in plan.formats
    assert plan.visual_plan.required is True
    assert plan.visual_plan.type == "comparison_matrix"


def test_10_formula_topic_selects_formula_sheet():
    """TEST 10: Formula-heavy topics select formula sheet format."""
    ctx = CanonicalNotesContext(
        topic="Quadratic Equations",
        class_level="Class 10",
        subject="Mathematics"
    )
    plan = decide_notes_plan(ctx)

    assert NoteFormat.FORMULA_SHEET in plan.formats
    assert any(s.type == "formula_box" for s in plan.section_plan)


def test_11_passive_lesson_strategy():
    """TEST 11: Passive/lecture lesson teaching method produces passive structured strategy."""
    ctx = make_context(
        topic="Ancient Civilizations",
        class_level="Class 6",
        lesson_teaching_method="passive"
    )
    plan = decide_notes_plan(ctx)

    assert plan.teaching_strategy.mode == "passive"
    assert "structured_explanation" in plan.teaching_strategy.features
    assert "summary" in plan.teaching_strategy.features


def test_12_active_lesson_strategy():
    """TEST 12: Active inquiry lesson teaching method produces active strategy with checkpoints."""
    ctx = make_context(
        topic="Acids and Bases",
        class_level="Class 8",
        lesson_teaching_method="active inquiry"
    )
    plan = decide_notes_plan(ctx)

    assert plan.teaching_strategy.mode == "active"
    assert "thinking_checkpoints" in plan.teaching_strategy.features
    assert any(s.type == "thinking_checkpoint" for s in plan.section_plan)


def test_13_unknown_teaching_method_uses_neutral_strategy():
    """TEST 13: Unknown teaching method selects balanced strategy (never converts to passive)."""
    ctx = CanonicalNotesContext(
        topic="Solar System",
        class_level="Class 5"
    )
    plan = decide_notes_plan(ctx)

    assert plan.teaching_strategy.mode == "balanced"
    assert plan.teaching_strategy.mode != "passive"


def test_14_exam_near_prioritizes_revision():
    """TEST 14: Near exam prioritizes exam preparation and high-yield revision."""
    ctx = CanonicalNotesContext(
        topic="Board Exam Revision: Carbon and its Compounds",
        class_level="Class 10",
        explicit_user_instructions="Preparing for board exam tomorrow"
    )
    plan = decide_notes_plan(ctx)

    assert plan.purpose.primary == PurposeType.EXAM_PREPARATION.value
    assert plan.revision_plan.required is True
    assert plan.revision_plan.priority == "high"
    assert "high_yield_summary" in plan.revision_plan.include
    assert NoteFormat.QUICK_REVISION in plan.formats
    assert NoteFormat.EXAM_PREPARATION in plan.formats


def test_15_user_intent_overrides_default_heuristics():
    """TEST 15: Explicit user instructions take highest precedence over default heuristics."""
    ctx = CanonicalNotesContext(
        topic="Newton's Laws of Motion",
        class_level="Class 9",
        student_mastery={"Newton's Laws of Motion": 0.90},
        explicit_user_instructions="Make detailed exam preparation notes."
    )
    plan = decide_notes_plan(ctx)

    # User explicitly requested detailed exam preparation
    assert plan.purpose.primary == PurposeType.EXAM_PREPARATION.value
    assert plan.depth == NoteDepth.DETAILED


def test_16_combined_exam_and_low_mastery():
    """
    TEST 16: Combined signals (mastery 0.30, exam tomorrow, misconception inertia).
    Engine must combine signals rather than allowing one rule to erase all context.
    """
    ctx = CanonicalNotesContext(
        topic="Newton's Laws of Motion",
        class_level="Class 9",
        student_mastery={"Newton's Laws of Motion": 0.30},
        student_misconceptions=["Inertia is a force"],
        explicit_user_instructions="Exam tomorrow"
    )
    plan = decide_notes_plan(ctx)

    # Exam state wins primary purpose, while low mastery & misconception drive high remediation
    assert plan.purpose.primary == PurposeType.EXAM_PREPARATION.value
    assert plan.remediation_plan.required is True
    assert plan.remediation_plan.priority == "high"
    assert plan.revision_plan.required is True
    assert plan.revision_plan.priority == "high"
    assert plan.difficulty == NoteDifficulty.FOUNDATIONAL
    assert "Inertia is a force" in plan.remediation_plan.target_concepts


def test_17_decision_determinism():
    """TEST 17: Identical CanonicalNotesContext produces byte-identical or semantically identical plans."""
    ctx = CanonicalNotesContext(
        topic="Periodic Table",
        class_level="Class 10",
        curriculum="CBSE",
        student_mastery={"Periodic Table": 0.65},
        student_misconceptions=["Atomic mass increases monotonically across all elements"]
    )

    plan1 = decide_notes_plan(ctx)
    plan2 = decide_notes_plan(ctx)

    assert plan1.model_dump() == plan2.model_dump()
    assert plan1.model_dump_json() == plan2.model_dump_json()


def test_18_decision_explainability():
    """TEST 18: Decisions include explicit reasons, evidence, and precedence trace."""
    ctx = CanonicalNotesContext(
        topic="Chemical Kinetics",
        class_level="Class 12",
        student_mastery={"Chemical Kinetics": 0.35}
    )
    plan = decide_notes_plan(ctx)

    assert len(plan.decision_reasons) >= 2
    assert len(plan.decision_trace) >= 2

    # Check that purpose trace documents winning candidate and reason
    purpose_trace = next(t for t in plan.decision_trace if t.decision == "primary_purpose")
    assert purpose_trace.winning_candidate == plan.purpose.primary
    assert len(purpose_trace.evidence) > 0
    assert purpose_trace.reason != ""

    # Decision confidence is distinct and non-zero
    assert 0.0 < plan.decision_confidence <= 1.0


def test_19_same_topic_different_student_profiles():
    """TEST 19: Same topic with different student profiles generates materially different plans."""
    ctx_struggling = CanonicalNotesContext(
        topic="Polynomials",
        class_level="Class 9",
        student_mastery={"Polynomials": 0.20},
        student_misconceptions=["Division by variable is a polynomial"]
    )
    ctx_advanced = CanonicalNotesContext(
        topic="Polynomials",
        class_level="Class 9",
        student_mastery={"Polynomials": 0.95}
    )

    plan_struggling = decide_notes_plan(ctx_struggling)
    plan_advanced = decide_notes_plan(ctx_advanced)

    assert plan_struggling.difficulty != plan_advanced.difficulty
    assert plan_struggling.depth != plan_advanced.depth
    assert plan_struggling.remediation_plan.required is True
    assert plan_advanced.remediation_plan.required is False
    assert NoteFormat.REMEDIAL_NOTES in plan_struggling.formats
    assert NoteFormat.REMEDIAL_NOTES not in plan_advanced.formats


def test_20_missing_context_truthfulness():
    """TEST 20: Missing context is not fabricated or assumed."""
    ctx = CanonicalNotesContext(topic="Simple Pendulum")
    plan = decide_notes_plan(ctx)

    assert plan.evidence["mastery"] is None
    assert plan.evidence["exam_state"] is None
    assert plan.purpose.primary == PurposeType.LEARNING.value


def test_21_curriculum_constraint():
    """TEST 21: Curriculum board constraint is reflected in generation constraints."""
    ctx = CanonicalNotesContext(
        topic="Reproduction in Organisms",
        class_level="Class 10",
        curriculum="ICSE"
    )
    plan = decide_notes_plan(ctx)

    assert any("icse" in c.lower() for c in plan.constraints)


def test_22_lesson_objective_constraint():
    """TEST 22: Lesson learning objectives are transformed into concrete constraints."""
    ctx = make_context(
        topic="Electric Circuits",
        class_level="Class 10",
        learning_objectives=["State Ohm's Law and calculate equivalent resistance"]
    )
    plan = decide_notes_plan(ctx)

    assert any("ohm" in c.lower() for c in plan.constraints)


def test_23_visual_plan():
    """TEST 23: Visual plan specifies valid type, required flag, and clear pedagogical focus."""
    ctx = CanonicalNotesContext(
        topic="Photosynthesis Process",
        class_level="Class 7"
    )
    plan = decide_notes_plan(ctx)

    assert plan.visual_plan.required is True
    assert plan.visual_plan.type == "flowchart"
    assert "photosynthesis" in plan.visual_plan.focus.lower()


def test_24_section_plan():
    """TEST 24: Section plan produces an ordered blueprint with required and target fields."""
    ctx = CanonicalNotesContext(
        topic="Magnetism",
        class_level="Class 8",
        student_misconceptions=["All metals are attracted to magnets"]
    )
    plan = decide_notes_plan(ctx)

    sec_types = [s.type for s in plan.section_plan]
    assert sec_types[0] == "overview"
    assert sec_types[1] == "core_concept"
    assert "worked_example" in sec_types
    assert "common_misconceptions" in sec_types
    assert "quick_summary" in sec_types
    assert "checkpoint_practice" in sec_types

    misc_item = next(s for s in plan.section_plan if s.type == "common_misconceptions")
    assert misc_item.required is True
    assert "All metals" in misc_item.target


def test_25_backward_compatibility():
    """
    TEST 25: Existing NotesDecisionEngine.evaluate(ctx) returns plan with all legacy properties intact:
    selected_formats, required_sections, tone_instructions, misconceptions_to_target, weak_concepts_to_reinforce.
    """
    ctx = CanonicalNotesContext(
        topic="Newton's Laws of Motion",
        class_level="Class 9",
        student_misconceptions=["Heavier objects fall faster"],
        weak_concepts=["Inertia"]
    )
    decision = NotesDecisionEngine.evaluate(ctx)

    assert hasattr(decision, "selected_formats")
    assert hasattr(decision, "required_sections")
    assert hasattr(decision, "tone_instructions")
    assert hasattr(decision, "misconceptions_to_target")
    assert hasattr(decision, "weak_concepts_to_reinforce")
    assert hasattr(decision, "depth")
    assert hasattr(decision, "difficulty")

    assert NoteFormat.LEARNING_NOTES in decision.selected_formats
    assert "Heavier objects fall faster" in decision.misconceptions_to_target
    assert "Inertia" in decision.weak_concepts_to_reinforce
    assert "core_concept" in decision.required_sections
    assert len(decision.tone_instructions) > 10


# ============================================================================
# GOLDEN TESTS
# ============================================================================

def test_mandatory_golden_test():
    """
    MANDATORY GOLDEN TEST:
    Topic: Newton's Laws of Motion
    CASE A:
        Class 7, mastery = 0.30, misconception = "inertia", teaching_method = "passive"
    CASE B:
        Class 7, mastery = 0.90, misconception = none, teaching_method = "active"

    Verify that Plan A and Plan B materially differ across:
    purpose, formats, difficulty, depth, teaching_strategy, remediation, practice,
    visual_plan, section_plan, constraints.
    """
    ctx_a = make_context(
        topic="Newton's Laws of Motion",
        class_level="Class 7",
        student_mastery={"Newton's Laws of Motion": 0.30},
        student_misconceptions=["Inertia is a force that acts on moving bodies"],
        lesson_teaching_method="passive"
    )

    ctx_b = make_context(
        topic="Newton's Laws of Motion",
        class_level="Class 7",
        student_mastery={"Newton's Laws of Motion": 0.90},
        student_misconceptions=[],
        lesson_teaching_method="active inquiry"
    )

    plan_a = decide_notes_plan(ctx_a)
    plan_b = decide_notes_plan(ctx_b)

    # 1. Purpose differs
    assert plan_a.purpose.primary == PurposeType.REMEDIATION.value
    assert plan_b.purpose.primary == PurposeType.LEARNING.value

    # 2. Formats differ
    assert NoteFormat.REMEDIAL_NOTES in plan_a.formats
    assert NoteFormat.REMEDIAL_NOTES not in plan_b.formats

    # 3. Difficulty differs
    assert plan_a.difficulty == NoteDifficulty.FOUNDATIONAL
    assert plan_b.difficulty in [NoteDifficulty.STANDARD, NoteDifficulty.ADVANCED]
    assert plan_a.difficulty != plan_b.difficulty

    # 4. Depth differs
    assert plan_a.depth == NoteDepth.DETAILED
    assert plan_b.depth in [NoteDepth.CONCISE, NoteDepth.STANDARD]
    assert plan_a.depth != plan_b.depth

    # 5. Teaching Strategy differs materially
    assert plan_a.teaching_strategy.mode == "passive"
    assert plan_b.teaching_strategy.mode == "active"
    assert plan_a.teaching_strategy.scaffolding in ["guided", "intensive"]
    assert plan_b.teaching_strategy.scaffolding == "minimal"
    assert "structured_explanation" in plan_a.teaching_strategy.features
    assert "thinking_checkpoints" in plan_b.teaching_strategy.features

    # 6. Remediation Plan differs materially
    assert plan_a.remediation_plan.required is True
    assert plan_a.remediation_plan.priority == "high"
    assert plan_b.remediation_plan.required is False
    assert plan_b.remediation_plan.priority == "none"

    # 7. Practice Plan differs materially
    assert plan_a.practice_plan.difficulty == "foundational"
    assert plan_b.practice_plan.difficulty in ["intermediate", "advanced"]
    assert "diagnostic" in plan_a.practice_plan.types
    assert "tricky_cases" in plan_b.practice_plan.types

    # 8. Section Plan differs materially
    sec_types_a = [s.type for s in plan_a.section_plan]
    sec_types_b = [s.type for s in plan_b.section_plan]
    assert "common_misconceptions" in sec_types_a
    assert "common_misconceptions" not in sec_types_b
    assert "thinking_checkpoint" not in sec_types_a
    assert "thinking_checkpoint" in sec_types_b

    # 9. Constraints differ materially
    assert any("misconception" in c for c in plan_a.constraints)
    assert not any("misconception" in c for c in plan_b.constraints)
    assert "avoid_unnecessary_advanced_derivations" in plan_a.constraints
    assert "minimize_repetitive_definitions" in plan_b.constraints


def test_active_passive_golden_test():
    """
    ACTIVE/PASSIVE GOLDEN TEST:
    Same topic, student, mastery. Change ONLY passive -> active.
    Plan must change in meaningful teaching strategy fields and section plan.
    """
    ctx_passive = make_context(
        topic="Cell Structure",
        class_level="Class 8",
        student_mastery={"Cell Structure": 0.60},
        lesson_teaching_method="passive"
    )
    ctx_active = make_context(
        topic="Cell Structure",
        class_level="Class 8",
        student_mastery={"Cell Structure": 0.60},
        lesson_teaching_method="active"
    )

    plan_p = decide_notes_plan(ctx_passive)
    plan_a = decide_notes_plan(ctx_active)

    assert plan_p.teaching_strategy.mode == "passive"
    assert plan_a.teaching_strategy.mode == "active"
    assert "structured_explanation" in plan_p.teaching_strategy.features
    assert "thinking_checkpoints" in plan_a.teaching_strategy.features

    # Active plan adds thinking_checkpoint section
    assert any(s.type == "thinking_checkpoint" for s in plan_a.section_plan)
    assert not any(s.type == "thinking_checkpoint" for s in plan_p.section_plan)


def test_misconception_golden_test():
    """
    MISCONCEPTION GOLDEN TEST:
    Same topic, class, mastery. Change: no misconception -> misconception.
    Plan must change remediation, targeted sections, and misconception correction requirements.
    """
    ctx_clean = CanonicalNotesContext(
        topic="Chemical Reactions",
        class_level="Class 9",
        student_mastery={"Chemical Reactions": 0.65}
    )
    ctx_with_misc = CanonicalNotesContext(
        topic="Chemical Reactions",
        class_level="Class 9",
        student_mastery={"Chemical Reactions": 0.65},
        student_misconceptions=["Mass disappears when gas is released in a reaction"]
    )

    plan_clean = decide_notes_plan(ctx_clean)
    plan_misc = decide_notes_plan(ctx_with_misc)

    assert plan_clean.remediation_plan.required is False
    assert plan_misc.remediation_plan.required is True
    assert plan_misc.remediation_plan.include_misconception_correction is True
    assert "Mass disappears" in plan_misc.remediation_plan.target_concepts[0]

    # Section blueprint changes
    assert not any(s.type == "common_misconceptions" for s in plan_clean.section_plan)
    assert any(s.type == "common_misconceptions" for s in plan_misc.section_plan)


def test_topic_format_golden_test():
    """
    TOPIC FORMAT GOLDEN TEST:
    - Water Cycle -> flowchart
    - Mitosis vs Meiosis -> comparison_matrix
    - Quadratic Equations -> formula_sheet
    - Newton's Laws -> conceptual / concept_map
    """
    plan_water = decide_notes_plan(CanonicalNotesContext(topic="Water Cycle", class_level="Class 6"))
    assert NoteFormat.FLOWCHART in plan_water.formats
    assert plan_water.visual_plan.type == "flowchart"

    plan_mitosis = decide_notes_plan(CanonicalNotesContext(topic="Mitosis vs Meiosis", class_level="Class 11"))
    assert NoteFormat.COMPARISON_NOTES in plan_mitosis.formats
    assert plan_mitosis.visual_plan.type == "comparison_matrix"

    plan_quad = decide_notes_plan(CanonicalNotesContext(topic="Quadratic Equations", class_level="Class 10"))
    assert NoteFormat.FORMULA_SHEET in plan_quad.formats

    plan_newton = decide_notes_plan(CanonicalNotesContext(topic="Newton's Laws of Motion", class_level="Class 9"))
    assert plan_newton.visual_plan.type in ["concept_map", "diagram"]


def test_api_decision_analyze_endpoint(auth_client):
    """
    API ENDPOINT TEST:
    POST /api/notes-generator/decision/analyze
    Returns {"success": true, "plan": {...}} without LLM calls or notes generation.
    """
    payload = {
        "topic": "Newton's Laws of Motion",
        "class_level": "Class 7",
        "subject": "Physics",
        "curriculum": "CBSE",
        "student": {
            "studentId": "stu-golden-1",
            "currentLearningState": {
                "mastery": {"Newton's Laws of Motion": 0.30}
            }
        },
        "lesson": {
            "teachingMethod": "passive"
        }
    }

    res = auth_client.post("/api/notes-generator/decision/analyze", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["success"] is True
    assert "plan" in data
    plan = data["plan"]

    assert plan["schema_version"] == "1.0"
    assert plan["purpose"]["primary"] == "remediation"
    assert plan["difficulty"] == "foundational"
    assert plan["teaching_strategy"]["mode"] == "passive"
    assert plan["remediation_plan"]["required"] is True
    assert len(plan["section_plan"]) > 0
    assert len(plan["decision_reasons"]) > 0
    assert len(plan["decision_trace"]) > 0
    assert "sections" not in data  # Proves notes were NOT generated
    assert "generated_notes" not in data
