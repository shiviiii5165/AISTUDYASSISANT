"""
LearnByGenie vNEXT — Story Grammar System
=========================================
9 story grammars with priority-ordered narrative beats:
  CONCEPT_TEACHING, TECHNICAL_SYSTEM, PROCESS, COMPARISON,
  DATA_STORY, HISTORY_EVOLUTION, RESEARCH, PROBLEM_SOLUTION, CASE_STUDY

Adaptive to any slide_count via priority-based selection.

Model (spec §2):
  PRIMARY_STORY_GRAMMAR + OPTIONAL_STORY_MODIFIERS

StoryGrammar is NOT a fixed slide-index mapping (spec §9).
It provides narrative constraints and candidate intents,
then adapts to slide_count + topic_intelligence + purpose + audience.
"""
from app.core.logging import logger
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from .schemas import (
    SlideIntent,
    VisualTypeHint,
    LayoutFamily,
    ContentDensity,
    StoryGrammarType,
    TextBudget,
    SlideBlueprint,
)


# ═══════════════════════════════════════════════════════════════
# NARRATIVE BEAT — a single slot in a story grammar
# ═══════════════════════════════════════════════════════════════

@dataclass
class NarrativeBeat:
    """A position in a story arc with priority for adaptive selection."""
    intent: SlideIntent
    priority: float          # 0.0-1.0, higher = more essential
    narrative_order: int     # relative position in narrative (0=first, 99=last)
    narrative_tag: str = ""  # distinguishes same-intent beats
    required: bool = False   # must always be included regardless of slide_count
    section_label: str = ""  # optional section group
    semantic_role: str = ""  # semantic role for domain-aware realization


# ═══════════════════════════════════════════════════════════════
# 7 STORY GRAMMARS
# ═══════════════════════════════════════════════════════════════

