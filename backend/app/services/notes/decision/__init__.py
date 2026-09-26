"""
LearnByGenie Notes Decision Engine
================================
STEP 2 ONLY of the Notes Intelligence architecture.
Transforms CanonicalNotesContext into a deterministic NotesGenerationPlan.
Answers: "Given what LearnByGenie knows, what does this learner actually need in their notes?"
"""
from .schemas import (
    NotesGenerationPlan,
    PurposePlan,
    PurposeType,
    TeachingStrategyPlan,
    VisualPlan,
    RemediationPlan,
    PracticePlan,
    RevisionPlan,
    SectionPlanItem,
    DecisionReason,
    DecisionTraceItem,
)
from .policies import (
    MasteryBracket,
    TopicCategory,
    MasteryPolicy,
    GradePolicy,
    DecisionPrecedence,
)
from .topic_analyzer import TopicAnalyzer
from .purpose_selector import PurposeSelector
from .mastery_policy import MasteryPolicyEngine, MasteryDecision
from .pedagogy_policy import PedagogyPolicyEngine
from .visual_planner import VisualPlanner
from .section_planner import SectionPlanner
from .explainability import ExplainabilityEngine
from .engine import NotesDecisionEngine, decide_notes_plan

__all__ = [
    "NotesGenerationPlan",
    "PurposePlan",
    "PurposeType",
    "TeachingStrategyPlan",
    "VisualPlan",
    "RemediationPlan",
    "PracticePlan",
    "RevisionPlan",
    "SectionPlanItem",
    "DecisionReason",
    "DecisionTraceItem",
    "MasteryBracket",
    "TopicCategory",
    "MasteryPolicy",
    "GradePolicy",
    "DecisionPrecedence",
    "TopicAnalyzer",
    "PurposeSelector",
    "MasteryPolicyEngine",
    "MasteryDecision",
    "PedagogyPolicyEngine",
    "VisualPlanner",
    "SectionPlanner",
    "ExplainabilityEngine",
    "NotesDecisionEngine",
    "decide_notes_plan",
]
