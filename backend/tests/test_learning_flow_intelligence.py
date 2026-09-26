"""
LearnByGenie Adaptive Learning Flow Intelligence — Comprehensive Test Suite
==========================================================================
Tests A through Q validating that:
"SAME TOPIC != SAME LEARNING PATH"
The system determines HOW a specific learner learns a specific topic,
with instructional mode, cognitive operations, practice progression,
remediation strategy, and mastery checks.
"""
import pytest
import asyncio
from datetime import datetime, timezone

from app.services.notes.context import NotesContextAnalyzer, AnalyzeContextRequest
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import (
    NotesGenerationPlan, LearningMode, CognitiveOperation,
    LearnerKnowledgeState, NoteFormat, NoteDepth, NoteDifficulty
)
from app.services.notes.decision.engine import NotesDecisionEngine
from app.services.notes.generation.engine import _build_deterministic_fallback
from app.services.notes.validation.validators.learning_flow import LearningFlowValidator
from app.services.notes.validation.engine import validate_notes
from app.services.notes.validation.schemas import ViolationSeverity


def _make_context(
    topic: str,
    subject: str = "Science",
    class_level: str = "Class 10",
    mastery: float = 0.5,
    misconceptions = None,
    learning_style: str = "visual",
    cognitive_state: str = "neutral",
    interaction_ratio: float = 0.5,
    purpose: str = "exam_revision",
    exam_in_days: int = 14,
    objectives = None,
    prerequisite_gap: str = None
) -> CanonicalNotesContext:
    teaching_method = "unknown"
    if cognitive_state == "active":
        teaching_method = "active"
    elif cognitive_state == "passive":
        teaching_method = "passive"

    lesson_dict = {
        "learningObjectives": objectives or [
            f"Understand core principles of {topic}.",
            f"Apply problem-solving mechanisms of {topic}.",
            f"Debunk standard misconceptions of {topic}."
        ],
        "teachingMethod": teaching_method,
        "expectedMisconceptions": list(misconceptions or [])
    }
    assessment_dict = {
        "mastery": {topic: mastery},
        "misconceptions": list(misconceptions or []),
        "recentQuizScore": mastery,
        "strugglingConcepts": [topic] if mastery < 0.4 else []
    }
    if prerequisite_gap:
        assessment_dict["weakConcepts"] = [prerequisite_gap]

    student_dict = {
        "learningPreferences": [learning_style],
        "currentLearningState": {
            "mastery": {topic: mastery},
            "recent_quiz_score": mastery,
            "struggling_concepts": [topic] if mastery < 0.4 else []
        }
    }

    instructions = None
    if exam_in_days <= 2:
        instructions = "urgent final exam revision in 24 hours"

    req = AnalyzeContextRequest(
        topic=topic,
        subject=subject,
        class_level=class_level,
        curriculum="CBSE",
        language="english",
        additional_instructions=instructions,
        lesson=lesson_dict,
        assessment=assessment_dict,
        student=student_dict
    )
    ctx = asyncio.run(NotesContextAnalyzer.analyze_context(req, user_id="test_flow_usr"))
    
    # Inject fine-grained overrides into canonical structure
    if prerequisite_gap:
        ctx.resolved_context.weak_concepts.append(prerequisite_gap)
    if misconceptions:
        ctx.resolved_context.misconceptions = list(misconceptions)
        ctx.lesson.expected_misconceptions = list(misconceptions)
    if teaching_method != "unknown":
        ctx.lesson.teaching_method = teaching_method
        ctx.resolved_context.teaching_method = teaching_method

    return ctx