STORY_GRAMMARS: Dict[StoryGrammarType, List[NarrativeBeat]] = {

    StoryGrammarType.CONCEPT_TEACHING: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="CONCEPT_COVER"),
        NarrativeBeat(SlideIntent.HOOK, 0.7, 1, narrative_tag="engagement", semantic_role="ENGAGEMENT_HOOK"),
        NarrativeBeat(SlideIntent.OBJECTIVES, 0.6, 2, narrative_tag="learning_goals", semantic_role="LEARNING_OBJECTIVES"),
        NarrativeBeat(SlideIntent.PREREQUISITES, 0.45, 3, semantic_role="FOUNDATIONAL_PREREQUISITES"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.95, 4, section_label="Core Concept", semantic_role="CORE_DEFINITION"),
        NarrativeBeat(SlideIntent.MENTAL_MODEL, 0.75, 5, semantic_role="INTUITIVE_MENTAL_MODEL"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.9, 6, narrative_tag="mechanism", semantic_role="PRIMARY_MECHANISM"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 7, narrative_tag="deeper_mechanism", semantic_role="DEEPER_MECHANISM"),
        NarrativeBeat(SlideIntent.WORKED_EXAMPLE, 0.85, 8, section_label="Application", semantic_role="STEP_BY_STEP_WORKED_EXAMPLE"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.7, 9, semantic_role="REAL_WORLD_APPLICATION"),
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.6, 10, section_label="Critical Thinking", semantic_role="COMMON_MISCONCEPTIONS"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.55, 11, semantic_role="CONTRASTING_ALTERNATIVES"),
        NarrativeBeat(SlideIntent.COMMON_MISTAKES, 0.5, 12, semantic_role="PITFALLS_TO_AVOID"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.4, 13, semantic_role="EMPIRICAL_EVIDENCE"),
        NarrativeBeat(SlideIntent.KNOWLEDGE_CHECK, 0.35, 14, semantic_role="KNOWLEDGE_CHECK"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="KEY_TAKEAWAYS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.TECHNICAL_SYSTEM: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="SYSTEM_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.85, 1, narrative_tag="problem_context", semantic_role="CONCURRENCY_PROBLEM_CONTEXT"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.7, 2, semantic_role="ENGINEERING_SIGNIFICANCE"),
        NarrativeBeat(SlideIntent.SYSTEM_OVERVIEW, 0.95, 3, section_label="Architecture", semantic_role="SYSTEM_ARCHITECTURE_OVERVIEW"),
        NarrativeBeat(SlideIntent.COMPONENT_BREAKDOWN, 0.9, 4, semantic_role="CORE_SUBSYSTEM_BREAKDOWN"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.85, 5, section_label="Mechanics", semantic_role="EXECUTION_LIFECYCLE_AND_EVENT_LOOP"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 6, narrative_tag="concurrency_model", semantic_role="CONCURRENCY_MODEL_MECHANICS"),
        NarrativeBeat(SlideIntent.CODE_EXAMPLE, 0.55, 7, semantic_role="CODE_IMPLEMENTATION"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.65, 8, section_label="Practice", semantic_role="PRODUCTION_DEPLOYMENT"),
        NarrativeBeat(SlideIntent.CASE_STUDY, 0.6, 9, semantic_role="HIGH_SCALE_CASE_STUDY"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.75, 10, narrative_tag="architecture_comparison", section_label="Evaluation", semantic_role="CONCURRENCY_ARCHITECTURE_COMPARISON"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.72, 11, narrative_tag="module_system_comparison", semantic_role="ECOSYSTEM_OR_MODULE_COMPARISON"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.75, 12, semantic_role="PERFORMANCE_TRADEOFFS_AND_BOTTLENECKS"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.65, 13, semantic_role="PRODUCTION_BEST_PRACTICES"),
        NarrativeBeat(SlideIntent.COMMON_MISTAKES, 0.5, 14, semantic_role="ANTI_PATTERNS"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.45, 15, semantic_role="BENCHMARK_THROUGHPUT"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="SYSTEM_SYNTHESIS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.PROCESS: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="PROCESS_COVER"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.8, 1, narrative_tag="motivation", semantic_role="SIGNIFICANCE_AND_IMPACT"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.85, 2, narrative_tag="structural_context", semantic_role="STRUCTURAL_CONTEXT"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.7, 3, narrative_tag="inputs_outputs", semantic_role="INPUTS_AND_OUTPUTS"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.95, 4, section_label="Stages",
                      narrative_tag="stage_overview", semantic_role="CORE_PROCESS_FLOW"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.85, 5, narrative_tag="stage_deep_1", semantic_role="STAGE_ONE_MECHANISM"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 6, narrative_tag="stage_deep_2", semantic_role="STAGE_TWO_TRANSFORMATION"),
        NarrativeBeat(SlideIntent.WORKED_EXAMPLE, 0.75, 7, section_label="Application", semantic_role="PRACTICAL_WORKED_EXAMPLE"),
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.65, 8, section_label="Critical Analysis", semantic_role="LIMITING_FACTORS_AND_CONSTRAINTS"),
        NarrativeBeat(SlideIntent.COMPONENT_BREAKDOWN, 0.6, 9, narrative_tag="decision_points", semantic_role="KEY_FACTORS"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.65, 10, semantic_role="REAL_WORLD_APPLICATION"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.4, 11, semantic_role="EFFICIENCY_METRICS"),
        NarrativeBeat(SlideIntent.COMMON_MISTAKES, 0.55, 12, section_label="Pitfalls", semantic_role="PROCESS_PITFALLS"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.5, 13, semantic_role="OPTIMIZATION_PRACTICES"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="KEY_TAKEAWAYS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.COMPARISON: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="COMPARISON_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.85, 1, narrative_tag="comparison_context", semantic_role="EVALUATION_CONTEXT"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.65, 2, narrative_tag="evaluation_criteria", semantic_role="EVALUATION_CRITERIA"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.9, 3, narrative_tag="option_a",
                      section_label="Option A", semantic_role="FIRST_OPTION_ANALYSIS"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.9, 4, narrative_tag="option_b",
                      section_label="Option B", semantic_role="SECOND_OPTION_ANALYSIS"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.95, 5, section_label="Comparison", semantic_role="HEAD_TO_HEAD_COMPARISON"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.8, 6, semantic_role="DECISION_TRADEOFFS"),
        NarrativeBeat(SlideIntent.CASE_STUDY, 0.6, 7, narrative_tag="use_cases",
                      section_label="Application", semantic_role="SELECTION_CASE_STUDY"),
        NarrativeBeat(SlideIntent.WORKED_EXAMPLE, 0.55, 8, semantic_role="SCENARIO_EVALUATION"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.5, 9, semantic_role="BENCHMARK_EVIDENCE"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.6, 10, narrative_tag="recommendation", semantic_role="DECISION_FRAMEWORK"),
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.45, 11, semantic_role="COMPARISON_MISCONCEPTIONS"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="RECOMMENDATION_SYNTHESIS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.DATA_STORY: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="DATA_STORY_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.9, 1, narrative_tag="baseline_question", semantic_role="CORE_QUESTION_AND_BASELINE"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.75, 2, semantic_role="STRATEGIC_IMPORTANCE"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.95, 3, narrative_tag="macro_trend", section_label="Trends", semantic_role="MACRO_GROWTH_TREND"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.88, 4, narrative_tag="segmentation", semantic_role="SEGMENTATION_AND_DISTRIBUTION"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.82, 5, narrative_tag="drivers", semantic_role="COST_AND_ECONOMIC_DRIVERS"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 6, narrative_tag="structural_factors", semantic_role="STRUCTURAL_DRIVERS_AND_CHALLENGES"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.75, 7, section_label="Analysis", semantic_role="BENCHMARK_COMPARISON"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.65, 8, narrative_tag="policy_and_market", semantic_role="POLICY_AND_MARKET_IMPLICATIONS"),
        NarrativeBeat(SlideIntent.CASE_STUDY, 0.6, 9, semantic_role="EMBLEMATIC_CASE_STUDY"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.55, 10, semantic_role="CAPITAL_AND_DEPLOYMENT_TRADEOFFS"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.45, 11, narrative_tag="recommendations", semantic_role="STRATEGIC_RECOMMENDATIONS"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="STRATEGIC_SYNTHESIS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],
    StoryGrammarType.HISTORY_EVOLUTION: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="HISTORICAL_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.9, 1, narrative_tag="pre_conditions", section_label="Context", semantic_role="PRE_CONDITIONS_AND_SETTING"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.75, 2, semantic_role="HISTORICAL_SIGNIFICANCE"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.9, 3, narrative_tag="turning_points", section_label="Causes", semantic_role="TURNING_POINTS_AND_CAUSES"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.85, 4, narrative_tag="catalyst_innovation", section_label="Transformation", semantic_role="CATALYST_INNOVATION"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 5, narrative_tag="structural_shift", semantic_role="STRUCTURAL_SHIFT"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.75, 6, narrative_tag="social_transformation", semantic_role="SOCIAL_TRANSFORMATION"),
        NarrativeBeat(SlideIntent.CASE_STUDY, 0.65, 7, narrative_tag="archetypal_evidence", semantic_role="ARCHETYPAL_CASE_STUDY"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.65, 8, narrative_tag="quantitative_evidence", semantic_role="HISTORICAL_DATA_AND_GROWTH"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.85, 9, narrative_tag="long_term_consequences", section_label="Consequences", semantic_role="LONG_TERM_CONSEQUENCES"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.5, 10, narrative_tag="modern_legacy", semantic_role="MODERN_LEGACY"),
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.45, 11, semantic_role="HISTORICAL_MYTHS"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="HISTORICAL_SYNTHESIS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.RESEARCH: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="RESEARCH_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.9, 1, narrative_tag="research_problem", section_label="Background", semantic_role="RESEARCH_PROBLEM_AND_GAP"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.75, 2, semantic_role="METHODOLOGICAL_SIGNIFICANCE"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.7, 3, narrative_tag="problem_formulation", semantic_role="PROBLEM_FORMULATION_AND_HYPOTHESIS"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.9, 4, narrative_tag="experimental_protocol", section_label="Methodology", semantic_role="EXPERIMENTAL_DESIGN_AND_PROTOCOL"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.95, 5, narrative_tag="empirical_results", section_label="Results", semantic_role="PRIMARY_EMPIRICAL_FINDINGS"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.85, 6, narrative_tag="ablation_analysis", semantic_role="ABLATION_AND_ERROR_ANALYSIS"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.8, 7, narrative_tag="discussion", section_label="Discussion", semantic_role="DISCUSSION_AND_INTERPRETATION"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.75, 8, narrative_tag="baseline_benchmarks", semantic_role="BENCHMARK_AND_BASELINE_COMPARISON"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.7, 9, narrative_tag="validity_threats", semantic_role="VALIDITY_THREATS_AND_LIMITATIONS"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.65, 10, narrative_tag="reproducibility", semantic_role="REPRODUCIBILITY_AND_OPEN_SCIENCE"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.55, 11, semantic_role="PRACTICAL_IMPLICATIONS"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="RESEARCH_SYNTHESIS"),
        NarrativeBeat(SlideIntent.REFERENCES, 0.5, 98, semantic_role="KEY_REFERENCES"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.PROBLEM_SOLUTION: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="PROBLEM_SOLUTION_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.9, 1, narrative_tag="problem_context", section_label="Problem", semantic_role="CORE_PROBLEM_STATEMENT"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.8, 2, narrative_tag="impact", semantic_role="PROBLEM_SEVERITY_AND_IMPACT"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.7, 3, narrative_tag="problem_evidence", semantic_role="EMPIRICAL_PROBLEM_EVIDENCE"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.65, 4, narrative_tag="root_cause", semantic_role="ROOT_CAUSE_ANALYSIS"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.9, 5, narrative_tag="proposed_solution", section_label="Solution", semantic_role="PROPOSED_ARCHITECTURE_AND_SOLUTION"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.85, 6, narrative_tag="implementation", semantic_role="IMPLEMENTATION_ROADMAP"),
        NarrativeBeat(SlideIntent.COMPONENT_BREAKDOWN, 0.7, 7, narrative_tag="solution_components", semantic_role="KEY_SOLUTION_PILLARS"),
        NarrativeBeat(SlideIntent.WORKED_EXAMPLE, 0.75, 8, section_label="Validation", semantic_role="VALIDATION_AND_PILOT_RESULTS"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.65, 9, narrative_tag="results", semantic_role="BENCHMARK_RESULTS"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.6, 10, narrative_tag="limitations", semantic_role="IMPLEMENTATION_CONSTRAINTS"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.55, 11, narrative_tag="alternatives", semantic_role="ALTERNATIVE_APPROACHES"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.5, 12, semantic_role="DEPLOYMENT_BEST_PRACTICES"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="SOLUTION_SYNTHESIS"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],

    StoryGrammarType.CASE_STUDY: [
        NarrativeBeat(SlideIntent.COVER, 1.0, 0, required=True, semantic_role="CASE_STUDY_COVER"),
        NarrativeBeat(SlideIntent.CONTEXT, 0.9, 1, narrative_tag="case_background", section_label="Background", semantic_role="ORGANIZATIONAL_BACKGROUND"),
        NarrativeBeat(SlideIntent.WHY_IT_MATTERS, 0.75, 2, semantic_role="STRATEGIC_STAKES"),
        NarrativeBeat(SlideIntent.OBJECTIVES, 0.6, 3, narrative_tag="case_objectives", semantic_role="KEY_OBJECTIVES"),
        NarrativeBeat(SlideIntent.CONCEPT_EXPLANATION, 0.85, 4, narrative_tag="situation", section_label="Analysis", semantic_role="INITIAL_SITUATION_ASSESSMENT"),
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.8, 5, narrative_tag="actions_taken", semantic_role="STRATEGIC_ACTIONS_TAKEN"),
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.85, 6, narrative_tag="outcomes", section_label="Results", semantic_role="MEASURABLE_BUSINESS_OUTCOMES"),
        NarrativeBeat(SlideIntent.COMPARISON, 0.7, 7, narrative_tag="benchmarks", semantic_role="INDUSTRY_BENCHMARKING"),
        NarrativeBeat(SlideIntent.CASE_STUDY, 0.65, 8, narrative_tag="detailed_analysis", semantic_role="DEEP_DIVE_PIVOTAL_DECISION"),
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.5, 9, semantic_role="UNEXPECTED_CHALLENGES"),
        NarrativeBeat(SlideIntent.BEST_PRACTICES, 0.6, 10, narrative_tag="lessons_learned", section_label="Takeaways", semantic_role="TRANSFERABLE_LESSONS_LEARNED"),
        NarrativeBeat(SlideIntent.REAL_WORLD_APPLICATION, 0.55, 11, narrative_tag="broader_implications", semantic_role="BROADER_INDUSTRY_IMPLICATIONS"),
        NarrativeBeat(SlideIntent.SUMMARY, 0.95, 97, required=True, semantic_role="EXECUTIVE_SUMMARY"),
        NarrativeBeat(SlideIntent.Q_AND_A, 0.3, 99, semantic_role="DISCUSSION"),
    ],
}


