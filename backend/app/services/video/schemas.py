"""
LearnByGenie AI Video Teacher V2 — Canonical Schemas & Universal Contracts
========================================================================
Defines strict Pydantic contracts for:
1. Domain Intelligence & Universal Archetypes
2. Dynamic Concept DAGs & Misconception Profiling
3. Pedagogical Teaching Structure (10-Stage Story)
4. Reusable Visual & Animation Specs
5. Video Knowledge Package (Context Anchor)
6. Timestamp Context Resolution, Confusion Diagnosis, Prerequisite Gap Detection
7. Explanation Strategy Escalation & Quick Mastery Checks
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import time


# ─────────────────────────────────────────────────────────────────────────────
# 1. DOMAINS & PEDAGOGICAL CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

class DomainCategory(str, Enum):
    COMPUTER_SCIENCE = "computer_science"
    MATHEMATICS      = "mathematics"
    PHYSICS          = "physics"
    CHEMISTRY        = "chemistry"
    BIOLOGY          = "biology"
    HISTORY          = "history"
    GEOGRAPHY        = "geography"
    ECONOMICS        = "economics"
    BUSINESS         = "business"
    ENGINEERING      = "engineering"
    LANGUAGE         = "language"
    SOCIAL_SCIENCE   = "social_science"
    GENERAL_KNOWLEDGE = "general_knowledge"
    OTHER            = "other"


class TeachingStoryStage(str, Enum):
    HOOK                     = "hook"
    INTUITION                = "intuition"
    PREREQUISITE_CONNECTION  = "prerequisite_connection"
    CORE_CONCEPT             = "core_concept"
    VISUAL_MECHANISM         = "visual_mechanism"
    WORKED_EXAMPLE           = "worked_example"
    COMMON_MISTAKE           = "common_mistake"
    SECOND_EXAMPLE           = "second_example"
    QUICK_CHECK              = "quick_check"
    SUMMARY                  = "summary"


class VisualStrategyArchetype(str, Enum):
    PROCESS_FLOW            = "process_flow"
    TIMELINE                = "timeline"
    CAUSE_EFFECT            = "cause_effect"
    COMPARISON              = "comparison"
    HIERARCHY               = "hierarchy"
    CONCEPT_MAP             = "concept_map"
    DATA_STRUCTURE          = "data_structure"
    ALGORITHM_TRACE         = "algorithm_trace"
    CODE_EXECUTION          = "code_execution"
    MATHEMATICAL_DERIVATION = "mathematical_derivation"
    GRAPH_PLOT              = "graph_plot"
    FORMULA_VISUALIZATION   = "formula_visualization"
    SCIENTIFIC_PROCESS      = "scientific_process"
    ANATOMICAL_DIAGRAM      = "anatomical_diagram"
    MAP                     = "map"
    TABLE                   = "table"
    CHART                   = "chart"
    NETWORK                 = "network"
    SYSTEM_ARCHITECTURE     = "system_architecture"
    STEP_SEQUENCE           = "step_sequence"
    REAL_WORLD_EXAMPLE      = "real_world_example"
    TEXTUAL_EXPLAINER       = "textual_explainer"
    GENERIC_DIAGRAM         = "generic_diagram"


class VisualAssetType(str, Enum):
    NONE            = "none"
    PYTHON_GRAPHICS = "python_graphics"
    STOCK_VIDEO     = "stock_video"
    STOCK_IMAGE     = "stock_image"
    AI_IMAGE        = "ai_image"
    AI_VIDEO        = "ai_video"
    MIXED           = "mixed"


class VideoStyle(str, Enum):
    ACADEMIC        = "academic"
    MODERN_EXPLAINER = "modern_explainer"
    TECHNICAL       = "technical"
    VISUAL_LEARNING = "visual_learning"
    CINEMATIC       = "cinematic"


class VideoQuality(str, Enum):
    QUICK    = "quick"
    STANDARD = "standard"
    PREMIUM  = "premium"


class AIIntensity(str, Enum):
    MINIMAL  = "minimal"
    BALANCED = "balanced"
    MAXIMUM  = "maximum"


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT  = "9:16"


class JobState(str, Enum):
    QUEUED           = "queued"
    ANALYZING_TOPIC  = "analyzing_topic"
    BUILDING_CONCEPT_GRAPH = "building_concept_graph"
    PLANNING         = "planning"
    STORYBOARDING    = "storyboarding"
    GENERATING_VISUALS = "generating_visuals"
    ASSET_RESOLUTION = "asset_resolution"
    GENERATING       = "generating"
    AUDIO            = "audio"
    COMPOSITING      = "compositing"
    QA               = "qa"
    READY            = "ready"
    COMPLETED        = "completed"
    FAILED           = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# 2. INTENT & CONCEPT GRAPH SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class LearningIntent(BaseModel):
    raw_prompt: str
    topic: str
    domain: DomainCategory = DomainCategory.GENERAL_KNOWLEDGE
    learner_level: str = "B.Tech"          # Class 9-12, B.Tech, Undergrad, etc.
    language: str = "hinglish"             # "english", "hindi", "hinglish"
    duration_seconds: int = 300            # Total seconds requested
    explanation_depth: str = "normal"      # "overview", "normal", "deep_dive"
    source_type: str = "topic"             # "topic", "pdf", "ppt", "notes", "youtube"
    source_ids: List[str] = Field(default_factory=list)
    custom_context: Optional[str] = None


class ConceptNode(BaseModel):
    id: str
    name: str
    summary: str
    prerequisites: List[str] = Field(default_factory=list)
    likely_misconceptions: List[str] = Field(default_factory=list)
    recommended_visual_archetype: VisualStrategyArchetype = VisualStrategyArchetype.GENERIC_DIAGRAM
    worked_example_hint: Optional[str] = None
    difficulty: str = "intermediate"
    key_terms: List[str] = Field(default_factory=list)


class ConceptGraph(BaseModel):
    topic: str
    domain: DomainCategory
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    nodes: List[ConceptNode] = Field(default_factory=list)
    recommended_sequence: List[str] = Field(default_factory=list)
    major_misconceptions: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 3. REUSABLE VISUAL SPECIFICATION & ANIMATION CONTRACTS
# ─────────────────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    time_label: str
    title: str
    description: str = ""
    impact: str = ""


class ComparisonColumn(BaseModel):
    header: str
    items: List[str] = Field(default_factory=list)
    color_accent: Optional[str] = None


class EquationStep(BaseModel):
    equation: str
    explanation: str = ""
    highlight_terms: List[str] = Field(default_factory=list)
    transformation: Optional[str] = None


class PlotSeries(BaseModel):
    x_values: List[float] = Field(default_factory=list)
    y_values: List[float] = Field(default_factory=list)
    label: str = ""
    color: Optional[str] = None


class PlotData(BaseModel):
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    series: List[PlotSeries] = Field(default_factory=list)
    curve_type: str = "linear"


class AnimationStep(BaseModel):
    step_index: int
    action: str = "reveal"                 # "highlight", "move", "connect", "disconnect", "reveal", "transform"
    target_id: str = ""
    description: str = ""
    duration_ratio: float = 0.25


class AnimationSpec(BaseModel):
    fps: int = 30
    total_frames: int = 150
    steps: List[AnimationStep] = Field(default_factory=list)
    active_focal_id: Optional[str] = None


class SourceRef(BaseModel):
    source_type: str = "topic"
    document_id: Optional[str] = None
    title: Optional[str] = None
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_start: Optional[int] = None
    timestamp_end: Optional[int] = None
    snippet: Optional[str] = None

    def get_badge(self) -> str:
        if self.page_number:
            return f"Page {self.page_number}"
        if self.slide_number:
            return f"Slide {self.slide_number}"
        if self.timestamp_start is not None:
            m1, s1 = divmod(self.timestamp_start, 60)
            return f"{m1:02d}:{s1:02d}"
        return "Source"


class AssetSpec(BaseModel):
    asset_id: str
    provider: str
    media_url: Optional[str] = None
    creator: str = "LearnByGenie"
    license: str = "Educational Fair Use / CC0"
    attribution_text: str = ""
    duration_seconds: float = 0.0
    width: int = 1280
    height: int = 720


class AudioSpec(BaseModel):
    voice: str = "hi-IN-MadhurNeural"
    language: str = "hinglish"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    music_track: Optional[str] = None
    ducking_db: float = -14.0
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0


class VisualSpec(BaseModel):
    visual_archetype: VisualStrategyArchetype = VisualStrategyArchetype.GENERIC_DIAGRAM
    diagram_type: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    formula: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    edges: List[List[str]] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    comparisons: List[ComparisonColumn] = Field(default_factory=list)
    equations: List[EquationStep] = Field(default_factory=list)
    plot_data: Optional[PlotData] = None
    table_headers: List[str] = Field(default_factory=list)
    table_rows: List[List[str]] = Field(default_factory=list)
    code_snippet: Optional[str] = None
    code_language: str = "python"
    focal_highlight: Optional[str] = None
    stock_keywords: List[str] = Field(default_factory=list)
    ai_prompt: Optional[str] = None
    theme: str = "academic"
    asset: Optional[AssetSpec] = None


class SceneSpec(BaseModel):
    scene_id: str
    order: int
    concept_id: str = ""
    concept_name: str = ""
    teaching_goal: str = ""
    purpose: Union[TeachingStoryStage, str] = TeachingStoryStage.CORE_CONCEPT
    duration: int = 15
    actual_duration: float = 0.0
    narration: str
    visual_strategy: VisualStrategyArchetype = VisualStrategyArchetype.GENERIC_DIAGRAM
    visual_type: VisualAssetType = VisualAssetType.PYTHON_GRAPHICS
    visual_spec: VisualSpec = Field(default_factory=VisualSpec)
    animation_spec: Optional[AnimationSpec] = None
    audio_spec: AudioSpec = Field(default_factory=AudioSpec)
    caption: str = ""
    source_refs: List[SourceRef] = Field(default_factory=list)
    prerequisite_refs: List[str] = Field(default_factory=list)
    misconception_tags: List[str] = Field(default_factory=list)
    worked_example: Optional[str] = None
    difficulty: str = "intermediate"
    ai_video_score: float = 0.10
    scene_hash: Optional[str] = None
    rendered_media_path: Optional[str] = None
    rendered_audio_path: Optional[str] = None
    status: str = "pending"
    generation_attempts: int = 0
    error_message: Optional[str] = None


class Storyboard(BaseModel):
    topic: str
    domain: DomainCategory = DomainCategory.GENERAL_KNOWLEDGE
    style: VideoStyle = VideoStyle.ACADEMIC
    language: str = "english"
    total_duration: int = 300
    scenes: List[SceneSpec] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    summary_notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# 4. VIDEO KNOWLEDGE PACKAGE
# ─────────────────────────────────────────────────────────────────────────────

class SceneKnowledge(BaseModel):
    scene_id: str
    order: int
    timestamp_start: float
    timestamp_end: float
    concept_id: str
    concept_name: str
    teaching_goal: str
    purpose: str
    narration: str
    transcript: str
    visual_strategy: str
    visual_state: Dict[str, Any] = Field(default_factory=dict)
    worked_example: Optional[str] = None
    misconception_tags: List[str] = Field(default_factory=list)
    prerequisite_refs: List[str] = Field(default_factory=list)
    source_refs: List[SourceRef] = Field(default_factory=list)


class VideoKnowledgePackage(BaseModel):
    video_id: str
    topic: str
    domain: str
    learner_level: str
    language: str
    total_duration_seconds: float
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    concept_graph: Dict[str, Any] = Field(default_factory=dict)
    scenes: List[SceneKnowledge] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: str(time.time()))


# ─────────────────────────────────────────────────────────────────────────────
# 5. ASK YOUR DOUBT, CONFUSION DIAGNOSIS & EXPLANATION STRATEGY
# ─────────────────────────────────────────────────────────────────────────────

class ConfusionType(str, Enum):
    DEFINITION_CONFUSION    = "DEFINITION_CONFUSION"
    PREREQUISITE_GAP        = "PREREQUISITE_GAP"
    RELATIONSHIP_CONFUSION  = "RELATIONSHIP_CONFUSION"
    PROCESS_CONFUSION       = "PROCESS_CONFUSION"
    VISUAL_CONFUSION        = "VISUAL_CONFUSION"
    FORMULA_CONFUSION       = "FORMULA_CONFUSION"
    EXAMPLE_CONFUSION       = "EXAMPLE_CONFUSION"
    TERMINOLOGY_CONFUSION   = "TERMINOLOGY_CONFUSION"
    MEMORY_CONFUSION        = "MEMORY_CONFUSION"
    APPLICATION_CONFUSION   = "APPLICATION_CONFUSION"


class ExplanationStrategy(str, Enum):
    SIMPLE               = "SIMPLE"
    VISUAL               = "VISUAL"
    REAL_WORLD_ANALOGY   = "REAL_WORLD_ANALOGY"
    STEP_BY_STEP         = "STEP_BY_STEP"
    PREREQUISITE_REPAIR  = "PREREQUISITE_REPAIR"
    FROM_BASICS          = "FROM_BASICS"
    SECOND_EXAMPLE       = "SECOND_EXAMPLE"
    COUNTEREXAMPLE       = "COUNTEREXAMPLE"
    EXAM_STYLE           = "EXAM_STYLE"
    CODE_TRACE           = "CODE_TRACE"
    FORMULA_BREAKDOWN    = "FORMULA_BREAKDOWN"


class PrerequisiteGapResult(BaseModel):
    has_gap: bool = False
    missing_prerequisite: Optional[str] = None
    repair_concept: Optional[str] = None
    brief_remedy: Optional[str] = None


class ConfusionDiagnosis(BaseModel):
    confusion_type: ConfusionType
    confidence: float = 0.90
    detected_gap: Optional[str] = None
    recommended_strategy: ExplanationStrategy = ExplanationStrategy.SIMPLE
    reasoning: str = ""


class MasteryCheck(BaseModel):
    question: str
    options: List[str]
    correct_answer_index: int
    explanation: str
    target_concept_id: str

    @property
    def correct_index(self) -> int:
        return self.correct_answer_index


class DoubtContext(BaseModel):
    video_id: str
    timestamp: float
    current_scene_id: str
    current_concept: str
    previous_concept: Optional[str] = None
    next_concept: Optional[str] = None
    relevant_narration: str = ""
    visual_state: Dict[str, Any] = Field(default_factory=dict)
    misconception_tags: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    examples_shown: List[str] = Field(default_factory=list)
    learner_level: str = "B.Tech"
    language: str = "hinglish"
    student_question: str = ""

    @property
    def concept_name(self) -> str:
        return self.current_concept

    @property
    def concept_id(self) -> str:
        return self.current_concept or self.current_scene_id


class DoubtAnswer(BaseModel):
    context_scene_id: str
    context_concept_name: str
    timestamp: float
    confusion_type: ConfusionType
    strategy_used: ExplanationStrategy
    explanation_markdown: str
    mini_diagram: Optional[str] = None
    step_trace: Optional[List[str]] = None
    code_trace: Optional[str] = None
    prerequisite_repaired: Optional[str] = None
    mastery_check: Optional[MasteryCheck] = None
    confidence: float = 0.95
    grounded_scene_ids: List[str] = Field(default_factory=list)

    @property
    def answer_text(self) -> str:
        return self.explanation_markdown

    @property
    def text(self) -> str:
        return self.explanation_markdown

    @property
    def quick_mastery_check(self) -> Optional[MasteryCheck]:
        return self.mastery_check


class DoubtTutorResponse(BaseModel):
    """Strict structured LLM Tutor Response validating pedagogical explanation output."""
    answer: str
    strategy_used: ExplanationStrategy
    concept_id: str
    prerequisite_repair_used: Optional[str] = None
    mini_diagram: Optional[str] = None
    steps: Optional[List[str]] = None
    example: Optional[str] = None
    exam_answer: Optional[str] = None
    mastery_check: Optional[MasteryCheck] = None
    confidence: float = 0.95
    grounded_scene_ids: List[str] = Field(default_factory=list)

    def to_doubt_answer(self, scene_id: str, concept_name: str, timestamp: float, confusion_type: ConfusionType) -> DoubtAnswer:
        return DoubtAnswer(
            context_scene_id=scene_id,
            context_concept_name=concept_name,
            timestamp=timestamp,
            confusion_type=confusion_type,
            strategy_used=self.strategy_used,
            explanation_markdown=self.answer,
            mini_diagram=self.mini_diagram,
            step_trace=self.steps,
            code_trace=self.example if self.strategy_used == ExplanationStrategy.CODE_TRACE else None,
            prerequisite_repaired=self.prerequisite_repair_used,
            mastery_check=self.mastery_check,
            confidence=self.confidence,
            grounded_scene_ids=self.grounded_scene_ids or [scene_id]
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. CONFIG, METRICS & RUNTIME PROJECT
# ─────────────────────────────────────────────────────────────────────────────

class VisualBudget(BaseModel):
    max_ai_video_seconds: int = 24
    max_ai_image_count: int = 4
    max_stock_requests: int = 6
    max_tts_characters: int = 8000
    max_scene_regenerations: int = 5
    quality_level: VideoQuality = VideoQuality.STANDARD


class CostBudget(BaseModel):
    max_cost_usd: float = 1.00
    estimated_cost_usd: float = 0.0


class UsageReport(BaseModel):
    total_duration_sec: int = 0
    ai_video_seconds: int = 0
    ai_image_count: int = 0
    stock_media_count: int = 0
    python_graphics_count: int = 0
    llm_tokens: int = 0
    llm_calls: int = 0
    tts_characters: int = 0
    render_time_sec: float = 0.0
    cache_hits: int = 0
    grounding_score: float = 1.0
    cost_per_minute_usd: float = 0.0
    ai_generation_ratio: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 7. V2.1 HARDENING: MASTERY, QUALITY GATES, REPAIR, GROUNDING & TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────

class LearnerMasteryState(str, Enum):
    NOT_SEEN             = "NOT_SEEN"
    INTRODUCED           = "INTRODUCED"
    PARTIALLY_UNDERSTOOD = "PARTIALLY_UNDERSTOOD"
    CONFUSED             = "CONFUSED"
    PREREQUISITE_GAP     = "PREREQUISITE_GAP"
    UNDERSTOOD           = "UNDERSTOOD"
    MASTERED             = "MASTERED"


class ConceptMasteryRecord(BaseModel):
    concept_id: str
    concept_name: str
    state: LearnerMasteryState = LearnerMasteryState.NOT_SEEN
    watch_progress_pct: float = 0.0
    confusion_count: int = 0
    prerequisite_gap_count: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    strategies_attempted: List[str] = Field(default_factory=list)
    last_strategy: Optional[str] = None
    last_interaction: float = Field(default_factory=time.time)
    evidence_for_mastery: List[str] = Field(default_factory=list)


class LearnerMasteryProfile(BaseModel):
    user_id: str
    lesson_id: str
    concepts: Dict[str, ConceptMasteryRecord] = Field(default_factory=dict)
    last_active_timestamp: float = 0.0
    last_sync_timestamp: float = Field(default_factory=time.time)


QUALITY_DIMENSION_GATES: Dict[str, float] = {
    "concept_coverage": 15.0,        # max 20
    "prerequisite_order": 10.0,      # max 15
    "visual_relevance": 10.0,        # max 15
    "example_quality": 9.0,          # max 15
    "misconception_handling": 6.0,   # max 10
    "language_naturalness": 7.0,     # max 10
    "narration_visual_sync": 7.0,    # max 10
    "doubt_context_readiness": 4.0,  # max 5
    "total_score_minimum": 80.0,     # max 100
}


class TeachingQualityScore(BaseModel):
    concept_coverage: float = 0.0        # max 20
    prerequisite_order: float = 0.0      # max 15
    visual_relevance: float = 0.0        # max 15
    example_quality: float = 0.0         # max 15
    misconception_handling: float = 0.0  # max 10
    language_naturalness: float = 0.0    # max 10
    narration_visual_sync: float = 0.0   # max 10
    doubt_context_readiness: float = 0.0 # max 5
    total_score: float = 0.0             # max 100
    passed_gates: bool = False
    dimension_gate_results: Dict[str, bool] = Field(default_factory=dict)
    failed_dimensions: List[str] = Field(default_factory=list)
    repair_recommendations: List[str] = Field(default_factory=list)
    is_hybrid: bool = True
    semantic_feedback: Optional[str] = None
    semantic_flaws: List[str] = Field(default_factory=list)
    semantic_dimension_scores: Dict[str, float] = Field(default_factory=dict)
    evaluated_at: float = Field(default_factory=time.time)


class RepairLog(BaseModel):
    repair_timestamp: float = Field(default_factory=time.time)
    pre_repair_score: float
    post_repair_score: float
    score_delta: float
    repaired_dimensions: List[str] = Field(default_factory=list)
    repair_actions: List[str] = Field(default_factory=list)
    kept_repaired: bool = True
    warning: Optional[str] = None


class SceneGroundingResult(BaseModel):
    scene_id: str
    total_claims: int = 0
    supported_claims: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    source_refs: List[SourceRef] = Field(default_factory=list)
    grounding_ratio: float = 1.0
    warnings: List[str] = Field(default_factory=list)


class SourceGroundingReport(BaseModel):
    source_id: str = ""
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: List[str] = Field(default_factory=list)
    source_coverage: float = 1.0
    grounding_score: float = 1.0
    scene_results: List[SceneGroundingResult] = Field(default_factory=list)
    affected_scenes: List[str] = Field(default_factory=list)
    has_ungrounded_claims: bool = False


class VideoTelemetry(BaseModel):
    intent_parse_ms: float = 0.0
    domain_detection_ms: float = 0.0
    curriculum_ms: float = 0.0
    storyboard_ms: float = 0.0
    visual_render_ms: float = 0.0
    tts_ms: float = 0.0
    composition_ms: float = 0.0
    qa_ms: float = 0.0
    repair_ms: float = 0.0
    total_generation_ms: float = 0.0
    ask_doubt_latency_ms: float = 0.0


class VideoMetrics(UsageReport):
    telemetry: VideoTelemetry = Field(default_factory=VideoTelemetry)
    quality_score: Optional[TeachingQualityScore] = None
    repair_log: Optional[RepairLog] = None
    source_grounding: Optional[SourceGroundingReport] = None


class VideoConfig(BaseModel):
    topic: str
    domain: DomainCategory = DomainCategory.GENERAL_KNOWLEDGE
    source_type: str = "topic"
    source_ids: List[str] = Field(default_factory=list)
    youtube_url: Optional[str] = None
    lesson_session_id: Optional[str] = None
    custom_context: Optional[str] = None
    
    duration: int = 300
    quality: VideoQuality = VideoQuality.STANDARD
    ai_intensity: AIIntensity = AIIntensity.MINIMAL
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    language: str = "hinglish"
    style: VideoStyle = VideoStyle.ACADEMIC
    audience: str = "btech"
    depth: str = "normal"
    
    include_narration: bool = True
    include_captions: bool = True
    include_diagrams: bool = True
    include_stock: bool = False
    include_ai_video: bool = False
    include_music: bool = False
    include_sources: bool = True


class VideoProject(BaseModel):
    id: str
    user_id: str
    topic: str
    config: VideoConfig
    storyboard: Storyboard
    knowledge_package: Optional[VideoKnowledgePackage] = None
    state: JobState = JobState.QUEUED
    status: str = "processing"
    progress: int = 0
    final_video_url: Optional[str] = None
    transcript_url: Optional[str] = None
    captions_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metrics: VideoMetrics = Field(default_factory=VideoMetrics)
    quality_score: Optional[TeachingQualityScore] = None
    repair_log: Optional[RepairLog] = None
    telemetry: VideoTelemetry = Field(default_factory=VideoTelemetry)
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# 13. V2.2 PRODUCTION VALIDATION & LEARNER PILOT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class FailureCode(str, Enum):
    LLM_TIMEOUT                  = "LLM_TIMEOUT"
    LLM_INVALID_OUTPUT           = "LLM_INVALID_OUTPUT"
    CURRICULUM_GENERATION_FAILED = "CURRICULUM_GENERATION_FAILED"
    TTS_PRIMARY_FAILED           = "TTS_PRIMARY_FAILED"
    TTS_ALL_PROVIDERS_FAILED     = "TTS_ALL_PROVIDERS_FAILED"
    VISUALIZER_FAILED            = "VISUALIZER_FAILED"
    FFMPEG_FAILED                = "FFMPEG_FAILED"
    MEDIA_CORRUPT                = "MEDIA_CORRUPT"
    STORAGE_UPLOAD_FAILED        = "STORAGE_UPLOAD_FAILED"
    DATABASE_WRITE_FAILED        = "DATABASE_WRITE_FAILED"
    SOURCE_RETRIEVAL_FAILED      = "SOURCE_RETRIEVAL_FAILED"
    QUALITY_GATE_FAILED          = "QUALITY_GATE_FAILED"
    UNKNOWN_INTERNAL_ERROR       = "UNKNOWN_INTERNAL_ERROR"


class FailureDetail(BaseModel):
    code: FailureCode
    severity: str = "ERROR"              # WARNING, ERROR, CRITICAL
    recoverable: bool = False
    retryable: bool = False
    safe_user_message: str              # Student-facing only (Decision #13)
    internal_diagnostic: str            # Hidden from students, internal logs only
    occurred_at: float = Field(default_factory=time.time)


class StorageArtifactClass(str, Enum):
    EPHEMERAL  = "EPHEMERAL"    # raw animation frames, temporary audio, concat manifests, intermediate mux files
    CACHEABLE  = "CACHEABLE"    # scene clips, narration, scene visual artifacts for regeneration, scene hashes
    PERSISTENT = "PERSISTENT"   # final video, captions, storyboard, VideoKnowledgePackage, source refs, quality report


class StoredArtifact(BaseModel):
    artifact_id: str
    file_path: str
    storage_class: StorageArtifactClass
    ttl_seconds: Optional[int] = None   # None for PERSISTENT; e.g. 86400 (24h) for CACHEABLE; 0 for EPHEMERAL
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReferentialAnchorType(str, Enum):
    SCENE                       = "scene"
    CONCEPT                     = "concept"
    VISUAL_ELEMENT              = "visual_element"
    WORKED_EXAMPLE              = "worked_example"
    EQUATION_STEP               = "equation_step"
    TIMELINE_EVENT              = "timeline_event"
    PREVIOUS_TUTOR_EXPLANATION  = "previous_tutor_explanation"


class ReferentialAnchor(BaseModel):
    anchor_id: str
    anchor_type: ReferentialAnchorType
    label: str
    aliases: List[str] = Field(default_factory=list)
    timestamp_sec: float = 0.0
    scene_id: Optional[str] = None
    content_snippet: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DoubtTurn(BaseModel):
    turn_id: str
    user_question: str
    timestamp_sec: float
    tutor_explanation: str
    strategy_used: str
    resolved: bool = True
    referential_mentions: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class DoubtSessionState(BaseModel):
    doubt_session_id: str
    lesson_id: str
    current_focus_concept: str = ""
    unresolved_confusion: Optional[str] = None
    previous_confusion: Optional[str] = None
    timestamp_history: List[float] = Field(default_factory=list)
    concept_history: List[str] = Field(default_factory=list)
    strategies_attempted: List[str] = Field(default_factory=list)
    mastery_state: LearnerMasteryState = LearnerMasteryState.NOT_SEEN
    recent_turns: List[DoubtTurn] = Field(default_factory=list)  # Bounded to last 3 turns (Decision #1 & #8)
    compressed_summary: str = ""
    referential_anchors: List[ReferentialAnchor] = Field(default_factory=list)
    last_updated: float = Field(default_factory=time.time)


class TransferQuestionPair(BaseModel):
    """Pre/Post question pair testing the same capability with equivalent difficulty (Decision #6)."""
    concept_id: str
    assessed_skill: str
    pre_question: str
    post_question: str
    difficulty: str = "MEDIUM"          # EASY, MEDIUM, HARD
    expected_reasoning_steps: List[str] = Field(default_factory=list)
    scoring_rubric: Dict[str, Any] = Field(default_factory=dict)
    equivalence_score: float = 1.0       # e.g., 0.95 - 1.0 (validated transfer equivalence)


class LearnerPilotSession(BaseModel):
    """Tracks real learner pilot sessions with strict provenance, privacy, and gain calculation (Decisions #5, #6, #7, #10, #14, #15, #16)."""
    session_id: str
    pilot_participant_id: str           # Opaque random ID or server-side HMAC pseudonym (Decision #7)
    provenance: str = "REAL_LEARNER_EVALUATION" # STRICT: REAL_LEARNER_EVALUATION vs INTERNAL_MANUAL_REVIEW (Decision #16)
    lesson_id: str
    topic: str
    
    # Normalized Assessment Scores [0.0, 1.0] (Decision #5)
    pre_score: float = 0.0              # normalized to [0.0, 1.0]
    post_score: float = 0.0             # normalized to [0.0, 1.0]
    delayed_score: Optional[float] = None # None/pending if delayed recall hasn't happened; NEVER fabricate (Decision #14)
    raw_gain: float = 0.0               # post_score - pre_score
    normalized_gain: Optional[float] = None # (post - pre)/(1 - pre) if pre < 1.0 else None. Handles negative gain, no div by zero!
    
    # Interactive Tutor Outcomes
    doubts_count: int = 0
    doubts_resolved: int = 0
    unresolved_doubts: int = 0
    first_explanation_resolutions: int = 0
    strategy_switches: int = 0
    prerequisite_repairs: int = 0
    
    # Latency / Engagement
    time_to_understanding_sec: float = 0.0
    lesson_completion_time_sec: float = 0.0
    learner_experience_rating: Optional[float] = None # 1-5 stars
    external_help_needed: bool = False  # Decision #10: Learner reported external help needed
    
    mastery_evidence: List[str] = Field(default_factory=list)
    recorded_at: float = Field(default_factory=time.time)

    @classmethod
    def compute_gains(cls, pre_score: float, post_score: float) -> tuple[float, Optional[float]]:
        """Calculates raw gain and normalized gain adhering to Decision #5."""
        pre = max(0.0, min(1.0, float(pre_score)))
        post = max(0.0, min(1.0, float(post_score)))
        raw = round(post - pre, 4)
        if pre < 1.0:
            norm = round((post - pre) / (1.0 - pre), 4)
        else:
            norm = None
        return raw, norm


class ProductionReadinessReport(BaseModel):
    """Production readiness metrics with sample metadata and time windows (Decisions #9, #10, #11)."""
    sample_count: int = 0
    measurement_window: str = "24h"     # "24h", "7d", "30d"
    generated_at: float = Field(default_factory=time.time)
    
    # Core tutor rates
    first_explanation_resolution_rate: float = 0.0
    adaptive_resolution_rate: float = 0.0
    average_explanations_per_resolved_doubt: float = 0.0
    prerequisite_repair_rate: float = 0.0
    unresolved_doubt_rate: float = 0.0
    external_help_escape_rate: float = 0.0 # learners_needing_external_help / pilot_learners
    
    # Latency percentiles
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    failure_rate: float = 0.0
    
    # Production Gate Compliance
    is_production_ready: bool = False
    readiness_notes: List[str] = Field(default_factory=list)

