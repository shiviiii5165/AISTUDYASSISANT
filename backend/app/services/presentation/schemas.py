"""
Presentation Engine — Core Schemas & Contracts
================================================
Strict Pydantic models governing presentation generation, slide specifications,
visual declarations, and design system choices.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SlideType(str, Enum):
    HERO            = "hero"            # Cover / Title
    SECTION_DIVIDER = "section_divider" # Transition divider
    CONCEPT         = "concept"         # Standard concept breakdown
    DEFINITION      = "definition"      # Key definition & terminology
    TWO_COLUMN      = "two_column"      # Side-by-side comparison/details
    IMAGE_INSIGHT   = "image_insight"   # Visual demonstration with insight
    ARCHITECTURE    = "architecture"    # Layered system diagram
    PROCESS_FLOW    = "process_flow"    # Sequential step workflow
    TIMELINE        = "timeline"        # Chronological progression
    COMPARISON      = "comparison"      # Pros vs Cons / A vs B matrix
    CASE_STUDY      = "case_study"      # Real-world Context -> Action -> Result
    KPI_METRICS     = "kpi_metrics"     # Key numbers & statistics
    TABLE           = "table"           # Structured data grid
    CHART           = "chart"           # Quantitative chart
    FORMULA         = "formula"         # Mathematical / chemical formulation
    CODE            = "code"            # Syntax code block
    EXAMPLE         = "example"         # Concrete illustrated example
    COMMON_MISTAKES = "common_mistakes" # Pitfalls & anti-patterns
    SUMMARY         = "summary"         # Key takeaways recap
    QUIZ            = "quiz"            # Knowledge check questions
    QA              = "qa"              # Closing & discussion

class ContentPattern(str, Enum):
    DEFINITION_BOX        = "definition_box"
    CONTRAST_PAIR         = "contrast_pair"
    COMPARISON_TABLE      = "comparison_table"
    NUMBERED_PROCESS      = "numbered_process"
    CASE_STUDY_BLOCK      = "case_study_block"
    ACTIVITY_BANNER       = "activity_banner"
    WORKED_EXAMPLE_TABLE  = "worked_example_table"
    ICON_BADGE_ROW        = "icon_badge_row"
    HUB_AND_SPOKE         = "hub_and_spoke"
    ILLUSTRATED_ICON_GRID = "illustrated_icon_grid"
    PARALLEL_COMPARISON   = "parallel_comparison"
    PLAIN_CONCEPT         = "plain_concept"
    CONCEPT_SPLIT         = "concept_split"
    ANNOTATED_TIERS       = "annotated_tiers"
    EXAMPLE_GRID          = "example_grid"


class DesignSystem(str, Enum):
    ACADEMIC_CLEAN  = "academic"        # University lecture & teaching
    MODERN_MINIMAL  = "minimal"         # Premium Canva/NotebookLM clean
    TECHNICAL_GRID  = "technical"       # CSE, Architecture, Engineering
    EDITORIAL       = "editorial"       # Magazine / Research report
    VISUAL_LEARNING = "visual"          # Diagram-first visual pedagogy


class VisualKind(str, Enum):
    NONE           = "none"
    DIAGRAM        = "diagram"
    ARCHITECTURE   = "architecture"
    FLOW           = "flow"
    TIMELINE       = "timeline"
    COMPARISON     = "comparison"
    HIERARCHY      = "hierarchy"
    IMAGE          = "image"
    TABLE          = "table"
    CODE           = "code"
    CHART_DEFERRED = "chart_deferred"


class DiagramSpec(BaseModel):
    diagram_type: str = "flow"  # "flow" | "architecture" | "timeline" | "comparison" | "hierarchy"
    title: str = ""
    nodes: List[str] = Field(default_factory=list)
    edges: List[List[str]] = Field(default_factory=list)
    layers: List[Dict[str, Any]] = Field(default_factory=list)  # for architecture
    steps: List[Dict[str, Any]] = Field(default_factory=list)   # for process_flow
    milestones: List[Dict[str, Any]] = Field(default_factory=list) # for timeline
    columns: List[Dict[str, Any]] = Field(default_factory=list) # for comparison


class VisualSpec(BaseModel):
    kind: VisualKind = VisualKind.NONE
    asset_required: bool = False
    image_prompt: str = ""
    image_bytes: Optional[bytes] = None
    diagram_spec: Optional[DiagramSpec] = None
    deferred_asset_type: Optional[str] = None  # Preserves Phase 3 asset type for deferred rendering (Phase 3.3)
    compatibility_state: Optional[str] = None  # "deferred_rendering" when adapter bridges to future renderer

    model_config = {"arbitrary_types_allowed": True}


class SlideSourceRef(BaseModel):
    source_type: str = "pdf"
    document_id: str = ""
    page: Optional[int] = None
    slide: Optional[int] = None
    snippet: str = ""


class SlideSelfCheck(BaseModel):
    """Quality self-check returned by the LLM for each generated slide."""
    fits_schema: bool = True
    has_example: bool = False
    has_number: bool = False
    no_filler: bool = True
    no_duplicate_bullets: bool = True
    no_title_repetition: bool = True
    notes_present: bool = True
    teacher_ready: bool = True
    visually_balanced: bool = True
    distinct_from_prior_slides: bool = True


class SlideSpec(BaseModel):
    slide_no: int
    type: SlideType = SlideType.CONCEPT
    title: str
    subtitle: str = ""
    key_message: str = ""
    body_bullets: List[str] = Field(default_factory=list)
    example: str = ""
    speaker_notes: str = ""
    image_query: str = ""
    content_pattern: Optional[ContentPattern] = None
    section_label: Optional[str] = None  # Eyebrow tag: "TYPE 1", "CHAPTER OVERVIEW", etc.
    self_check: Optional[SlideSelfCheck] = None
    visual: Optional[VisualSpec] = None
    source_refs: List[SlideSourceRef] = Field(default_factory=list)

    # Specialized structured data
    layers: List[Dict[str, Any]] = Field(default_factory=list)
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: List[Dict[str, Any]] = Field(default_factory=list)
    quiz_options: List[str] = Field(default_factory=list)
    quiz_answer: str = ""

    # Phase 2 structured content (optional; backward-compatible)
    content: Optional[Any] = None  # SlideContent when Phase 2 active
    quality_scores: Optional[Any] = None  # ContentQualityScores when audited
    fit_risk: Optional[str] = None



class PresentationConfig(BaseModel):
    topic: str
    slide_count: int = 12
    audience: str = "university"
    language: str = "english"
    depth: str = "full"
    design: DesignSystem = DesignSystem.ACADEMIC_CLEAN
    theme: str = "blue_professional"
    source_type: str = "general"  # "general" | "uploaded_material" | "uploaded_material_plus_web"
    source_id: Optional[str] = None
    custom_context: Optional[str] = None
    
    # Feature Toggles
    enable_diagrams: bool = True
    enable_images: bool = True
    enable_speaker_notes: bool = True
    enable_sources: bool = True
    enable_examples: bool = True
    enable_quiz: bool = False

    @field_validator("slide_count")
    @classmethod
    def validate_slide_count(cls, v: int) -> int:
        if v not in [10, 11, 12, 13, 14, 15, 16, 17]:
            raise ValueError(f"slide_count must be between 10 and 17 (got {v})")
        return v


class PresentationSpec(BaseModel):
    title: str
    subtitle: str = ""
    config: PresentationConfig
    key_takeaways: List[str] = Field(default_factory=list)
    slides: List[SlideSpec] = Field(default_factory=list)
    expansion_reason: str = ""

    def validate_exact_count(self) -> bool:
        return self.config.slide_count <= len(self.slides) <= self.config.slide_count + 2


# ═══════════════════════════════════════════════════════════════
# vNEXT Phase 1 — Presentation Intelligence Schemas
# ═══════════════════════════════════════════════════════════════


class SlideIntent(str, Enum):
    """Semantic purpose of a slide — WHY the slide exists.
    Kept separate from VisualTypeHint (WHAT visual) and LayoutFamily (HOW composed)."""
    COVER                = "cover"
    HOOK                 = "hook"
    CONTEXT              = "context"
    WHY_IT_MATTERS       = "why_it_matters"
    AGENDA               = "agenda"
    OBJECTIVES           = "objectives"
    PREREQUISITES        = "prerequisites"
    DEFINITION           = "definition"
    MENTAL_MODEL         = "mental_model"
    CONCEPT_EXPLANATION  = "concept_explanation"
    SYSTEM_OVERVIEW      = "system_overview"
    COMPONENT_BREAKDOWN  = "component_breakdown"
    PROCESS_EXPLANATION  = "process_explanation"
    COMPARISON           = "comparison"
    TRADEOFF             = "tradeoff"
    WORKED_EXAMPLE       = "worked_example"
    CODE_EXAMPLE         = "code_example"
    FORMULA_EXPLANATION  = "formula_explanation"
    CASE_STUDY           = "case_study"
    REAL_WORLD_APPLICATION = "real_world_application"
    DATA_INSIGHT         = "data_insight"
    MISCONCEPTION        = "misconception"
    COMMON_MISTAKES      = "common_mistakes"
    BEST_PRACTICES       = "best_practices"
    DIAGNOSTIC           = "diagnostic"
    KNOWLEDGE_CHECK      = "knowledge_check"
    SUMMARY              = "summary"
    REFERENCES           = "references"
    Q_AND_A              = "q_and_a"


class VisualTypeHint(str, Enum):
    """Best visual representation of the idea — WHAT visual form.
    Independent from SlideIntent and LayoutFamily."""
    NONE                    = "none"
    TYPOGRAPHY_ONLY         = "typography_only"
    ICON_SUPPORT            = "icon_support"
    LAYERED_ARCHITECTURE    = "layered_architecture"
    PIPELINE                = "pipeline"
    PROCESS_FLOW            = "process_flow"
    SEQUENCE_FLOW           = "sequence_flow"
    CYCLE                   = "cycle"
    TIMELINE                = "timeline"
    HIERARCHY               = "hierarchy"
    TAXONOMY                = "taxonomy"
    CAUSE_EFFECT            = "cause_effect"
    COMPARISON_MATRIX       = "comparison_matrix"
    DECISION_TREE           = "decision_tree"
    HUB_AND_SPOKE           = "hub_and_spoke"
    FUNNEL                  = "funnel"
    TABLE                   = "table"
    CHART                   = "chart"
    KPI                     = "kpi"
    CODE_BLOCK              = "code_block"
    FORMULA                 = "formula"
    ANNOTATED_ILLUSTRATION  = "annotated_illustration"
    PHOTOGRAPH              = "photograph"
    MAP                     = "map"
    BEFORE_AFTER            = "before_after"


class LayoutFamily(str, Enum):
    """How slide objects are composed — layout geometry.
    Independent from SlideIntent and VisualTypeHint."""
    HERO                   = "hero"
    CENTERED_FOCAL         = "centered_focal"
    LEFT_TEXT_RIGHT_VISUAL  = "left_text_right_visual"
    LEFT_VISUAL_RIGHT_TEXT  = "left_visual_right_text"
    TWO_COLUMN             = "two_column"
    THREE_CARD             = "three_card"
    FOUR_CARD              = "four_card"
    DIAGRAM_DOMINANT       = "diagram_dominant"
    FULL_WIDTH_PROCESS     = "full_width_process"
    SPLIT_COMPARISON       = "split_comparison"
    MATRIX                 = "matrix"
    TIMELINE_LAYOUT        = "timeline_layout"
    EDITORIAL_ASYMMETRIC   = "editorial_asymmetric"
    DATA_DASHBOARD         = "data_dashboard"
    CODE_PLUS_EXPLANATION  = "code_plus_explanation"
    FORMULA_PLUS_EXAMPLE   = "formula_plus_example"
    CASE_STUDY_LAYOUT      = "case_study_layout"
    SUMMARY_GRID           = "summary_grid"


class ContentDensity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class PresentationGoal(str, Enum):
    TEACH                    = "teach"
    EXPLAIN                  = "explain"
    INTRODUCE                = "introduce"
    DEEP_DIVE                = "deep_dive"
    REVISE                   = "revise"
    EXAM_PREP                = "exam_prep"
    TECHNICAL_BRIEF          = "technical_brief"
    BUSINESS_PITCH           = "business_pitch"
    REPORT                   = "report"
    RESEARCH_PRESENTATION    = "research_presentation"
    PROJECT_PRESENTATION     = "project_presentation"
    TRAINING                 = "training"
    WORKSHOP                 = "workshop"
    CASE_STUDY_PRESENTATION  = "case_study_presentation"
    COMPARISON_PRESENTATION  = "comparison_presentation"
    DATA_STORY               = "data_story"
    PROCESS_EXPLANATION      = "process_explanation"
    PROPOSAL                 = "proposal"


class PresentationMode(str, Enum):
    LECTURE           = "lecture"
    WORKSHOP          = "workshop"
    SELF_STUDY        = "self_study"
    SEMINAR           = "seminar"
    CONFERENCE        = "conference"
    CLASSROOM         = "classroom"
    TRAINING_SESSION  = "training_session"
    BRIEFING          = "briefing"


class TemplateSelectionSource(str, Enum):
    AUTO_RECOMMENDED  = "auto_recommended"
    USER_OVERRIDE     = "user_override"
    DEFAULT_FALLBACK  = "default_fallback"


class StoryGrammarType(str, Enum):
    CONCEPT_TEACHING   = "concept_teaching"
    TECHNICAL_SYSTEM   = "technical_system"
    PROCESS            = "process"
    COMPARISON         = "comparison"
    DATA_STORY         = "data_story"
    HISTORY_EVOLUTION  = "history_evolution"
    RESEARCH           = "research"
    PROBLEM_SOLUTION   = "problem_solution"
    CASE_STUDY         = "case_study"


class TextBudget(BaseModel):
    """Explicit per-component word limits communicated before content generation."""
    title_max_words: int = 10
    subtitle_max_words: int = 22
    body_max_words: int = 70
    card_title_max_words: int = 5
    card_body_max_words: int = 18
    example_max_words: int = 60
    speaker_note_min_words: int = 90
    speaker_note_max_words: int = 160

    # Phase 2 aliases & properties (backward and forward compatible)
    body_words_max: Optional[int] = None
    body_words_min: Optional[int] = None
    title_words_max: Optional[int] = None
    subtitle_words_max: Optional[int] = None

    def model_post_init(self, __context: Any) -> None:
        if self.body_words_max is None:
            self.body_words_max = self.body_max_words
        else:
            self.body_max_words = self.body_words_max
        if self.body_words_min is None:
            self.body_words_min = 20
        if self.title_words_max is None:
            self.title_words_max = self.title_max_words
        else:
            self.title_max_words = self.title_words_max
        if self.subtitle_words_max is None:
            self.subtitle_words_max = self.subtitle_max_words
        else:
            self.subtitle_max_words = self.subtitle_words_max


class SlideBlueprint(BaseModel):
    """Per-slide plan created BEFORE content expansion.
    Describes what the slide IS, not the final prose."""
    slide_id: str = ""
    slide_number: int = 1
    intent: SlideIntent = SlideIntent.CONCEPT_EXPLANATION
    learning_purpose: str = ""
    narrative_role: str = ""
    semantic_role: str = ""
    comparison_target: str = ""
    primary_message: str = ""
    supporting_concepts: List[str] = Field(default_factory=list)
    canonical_concepts: List[str] = Field(default_factory=list)
    content_density: ContentDensity = ContentDensity.MEDIUM
    visual_priority: float = 0.5
    visual_type: VisualTypeHint = VisualTypeHint.NONE
    layout_family: LayoutFamily = LayoutFamily.CENTERED_FOCAL
    text_budget: TextBudget = Field(default_factory=TextBudget)
    speaker_note_goal: str = ""
    evidence_requirements: List[str] = Field(default_factory=list)
    section_label: Optional[str] = None


class DomainClassification(BaseModel):
    """Result of topic domain classification with provenance."""
    domain: str = "general"
    subdomain: str = ""
    confidence: float = 0.5
    classification_basis: str = "default"


class PresentationBrief(BaseModel):
    """Internal normalized representation built from PresentationConfig.
    Carries inferred intelligence that guides all downstream agents.
    The frontend API contract (PresentationConfig) remains unchanged."""

    # ─── Identity ──────────────────────────────────────────────
    topic: str
    canonical_topic: str = ""

    # ─── Domain ────────────────────────────────────────────────
    domain: str = "general"
    subdomain: str = ""
    domain_confidence: float = 0.5
    classification_basis: str = "DETERMINISTIC_RULE"

    # ─── Audience ──────────────────────────────────────────────
    education_level: str = "university"
    audience_expertise: str = "intermediate"

    # ─── Purpose ───────────────────────────────────────────────
    presentation_goal: PresentationGoal = PresentationGoal.TEACH
    presentation_mode: PresentationMode = PresentationMode.LECTURE

    # ─── Timing ────────────────────────────────────────────────
    duration_estimate: int = 25  # minutes

    # ─── Complexity ────────────────────────────────────────────
    technicality: ContentDensity = ContentDensity.MEDIUM
    visual_preference: str = "balanced"

    # ─── Template / Theme with override tracking ───────────────
    selected_template: str = "academic"
    recommended_template: str = "academic"
    template_selection_source: TemplateSelectionSource = TemplateSelectionSource.AUTO_RECOMMENDED

    selected_theme: str = "blue_professional"
    recommended_theme: str = "blue_professional"
    theme_selection_source: TemplateSelectionSource = TemplateSelectionSource.AUTO_RECOMMENDED

    # ─── Story ─────────────────────────────────────────────────
    primary_story_grammar: StoryGrammarType = StoryGrammarType.CONCEPT_TEACHING
    story_modifiers: List[StoryGrammarType] = Field(default_factory=list)

    # ─── Config (forwarded from PresentationConfig) ────────────
    slide_count: int = 12
    language: str = "english"
    knowledge_source: str = "general"
    source_hash: str = ""
    custom_context: Optional[str] = None

    # ─── Feature toggles ──────────────────────────────────────
    enable_diagrams: bool = True
    enable_images: bool = True
    enable_speaker_notes: bool = True
    enable_sources: bool = True
    enable_examples: bool = True
    enable_quiz: bool = False

    # ─── Versioning ────────────────────────────────────────────
    planner_version: str = "vnext_phase1"
    story_grammar_version: str = "1.0"
    blueprint_schema_version: str = "1.0"
    topic_intelligence_version: str = "1.0"

    # ─── Phase 2 Content Engine Versioning ─────────────────────
    content_engine_version: str = "2.0"
    content_schema_version: str = "2.0"
    content_prompt_version: str = "2.0"
    content_quality_auditor_version: str = "2.0"


class PipelineProvenance(BaseModel):
    """Telemetry/debug metadata tracking which engine path was used.
    Never exposed to normal users; persisted in outline_data for debugging."""
    planning_engine: str = "VNEXT"  # "VNEXT" | "LEGACY_FALLBACK"
    planning_fallback_used: bool = False
    planning_fallback_reason: str = ""  # e.g. "BRIEF_BUILD_FAILED", "TOPIC_INTELLIGENCE_FAILED"
    planner_version: str = "vnext_phase1"
    story_grammar_version: str = "1.0"
    blueprint_schema_version: str = "1.0"
    topic_intelligence_version: str = "1.0"

    # Phase 2 content provenance (additive)
    content_engine: str = "phase2"
    content_engine_version: str = "2.0"
    content_schema_version: str = "2.0"
    content_fallback_used: bool = False
    content_fallback_reason: str = ""
    content_repair_count: int = 0

    # Allowed fallback stages:
    # BRIEF_BUILD_FAILED, TOPIC_INTELLIGENCE_FAILED, STORY_PLANNING_FAILED,
    # BLUEPRINT_VALIDATION_FAILED, LLM_ENRICHMENT_FAILED
    # Phase 2 content stages:
    # CONTENT_GENERATION_FAILED, SCHEMA_PARSE_FAILED,
    # EVIDENCE_VALIDATION_FAILED, QUALITY_GATE_FAILED, TARGETED_REPAIR_FAILED


# ═══════════════════════════════════════════════════════════════
# vNEXT Phase 2 — Content Intelligence Engine Schemas
# ═══════════════════════════════════════════════════════════════


class ClaimType(str, Enum):
    """Classification of factual claims within generated content."""
    GENERAL_CONCEPT        = "general_concept"
    VERIFIABLE_FACT        = "verifiable_fact"
    NUMERIC_CLAIM          = "numeric_claim"
    HISTORICAL_CLAIM       = "historical_claim"
    RESEARCH_FINDING       = "research_finding"
    CASE_STUDY_CLAIM       = "case_study_claim"
    OPINION_INTERPRETATION = "opinion_interpretation"


class ClaimVerificationStatus(str, Enum):
    """Verification state of a factual claim."""
    VERIFIED           = "verified"
    SOURCE_PENDING     = "source_pending"
    UNVERIFIED_REMOVED = "unverified_removed"


class ContentOrigin(str, Enum):
    """Provenance tag for each meaningful content unit."""
    SOURCE_DOCUMENT        = "source_document"
    EXTERNAL_SOURCE        = "external_source"
    MODEL_BACKGROUND       = "model_background"
    DETERMINISTIC_STRUCTURE = "deterministic_structure"
    CONTENT_SEMANTIC_GAP   = "content_semantic_gap"


class SemanticStatus(str, Enum):
    """Semantic status of generated slide content, separated from source provenance."""
    GROUNDED = "grounded"
    ENRICHED = "enriched"
    GAP      = "gap"


class SemanticFailureReason(str, Enum):
    """Structured failure reasons for semantic validation and enrichment lifecycle."""
    MISSING_RELATIONSHIP        = "MISSING_RELATIONSHIP"
    INSUFFICIENT_CONCEPT_PACKET = "INSUFFICIENT_CONCEPT_PACKET"
    UNSUPPORTED_CLAIM           = "UNSUPPORTED_CLAIM"
    GENERIC_GENERATION          = "GENERIC_GENERATION"
    ENRICHMENT_FAILED           = "ENRICHMENT_FAILED"


class QualityGateError(Exception):
    """Raised when presentation specification fails the quality gate and export must be blocked."""
    pass


class ClaimEvidence(BaseModel):
    """Evidence record for a factual claim requiring verification."""
    claim_text: str = ""
    claim_type: ClaimType = ClaimType.GENERAL_CONCEPT
    source_required: bool = False
    source_id: str = ""
    source_quality: str = ""
    verification_status: ClaimVerificationStatus = ClaimVerificationStatus.SOURCE_PENDING


class LayoutCapacity(BaseModel):
    """Renderer/layout constraints passed into ContentAgent before generation.
    Content must be generated FOR the component capacity, not squeezed later."""
    max_cards: int = 4
    max_bullets: int = 5
    max_process_steps: int = 6
    max_table_rows: int = 5
    max_table_columns: int = 4
    max_code_lines: int = 8
    max_chart_annotations: int = 6
    max_label_length: int = 40


class SpeakerNoteCue(BaseModel):
    """Structured teaching cue embedded within speaker notes.
    Stored structurally; renderer formats them appropriately."""
    cue_type: str = ""  # TEACHING_CUE, PROBING_QUESTION, MISCONCEPTION_WARNING, TRANSITION
    text: str = ""


class MisconceptionBlock(BaseModel):
    """Structured misconception content for MISCONCEPTION intent slides."""
    incorrect_belief: str = ""
    correct_explanation: str = ""
    why_confusion_occurs: str = ""
    diagnostic_question: str = ""


class ComparisonRow(BaseModel):
    """A single dimension in a comparison slide."""
    dimension: str = ""
    target_a_value: str = ""
    target_b_value: str = ""


class DataPoint(BaseModel):
    """Structured data point for DATA_INSIGHT slides.
    Never fabricate — mark unresolved when source unavailable."""
    metric: str = ""
    value: str = ""
    unit: str = ""
    time_period: str = ""
    scope: str = ""
    source_id: str = ""
    is_verified: bool = False


class SlideContent(BaseModel):
    """Phase 2 structured content model for a single slide.
    Only populate fields relevant to the SlideIntent.
    Empty optional fields are correct when semantically irrelevant."""
    title: str = ""
    subtitle: str = ""
    primary_takeaway: str = ""
    supporting_points: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    callout: str = ""
    example: str = ""
    misconception: Optional[MisconceptionBlock] = None
    formula: str = ""
    formula_symbol_meanings: str = ""
    code: str = ""
    code_language: str = ""
    data_points: List[DataPoint] = Field(default_factory=list)
    comparison_target_a: str = ""
    comparison_target_b: str = ""
    comparison_rows: List[ComparisonRow] = Field(default_factory=list)
    process_steps: List[str] = Field(default_factory=list)
    citation_claims: List[ClaimEvidence] = Field(default_factory=list)
    speaker_notes: str = ""
    speaker_note_cues: List[SpeakerNoteCue] = Field(default_factory=list)
    content_origin: ContentOrigin = ContentOrigin.MODEL_BACKGROUND
    semantic_status: SemanticStatus = SemanticStatus.GROUNDED
    semantic_failure_reasons: List[str] = Field(default_factory=list)
    fit_risk: str = ""  # empty = no risk; otherwise describes the overflow situation
    word_count: int = 0
    text_budget_used: int = 0
    text_budget_max: int = 0


class ContentQualityScores(BaseModel):
    """Phase 2 content quality auditor scores (0–100 per dimension).
    Score is diagnostic — hard factual/evidence failures override aggregate score."""
    content_correctness: int = 0
    topic_specificity: int = 0
    primary_idea_clarity: int = 0
    content_depth: int = 0
    audience_fit: int = 0
    slide_nativeness: int = 0
    text_budget_compliance: int = 0
    example_quality: int = 0
    terminology_consistency: int = 0
    evidence_integrity: int = 0
    speaker_note_value: int = 0
    cross_slide_novelty: int = 0
    # Aggregate (average of all dimensions)
    aggregate_score: int = 0
    # Hard fail flag — overrides aggregate
    has_hard_fail: bool = False
    hard_fail_reasons: List[str] = Field(default_factory=list)


class SlideConceptPacket(BaseModel):
    """Semantic unit resolving grounded topic knowledge for a single slide.
    
    Empty/unknown arrays are strictly preferred over fabricated domain knowledge.
    Fields originate from verified source context, grounded TopicIntelligencePack,
    or structural blueprint inference."""
    primary_concept: str = ""
    supporting_concepts: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    required_terms: List[str] = Field(default_factory=list)
    domain_native_terms: List[str] = Field(default_factory=list)
    process_stages: List[str] = Field(default_factory=list)
    cause_effect_pairs: List[Dict[str, str]] = Field(default_factory=list)
    comparison_dimensions: List[str] = Field(default_factory=list)
    example_candidates: List[str] = Field(default_factory=list)
    misconceptions: List[Dict[str, str]] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    source_grounded_facts: List[str] = Field(default_factory=list)
    contextual_leakage_risks: List[str] = Field(default_factory=list)


class ContentProvenance(BaseModel):
    """Phase 2 content generation provenance tracking.
    Attached to pipeline telemetry alongside PipelineProvenance."""
    content_engine: str = "phase2"
    content_engine_version: str = "2.2"
    content_schema_version: str = "2.2"
    content_prompt_version: str = "2.2"
    content_quality_auditor_version: str = "2.2"
    content_fallback_used: bool = False
    content_fallback_reason: str = ""
    repair_count: int = 0
    
    # Semantic Content Truth Repair provenance fields
    semantic_grounding_status: str = "GROUNDED" # GROUNDED | ENRICHED | GAP
    semantic_gap_reason: str = ""
    semantic_enrichment_attempted: bool = False
    semantic_repair_count: int = 0
    # Allowed failure stages:
    # CONTENT_GENERATION_FAILED, SCHEMA_PARSE_FAILED,
    # EVIDENCE_VALIDATION_FAILED, QUALITY_GATE_FAILED,
    # TARGETED_REPAIR_FAILED