# ═══════════════════════════════════════════════════════════════
# MODIFIER EFFECTS — how modifiers alter a grammar's priorities
# ═══════════════════════════════════════════════════════════════

MODIFIER_PRIORITY_BOOSTS: Dict[StoryGrammarType, Dict[SlideIntent, float]] = {
    StoryGrammarType.CONCEPT_TEACHING: {
        SlideIntent.DEFINITION: 0.15,
        SlideIntent.MENTAL_MODEL: 0.15,
        SlideIntent.WORKED_EXAMPLE: 0.1,
        SlideIntent.MISCONCEPTION: 0.1,
    },
    StoryGrammarType.COMPARISON: {
        SlideIntent.COMPARISON: 0.15,
        SlideIntent.TRADEOFF: 0.1,
    },
    StoryGrammarType.PROCESS: {
        SlideIntent.PROCESS_EXPLANATION: 0.1,
        SlideIntent.WORKED_EXAMPLE: 0.1,
    },
    StoryGrammarType.DATA_STORY: {
        SlideIntent.DATA_INSIGHT: 0.15,
        SlideIntent.CASE_STUDY: 0.1,
    },
    StoryGrammarType.HISTORY_EVOLUTION: {
        SlideIntent.CONTEXT: 0.1,
        SlideIntent.PROCESS_EXPLANATION: 0.1,
    },
    StoryGrammarType.TECHNICAL_SYSTEM: {
        SlideIntent.SYSTEM_OVERVIEW: 0.1,
        SlideIntent.COMPONENT_BREAKDOWN: 0.1,
        SlideIntent.CODE_EXAMPLE: 0.1,
    },
    StoryGrammarType.RESEARCH: {
        SlideIntent.DATA_INSIGHT: 0.1,
        SlideIntent.PROCESS_EXPLANATION: 0.1,
        SlideIntent.REFERENCES: 0.15,
    },
    StoryGrammarType.PROBLEM_SOLUTION: {
        SlideIntent.CONTEXT: 0.1,
        SlideIntent.PROCESS_EXPLANATION: 0.1,
        SlideIntent.WORKED_EXAMPLE: 0.1,
    },
    StoryGrammarType.CASE_STUDY: {
        SlideIntent.CASE_STUDY: 0.15,
        SlideIntent.DATA_INSIGHT: 0.1,
        SlideIntent.REAL_WORLD_APPLICATION: 0.1,
    },
}

