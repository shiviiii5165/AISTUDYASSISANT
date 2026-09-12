"""
TeachGenie Notes Decision Engine — Primary Deterministic Decision Engine
========================================================================
STEP 2 ONLY of the Notes Intelligence architecture.
Transforms CanonicalNotesContext into a strongly typed NotesGenerationPlan.
Answers: "Given what TeachGenie knows, what does this learner actually need in their notes?"
Zero LLM calls. Zero note generation. Deterministic and explainable.
"""
from typing import List, Dict, Any, Optional
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.schemas import (
    NoteFormat, NoteDepth, NoteDifficulty, DecisionOutput
)
from .schemas import (
    NotesGenerationPlan, PurposePlan, PurposeType,
    TeachingStrategyPlan, VisualPlan, RemediationPlan,
    PracticePlan, RevisionPlan, SectionPlanItem,
    DecisionReason, DecisionTraceItem
)
from .policies import (
    MasteryPolicy, MasteryBracket, TopicCategory,
    GradePolicy, DecisionPrecedence
)
from .topic_analyzer import TopicAnalyzer
from .purpose_selector import PurposeSelector
from .mastery_policy import MasteryPolicyEngine
from .pedagogy_policy import PedagogyPolicyEngine
from .visual_planner import VisualPlanner
from .section_planner import SectionPlanner
from .explainability import ExplainabilityEngine
from .learning_flow_planner import LearningFlowPlanner


