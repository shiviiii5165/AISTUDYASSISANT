"""
LearnByGenie Notes Decision Engine — Domain Schemas & Contracts
=============================================================
Strict Pydantic contracts for Step 2 of the Notes Intelligence Layer.
Transforms CanonicalNotesContext into a deterministic NotesGenerationPlan.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

from app.services.notes.schemas import NoteFormat, NoteDepth, NoteDifficulty
from .learning_flow_schemas import (
    LearningMode, CognitiveOperation, LearnerKnowledgeState,
    LearnerEntryState, LearningStageItem, LearningCheckpoint,
    AdaptationRule, MasteryCheckPlan, PrerequisiteStrategy,
    ExplanationStrategy, InteractionStrategy, RetrievalStrategy,
    MisconceptionStrategy, ExampleStrategy, PracticeStrategy,
    RevisionStrategy, LearningFlowPlan
)


class PurposeType(str, Enum):
    LEARNING = "learning"
    REVISION = "revision"
    EXAM_PREPARATION = "exam_preparation"
    REMEDIATION = "remediation"
    LESSON_SUMMARY = "lesson_summary"
    LECTURE_CAPTURE = "lecture_capture"
    CONCEPT_REFERENCE = "concept_reference"


class PurposePlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    primary: str = PurposeType.LEARNING.value
    secondary: List[str] = Field(default_factory=list)


class TeachingStrategyPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: str = "balanced"  # "active" | "passive" | "balanced"
    scaffolding: str = "moderate"  # "minimal" | "moderate" | "guided" | "intensive"
    features: List[str] = Field(default_factory=list)
    tone_instructions: str = ""


class VisualPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = False
    type: str = "optional"  # "flowchart" | "comparison_matrix" | "diagram" | "timeline" | "mind_map" | "concept_map" | "optional"
    focus: Optional[str] = None


class RemediationPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = False
    priority: str = "none"  # "high" | "medium" | "low" | "none"
    target_concepts: List[str] = Field(default_factory=list)
    include_misconception_correction: bool = False
    include_guided_examples: bool = False


class PracticePlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = True
    count: int = 3
    difficulty: str = "basic"  # "foundational" | "basic" | "intermediate" | "advanced"
    types: List[str] = Field(default_factory=lambda: ["recall", "application"])


class RevisionPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool = False
    priority: str = "none"  # "high" | "medium" | "low" | "none"
    include: List[str] = Field(default_factory=list)  # "key_points", "formulas", "common_mistakes", "high_yield_summary"


class SectionPlanItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    title: Optional[str] = None
    required: bool = True
    target: Optional[str] = None
    sub_concepts: List[str] = Field(default_factory=list)


class DecisionReason(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision: str
    reason: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class DecisionTraceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision: str
    candidates: List[str] = Field(default_factory=list)
    winning_candidate: str
    reason: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class NotesGenerationPlan(BaseModel):
    """
    Step 2 Canonical Output: Deterministic generation plan answering:
    'Given what LearnByGenie knows, what does this learner actually need in their notes?'
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = "1.0"

    purpose: PurposePlan
    formats: List[NoteFormat]
    difficulty: NoteDifficulty
    depth: NoteDepth
    teaching_strategy: TeachingStrategyPlan

    section_plan: List[SectionPlanItem]
    visual_plan: VisualPlan
    remediation_plan: RemediationPlan
    practice_plan: PracticePlan
    revision_plan: RevisionPlan

    constraints: List[str] = Field(default_factory=list)

    learning_flow_plan: Optional[LearningFlowPlan] = None

    decision_reasons: List[DecisionReason] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    decision_trace: List[DecisionTraceItem] = Field(default_factory=list)
    decision_confidence: float = 1.0  # 0.0 to 1.0

    # Backward compatibility fields for legacy consumers (NotesGenerator, NotesValidator, tests)
    selected_formats: List[NoteFormat] = Field(default_factory=list)
    required_sections: List[str] = Field(default_factory=list)
    tone_instructions: str = ""
    misconceptions_to_target: List[str] = Field(default_factory=list)
    weak_concepts_to_reinforce: List[str] = Field(default_factory=list)

    @classmethod
    def create(cls, **data: Any) -> "NotesGenerationPlan":
        """Factory helper ensuring backward-compatible accessors are always synchronized."""
        formats = data.get("formats", [])
        if not data.get("selected_formats") and formats:
            data["selected_formats"] = list(formats)

        section_plan = data.get("section_plan", [])
        if not data.get("required_sections") and section_plan:
            data["required_sections"] = [
                s.type if hasattr(s, "type") else s.get("type")
                for s in section_plan
                if (s.required if hasattr(s, "required") else s.get("required", True))
            ]

        teaching_strategy = data.get("teaching_strategy")
        if not data.get("tone_instructions") and teaching_strategy:
            data["tone_instructions"] = (
                teaching_strategy.tone_instructions
                if hasattr(teaching_strategy, "tone_instructions")
                else teaching_strategy.get("tone_instructions", "")
            )

        remediation_plan = data.get("remediation_plan")
        if not data.get("misconceptions_to_target") and remediation_plan:
            targets = (
                remediation_plan.target_concepts
                if hasattr(remediation_plan, "target_concepts")
                else remediation_plan.get("target_concepts", [])
            )
            data["misconceptions_to_target"] = list(targets[:3])

        return cls(**data)