# Intents to inject if a modifier is active and they're not in the primary grammar
MODIFIER_INJECT_INTENTS: Dict[StoryGrammarType, List[NarrativeBeat]] = {
    StoryGrammarType.CONCEPT_TEACHING: [
        NarrativeBeat(SlideIntent.MISCONCEPTION, 0.6, 10, narrative_tag="mod_misconception"),
        NarrativeBeat(SlideIntent.DEFINITION, 0.7, 3, narrative_tag="mod_definition"),
    ],
    StoryGrammarType.COMPARISON: [
        NarrativeBeat(SlideIntent.COMPARISON, 0.7, 9, narrative_tag="mod_comparison"),
        NarrativeBeat(SlideIntent.TRADEOFF, 0.6, 10, narrative_tag="mod_tradeoff"),
    ],
    StoryGrammarType.DATA_STORY: [
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.6, 8, narrative_tag="mod_data"),
    ],
    StoryGrammarType.PROCESS: [
        NarrativeBeat(SlideIntent.PROCESS_EXPLANATION, 0.65, 5, narrative_tag="mod_process"),
    ],
    StoryGrammarType.HISTORY_EVOLUTION: [
        NarrativeBeat(SlideIntent.CONTEXT, 0.6, 2, narrative_tag="mod_historical"),
    ],
    StoryGrammarType.RESEARCH: [
        NarrativeBeat(SlideIntent.DATA_INSIGHT, 0.6, 6, narrative_tag="mod_research_data"),
        NarrativeBeat(SlideIntent.REFERENCES, 0.55, 98, narrative_tag="mod_references"),
    ],
}


# ═══════════════════════════════════════════════════════════════
# VISUAL TYPE DEFAULTS BY INTENT
# ═══════════════════════════════════════════════════════════════

DEFAULT_VISUAL_BY_INTENT: Dict[SlideIntent, VisualTypeHint] = {
    SlideIntent.COVER: VisualTypeHint.TYPOGRAPHY_ONLY,
    SlideIntent.HOOK: VisualTypeHint.PHOTOGRAPH,
    SlideIntent.CONTEXT: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.WHY_IT_MATTERS: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.AGENDA: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.OBJECTIVES: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.PREREQUISITES: VisualTypeHint.NONE,
    SlideIntent.DEFINITION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
    SlideIntent.MENTAL_MODEL: VisualTypeHint.HUB_AND_SPOKE,
    SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.LAYERED_ARCHITECTURE,
    SlideIntent.COMPONENT_BREAKDOWN: VisualTypeHint.HUB_AND_SPOKE,
    SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.PROCESS_FLOW,
    SlideIntent.COMPARISON: VisualTypeHint.COMPARISON_MATRIX,
    SlideIntent.TRADEOFF: VisualTypeHint.TABLE,
    SlideIntent.WORKED_EXAMPLE: VisualTypeHint.TABLE,
    SlideIntent.CODE_EXAMPLE: VisualTypeHint.CODE_BLOCK,
    SlideIntent.FORMULA_EXPLANATION: VisualTypeHint.FORMULA,
    SlideIntent.CASE_STUDY: VisualTypeHint.PHOTOGRAPH,
    SlideIntent.REAL_WORLD_APPLICATION: VisualTypeHint.PHOTOGRAPH,
    SlideIntent.DATA_INSIGHT: VisualTypeHint.CHART,
    SlideIntent.MISCONCEPTION: VisualTypeHint.BEFORE_AFTER,
    SlideIntent.COMMON_MISTAKES: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.BEST_PRACTICES: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.DIAGNOSTIC: VisualTypeHint.TABLE,
    SlideIntent.KNOWLEDGE_CHECK: VisualTypeHint.NONE,
    SlideIntent.SUMMARY: VisualTypeHint.ICON_SUPPORT,
    SlideIntent.REFERENCES: VisualTypeHint.NONE,
    SlideIntent.Q_AND_A: VisualTypeHint.TYPOGRAPHY_ONLY,
}