def decide_notes_plan(context: CanonicalNotesContext) -> NotesGenerationPlan:
    """
    Step 2 Primary Entry Point:
    Analyzes CanonicalNotesContext deterministically and synthesizes
    a complete NotesGenerationPlan.
    """
    ctx = context

    # ── 1. Basic Dimension Parsing ──
    class_num = GradePolicy.parse_class_number(ctx.class_level)
    topic_category = TopicAnalyzer.classify(ctx)

    topic_lower = (ctx.topic or "").lower()
    instructions_lower = (ctx.explicit_user_instructions or "").lower()
    subject_lower = (ctx.subject or "").lower()
    combined_search = f"{topic_lower} {instructions_lower}"

    # Extract student mastery map
    mastery_map: Dict[str, float] = {}
    if ctx.student_mastery:
        mastery_map = dict(ctx.student_mastery)
    elif hasattr(ctx, "assessment") and ctx.assessment and ctx.assessment.mastery:
        mastery_map = dict(ctx.assessment.mastery)
    elif hasattr(ctx, "student") and ctx.student and ctx.student.current_learning_state:
        mastery_map = ctx.student.current_learning_state.get("mastery", {})

    # ── 2. Mastery Evaluation ──
    mastery_decision = MasteryPolicyEngine.evaluate(
        mastery_map=mastery_map,
        class_num=class_num,
        topic=ctx.topic,
        explicit_depth=ctx.requested_depth
    )
    avg_mastery = mastery_decision.score

    # ── 3. Purpose Selection ──
    purpose_plan = PurposeSelector.select(ctx, avg_mastery=avg_mastery)

    # ── 4. Exam State Signal ──
    exam_state: Optional[str] = None
    if "exam" in combined_search or "test" in combined_search:
        exam_state = "near"

    # Misconceptions extraction
    all_misconceptions = list(dict.fromkeys(
        ctx.student_misconceptions + ctx.expected_misconceptions +
        ([p.get("concept", "") for p in ctx.quiz_mistakes if isinstance(p, dict) and p.get("concept")] if hasattr(ctx, "quiz_mistakes") and ctx.quiz_mistakes else [])
    ))
    all_misconceptions = [m for m in all_misconceptions if m]
    has_misconceptions = bool(all_misconceptions or (hasattr(ctx, "quiz_mistakes") and ctx.quiz_mistakes))

    # ── 5. Format Selection (Deterministic Multi-Format) ──
    selected_formats: List[NoteFormat] = []

    if ctx.requested_format:
        selected_formats.append(ctx.requested_format)
    else:
        # Base format
        selected_formats.append(NoteFormat.LEARNING_NOTES)

        # Topic structure -> Format
        if topic_category == TopicCategory.PROCESS:
            if NoteFormat.FLOWCHART not in selected_formats:
                selected_formats.append(NoteFormat.FLOWCHART)

        elif topic_category == TopicCategory.COMPARISON:
            if NoteFormat.COMPARISON_NOTES not in selected_formats:
                selected_formats.append(NoteFormat.COMPARISON_NOTES)

        elif topic_category == TopicCategory.FORMULA_HEAVY:
            if NoteFormat.FORMULA_SHEET not in selected_formats:
                selected_formats.append(NoteFormat.FORMULA_SHEET)

        # Keyword heuristics for formulas (Physics/Maths)
        formula_keywords = ["physics", "math", "mathematics", "chemistry", "formula", "equation", "theorem", "law", "derivation"]
        if any(k in subject_lower or k in combined_search for k in formula_keywords):
            if NoteFormat.FORMULA_SHEET not in selected_formats:
                selected_formats.append(NoteFormat.FORMULA_SHEET)

        # Interconnected classification -> Mind Map
        mindmap_keywords = ["classification", "ecosystem", "system", "structure", "overview", "anatomy", "kingdom"]
        if any(k in combined_search for k in mindmap_keywords):
            if NoteFormat.MIND_MAP not in selected_formats:
                selected_formats.append(NoteFormat.MIND_MAP)

        # Low mastery or misconceptions -> Remedial Notes
        if mastery_decision.bracket == MasteryBracket.LOW or has_misconceptions:
            if NoteFormat.REMEDIAL_NOTES not in selected_formats:
                selected_formats.append(NoteFormat.REMEDIAL_NOTES)

        # Exam / Revision intent
        if exam_state or purpose_plan.primary in [PurposeType.EXAM_PREPARATION.value, PurposeType.REVISION.value]:
            if NoteFormat.QUICK_REVISION not in selected_formats:
                selected_formats.append(NoteFormat.QUICK_REVISION)
            if NoteFormat.EXAM_PREPARATION not in selected_formats:
                selected_formats.append(NoteFormat.EXAM_PREPARATION)

    # ── 6. Difficulty and Depth Selection ──
    difficulty = mastery_decision.difficulty
    depth = mastery_decision.depth

    # User explicit overrides win over heuristics (Highest Precedence)
    if "detailed" in instructions_lower:
        depth = NoteDepth.DETAILED
    elif "concise" in instructions_lower or "brief" in instructions_lower:
        depth = NoteDepth.CONCISE
    elif "deep" in instructions_lower or "comprehensive" in instructions_lower:
        depth = NoteDepth.DEEP

    if "foundational" in instructions_lower or "basic" in instructions_lower:
        difficulty = NoteDifficulty.FOUNDATIONAL
    elif "advanced" in instructions_lower:
        difficulty = NoteDifficulty.ADVANCED

    # ── 7. Teaching Strategy Formulation ──
    teaching_strategy = PedagogyPolicyEngine.evaluate(
        ctx=ctx,
        class_num=class_num,
        mastery_bracket=mastery_decision.bracket,
        base_scaffolding=mastery_decision.scaffolding
    )

    # ── 8. Visual Plan Blueprint ──
    visual_plan = VisualPlanner.plan(
        ctx=ctx,
        topic_category=topic_category,
        selected_formats=selected_formats
    )

    # ── 9. Section Plan Blueprint ──
    is_active = (teaching_strategy.mode == "active")
    section_plan = SectionPlanner.plan(
        selected_formats=selected_formats,
        has_misconceptions=has_misconceptions,
        misconceptions=all_misconceptions,
        class_num=class_num,
        is_active_mode=is_active
    )

    # ── 10. Remediation Plan ──
    remediation_required = (
        mastery_decision.remediation_required or
        has_misconceptions or
        NoteFormat.REMEDIAL_NOTES in selected_formats
    )

    if mastery_decision.bracket == MasteryBracket.LOW or len(all_misconceptions) >= 2:
        rem_priority = "high"
    elif has_misconceptions or mastery_decision.bracket == MasteryBracket.MEDIUM:
        rem_priority = "medium"
    elif remediation_required:
        rem_priority = "low"
    else:
        rem_priority = "none"

    remediation_plan = RemediationPlan(
        required=remediation_required,
        priority=rem_priority,
        target_concepts=all_misconceptions if all_misconceptions else list(dict.fromkeys(ctx.weak_concepts)),
        include_misconception_correction=bool(all_misconceptions),
        include_guided_examples=(mastery_decision.bracket == MasteryBracket.LOW)
    )

    # ── 11. Practice Plan ──
    practice_count = 2 if NoteFormat.QUICK_REVISION in selected_formats else (4 if mastery_decision.bracket == MasteryBracket.LOW else 3)
    practice_plan = PracticePlan(
        required=True,
        count=practice_count,
        difficulty=mastery_decision.practice_difficulty,
        types=mastery_decision.practice_types
    )

    # ── 12. Revision Plan ──
    is_revision_needed = (
        exam_state is not None or
        purpose_plan.primary in [PurposeType.REVISION.value, PurposeType.EXAM_PREPARATION.value] or
        NoteFormat.QUICK_REVISION in selected_formats or
        NoteFormat.EXAM_PREPARATION in selected_formats
    )

    if exam_state or purpose_plan.primary == PurposeType.EXAM_PREPARATION.value:
        rev_priority = "high"
        rev_includes = ["high_yield_summary", "formulas", "common_mistakes", "key_points"]
    elif is_revision_needed:
        rev_priority = "medium"
        rev_includes = ["key_points", "common_mistakes", "high_yield_summary"]
    else:
        rev_priority = "none"
        rev_includes = []

    revision_plan = RevisionPlan(
        required=is_revision_needed,
        priority=rev_priority,
        include=rev_includes
    )

    # ── 13. Constraints Construction ──
    constraints: List[str] = [
        "stay_within_curriculum_scope",
        f"target_grade_{class_num}_vocabulary"
    ]

    curriculum_str = (
        ctx.resolved_context.curriculum
        if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum
        else str(ctx.curriculum or "CBSE")
    )
    constraints.append(f"align_to_{curriculum_str.lower()}_standards")

    for obj in ctx.learning_objectives[:3]:
        # Clean objective text for constraint identifier
        clean_obj = "".join(c if c.isalnum() else "_" for c in obj[:40]).strip("_").lower()
        if clean_obj:
            constraints.append(f"satisfy_objective_{clean_obj}")

    for misc in all_misconceptions[:3]:
        clean_misc = "".join(c if c.isalnum() else "_" for c in misc[:40]).strip("_").lower()
        if clean_misc:
            constraints.append(f"target_misconception_{clean_misc}")

    for weak in ctx.weak_concepts[:3]:
        clean_weak = "".join(c if c.isalnum() else "_" for c in weak[:40]).strip("_").lower()
        if clean_weak:
            constraints.append(f"reinforce_weak_concept_{clean_weak}")

    if mastery_decision.bracket == MasteryBracket.LOW:
        constraints.append("avoid_unnecessary_advanced_derivations")
        constraints.append("provide_step_by_step_scaffolding")
    elif mastery_decision.bracket == MasteryBracket.HIGH:
        constraints.append("minimize_repetitive_definitions")
        constraints.append("emphasize_advanced_applications")

    if exam_state:
        constraints.append("highlight_board_exam_frequently_asked_patterns")
        constraints.append("include_time_saving_exam_tips")

    constraints = sorted(list(dict.fromkeys(constraints)))

    # ── 14. Explainability, Evidence, and Decision Trace ──
    evidence = ExplainabilityEngine.compile_evidence(
        ctx=ctx,
        topic_category=topic_category,
        avg_mastery=avg_mastery,
        exam_state=exam_state
    )

    decision_confidence = ExplainabilityEngine.compute_decision_confidence(
        ctx=ctx,
        avg_mastery=avg_mastery
    )

    reasons, trace = ExplainabilityEngine.build_trace_and_reasons(
        ctx=ctx,
        topic_category=topic_category,
        mastery_bracket=mastery_decision.bracket,
        avg_mastery=avg_mastery,
        primary_purpose=purpose_plan.primary,
        secondary_purposes=purpose_plan.secondary,
        difficulty=difficulty.value if hasattr(difficulty, "value") else str(difficulty),
        depth=depth.value if hasattr(depth, "value") else str(depth),
        mode=teaching_strategy.mode,
        remediation_required=remediation_plan.required,
        remediation_priority=remediation_plan.priority,
        exam_state=exam_state
    )

    # ── 15. Adaptive Learning Flow Synthesis ──
    learning_flow_plan = LearningFlowPlanner.plan(
        ctx=ctx,
        mastery_bracket=mastery_decision.bracket,
        avg_mastery=avg_mastery,
        topic_category=topic_category,
        primary_purpose=purpose_plan.primary,
        exam_state=exam_state,
        teaching_mode=teaching_strategy.mode
    )
    if learning_flow_plan and learning_flow_plan.practice_strategy and practice_plan.difficulty:
        learning_flow_plan.practice_strategy.starting_difficulty = practice_plan.difficulty

    # ── 16. Backward-Compatible Synthesis ──
    required_sections = [item.type for item in section_plan if item.required]

    return NotesGenerationPlan(
        schema_version="1.0",
        purpose=purpose_plan,
        formats=selected_formats,
        difficulty=difficulty,
        depth=depth,
        teaching_strategy=teaching_strategy,
        section_plan=section_plan,
        visual_plan=visual_plan,
        remediation_plan=remediation_plan,
        practice_plan=practice_plan,
        revision_plan=revision_plan,
        constraints=constraints,
        learning_flow_plan=learning_flow_plan,
        decision_reasons=reasons,
        evidence=evidence,
        decision_trace=trace,
        decision_confidence=decision_confidence,
        # Backward compatibility accessors
        selected_formats=selected_formats,
        required_sections=required_sections,
        tone_instructions=teaching_strategy.tone_instructions,
        misconceptions_to_target=all_misconceptions[:3],
        weak_concepts_to_reinforce=list(dict.fromkeys(ctx.weak_concepts))[:3]
    )


class NotesDecisionEngine:
    """
    Evaluates CanonicalNotesContext and produces deterministic pedagogical generation decisions.
    Full backward-compatible wrapper.
    """

    @staticmethod
    def evaluate(ctx: CanonicalNotesContext) -> NotesGenerationPlan:
        """Evaluates canonical context and returns a strongly-typed NotesGenerationPlan."""
        return decide_notes_plan(ctx)

    @staticmethod
    def decide(ctx: CanonicalNotesContext) -> NotesGenerationPlan:
        """Alias for evaluate: produces deterministic NotesGenerationPlan."""
        return decide_notes_plan(ctx)

    @staticmethod
    def create_plan(ctx: CanonicalNotesContext) -> NotesGenerationPlan:
        """Alias for decide: produces deterministic NotesGenerationPlan."""
        return decide_notes_plan(ctx)

    @staticmethod
    def _parse_class_number(class_level: str) -> int:
        return GradePolicy.parse_class_number(class_level)

