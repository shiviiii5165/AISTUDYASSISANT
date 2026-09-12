"""
TeachGenie Notes Context Engine — Strict Domain Schemas & Contracts
===================================================================
CanonicalNotesContext contract for Step 1 of the Notes Intelligence Layer.
Provides lossless provenance tracking, structured conflict metadata,
deterministic completeness scoring, and multi-source educational contexts.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict
from datetime import datetime, timezone
import uuid
from .normalizer import ContextNormalizer
from .topic_descriptor import TopicDescriptor


class NotesContextSource(str, Enum):
    EXPLICIT_INPUT = "explicit_input"      # Priority 1, Confidence 1.00
    LESSON = "lesson"                      # Priority 2, Confidence 0.95
    CURRICULUM = "curriculum"              # Priority 3, Confidence 0.90
    STUDENT = "student"                    # Priority 4, Confidence 0.85
    ASSESSMENT = "assessment"              # Priority 5, Confidence 0.80
    TEACHME = "teachme"                    # Priority 6, Confidence 0.75
    PPT = "ppt"                            # Priority 7, Confidence 0.70
    SOURCE_DOCUMENT = "source_document"    # Priority 8, Confidence 0.60
    GENERIC = "generic"                    # Priority 8, Confidence 0.50


SOURCE_PRIORITY_MAP: Dict[NotesContextSource, int] = {
    NotesContextSource.EXPLICIT_INPUT: 1,
    NotesContextSource.LESSON: 2,
    NotesContextSource.CURRICULUM: 3,
    NotesContextSource.STUDENT: 4,
    NotesContextSource.ASSESSMENT: 5,
    NotesContextSource.TEACHME: 6,
    NotesContextSource.PPT: 7,
    NotesContextSource.SOURCE_DOCUMENT: 8,
    NotesContextSource.GENERIC: 8,
}

SOURCE_CONFIDENCE_MAP: Dict[NotesContextSource, float] = {
    NotesContextSource.EXPLICIT_INPUT: 1.0,
    NotesContextSource.LESSON: 0.95,
    NotesContextSource.CURRICULUM: 0.90,
    NotesContextSource.STUDENT: 0.85,
    NotesContextSource.ASSESSMENT: 0.80,
    NotesContextSource.TEACHME: 0.75,
    NotesContextSource.PPT: 0.70,
    NotesContextSource.SOURCE_DOCUMENT: 0.60,
    NotesContextSource.GENERIC: 0.50,
}


class ContextResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    CONFLICTING = "conflicting"


class FieldProvenance(BaseModel):
    """Field-level provenance explaining the origin and reliability of a resolved value."""
    value: Any
    source: NotesContextSource
    priority: int
    confidence: float
    status: ContextResolutionStatus = ContextResolutionStatus.RESOLVED
    raw_value: Optional[Any] = None


class ContextConflict(BaseModel):
    """Structured conflict representation preserving conflicting values without silent overwrite."""
    field: str
    severity: str = "medium"  # "low" | "medium" | "high"
    values: List[Dict[str, Any]] = Field(default_factory=list)  # [{"source": "student", "value": "8"}]
    resolved_value: Any
    resolved_from: str
    reason: Optional[str] = None


class ContextCompleteness(BaseModel):
    """Deterministic rule-based context completeness assessment."""
    score: float = 0.0  # 0.0 to 100.0
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    breakdown: Dict[str, float] = Field(default_factory=dict)


# Sub-contexts representing distinct source boundaries

class RequestContext(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    user_id: str = "anonymous"
    mode: str = "topic"  # "topic" | "lesson_context" | "assessment_driven" | "teachme_driven" | "ppt_driven" | "combined"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExplicitInputContext(BaseModel):
    topic: str
    raw_topic: str = ""
    class_level: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None
    curriculum: Optional[str] = None
    language: Optional[str] = None
    additional_instructions: Optional[str] = None


class StudentContext(BaseModel):
    student_id: Optional[str] = None
    class_level: Optional[str] = None
    grade: Optional[int] = None
    age_group: Optional[str] = None
    language: Optional[str] = None
    learning_preferences: List[str] = Field(default_factory=list)
    current_learning_state: Dict[str, Any] = Field(default_factory=dict)
    status: str = "unknown"  # "resolved" | "unknown" | "unavailable"


class CurriculumContext(BaseModel):
    curriculum_id: Optional[str] = None
    board: Optional[str] = None  # e.g. "CBSE", "ICSE", "State Board"
    subject: Optional[str] = None
    grade: Optional[int] = None
    course: Optional[str] = None
    chapter: Optional[str] = None
    unit: Optional[str] = None
    curriculum_objectives: List[str] = Field(default_factory=list)
    syllabus_references: List[str] = Field(default_factory=list)
    status: str = "unknown"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return (self.board or "").lower() == other.strip().lower()
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.board or ""


class LessonContext(BaseModel):
    roadmap_id: Optional[str] = None
    stage_id: Optional[str] = None
    stage_title: Optional[str] = None
    stage_topic: Optional[str] = None
    stage_objective: Optional[str] = None
    learning_objectives: List[str] = Field(default_factory=list)
    structured_objectives: Optional[Dict[str, List[str]]] = None
    activities: List[str] = Field(default_factory=list)
    teaching_method: Optional[str] = None  # e.g. "active", "inquiry", "passive", "discussion"
    teacher_explanation: Optional[str] = None
    lesson_sequence: List[str] = Field(default_factory=list)
    teacher_instructions: List[str] = Field(default_factory=list)
    expected_misconceptions: List[str] = Field(default_factory=list)
    status: str = "unknown"


class AssessmentContext(BaseModel):
    quiz_id: Optional[str] = None
    latest_score: Optional[float] = None
    attempts: int = 0
    weak_concepts: List[str] = Field(default_factory=list)
    mastery: Dict[str, float] = Field(default_factory=dict)
    misconceptions: List[Dict[str, Any]] = Field(default_factory=list)
    wrong_answer_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "unknown"


class TeachMeContext(BaseModel):
    session_id: Optional[str] = None
    misconceptions: List[Dict[str, Any]] = Field(default_factory=list)
    confused_concepts: List[str] = Field(default_factory=list)
    learner_questions: List[str] = Field(default_factory=list)
    interventions: List[str] = Field(default_factory=list)
    conversation_signals: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    status: str = "unknown"


class PPTContext(BaseModel):
    deck_id: Optional[str] = None
    slide_count: int = 0
    slide_topics: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    diagram_ideas: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    status: str = "unknown"


class SourcesContext(BaseModel):
    source_documents: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "unknown"


class ResolvedContext(BaseModel):
    """Authoritative consolidated context resolved by strict priority without data loss."""
    topic: str
    raw_topic: str
    class_level: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None
    curriculum: Optional[str] = None
    language: str = "english"
    teaching_method: str = "unknown"
    mastery_state: Dict[str, float] = Field(default_factory=dict)
    misconceptions: List[str] = Field(default_factory=list)
    weak_concepts: List[str] = Field(default_factory=list)


class ProvenanceContext(BaseModel):
    field_sources: Dict[str, FieldProvenance] = Field(default_factory=dict)
    confidence: float = 1.0
    conflicts: List[ContextConflict] = Field(default_factory=list)


class CanonicalNotesContext(BaseModel):
    """
    Step 1 Canonical Output: One unified, normalized, prioritized, and validated context object.
    Provides complete traceability, conflict tracking, and backwards compatibility.
    """
    context_schema_version: str = "1.0"
    request: RequestContext
    explicit_input: ExplicitInputContext
    student: StudentContext
    curriculum: CurriculumContext
    lesson: LessonContext
    assessment: AssessmentContext
    teach_me: TeachMeContext
    ppt: PPTContext
    sources: SourcesContext
    resolved_context: ResolvedContext
    provenance: ProvenanceContext
    completeness: ContextCompleteness
    topic_descriptor: Optional[TopicDescriptor] = None

    # Optional generation override attributes for downstream compatibility
    requested_depth: Optional[Any] = None
    requested_format: Optional[Any] = None

    @model_validator(mode="before")
    @classmethod
    def _handle_legacy_or_canonical(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # If already in canonical form (has 'resolved_context' and 'request')
        if "resolved_context" in data and "request" in data:
            return data

        # Otherwise, legacy or simplified construction:
        topic_raw = data.get("topic", "")
        raw_topic, norm_topic = ContextNormalizer.normalize_topic(topic_raw)
        grade_num, class_disp = ContextNormalizer.normalize_grade(data.get("class_level") or data.get("classLevel") or "Class 10")
        board = ContextNormalizer.normalize_curriculum(data.get("curriculum") or "CBSE")
        subject_val = data.get("subject", "General")
        lang_val = ContextNormalizer.normalize_language(data.get("language") or "english")
        mode_val = data.get("mode", "topic")
        instructions = data.get("explicit_user_instructions") or data.get("user_instructions")

        req_ctx = RequestContext(mode=mode_val)
        exp_ctx = ExplicitInputContext(
            topic=norm_topic or topic_raw,
            raw_topic=raw_topic or topic_raw,
            class_level=class_disp,
            grade=grade_num,
            subject=subject_val,
            curriculum=board,
            language=lang_val,
            additional_instructions=instructions
        )

        mastery_dict = {}
        for k, v in data.get("student_mastery", {}).items():
            norm_v = ContextNormalizer.normalize_mastery(v)
            if norm_v is not None:
                mastery_dict[k.lower()] = norm_v

        stu_data = data.get("student")
        if not mastery_dict and stu_data:
            cls_map = stu_data.current_learning_state if hasattr(stu_data, "current_learning_state") else (stu_data.get("current_learning_state", {}) if isinstance(stu_data, dict) else {})
            if isinstance(cls_map, dict):
                for k, v in cls_map.get("mastery", {}).items():
                    norm_v = ContextNormalizer.normalize_mastery(v)
                    if norm_v is not None:
                        mastery_dict[k.lower()] = norm_v

        if isinstance(stu_data, StudentContext):
            stu_ctx = stu_data
            if mastery_dict and not stu_ctx.current_learning_state.get("mastery"):
                stu_ctx.current_learning_state["mastery"] = mastery_dict
        else:
            stu_ctx = StudentContext(
                class_level=class_disp,
                grade=grade_num,
                language=lang_val,
                current_learning_state={"mastery": mastery_dict},
                status="resolved" if mastery_dict else "unknown"
            )

        curr_ctx = CurriculumContext(
            board=board,
            subject=subject_val,
            grade=grade_num,
            status="resolved" if board else "unknown"
        )

        les_data = data.get("lesson")
        if isinstance(les_data, LessonContext):
            les_ctx = les_data
            if data.get("expected_misconceptions") and not les_ctx.expected_misconceptions:
                les_ctx.expected_misconceptions = list(data.get("expected_misconceptions"))
        elif isinstance(les_data, dict):
            les_ctx = LessonContext(**les_data)
            if data.get("expected_misconceptions") and not les_ctx.expected_misconceptions:
                les_ctx.expected_misconceptions = list(data.get("expected_misconceptions"))
        else:
            les_ctx = LessonContext(
                stage_title=data.get("stage_title") or data.get("roadmap_title"),
                learning_objectives=data.get("learning_objectives") or [],
                structured_objectives=data.get("structured_objectives"),
                activities=data.get("lesson_activities") or [],
                teacher_instructions=data.get("teacher_instructions") or [],
                lesson_sequence=data.get("teaching_flow") or [],
                expected_misconceptions=data.get("expected_misconceptions") or [],
                status="resolved" if data.get("stage_title") or data.get("learning_objectives") or data.get("structured_objectives") else "unknown"
            )

        ass_ctx = AssessmentContext(
            weak_concepts=data.get("weak_concepts") or [],
            wrong_answer_patterns=data.get("quiz_mistakes") or [],
            mastery=mastery_dict,
            status="resolved" if data.get("quiz_mistakes") or data.get("weak_concepts") else "unknown"
        )

        tm_ctx = TeachMeContext(
            summary=data.get("teachme_summary"),
            confused_concepts=data.get("weak_concepts") or [],
            status="resolved" if data.get("teachme_summary") else "unknown"
        )

        ppt_ctx = PPTContext(
            summary=data.get("ppt_summary"),
            status="resolved" if data.get("ppt_summary") else "unknown"
        )

        src_ctx = SourcesContext(
            evidence=data.get("source_evidence") or [],
            status="resolved" if data.get("source_evidence") else "unknown"
        )

        resolved = ResolvedContext(
            topic=norm_topic or topic_raw,
            raw_topic=raw_topic or topic_raw,
            class_level=class_disp,
            grade=grade_num,
            subject=subject_val,
            curriculum=board,
            language=lang_val,
            teaching_method="unknown",
            mastery_state=mastery_dict,
            misconceptions=data.get("student_misconceptions") or [],
            weak_concepts=data.get("weak_concepts") or []
        )

        prov = ProvenanceContext(
            field_sources={},
            confidence=1.0,
            conflicts=[]
        )

        comp = ContextCompleteness(
            score=100.0,
            missing_fields=[],
            warnings=[]
        )

        return {
            "context_schema_version": "1.0",
            "request": req_ctx,
            "explicit_input": exp_ctx,
            "student": stu_ctx,
            "curriculum": curr_ctx,
            "lesson": les_ctx,
            "assessment": ass_ctx,
            "teach_me": tm_ctx,
            "ppt": ppt_ctx,
            "sources": src_ctx,
            "resolved_context": resolved,
            "provenance": prov,
            "completeness": comp,
            "topic_descriptor": data.get("topic_descriptor") or TopicDescriptor.create(
                topic=norm_topic or topic_raw,
                subject=subject_val,
                class_level=class_disp,
                grade=grade_num,
                board=board,
                curriculum=board,
                source_scope="lesson_plan" if data.get("learning_objectives") or (les_ctx and les_ctx.learning_objectives) else "general"
            ),
            "requested_depth": data.get("requested_depth"),
            "requested_format": data.get("requested_format"),
        }


    # Backward compatibility properties for Decision Engine and existing generator routes
    @property
    def descriptor(self) -> TopicDescriptor:
        if self.topic_descriptor:
            return self.topic_descriptor
        return TopicDescriptor.create(
            topic=self.topic,
            subject=self.subject,
            class_level=self.class_level,
            board=self.curriculum,
            source_scope="lesson_plan" if self.lesson.learning_objectives else "general"
        )

    @property
    def topic(self) -> str:
        return self.resolved_context.topic

    @property
    def raw_topic(self) -> str:
        return self.resolved_context.raw_topic

    @property
    def subject(self) -> str:
        return self.resolved_context.subject or "General"

    @property
    def class_level(self) -> str:
        return self.resolved_context.class_level or "Class 10"

    @property
    def curriculum_val(self) -> str:
        return self.resolved_context.curriculum or "CBSE"

    @property
    def curriculum(self) -> str:
        # Returns curriculum string if present, else fallback
        return self.resolved_context.curriculum or "CBSE"

    @property
    def language(self) -> str:
        return self.resolved_context.language or "english"

    @property
    def mode(self) -> str:
        return self.request.mode

    @property
    def explicit_user_instructions(self) -> Optional[str]:
        return self.explicit_input.additional_instructions

    @property
    def student_mastery(self) -> Dict[str, float]:
        return self.resolved_context.mastery_state

    @property
    def student_misconceptions(self) -> List[str]:
        return self.resolved_context.misconceptions

    @property
    def weak_concepts(self) -> List[str]:
        return self.resolved_context.weak_concepts

    @property
    def expected_misconceptions(self) -> List[str]:
        return self.lesson.expected_misconceptions

    @property
    def learning_objectives(self) -> List[str]:
        return self.lesson.learning_objectives

    @property
    def lesson_activities(self) -> List[str]:
        return self.lesson.activities

    @property
    def teacher_instructions(self) -> List[str]:
        return self.lesson.teacher_instructions

    @property
    def teaching_flow(self) -> List[str]:
        return self.lesson.lesson_sequence

    @property
    def quiz_mistakes(self) -> List[Dict[str, Any]]:
        return self.assessment.wrong_answer_patterns

    @property
    def ppt_summary(self) -> Optional[str]:
        return self.ppt.summary

    @property
    def teachme_summary(self) -> Optional[str]:
        return self.teach_me.summary

    @property
    def source_evidence(self) -> List[Dict[str, Any]]:
        return self.sources.evidence

    @property
    def roadmap_title(self) -> Optional[str]:
        return self.lesson.stage_title

    @property
    def stage_title(self) -> Optional[str]:
        return self.lesson.stage_title

    @property
    def lineage_ids(self) -> Dict[str, Optional[str]]:
        return {
            "roadmap_id": self.lesson.roadmap_id,
            "stage_id": self.lesson.stage_id,
            "quiz_id": self.assessment.quiz_id,
            "teach_session_id": self.teach_me.session_id,
            "deck_id": self.ppt.deck_id,
            "student_id": self.student.student_id,
        }


class ContextSnapshot(BaseModel):
    """Immutable context snapshot preserving context state at note request time."""
    snapshot_id: str
    created_at: str
    context_version: str = "1.0"
    user_id: str
    context: CanonicalNotesContext


# Wire Request & Response contracts for Context Engine API
class AnalyzeContextRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    topic: str
    class_level: Optional[str] = None
    subject: Optional[str] = None
    curriculum: Optional[str] = None
    language: Optional[str] = None
    additional_instructions: Optional[str] = None
    mode: str = "topic"
    
    # ID pointers to existing entities
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Direct payload support for unit tests and direct module passing
    student: Optional[Dict[str, Any]] = None
    curriculum_data: Optional[Dict[str, Any]] = Field(default=None, alias="curriculumData")
    lesson: Optional[Dict[str, Any]] = None
    assessment: Optional[Dict[str, Any]] = None
    teach_me: Optional[Dict[str, Any]] = Field(default=None, alias="teachMe")
    ppt: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, Any]] = None


class AnalyzeContextResponse(BaseModel):
    success: bool = True
    context: CanonicalNotesContext
    snapshot_id: str