# Domain-specific visual overrides
DOMAIN_VISUAL_OVERRIDES: Dict[str, Dict[SlideIntent, VisualTypeHint]] = {
    "computer_science": {
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.LAYERED_ARCHITECTURE,
        SlideIntent.DEFINITION: VisualTypeHint.HUB_AND_SPOKE,
        SlideIntent.CODE_EXAMPLE: VisualTypeHint.CODE_BLOCK,
    },
    "biology": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.COMPONENT_BREAKDOWN: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.CYCLE,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.DEFINITION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.CONTEXT: VisualTypeHint.ANNOTATED_ILLUSTRATION,
    },
    "history": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.TIMELINE,
        SlideIntent.COMPONENT_BREAKDOWN: VisualTypeHint.TIMELINE,
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.TIMELINE,
        SlideIntent.CONTEXT: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.CASE_STUDY: VisualTypeHint.PHOTOGRAPH,
    },
    "mathematics": {
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.FORMULA,
        SlideIntent.WORKED_EXAMPLE: VisualTypeHint.TABLE,
    },
    "engineering": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.LAYERED_ARCHITECTURE,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.PIPELINE,
    },
    "medicine_health_sciences": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.PROCESS_FLOW,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.DATA_INSIGHT: VisualTypeHint.CHART,
        SlideIntent.DEFINITION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
    },
    "law": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.HIERARCHY,
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.PROCESS_FLOW,
        SlideIntent.COMPARISON: VisualTypeHint.TABLE,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.HIERARCHY,
    },
    "languages": {
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.TABLE,
        SlideIntent.WORKED_EXAMPLE: VisualTypeHint.TABLE,
        SlideIntent.COMPARISON: VisualTypeHint.COMPARISON_MATRIX,
    },
    "education": {
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.PROCESS_FLOW,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.HUB_AND_SPOKE,
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.HIERARCHY,
    },
    "social_sciences": {
        SlideIntent.DATA_INSIGHT: VisualTypeHint.CHART,
        SlideIntent.CONTEXT: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.HUB_AND_SPOKE,
    },
    "environmental_science": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.DATA_INSIGHT: VisualTypeHint.CHART,
        SlideIntent.PROCESS_EXPLANATION: VisualTypeHint.CYCLE,
        SlideIntent.CONTEXT: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
        SlideIntent.DEFINITION: VisualTypeHint.ANNOTATED_ILLUSTRATION,
    },
    "finance_accounting": {
        SlideIntent.DATA_INSIGHT: VisualTypeHint.CHART,
        SlideIntent.COMPARISON: VisualTypeHint.TABLE,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.PIPELINE,
        SlideIntent.WORKED_EXAMPLE: VisualTypeHint.TABLE,
    },
    "literature_humanities": {
        SlideIntent.SYSTEM_OVERVIEW: VisualTypeHint.TIMELINE,
        SlideIntent.CONTEXT: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.CONCEPT_EXPLANATION: VisualTypeHint.PHOTOGRAPH,
        SlideIntent.COMPARISON: VisualTypeHint.COMPARISON_MATRIX,
    },
}


# ═══════════════════════════════════════════════════════════════
# LAYOUT FAMILY DEFAULTS BY INTENT
# ═══════════════════════════════════════════════════════════════

DEFAULT_LAYOUT_BY_INTENT: Dict[SlideIntent, LayoutFamily] = {
    SlideIntent.COVER: LayoutFamily.HERO,
    SlideIntent.HOOK: LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    SlideIntent.CONTEXT: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.WHY_IT_MATTERS: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.AGENDA: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.OBJECTIVES: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.PREREQUISITES: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.DEFINITION: LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    SlideIntent.MENTAL_MODEL: LayoutFamily.DIAGRAM_DOMINANT,
    SlideIntent.CONCEPT_EXPLANATION: LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    SlideIntent.SYSTEM_OVERVIEW: LayoutFamily.DIAGRAM_DOMINANT,
    SlideIntent.COMPONENT_BREAKDOWN: LayoutFamily.THREE_CARD,
    SlideIntent.PROCESS_EXPLANATION: LayoutFamily.FULL_WIDTH_PROCESS,
    SlideIntent.COMPARISON: LayoutFamily.SPLIT_COMPARISON,
    SlideIntent.TRADEOFF: LayoutFamily.SPLIT_COMPARISON,
    SlideIntent.WORKED_EXAMPLE: LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    SlideIntent.CODE_EXAMPLE: LayoutFamily.CODE_PLUS_EXPLANATION,
    SlideIntent.FORMULA_EXPLANATION: LayoutFamily.FORMULA_PLUS_EXAMPLE,
    SlideIntent.CASE_STUDY: LayoutFamily.CASE_STUDY_LAYOUT,
    SlideIntent.REAL_WORLD_APPLICATION: LayoutFamily.LEFT_TEXT_RIGHT_VISUAL,
    SlideIntent.DATA_INSIGHT: LayoutFamily.DATA_DASHBOARD,
    SlideIntent.MISCONCEPTION: LayoutFamily.SPLIT_COMPARISON,
    SlideIntent.COMMON_MISTAKES: LayoutFamily.THREE_CARD,
    SlideIntent.BEST_PRACTICES: LayoutFamily.THREE_CARD,
    SlideIntent.DIAGNOSTIC: LayoutFamily.MATRIX,
    SlideIntent.KNOWLEDGE_CHECK: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.SUMMARY: LayoutFamily.SUMMARY_GRID,
    SlideIntent.REFERENCES: LayoutFamily.CENTERED_FOCAL,
    SlideIntent.Q_AND_A: LayoutFamily.HERO,
}


# ═══════════════════════════════════════════════════════════════
# TEXT BUDGET BY INTENT
# ═══════════════════════════════════════════════════════════════

TEXT_BUDGET_BY_INTENT: Dict[SlideIntent, TextBudget] = {
    SlideIntent.COVER: TextBudget(
        title_max_words=10, subtitle_max_words=22, body_max_words=0,
        example_max_words=0, speaker_note_min_words=0, speaker_note_max_words=50,
    ),
    SlideIntent.HOOK: TextBudget(
        title_max_words=10, body_max_words=40, example_max_words=30,
    ),
    SlideIntent.DEFINITION: TextBudget(
        title_max_words=10, body_max_words=60, example_max_words=50,
    ),
    SlideIntent.CONCEPT_EXPLANATION: TextBudget(
        title_max_words=10, body_max_words=70, example_max_words=60,
    ),
    SlideIntent.SYSTEM_OVERVIEW: TextBudget(
        title_max_words=10, body_max_words=50, example_max_words=40,
    ),
    SlideIntent.PROCESS_EXPLANATION: TextBudget(
        title_max_words=10, body_max_words=60, example_max_words=50,
    ),
    SlideIntent.COMPARISON: TextBudget(
        title_max_words=10, body_max_words=50, card_body_max_words=25,
    ),
    SlideIntent.WORKED_EXAMPLE: TextBudget(
        title_max_words=10, body_max_words=80, example_max_words=80,
    ),
    SlideIntent.CASE_STUDY: TextBudget(
        title_max_words=10, body_max_words=70, example_max_words=70,
    ),
    SlideIntent.DATA_INSIGHT: TextBudget(
        title_max_words=10, body_max_words=50, example_max_words=40,
    ),
    SlideIntent.CODE_EXAMPLE: TextBudget(
        title_max_words=10, body_max_words=40, example_max_words=80,
    ),
    SlideIntent.SUMMARY: TextBudget(
        title_max_words=8, body_max_words=50, example_max_words=0,
    ),
    SlideIntent.Q_AND_A: TextBudget(
        title_max_words=6, body_max_words=0, example_max_words=0,
        speaker_note_min_words=0, speaker_note_max_words=50,
    ),
}


