"""
Teach Me Engine — Core Schemas & Diagnostic Contracts
======================================================
Strict Pydantic contracts for Lesson Plans, Concepts, Misconceptions,
Learning State, Diagnostic Checkpoints, and Multi-Source Evidence Grounding.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from ..knowledge.sources import SourceType, EvidenceItem


class LearningMode(str, Enum):
    INTERACTIVE_TEACHER = "interactive_teacher"
    LEARN_FROM_SOURCE   = "learn_from_source"
    SOCRATIC_TEACHER    = "socratic_teacher"
    EXAM_COACH          = "exam_coach"
    REVISION            = "revision"
    DEEP_DIVE           = "deep_dive"


class LearningLevel(str, Enum):
    SCHOOL    = "school"
    BEGINNER  = "beginner"
    COLLEGE   = "college"
    BTECH     = "btech"
    ADVANCED  = "advanced"
    PROFESSOR = "professor"


class LearningDepth(str, Enum):
    QUICK  = "quick"
    NORMAL = "normal"
    DEEP   = "deep"
    EXAM   = "exam"


class ExplanationStrategy(str, Enum):
    FORMAL_EXPLANATION       = "formal_explanation"
    REAL_WORLD_ANALOGY       = "real_world_analogy"
    CONCRETE_CASE_EXAMPLE    = "concrete_case_example"
    STEP_BY_STEP_BREAKDOWN   = "step_by_step_breakdown"
    VISUAL_MENTAL_MODEL      = "visual_mental_model"
    PREREQUISITE_SCAFFOLDING = "prerequisite_scaffolding"
    EXPLAIN_IT_BACK          = "explain_it_back"


class CheckpointType(str, Enum):
    RECALL              = "recall"
    CONCEPTUAL          = "conceptual"
    WHY                 = "why"
    HOW                 = "how"
    PREDICTION          = "prediction"
    APPLICATION         = "application"
    NUMERICAL           = "numerical"
    OWN_WORDS           = "own_words"
    MISCONCEPTION_CHECK = "misconception_check"
    EXAM_STYLE          = "exam_style"


class ConceptStatus(str, Enum):
    PENDING  = "pending"
    LEARNING = "learning"
    MASTERED = "mastered"


class MisconceptionItem(BaseModel):
    id: str = ""
    concept_id: str
    misconception: str
    severity: str = "medium"  # "low" | "medium" | "high"
    first_detected: str = ""
    last_detected: str = ""
    resolved: bool = False
    resolution_strategy: Optional[str] = None


class ConceptMasteryProfile(BaseModel):
    concept_id: str
    mastery_score: float = 0.0      # 0.0 to 1.0
    confidence: float = 0.0         # 0.0 to 1.0 (observation & consistency weighted)
    evidence_count: int = 0         # Total assessment attempts on this concept
    recent_scores: List[float] = Field(default_factory=list)
    difficulty_level: str = "medium"
    active_misconceptions: List[str] = Field(default_factory=list)
    last_assessed_at: Optional[str] = None

    def is_mastered(self) -> bool:
        """Requires high mastery score, sufficient observation confidence, and no unresolved blocking misconceptions."""
        has_blocking_misconception = len(self.active_misconceptions) > 0
        return (
            self.mastery_score >= 0.85 and
            self.confidence >= 0.50 and
            self.evidence_count >= 2 and
            not has_blocking_misconception
        )


class ConceptSpec(BaseModel):
    id: str
    name: str
    order: int
    summary: str = ""
    status: ConceptStatus = ConceptStatus.PENDING
    mastery_score: float = 0.0
    confidence: float = 0.0
    attempts_count: int = 0
    active_strategy: ExplanationStrategy = ExplanationStrategy.FORMAL_EXPLANATION


class CheckpointSpec(BaseModel):
    enabled: bool = True
    type: CheckpointType = CheckpointType.CONCEPTUAL
    question: str
    expected_skill: str = ""
    difficulty: str = "medium"  # "easy" | "medium" | "hard"
    hint: Optional[str] = None
    idempotency_key: Optional[str] = None


class EvaluationResult(BaseModel):
    correctness: str = "correct"  # "correct" | "partial" | "incorrect"
    score: float = 1.0            # 0.0 to 1.0
    misconception: Optional[str] = None
    misconception_severity: str = "medium"
    feedback: str = ""
    needs_reteach: bool = False
    mastery_delta: float = 0.0
    confidence_delta: float = 0.0
    suggested_next_action: str = "continue"  # "advance_next_concept" | "reinforce_with_example" | "switch_strategy_reteach" | "simpler_check" | "explain_it_back"


class LessonPlan(BaseModel):
    topic: str
    overview: str = ""
    concepts: List[ConceptSpec] = Field(default_factory=list)
    target_level: LearningLevel = LearningLevel.BTECH
    language: str = "english"
    depth: LearningDepth = LearningDepth.NORMAL
    mode: LearningMode = LearningMode.INTERACTIVE_TEACHER
    source_type: SourceType = SourceType.TOPIC
    source_ids: List[str] = Field(default_factory=list)
    user_id: str = ""


class TurnTelemetry(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    retrieved_chunks: int = 0
    grounding_score: float = 1.0
    model: str = ""
    provider: str = ""
    cache_hit: bool = False


from typing import List, Dict, Any, Optional, Union

# ...

class LearningState(BaseModel):
    session_id: str
    user_id: str = ""
    topic: str
    current_concept_id: str = ""
    covered_concepts: List[str] = Field(default_factory=list)
    mastery: Dict[str, float] = Field(default_factory=dict)
    confidence: Dict[str, float] = Field(default_factory=dict)
    profiles: Dict[str, ConceptMasteryProfile] = Field(default_factory=dict)
    misconceptions: List[Union[MisconceptionItem, str]] = Field(default_factory=list)
    strategies_used: List[str] = Field(default_factory=list)
    active_checkpoint: Optional[CheckpointSpec] = None
    processed_answer_keys: List[str] = Field(default_factory=list)  # Idempotency log
    recent_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # Configuration
    language: str = "english"
    level: LearningLevel = LearningLevel.BTECH
    mode: LearningMode = LearningMode.INTERACTIVE_TEACHER
    depth: LearningDepth = LearningDepth.NORMAL
    source_type: SourceType = SourceType.TOPIC
    source_ids: List[str] = Field(default_factory=list)
    last_telemetry: Optional[TurnTelemetry] = None

    def get_current_profile(self) -> ConceptMasteryProfile:
        if self.current_concept_id not in self.profiles:
            self.profiles[self.current_concept_id] = ConceptMasteryProfile(
                concept_id=self.current_concept_id,
                mastery_score=self.mastery.get(self.current_concept_id, 0.0),
                confidence=self.confidence.get(self.current_concept_id, 0.0),
            )
        return self.profiles[self.current_concept_id]

    def get_current_mastery(self) -> float:
        return self.mastery.get(self.current_concept_id, 0.0)

    def get_current_confidence(self) -> float:
        return self.confidence.get(self.current_concept_id, 0.0)

    def is_concept_mastered(self, concept_id: str) -> bool:
        if concept_id in self.profiles:
            return self.profiles[concept_id].is_mastered()
        return self.mastery.get(concept_id, 0.0) >= 0.85 and self.confidence.get(concept_id, 0.0) >= 0.50
