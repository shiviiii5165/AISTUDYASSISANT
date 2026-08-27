"""
Teach Me Engine Package (Production-Grade)
===========================================
"""
from .schemas import (
    LearningMode, LearningLevel, LearningDepth, ExplanationStrategy,
    CheckpointType, ConceptStatus, ConceptSpec, CheckpointSpec,
    EvaluationResult, LessonPlan, LearningState, MisconceptionItem,
    ConceptMasteryProfile, TurnTelemetry
)
from .orchestrator import start_teaching_session, handle_user_turn, handle_quick_command, generate_deterministic_summary
from .teacher_agent import plan_new_lesson, teach_current_concept, adapt_explanation_strategy, self_explain_concept
from .assessment_agent import evaluate_student_answer
from .mastery import calculate_mastery_update, get_mastery_level_label, calculate_confidence_score
from .grounding_evaluator import validate_and_score_grounding, detect_source_conflicts, extract_citations_from_text
from .telemetry import record_turn_telemetry, get_session_aggregate_metrics
from .exports import export_lesson_to_pptx
from .tools import (
    search_material, get_source_page, get_source_slide,
    get_learning_state, save_learning_state, get_lesson_plan, save_lesson_plan,
    update_mastery_profile, record_misconception_item, resolve_misconception,
    mark_concept_complete, get_next_concept, verify_session_ownership,
    update_mastery, record_misconception
)

__all__ = [
    "LearningMode",
    "LearningLevel",
    "LearningDepth",
    "ExplanationStrategy",
    "CheckpointType",
    "ConceptStatus",
    "ConceptSpec",
    "CheckpointSpec",
    "EvaluationResult",
    "LessonPlan",
    "LearningState",
    "MisconceptionItem",
    "ConceptMasteryProfile",
    "TurnTelemetry",
    "start_teaching_session",
    "handle_user_turn",
    "handle_quick_command",
    "generate_deterministic_summary",
    "plan_new_lesson",
    "teach_current_concept",
    "adapt_explanation_strategy",
    "self_explain_concept",
    "evaluate_student_answer",
    "calculate_mastery_update",
    "get_mastery_level_label",
    "calculate_confidence_score",
    "validate_and_score_grounding",
    "detect_source_conflicts",
    "extract_citations_from_text",
    "record_turn_telemetry",
    "get_session_aggregate_metrics",
    "export_lesson_to_pptx",
    "search_material",
    "get_source_page",
    "get_source_slide",
    "get_learning_state",
    "save_learning_state",
    "get_lesson_plan",
    "save_lesson_plan",
    "update_mastery_profile",
    "record_misconception_item",
    "resolve_misconception",
    "mark_concept_complete",
    "get_next_concept",
    "verify_session_ownership",
    "update_mastery",
    "record_misconception",
]