# ═══════════════════════════════════════════════════════════════
# BACKWARD-COMPAT: INTENT → LEGACY SLIDE TYPE
# ═══════════════════════════════════════════════════════════════

INTENT_TO_LEGACY_TYPE: Dict[SlideIntent, str] = {
    SlideIntent.COVER: "hero",
    SlideIntent.HOOK: "concept",
    SlideIntent.CONTEXT: "concept",
    SlideIntent.WHY_IT_MATTERS: "concept",
    SlideIntent.AGENDA: "concept",
    SlideIntent.OBJECTIVES: "concept",
    SlideIntent.PREREQUISITES: "concept",
    SlideIntent.DEFINITION: "definition",
    SlideIntent.MENTAL_MODEL: "concept",
    SlideIntent.CONCEPT_EXPLANATION: "concept",
    SlideIntent.SYSTEM_OVERVIEW: "architecture",
    SlideIntent.COMPONENT_BREAKDOWN: "concept",
    SlideIntent.PROCESS_EXPLANATION: "process_flow",
    SlideIntent.COMPARISON: "comparison",
    SlideIntent.TRADEOFF: "comparison",
    SlideIntent.WORKED_EXAMPLE: "example",
    SlideIntent.CODE_EXAMPLE: "concept",
    SlideIntent.FORMULA_EXPLANATION: "concept",
    SlideIntent.CASE_STUDY: "case_study",
    SlideIntent.REAL_WORLD_APPLICATION: "concept",
    SlideIntent.DATA_INSIGHT: "kpi_metrics",
    SlideIntent.MISCONCEPTION: "common_mistakes",
    SlideIntent.COMMON_MISTAKES: "common_mistakes",
    SlideIntent.BEST_PRACTICES: "concept",
    SlideIntent.DIAGNOSTIC: "concept",
    SlideIntent.KNOWLEDGE_CHECK: "quiz",
    SlideIntent.SUMMARY: "summary",
    SlideIntent.REFERENCES: "concept",
    SlideIntent.Q_AND_A: "qa",
}


# ═══════════════════════════════════════════════════════════════
# CORE ADAPTATION LOGIC
# ═══════════════════════════════════════════════════════════════

def adapt_grammar_to_slide_count(
    primary: StoryGrammarType,
    modifiers: List[StoryGrammarType],
    slide_count: int,
    domain: str = "general",
    enable_quiz: bool = False,
    topic_intelligence: Optional[Dict[str, Any]] = None,
) -> List[NarrativeBeat]:
    """
    Adapt a story grammar to a specific slide count.
    
    Algorithm:
      1. Start with primary grammar's beats
      2. Apply modifier priority boosts + inject missing beats
      3. Always include required beats (COVER, SUMMARY)
      4. Select top-priority beats to fill remaining positions
      5. Sort selected beats by narrative_order
      6. No fixed slide-index mapping (spec §9)
    """
    # 1. Clone primary grammar beats
    beats = [
        NarrativeBeat(
            intent=b.intent,
            priority=b.priority,
            narrative_order=b.narrative_order,
            narrative_tag=b.narrative_tag,
            required=b.required,
            section_label=b.section_label,
            semantic_role=b.semantic_role,
        )
        for b in STORY_GRAMMARS.get(primary, STORY_GRAMMARS[StoryGrammarType.CONCEPT_TEACHING])
    ]

    # 2. Apply modifier effects
    for mod in modifiers:
        # Boost priorities
        boosts = MODIFIER_PRIORITY_BOOSTS.get(mod, {})
        for beat in beats:
            if beat.intent in boosts:
                beat.priority = min(1.0, beat.priority + boosts[beat.intent])

        # Inject missing intents from modifiers
        inject_beats = MODIFIER_INJECT_INTENTS.get(mod, [])
        existing_intents = {b.intent for b in beats}
        for ib in inject_beats:
            # Prevent duplicate intent injection: only inject if intent not already present in grammar
            if ib.intent not in existing_intents:
                beats.append(NarrativeBeat(
                    intent=ib.intent,
                    priority=ib.priority,
                    narrative_order=ib.narrative_order,
                    narrative_tag=ib.narrative_tag,
                    required=ib.required,
                    section_label=ib.section_label,
                    semantic_role=ib.semantic_role or f"MOD_{ib.intent.value.upper()}",
                ))
                existing_intents.add(ib.intent)

    # 2.5 Apply topic intelligence signal priority boosts
    if topic_intelligence:
        if topic_intelligence.get("misconceptions"):
            for beat in beats:
                if beat.intent == SlideIntent.MISCONCEPTION:
                    beat.priority = min(1.0, beat.priority + 0.35)
        if topic_intelligence.get("comparison_candidates"):
            for beat in beats:
                if beat.intent in (SlideIntent.COMPARISON, SlideIntent.TRADEOFF):
                    beat.priority = min(1.0, beat.priority + 0.3)
        if topic_intelligence.get("processes"):
            for beat in beats:
                if beat.intent == SlideIntent.PROCESS_EXPLANATION:
                    beat.priority = min(1.0, beat.priority + 0.3)
        if topic_intelligence.get("real_world_examples"):
            for beat in beats:
                if beat.intent == SlideIntent.REAL_WORLD_APPLICATION:
                    beat.priority = min(1.0, beat.priority + 0.25)

    # 3. Handle quiz toggle
    if not enable_quiz:
        beats = [b for b in beats if b.intent != SlideIntent.KNOWLEDGE_CHECK]
    else:
        # Mark existing quiz beat as required, or inject one
        quiz_exists = False
        for b in beats:
            if b.intent == SlideIntent.KNOWLEDGE_CHECK:
                b.required = True
                b.priority = 1.0
                quiz_exists = True
        if not quiz_exists:
            beats.append(NarrativeBeat(
                SlideIntent.KNOWLEDGE_CHECK, 1.0, 95,
                narrative_tag="quiz", required=True,
                semantic_role="KNOWLEDGE_CHECK",
            ))

    # 4. Separate required and optional beats
    required = [b for b in beats if b.required]
    optional = [b for b in beats if not b.required]

    # Sort optional by priority descending
    optional.sort(key=lambda b: b.priority, reverse=True)

    # How many optional beats can we include?
    remaining = slide_count - len(required)
    selected_optional = optional[:max(0, remaining)]

    # 5. Combine and sort by narrative_order
    selected = required + selected_optional
    selected.sort(key=lambda b: b.narrative_order)

    logger.info(
        f"[StoryGrammar] Adapted {primary.value} to {slide_count} slides: "
        f"{[b.intent.value for b in selected]}"
    )
    return selected


