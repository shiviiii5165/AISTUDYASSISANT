"""
TeachGenie Notes Decision Engine — Adaptive Learning Flow Schemas
==================================================================
Provides machine-readable, strongly-typed domain contracts for
determining HOW a learner should learn a specific topic.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class LearningMode(str, Enum):
    """Pedagogical instructional mode governing a learning flow or individual stage."""
    ABSORPTION = "absorption"
    GUIDED_DISCOVERY = "guided_discovery"
    ACTIVE_RETRIEVAL = "active_retrieval"
    REMEDIATION = "remediation"
    PRACTICE = "practice"
    MASTERY = "mastery"
    EXAM_PREPARATION = "exam_preparation"
    REVISION = "revision"
    MIXED = "mixed"


class CognitiveOperation(str, Enum):
    """Specific cognitive operation required of the learner at a given stage."""
    RECOGNIZE = "recognize"
    RECALL = "recall"
    EXPLAIN = "explain"
    CLASSIFY = "classify"
    COMPARE = "compare"
    PREDICT = "predict"
    DERIVE = "derive"
    CALCULATE = "calculate"
    APPLY = "apply"
    DIAGNOSE = "diagnose"
    EVALUATE = "evaluate"
    CREATE = "create"
    TRANSFER = "transfer"


class LearnerKnowledgeState(str, Enum):
    """Inferred current knowledge level of the student."""
    NOVICE = "novice"
    EMERGING = "emerging"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class LearnerEntryState(BaseModel):
    """
    Step 2 Evaluated Entry State:
    Explicitly derived from Step 1 context with field-level provenance.
    Never fabricates state; unknown remains unknown.
    """
    model_config = ConfigDict(populate_by_name=True)

    knowledge_state: str = LearnerKnowledgeState.UNKNOWN.value
    mastery: str = "unknown"  # "low" | "medium" | "high" | "unknown"
    mastery_score: Optional[float] = None
    confidence: str = "unknown"  # "low" | "medium" | "high" | "unknown"
    misconception_state: str = "none_known"  # "none_known" | "suspected" | "confirmed" | "multiple" | "unknown"
    prerequisite_state: str = "unknown"  # "missing" | "partial" | "adequate" | "unknown"
    exam_urgency: str = "none"  # "none" | "low" | "medium" | "high" | "immediate"
    engagement_state: str = "unknown"  # "passive" | "active" | "inconsistent" | "unknown"
    prior_exposure: str = "unknown"  # "none" | "low" | "high" | "unknown"
    provenance: Dict[str, str] = Field(default_factory=dict)


class LearningStageItem(BaseModel):
    """An individual instructional stage within the ordered learning flow."""
    model_config = ConfigDict(populate_by_name=True)

    stage_id: str
    stage_name: str
    mode: LearningMode
    cognitive_operation: CognitiveOperation
    target_concept: str
    instructional_goal: str
    is_interactive: bool = False
    interaction_type: Optional[str] = None  # "prediction_prompt" | "thinking_checkpoint" | "explain_back" | "retrieval_question"
    scaffolding_level: str = "moderate"  # "minimal" | "moderate" | "guided" | "intensive"
    rationale: str = ""


class LearningCheckpoint(BaseModel):
    """
    Diagnostic gating checkpoint:
    Answers 'What evidence would tell TeachGenie whether to proceed, reteach, or increase difficulty?'
    """
    model_config = ConfigDict(populate_by_name=True)

    checkpoint_id: str
    after_stage: str
    cognitive_operation: CognitiveOperation
    prompt: str
    expected_evidence: str
    if_success: str
    if_failure: str
    remediation_action: str


class AdaptationRule(BaseModel):
    """Deterministic policy rule governing branch adaptation."""
    model_config = ConfigDict(populate_by_name=True)

    condition: str
    action: str
    rationale: str


class MasteryCheckPlan(BaseModel):
    """Exit verification plan establishing verifiable evidence of learning completion."""
    model_config = ConfigDict(populate_by_name=True)

    required: bool = True
    method: str  # "transfer_problem" | "self_explanation" | "concept_application" | "error_analysis"
    target_concepts: List[str] = Field(default_factory=list)
    cognitive_operation: CognitiveOperation = CognitiveOperation.APPLY
    success_criteria: str
    fallback_if_failed: str


class PrerequisiteStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = False
    gap_identified: Optional[str] = None
    bridge_action: Optional[str] = None


class ExplanationStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    depth: str = "standard"  # "concise" | "standard" | "detailed" | "scaffolded"
    analogy_style: str = "concrete"  # "concrete" | "formal" | "minimal"
    formal_notation: bool = True


class InteractionStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    engagement_mode: str = "passive"  # "passive" | "active" | "mixed"
    interaction_intensity: str = "low"  # "none" | "low" | "medium" | "high"
    cognitive_participation: List[str] = Field(default_factory=list)


class RetrievalStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frequency: str = "strategic"  # "none" | "strategic" | "frequent"
    formats: List[str] = Field(default_factory=list)


class MisconceptionStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = False
    has_misconceptions: bool = False
    remediation_depth: str = "none"  # "none" | "callout" | "full_semantic_repair"
    target_misconceptions: List[str] = Field(default_factory=list)
    remediation_target_keys: List[str] = Field(default_factory=list)


class ExampleStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    style: str = "representative_procedural"  # "concrete_guided" | "representative_procedural" | "tricky_edge_case" | "exam_marking_oriented"
    scaffolding: str = "moderate"


class PracticeStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    starting_difficulty: str = "basic"
    target_difficulty: str = "intermediate"
    scaffolding_level: str = "moderate"  # "high" | "moderate" | "minimal"
    progression: List[str] = Field(default_factory=lambda: ["recall", "conceptual", "application"])
    item_count: int = 3
    feedback_style: str = "step_by_step"
    retry_policy: str = "guided_hint"


class RevisionStrategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    compression_ratio: str = "medium"  # "high" | "medium" | "low"
    focus_areas: List[str] = Field(default_factory=list)


class LearningFlowPlan(BaseModel):
    """
    Step 2 Structured Learning Flow:
    Answers: 'What should this learner learn, in what sequence, using what learning strategy,
    and what evidence should indicate progress?'
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = "1.0"
    entry_state: LearnerEntryState = Field(default_factory=LearnerEntryState)
    target_state: str = "proficient"
    learning_mode: LearningMode = LearningMode.MIXED
    sequence: List[LearningStageItem] = Field(default_factory=list)
    checkpoints: List[LearningCheckpoint] = Field(default_factory=list)
    prerequisite_strategy: PrerequisiteStrategy = Field(default_factory=PrerequisiteStrategy)
    explanation_strategy: ExplanationStrategy = Field(default_factory=ExplanationStrategy)
    interaction_strategy: InteractionStrategy = Field(default_factory=InteractionStrategy)
    retrieval_strategy: RetrievalStrategy = Field(default_factory=RetrievalStrategy)
    misconception_strategy: MisconceptionStrategy = Field(default_factory=MisconceptionStrategy)
    example_strategy: ExampleStrategy = Field(default_factory=ExampleStrategy)
    practice_strategy: PracticeStrategy = Field(default_factory=PracticeStrategy)
    revision_strategy: RevisionStrategy = Field(default_factory=RevisionStrategy)
    mastery_check: MasteryCheckPlan = Field(default_factory=lambda: MasteryCheckPlan(
        method="concept_application",
        target_concepts=[],
        cognitive_operation=CognitiveOperation.APPLY,
        success_criteria="Correct application of foundational principles to solve domain problem",
        fallback_if_failed="Review fundamental mechanism and procedural steps"
    ))
    exit_condition: str = "Demonstrated conceptual and procedural mastery"
    adaptation_rules: List[AdaptationRule] = Field(default_factory=list)
    rationale: str = ""
    confidence: float = 1.0
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def primary_mode(self) -> LearningMode:
        return self.learning_mode

    @primary_mode.setter
    def primary_mode(self, val: LearningMode) -> None:
        self.learning_mode = val