# ── Test A: Low-Mastery Newton's Laws ──
def test_a_low_mastery_newtons_laws():
    ctx = _make_context(
        topic="Newton's Laws of Motion",
        subject="Physics",
        mastery=0.20,
        misconceptions=["Force is required to keep an object moving at constant speed"]
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan

    # Mode must be Remediation or Guided Discovery
    assert flow.primary_mode in (LearningMode.REMEDIATION, LearningMode.GUIDED_DISCOVERY)
    stage_names = [s.stage_name for s in flow.sequence]
    assert "prerequisite_bridge" in stage_names
    assert "misconception_repair" in stage_names

    # Practice must start foundational/basic
    assert flow.practice_strategy.starting_difficulty in ("foundational", "basic")
    assert flow.practice_strategy.scaffolding_level == "high"


# ── Test B: High-Mastery Newton's Laws ──
def test_b_high_mastery_newtons_laws():
    ctx = _make_context(
        topic="Newton's Laws of Motion",
        subject="Physics",
        mastery=0.88,
        cognitive_state="active"
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan

    # Mode must be Mastery
    assert flow.primary_mode == LearningMode.MASTERY
    stage_names = [s.stage_name for s in flow.sequence]
    assert "concept_compression" in stage_names
    assert "edge_cases_and_traps" in stage_names or "challenge_practice" in stage_names
    assert "prerequisite_bridge" not in stage_names

    # Practice must start advanced
    assert flow.practice_strategy.starting_difficulty == "advanced"
    assert flow.practice_strategy.scaffolding_level == "minimal"


# ── Test C: Passive Lesson Flow ──
def test_c_passive_lesson_flow():
    ctx = _make_context(
        topic="Cell Structure",
        subject="Biology",
        mastery=0.50,
        cognitive_state="passive",
        interaction_ratio=0.1
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan

    # Should activate learner via Guided Discovery
    assert flow.primary_mode == LearningMode.GUIDED_DISCOVERY
    # Must contain interactive elements
    has_interactive = any(s.is_interactive for s in flow.sequence)
    assert has_interactive, "Passive lesson flow must include interactive stages"


# ── Test D: Active Lesson Flow ──
def test_d_active_lesson_flow():
    ctx = _make_context(
        topic="Quadratic Equations",
        subject="Mathematics",
        mastery=0.65,
        cognitive_state="active",
        interaction_ratio=0.85
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan

    # Should build on engagement
    assert flow.primary_mode in (LearningMode.ACTIVE_RETRIEVAL, LearningMode.PRACTICE, LearningMode.MASTERY)
    stage_names = [s.stage_name for s in flow.sequence]
    assert "diagnostic_retrieval" in stage_names or "transfer_problem" in stage_names or "challenge_practice" in stage_names


# ── Test E: Exam-Urgent Flow ──
def test_e_exam_urgent_flow():
    ctx = _make_context(
        topic="Chemical Bonding",
        subject="Chemistry",
        mastery=0.55,
        exam_in_days=2
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan

    assert flow.primary_mode == LearningMode.EXAM_PREPARATION
    stage_names = [s.stage_name for s in flow.sequence]
    assert "high_yield_synthesis" in stage_names or "revision_synthesis" in stage_names
    assert "rapid_prerequisite_scan" in stage_names or "active_retrieval" in stage_names


# ── Test F: Remediation Flow with Misconception Debunking ──
def test_f_remediation_flow():
    ctx = _make_context(
        topic="Gravitation",
        subject="Physics",
        mastery=0.30,
        misconceptions=["Heavier objects fall faster due to stronger gravitational acceleration"]
    )
    plan = NotesDecisionEngine.decide(ctx)
    flow = plan.learning_flow_plan
    assert flow.misconception_strategy.has_misconceptions is True
    assert len(flow.misconception_strategy.remediation_target_keys) > 0

    # Test generation produces debunking section
    doc = _build_deterministic_fallback(ctx, plan)
    sec_types = [s.section_type for s in doc.sections]
    assert "common_misconceptions" in sec_types or any("misconception" in s.title.lower() for s in doc.sections)


# ── Test G: Prerequisite-Gap Flow ──
def test_g_prerequisite_gap_flow():
    ctx = _make_context(
        topic="Photosynthesis",
        subject="Biology",
        mastery=0.35,
        prerequisite_gap="Chloroplast structure and thylakoid membrane function"
    )
    plan = NotesDecisionEngine.decide(ctx)
    flow = plan.learning_flow_plan
    assert flow.prerequisite_strategy.gap_identified is not None
    assert "Chloroplast" in flow.prerequisite_strategy.gap_identified

    stage_names = [s.stage_name for s in flow.sequence]
    assert "prerequisite_bridge" in stage_names
    bridge_idx = stage_names.index("prerequisite_bridge")
    assert bridge_idx <= 1


# ── Test H: Unknown-Topic Flow (No Catalog) ──
def test_h_unknown_topic_flow():
    ctx = _make_context(
        topic="Post-Quantum Lattice-Based Cryptography",
        subject="Computer Science",
        mastery=0.45
    )
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    flow = plan.learning_flow_plan
    assert len(flow.sequence) >= 5

    # Generate document dynamically without catalog
    doc = _build_deterministic_fallback(ctx, plan)
    assert doc is not None
    assert len(doc.sections) >= 5
    assert doc.learning_flow_plan is not None
    assert doc.learning_flow_quality is not None
    assert doc.learning_flow_quality["stages_executed"] > 0


# ── Test I: Cross-Domain Adaptation ──
@pytest.mark.parametrize("domain_subj,domain_top", [
    ("Physics", "Thermodynamic Heat Engines"),
    ("Biology", "Cellular Respiration and ATP Synthase"),
    ("Mathematics", "Eigenvalues and Matrix Diagonalization"),
    ("Computer Science", "Graph Search and Dijkstra Algorithm"),
    ("Economics", "Macroeconomic Monetary Policy and Inflation"),
    ("Engineering", "Stress-Strain Analysis in Beam Deflection")
])
def test_i_cross_domain_adaptation(domain_subj, domain_top):
    ctx = _make_context(topic=domain_top, subject=domain_subj, mastery=0.5)
    plan = NotesDecisionEngine.decide(ctx)
    assert plan.learning_flow_plan is not None
    assert len(plan.learning_flow_plan.sequence) >= 5

    doc = _build_deterministic_fallback(ctx, plan)
    assert len(doc.sections) >= 4
    assert doc.topic.lower() == domain_top.lower()
    assert doc.subject.lower() == domain_subj.lower()


# ── Test J: Same-Topic / Different-Student Test (CRITICAL) ──
def test_j_same_topic_different_student():
    """
    Core invariant: SAME TOPIC != SAME LEARNING PATH.
    Compare Student A (struggling, grade 9, mastery 0.18, visual, misconception)
    vs Student B (advanced, grade 12, mastery 0.88, active).
    """
    topic = "Chemical Bonding"

    # Student A: Struggling
    ctx_a = _make_context(
        topic=topic,
        subject="Chemistry",
        class_level="Class 9",
        mastery=0.18,
        misconceptions=["Electrons orbit the nucleus in rigid concentric train tracks"],
        learning_style="visual",
        cognitive_state="passive"
    )
    plan_a = NotesDecisionEngine.decide(ctx_a)
    doc_a = _build_deterministic_fallback(ctx_a, plan_a)

    # Student B: Advanced
    ctx_b = _make_context(
        topic=topic,
        subject="Chemistry",
        class_level="Class 12",
        mastery=0.88,
        learning_style="verbal",
        cognitive_state="active"
    )
    plan_b = NotesDecisionEngine.decide(ctx_b)
    doc_b = _build_deterministic_fallback(ctx_b, plan_b)

    # Invariants
    assert plan_a.learning_flow_plan.primary_mode != plan_b.learning_flow_plan.primary_mode
    assert plan_a.learning_flow_plan.primary_mode in (LearningMode.REMEDIATION, LearningMode.GUIDED_DISCOVERY)
    assert plan_b.learning_flow_plan.primary_mode == LearningMode.MASTERY

    # Stages must be differentiated
    stages_a = [s.stage_name for s in plan_a.learning_flow_plan.sequence]
    stages_b = [s.stage_name for s in plan_b.learning_flow_plan.sequence]
    assert stages_a != stages_b
    assert "prerequisite_bridge" in stages_a
    assert "prerequisite_bridge" not in stages_b
    assert "concept_compression" in stages_b

    # Practice strategies differentiated
    assert plan_a.learning_flow_plan.practice_strategy.starting_difficulty != plan_b.learning_flow_plan.practice_strategy.starting_difficulty
    assert plan_a.learning_flow_plan.practice_strategy.starting_difficulty in ("foundational", "basic")
    assert plan_b.learning_flow_plan.practice_strategy.starting_difficulty == "advanced"

    # Section counts or types differentiated
    sec_types_a = [s.section_type for s in doc_a.sections]
    sec_types_b = [s.section_type for s in doc_b.sections]
    assert sec_types_a != sec_types_b


# ── Test K: Determinism Test ──
def test_k_determinism():
    ctx = _make_context(topic="Photosynthesis", subject="Biology", mastery=0.4)
    plan1 = NotesDecisionEngine.decide(ctx)
    plan2 = NotesDecisionEngine.decide(ctx)

    assert plan1.learning_flow_plan.primary_mode == plan2.learning_flow_plan.primary_mode
    assert [s.stage_name for s in plan1.learning_flow_plan.sequence] == [s.stage_name for s in plan2.learning_flow_plan.sequence]
    assert plan1.learning_flow_plan.practice_strategy.starting_difficulty == plan2.learning_flow_plan.practice_strategy.starting_difficulty


# ── Test L: Catalog Bypass Test ──
def test_l_catalog_bypass():
    """Topics that exist in CurriculumCatalog still get learner-personalized flows."""
    ctx_low = _make_context(topic="Cell Structure", subject="Biology", mastery=0.15)
    ctx_high = _make_context(topic="Cell Structure", subject="Biology", mastery=0.92, cognitive_state="active")

    plan_low = NotesDecisionEngine.decide(ctx_low)
    plan_high = NotesDecisionEngine.decide(ctx_high)

    assert plan_low.learning_flow_plan.primary_mode != plan_high.learning_flow_plan.primary_mode
    assert plan_low.learning_flow_plan.practice_strategy.starting_difficulty != plan_high.learning_flow_plan.practice_strategy.starting_difficulty


# ── Test M: Active Validation Rejects Passive Fake ──
def test_m_active_validation_rejects_passive_fake():
    ctx = _make_context(topic="Light Reflection", subject="Physics", mastery=0.5, cognitive_state="passive")
    plan = NotesDecisionEngine.decide(ctx)
    doc = _build_deterministic_fallback(ctx, plan)

    # Deliberately falsify an interactive section to be completely passive (no ?, no prompt, no challenge)
    for sec in doc.sections:
        if sec.semantic_evidence and sec.semantic_evidence.is_interactive:
            sec.title = "Standard Description"
            sec.content = "This is a passive narrative paragraph describing wave optics without any interactive elements."
            break

    violations, details, score = LearningFlowValidator.validate(doc, plan, ctx)
    fraud_viols = [v for v in violations if v.code == "LEARNING_FLOW_INTERACTIVE_PASSIVE_FRAUD"]
    assert len(fraud_viols) > 0, "Validator must detect passive text posing as interactive stage"


# ── Test N: Mastery Check Exit Condition ──
def test_n_mastery_check_exit_condition():
    ctx = _make_context(topic="Chemical Bonding", subject="Chemistry", mastery=0.4)
    plan = NotesDecisionEngine.decide(ctx)
    mastery_check = plan.learning_flow_plan.mastery_check
    assert mastery_check.required is True
    assert len(mastery_check.success_criteria) > 10
    assert len(mastery_check.fallback_if_failed) > 10


# ── Test O: Practice Adaptation ──
def test_o_practice_adaptation():
    ctx_low = _make_context(topic="Kinematics", subject="Physics", mastery=0.15)
    ctx_high = _make_context(topic="Kinematics", subject="Physics", mastery=0.90, cognitive_state="active")

    plan_low = NotesDecisionEngine.decide(ctx_low)
    plan_high = NotesDecisionEngine.decide(ctx_high)

    doc_low = _build_deterministic_fallback(ctx_low, plan_low)
    doc_high = _build_deterministic_fallback(ctx_high, plan_high)

    assert doc_low.practice[0]["difficulty"] in ("foundational", "basic")
    assert doc_high.practice[0]["difficulty"] == "advanced"


# ── Test P: No Static Template ──
def test_p_no_static_template():
    scenarios = [
        _make_context("Newton's Laws", "Physics", mastery=0.15),
        _make_context("Newton's Laws", "Physics", mastery=0.92, cognitive_state="active"),
        _make_context("Newton's Laws", "Physics", mastery=0.55, exam_in_days=2),
        _make_context("Cell Structure", "Biology", mastery=0.50, cognitive_state="passive"),
        _make_context("Quadratic Equations", "Mathematics", mastery=0.60, prerequisite_gap="Factoring polynomials")
    ]

    sequences = []
    modes = set()
    for sc in scenarios:
        pl = NotesDecisionEngine.decide(sc)
        seq = [s.stage_name for s in pl.learning_flow_plan.sequence]
        sequences.append(tuple(seq))
        modes.add(pl.learning_flow_plan.primary_mode)

    # Must produce at least 3 distinct sequences and at least 3 distinct modes
    assert len(set(sequences)) >= 3, "System must not use a static sequence template"
    assert len(modes) >= 3, "System must not use a static primary mode"


# ── Test Q: Full End-to-End Artifact Certification ──
def test_q_full_end_to_end_artifact_certification():
    ctx = _make_context(
        topic="Chemical Bonding",
        subject="Chemistry",
        mastery=0.25,
        misconceptions=["Ionic bonds involve sharing electrons equally"]
    )
    plan = NotesDecisionEngine.decide(ctx)
    doc = _build_deterministic_fallback(ctx, plan)

    val_res = asyncio.run(validate_notes(ctx, plan, doc, enable_llm=False))
    assert val_res.status in ("valid", "valid_with_warnings")
    assert val_res.overall_score >= 80.0
    assert not any(v.severity == ViolationSeverity.CRITICAL for v in val_res.violations)