def sanitize_visual_type_for_topic(
    visual: VisualTypeHint,
    intent: SlideIntent,
    domain: str,
    topic: str = "",
    grammar: Optional[StoryGrammarType] = None,
) -> VisualTypeHint:
    """
    Validates VisualTypeHint against domain + beat semantics (spec §6).
    Enforces that biology never uses layered_architecture, history never uses
    technical architecture metaphors, and ML research never uses code_block for generic methodology.
    """
    topic_lower = topic.lower()

    # 1. Biology sanity: no layered_architecture
    if domain in ("biology", "medicine_health_sciences"):
        if visual == VisualTypeHint.LAYERED_ARCHITECTURE:
            return VisualTypeHint.ANNOTATED_ILLUSTRATION

    # 2. History sanity: no layered_architecture or code_block
    if domain in ("history", "literature_humanities", "law"):
        if visual in (VisualTypeHint.LAYERED_ARCHITECTURE, VisualTypeHint.CODE_BLOCK):
            if intent == SlideIntent.PROCESS_EXPLANATION:
                return VisualTypeHint.TIMELINE
            return VisualTypeHint.PHOTOGRAPH

    # 3. Environmental science sanity: no layered_architecture
    if domain == "environmental_science":
        if visual == VisualTypeHint.LAYERED_ARCHITECTURE:
            return VisualTypeHint.ANNOTATED_ILLUSTRATION

    # 4. Research methodology / ML research sanity: no code_block for generic methodology
    if "research" in topic_lower or "methodology" in topic_lower or grammar == StoryGrammarType.RESEARCH:
        if visual == VisualTypeHint.CODE_BLOCK and intent != SlideIntent.CODE_EXAMPLE:
            if intent == SlideIntent.DEFINITION:
                return VisualTypeHint.HUB_AND_SPOKE
            if intent == SlideIntent.PROCESS_EXPLANATION:
                return VisualTypeHint.PROCESS_FLOW
            return VisualTypeHint.ANNOTATED_ILLUSTRATION

    return visual


