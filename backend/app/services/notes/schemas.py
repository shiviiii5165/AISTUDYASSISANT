"""
AI Notes Generation Engine — Schemas & Data Contracts
======================================================
Strict Pydantic contracts for canonical notes context, pedagogical note structures,
quality scoring reports, and generated note documents for Class 3–12 learners.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class NoteFormat(str, Enum):
    LEARNING_NOTES = "learning_notes"
    QUICK_REVISION = "quick_revision"
    EXAM_PREPARATION = "exam_preparation"
    LECTURE_NOTES = "lecture_notes"
    VISUAL_NOTES = "visual_notes"
    MIND_MAP = "mind_map"
    FLOWCHART = "flowchart"
    COMPARISON_NOTES = "comparison_notes"
    FORMULA_SHEET = "formula_sheet"
    REMEDIAL_NOTES = "remedial_notes"


class NoteDepth(str, Enum):
    CONCISE = "concise"
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    DEEP = "deep"


class NoteDifficulty(str, Enum):
    FOUNDATIONAL = "foundational"
    BASIC = "basic"
    STANDARD = "standard"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class VisualSpec(BaseModel):
    type: str = "flowchart"  # "flowchart" | "mind_map" | "process" | "hierarchy" | "cycle" | "comparison_matrix"
    title: str = ""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    mermaid_code: Optional[str] = None


class CalloutItem(BaseModel):
    type: str = "tip"  # "warning" | "tip" | "exam_alert" | "misconception" | "fun_fact"
    title: str = ""
    text: str = ""


class SectionSemanticEvidence(BaseModel):
    """Internal auditable pedagogical metadata for Step 4 & certification. Omitted from student HTML/PDF."""
    concept_id: Optional[str] = None
    instructional_role: str = "core_concept"  # "core_concept" | "worked_example" | "comparison" | "misconception_remediation" | "revision"
    explanation_present: bool = True
    intuition_present: bool = False
    example_present: bool = False
    worked_example_present: bool = False
    practice_targets: List[str] = Field(default_factory=list)
    misconception_targets: List[str] = Field(default_factory=list)
    visual_targets: List[str] = Field(default_factory=list)
    revision_targets: List[str] = Field(default_factory=list)
    learning_flow_stage: Optional[str] = None
    learning_mode: Optional[str] = None
    cognitive_operation: Optional[str] = None
    is_interactive: bool = False
    interaction_type: Optional[str] = None
    provenance_reason: Optional[str] = None


class NoteSection(BaseModel):
    id: str = Field(default_factory=lambda: f"sec_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    section_type: str = "core_concept"  # "overview", "core_concept", "worked_example", "formula_box", "flowchart", "mind_map", "comparison_table", "common_misconceptions", "quick_summary", "exam_tips", "checkpoint_practice", etc.
    title: str
    content: str
    target_concept: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    callouts: List[CalloutItem] = Field(default_factory=list)
    visual_spec: Optional[VisualSpec] = None
    semantic_evidence: Optional[SectionSemanticEvidence] = None
    provenance: Optional[str] = "generated_from_context"  # "curated_catalog" | "authoritative_source" | "generated_from_context" | "deterministic_fallback"

    @property
    def heading(self) -> str:
        return self.title


class NotesQualityReport(BaseModel):
    score: float = 100.0  # 0.0 to 100.0
    accuracy: float = 25.0
    curriculum_alignment: float = 20.0
    grade_appropriateness: float = 15.0
    clarity: float = 15.0
    completeness: float = 10.0
    relevance: float = 5.0
    format_compliance: float = 5.0
    misconception_coverage: float = 5.0
    warnings: List[str] = Field(default_factory=list)
    feedback: List[str] = Field(default_factory=list)


class NotesDocument(BaseModel):
    schema_version: str = "1.0"
    id: str
    document_id: Optional[str] = None
    title: str
    subject: str = "General"
    class_level: str = "Class 10"
    topic: str
    curriculum: str = "CBSE"
    language: str = "english"
    mode: str = "topic"  # "topic" | "lesson_context"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    learning_objectives: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    selected_formats: List[NoteFormat] = Field(default_factory=lambda: [NoteFormat.LEARNING_NOTES])
    depth: NoteDepth = NoteDepth.STANDARD
    difficulty: NoteDifficulty = NoteDifficulty.STANDARD
    sections: List[NoteSection] = Field(default_factory=list)
    visuals: List[VisualSpec] = Field(default_factory=list)
    practice: List[Dict[str, Any]] = Field(default_factory=list)
    revision_summary: Optional[Dict[str, Any]] = None
    source_citations: List[Dict[str, Any]] = Field(default_factory=list)
    quality: NotesQualityReport = Field(default_factory=NotesQualityReport)
    lineage: Dict[str, Any] = Field(default_factory=dict)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    generation_warnings: List[str] = Field(default_factory=list)
    generation_mode: Optional[str] = None
    structural_repairs: List[str] = Field(default_factory=list)
    provenance: Optional[str] = "generated_from_context"
    learning_flow_plan: Optional[Dict[str, Any]] = None
    learning_flow_quality: Optional[Dict[str, Any]] = None

    @field_validator("curriculum", mode="before")
    @classmethod
    def _validate_curriculum(cls, v: Any) -> str:
        if hasattr(v, "board"):
            return str(v.board or "unknown")
        if isinstance(v, dict) and "board" in v:
            return str(v["board"] or "unknown")
        if v is None:
            return "unknown"
        val = str(v).strip()
        if not val or val.lower() == "none":
            return "unknown"
        return val

    @classmethod
    def create_synced(cls, **data: Any) -> "NotesDocument":
        doc_id = data.get("document_id") or data.get("id") or f"note_{int(datetime.now(timezone.utc).timestamp()*1000)}"
        data["id"] = doc_id
        data["document_id"] = doc_id
        return cls(**data)



from .context.schemas import (
    CanonicalNotesContext,
    FieldProvenance,
    ContextConflict,
    ContextCompleteness,
    NotesContextSource,
    ContextResolutionStatus,
    ContextSnapshot,
    AnalyzeContextRequest,
    AnalyzeContextResponse,
)


class DecisionOutput(BaseModel):
    selected_formats: List[NoteFormat]
    depth: NoteDepth
    difficulty: NoteDifficulty
    required_sections: List[str]
    tone_instructions: str
    misconceptions_to_target: List[str] = Field(default_factory=list)
    weak_concepts_to_reinforce: List[str] = Field(default_factory=list)


# Wire request contracts
class GenerateNotesRequest(BaseModel):
    mode: str = "topic"  # "topic" | "lesson_context"
    topic: str
    class_level: str = "Class 10"
    subject: str = "General"
    curriculum: str = "CBSE"
    language: str = "english"
    
    # Optional lineage identifiers for lesson-context mode
    roadmap_id: Optional[str] = None
    stage_id: Optional[str] = None
    teach_session_id: Optional[str] = None
    quiz_id: Optional[str] = None
    deck_id: Optional[str] = None
    source_document_ids: Optional[List[str]] = None
    
    # Optional overrides
    requested_depth: Optional[str] = None
    requested_format: Optional[str] = None
    user_instructions: Optional[str] = None