def generate_blueprints_from_grammar(
    beats: List[NarrativeBeat],
    domain: str = "general",
    topic_intelligence: Optional[Dict[str, Any]] = None,
    topic: str = "",
) -> List[SlideBlueprint]:
    """
    Convert selected narrative beats into SlideBlueprint skeletons.
    Assigns visual_type, layout_family, text_budget deterministically.
    Applies domain + beat semantic validation to VisualTypeHint.
    """
    blueprints = []
    topic_str = topic or (topic_intelligence.get("topic", "") if topic_intelligence else "")

    for i, beat in enumerate(beats):
        # Determine visual type: domain-specific override → default → NONE
        domain_overrides = DOMAIN_VISUAL_OVERRIDES.get(domain, {})
        visual = domain_overrides.get(
            beat.intent,
            DEFAULT_VISUAL_BY_INTENT.get(beat.intent, VisualTypeHint.NONE),
        )

        # Sanitize visual type against domain + topic semantics (spec §6)
        visual = sanitize_visual_type_for_topic(
            visual=visual,
            intent=beat.intent,
            domain=domain,
            topic=topic_str or "Core Concepts",
        )

        # Determine layout family
        layout = DEFAULT_LAYOUT_BY_INTENT.get(beat.intent, LayoutFamily.CENTERED_FOCAL)

        # Determine text budget
        budget = TEXT_BUDGET_BY_INTENT.get(beat.intent, TextBudget())

        # Determine content density from intent
        dense_intents = {
            SlideIntent.COMPARISON, SlideIntent.WORKED_EXAMPLE,
            SlideIntent.CODE_EXAMPLE, SlideIntent.DATA_INSIGHT,
        }
        light_intents = {
            SlideIntent.COVER, SlideIntent.HOOK, SlideIntent.Q_AND_A,
            SlideIntent.SUMMARY,
        }
        if beat.intent in dense_intents:
            density = ContentDensity.HIGH
        elif beat.intent in light_intents:
            density = ContentDensity.LOW
        else:
            density = ContentDensity.MEDIUM

        # Determine visual priority
        vis_priority = beat.priority
        if visual == VisualTypeHint.NONE:
            vis_priority = 0.1

        # Canonical concepts from topic intelligence
        canonical = []
        if topic_intelligence:
            all_concepts = topic_intelligence.get("canonical_concepts", [])
            if not all_concepts:
                all_concepts = topic_intelligence.get("core_subtopics", [])
            if all_concepts and i > 0 and i < len(beats) - 1:
                # Distribute concepts across content slides
                content_idx = i - 1  # skip cover
                per_slide = max(1, len(all_concepts) // max(1, len(beats) - 2))
                start = content_idx * per_slide
                canonical = [
                    c.get("term", c) if isinstance(c, dict) else str(c)
                    for c in all_concepts[start:start + per_slide]
                ]

        if canonical:
            concept_phrase = canonical[i % len(canonical)]
        elif beat.semantic_role and beat.semantic_role != beat.intent.value:
            concept_phrase = beat.semantic_role.replace("_", " ").title()
        else:
            concept_phrase = ""

        topic_name = topic_str
        target_phrase = concept_phrase if concept_phrase and concept_phrase.lower() != topic_name.lower() else topic_name

        if not topic_str:
            bp_message = ""
        elif beat.intent == SlideIntent.COVER:
            bp_message = f"Foundational Principles and Overview of {topic_name}"
        elif beat.intent == SlideIntent.HOOK:
            bp_message = f"Why {topic_name} Demands Immediate Strategic Focus"
        elif beat.intent == SlideIntent.CONTEXT:
            bp_message = f"Operational Context and Environmental Baseline for {topic_name}"
        elif beat.intent == SlideIntent.WHY_IT_MATTERS:
            bp_message = f"Strategic Significance and Modern Implications of {topic_name}"
        elif beat.intent == SlideIntent.OBJECTIVES:
            bp_message = f"Core Learning Objectives and Structural Roadmap for {topic_name}"
        elif beat.intent == SlideIntent.AGENDA:
            bp_message = f"Session Agenda and Progression Architecture for {topic_name}"
        elif beat.intent == SlideIntent.DEFINITION:
            bp_message = f"Formal Definition and Operational Scope of {target_phrase}"
        elif beat.intent == SlideIntent.MENTAL_MODEL:
            bp_message = f"Conceptual Framework Governs Core Behaviors in {topic_name}"
        elif beat.intent == SlideIntent.PROCESS_EXPLANATION:
            bp_message = f"Stepwise Operational Mechanism Regulates {target_phrase}"
        elif beat.intent == SlideIntent.COMPARISON:
            bp_message = f"Comparative Analysis Distinguishes Key Trade-offs in {topic_name}"
        elif beat.intent == SlideIntent.TRADEOFF:
            bp_message = f"Architectural Trade-offs and Constraints in {topic_name}"
        elif beat.intent == SlideIntent.WORKED_EXAMPLE:
            bp_message = f"Worked Example Demonstrates Practical Execution of {target_phrase}"
        elif beat.intent == SlideIntent.CASE_STUDY:
            bp_message = f"Empirical Case Study Validates Performance in {topic_name}"
        elif beat.intent == SlideIntent.REAL_WORLD_APPLICATION:
            bp_message = f"Real-World Production Deployment of {target_phrase}"
        elif beat.intent == SlideIntent.MISCONCEPTION:
            bp_message = f"Common Misconceptions Obscure Empirical Mechanisms in {topic_name}"
        elif beat.intent == SlideIntent.COMMON_MISTAKES:
            bp_message = f"Frequent Implementation Errors and Mitigation in {topic_name}"
        elif beat.intent == SlideIntent.COMPONENT_BREAKDOWN:
            bp_message = f"Architectural Decomposition and Modular Subsystems of {topic_name}"
        elif beat.intent == SlideIntent.SYSTEM_OVERVIEW:
            bp_message = f"Systemic Architecture and End-to-End Topology of {topic_name}"
        elif beat.intent == SlideIntent.DATA_INSIGHT:
            bp_message = f"Empirical Findings and Key Metrics Validate Dynamics in {topic_name}"
        elif beat.intent == SlideIntent.BEST_PRACTICES:
            bp_message = f"Strategic Best Practices and Governance for {topic_name}"
        elif beat.intent == SlideIntent.SUMMARY:
            bp_message = f"Unified Synthesis Integrates Foundational Principles of {topic_name}"
        elif beat.intent == SlideIntent.Q_AND_A:
            bp_message = f"Discussion Topics and Critical Questions on {topic_name}"
        elif beat.intent == SlideIntent.REFERENCES:
            bp_message = f"Essential Academic Literature and Benchmark Sources"
        else:
            if concept_phrase and concept_phrase.lower() != topic_name.lower():
                bp_message = f"{concept_phrase} Establishes Operational Foundation in {topic_name}"
            else:
                perspectives = [
                    f"Foundational Framework and Operational Mechanisms of {topic_name}",
                    f"Structural Dynamics and Architectural Trade-offs in {topic_name}",
                    f"Critical Implementation Factors and Methodologies for {topic_name}",
                    f"Advanced Integration and Systemic Behavior in {topic_name}",
                ]
                bp_message = perspectives[i % len(perspectives)]

        # Ensure distinct messages across all blueprints in this generation
        seen_msgs = {b.primary_message.lower().strip() for b in blueprints if b.primary_message}
        if bp_message and bp_message.lower().strip() in seen_msgs:
            bp_message = f"{bp_message}: Phase {i+1}"

        bp = SlideBlueprint(
            slide_id=f"slide_{i+1}",
            slide_number=i + 1,
            intent=beat.intent,
            learning_purpose=bp_message or beat.semantic_role or beat.intent.value,
            primary_message=bp_message,
            narrative_role=beat.narrative_tag or beat.intent.value,
            semantic_role=beat.semantic_role or beat.narrative_tag or beat.intent.value,
            content_density=density,
            visual_priority=vis_priority,
            visual_type=visual,
            layout_family=layout,
            text_budget=budget,
            section_label=beat.section_label or None,
            canonical_concepts=canonical,
        )
        blueprints.append(bp)

    return blueprints


def blueprint_to_outline_dict(bp: SlideBlueprint) -> Dict[str, Any]:
    """
    Convert SlideBlueprint to outline dict for backward compatibility
    with the existing content agent.
    """
    legacy_type = INTENT_TO_LEGACY_TYPE.get(bp.intent, "concept")

    # Determine visual_hint from visual_type
    visual_hint_map = {
        VisualTypeHint.NONE: "none",
        VisualTypeHint.TYPOGRAPHY_ONLY: "none",
        VisualTypeHint.LAYERED_ARCHITECTURE: "architecture",
        VisualTypeHint.PIPELINE: "flow",
        VisualTypeHint.PROCESS_FLOW: "flow",
        VisualTypeHint.TIMELINE: "timeline",
        VisualTypeHint.COMPARISON_MATRIX: "comparison",
        VisualTypeHint.CHART: "diagram",
        VisualTypeHint.PHOTOGRAPH: "image",
        VisualTypeHint.CODE_BLOCK: "none",
    }
    visual_hint = visual_hint_map.get(bp.visual_type, "none")

    return {
        "slide_no": bp.slide_number,
        "type": legacy_type,
        "title": bp.primary_message or "",
        "key_message": bp.primary_message or "",
        "visual_hint": visual_hint,
        "section_label": bp.section_label,
        # vNext enrichment fields (available to content agent)
        "intent": bp.intent.value,
        "learning_purpose": bp.learning_purpose,
        "narrative_role": bp.narrative_role,
        "text_budget": bp.text_budget.model_dump(),
        "content_density": bp.content_density.value,
        "layout_family": bp.layout_family.value,
        "visual_type": bp.visual_type.value,
        "evidence_requirements": bp.evidence_requirements,
        "speaker_note_goal": bp.speaker_note_goal,
        "canonical_concepts": bp.canonical_concepts,
        "supporting_concepts": bp.supporting_concepts,
    }
