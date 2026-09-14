"""
TeachGenie Lesson Planner — Resource Intelligence Schemas & Contracts
=====================================================================
Unified data contracts for Stage Resource Intelligence, query profiles,
candidate ranking, action priority, and multi-provider normalized models.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StageIntent(str, Enum):
    INTRODUCTION = "INTRODUCTION"
    CONCEPT_LEARNING = "CONCEPT_LEARNING"
    DEEP_EXPLANATION = "DEEP_EXPLANATION"
    PRACTICE = "PRACTICE"
    REMEDIAL = "REMEDIAL"
    ASSESSMENT = "ASSESSMENT"
    REVISION = "REVISION"
    EXAM_PREPARATION = "EXAM_PREPARATION"
    PROJECT = "PROJECT"
    ADVANCED_RESEARCH = "ADVANCED_RESEARCH"


class ResourceType(str, Enum):
    YOUTUBE_VIDEO = "YOUTUBE_VIDEO"
    ACADEMIC_REFERENCE = "ACADEMIC_REFERENCE"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    CODING_PROBLEM = "CODING_PROBLEM"
    PRACTICE_PROBLEM = "PRACTICE_PROBLEM"
    GUIDE = "GUIDE"
    TUTORIAL = "TUTORIAL"


class VerificationLevel(str, Enum):
    PROVIDER_VERIFIED = "PROVIDER_VERIFIED"
    DOMAIN_VERIFIED = "DOMAIN_VERIFIED"
    METADATA_VERIFIED = "METADATA_VERIFIED"
    LIVE_URL_VERIFIED = "LIVE_URL_VERIFIED"


class StageActionPriority(str, Enum):
    PRIMARY = "PRIMARY"          # "Top Pick" (at most 1 per stage)
    RECOMMENDED = "RECOMMENDED"  # "Recommended" (1-2 per stage)
    AVAILABLE = "AVAILABLE"      # standard action without distracting badge


class ProviderDiagnosticState(str, Enum):
    SUCCESS = "SUCCESS"
    NO_RELEVANT_RESULTS = "NO_RELEVANT_RESULTS"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    HTTP_BLOCKED = "HTTP_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    PARSER_FAILURE = "PARSER_FAILURE"
    INVALID_RESULT = "INVALID_RESULT"
    DISABLED_BY_POLICY = "DISABLED_BY_POLICY"


class SourceProvenance(str, Enum):
    LIVE_SEARCH_RESULT = "LIVE_SEARCH_RESULT"
    CURATED_CANONICAL_MAPPING = "CURATED_CANONICAL_MAPPING"
    DIRECT_URL_VERIFIED = "DIRECT_URL_VERIFIED"
    INTERNAL_GENERATED = "INTERNAL_GENERATED"


class DeliveryProvenance(str, Enum):
    FRESH_COMPUTE = "FRESH_COMPUTE"
    LIVE_PROVIDER_FETCH = "LIVE_PROVIDER_FETCH"
    LIVE_FETCH = "LIVE_FETCH"
    BACKEND_CACHE_HIT = "BACKEND_CACHE_HIT"
    FRONTEND_CACHE_HIT = "FRONTEND_CACHE_HIT"


# Backward compatibility alias
ProviderProvenance = SourceProvenance



class ResourceQueryContext(BaseModel):
    """
    Full canonical educational context for resource retrieval.
    Guarantees that queries are never built from isolated stage-title tokens.
    """
    roadmap_id: str
    plan_version: str = "1.0"
    stage_id: str
    original_topic: str
    normalized_topic: str
    domain: str
    specialization: Optional[str] = None
    learner_level: str = "B.Tech"
    primary_intent: str = "CONCEPT_LEARNING"
    instructional_mode: str = "DIRECT_INSTRUCTION"
    stage_type: str = "concept_intro"
    learning_objectives: List[str] = Field(default_factory=list)
    canonical_concept_ids: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    resource_role: str = "conceptual_reference"
    negative_terms: List[str] = Field(default_factory=list)


class ResourceIntentProfile(BaseModel):
    """
    Rich pedagogical intent extracted from the roadmap, stage, and learner profile.
    Guarantees that resource discovery targets actual concept mastery rather than
    literal sentence keywords.
    """
    roadmap_id: str
    stage_id: str
    domain: str = "general"
    specialization: Optional[str] = None
    subject: str = ""
    canonical_topic: str
    stage_title: str
    concept_ids: List[str] = Field(default_factory=list)
    concept_names: List[str] = Field(default_factory=list)
    concept_synonyms: List[str] = Field(default_factory=list)
    canonical_concept_ids: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    learner_weaknesses: List[str] = Field(default_factory=list)
    mastery_state: str = "in_progress"
    learner_level: str = "B.Tech"
    instructional_mode: str = "DIRECT_INSTRUCTION"
    preferred_language: str = "english"
    stage_intent: StageIntent = StageIntent.CONCEPT_LEARNING
    is_programming_topic: bool = False
    programming_language: Optional[str] = None
    assessment_focus: Optional[str] = None
    query_terms: List[str] = Field(default_factory=list)
    negative_terms: List[str] = Field(default_factory=list)
    recommended_resource_types: List[ResourceType] = Field(default_factory=list)
    stage_archetype: Optional[str] = None
    plan_version: Any = 1
    fallback_concept_id: Optional[str] = None
    context: Optional[ResourceQueryContext] = None


class ResourceCandidate(BaseModel):
    """
    Normalized, evidence-based candidate resource retrieved from verified providers.
    """
    id: str
    provider: str  # "youtube", "semantic_scholar", "arxiv", "crossref", "tavily", "wikipedia"
    resource_type: ResourceType
    title: str
    canonical_url: str
    description: str
    source_name: str
    author_or_channel: str
    thumbnail_url: Optional[str] = None
    thumbnail_fallbacks: List[str] = Field(default_factory=list)

    published_at: Optional[str] = None
    year: Optional[int] = None
    duration_seconds: Optional[int] = None
    duration_formatted: Optional[str] = None

    view_count: Optional[int] = None
    like_count: Optional[int] = None

    paper_id: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    citation_count: Optional[int] = None
    influential_citation_count: Optional[int] = None
    open_access: Optional[bool] = None
    publication_type: Optional[str] = None  # Journal Article, Conference Paper, Preprint, Book Chapter
    peer_review_status: Optional[str] = None  # Peer-reviewed, Preprint, Unknown
    venue: Optional[str] = None

    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    language: str = "english"

    # Multi-factor score signals (0.0 to 1.0)
    concept_relevance: float = 0.0
    objective_coverage: float = 0.0
    stage_intent_match: float = 0.0
    learner_level_match: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0
    engagement_score: float = 0.0
    final_score: float = 0.0

    fit_label: str = "Strong fit"  # Excellent fit (>=0.85), Strong fit (>=0.70), Useful supplement (<0.70)
    why_recommended: str = ""

    verified: bool = True
    verification_levels: List[VerificationLevel] = Field(default_factory=list)
    source_provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value
    delivery_provenance: str = DeliveryProvenance.LIVE_FETCH.value
    provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value
    metadata: Dict[str, Any] = Field(default_factory=dict)


class YouTubeItemOutput(BaseModel):
    title: str
    channel: str
    thumbnail: Optional[str] = None
    thumbnail_fallbacks: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    url: str
    relevance: float = 0.85
    match_percentage: Optional[int] = None
    fit_label: str = "Strong fit"
    difficulty: str = "intermediate"
    source: str = "YouTube"
    reason: str = ""
    why_recommended: Optional[str] = None
    verification_level: str = "PROVIDER_VERIFIED"
    source_provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value
    delivery_provenance: str = DeliveryProvenance.LIVE_FETCH.value
    provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value


class YouTubeResponseOutput(BaseModel):
    enabled: bool = True
    status: str = "active"
    canonical_topic: Optional[str] = None
    items: List[YouTubeItemOutput] = Field(default_factory=list)
    stage_intent: Optional[str] = None
    diagnostic_info: Optional[Dict[str, Any]] = None

    @property
    def videos(self) -> List[YouTubeItemOutput]:
        return self.items


class MaterialItemOutput(BaseModel):
    id: Optional[str] = None
    title: str
    url: Optional[str] = None
    related_practice_url: Optional[str] = None
    description: str
    source: str
    type: str
    relevance: float = 0.85
    match_percentage: Optional[int] = None
    fit_label: str = "Strong fit"
    difficulty: str = "intermediate"
    publication_type: Optional[str] = None
    peer_review_status: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    citation_count: Optional[int] = None
    open_access: Optional[bool] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    why_recommended: Optional[str] = None
    verification_level: str = "DOMAIN_VERIFIED"
    source_provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value
    delivery_provenance: str = DeliveryProvenance.FRESH_COMPUTE.value
    provenance: str = SourceProvenance.LIVE_SEARCH_RESULT.value


class LearningMaterialsCategoriesOutput(BaseModel):
    academic_references: List[MaterialItemOutput] = Field(default_factory=list)
    research_papers: List[MaterialItemOutput] = Field(default_factory=list)
    practice_coding: List[MaterialItemOutput] = Field(default_factory=list)
    documentation: List[MaterialItemOutput] = Field(default_factory=list)
    guides_tutorials: List[MaterialItemOutput] = Field(default_factory=list)
    # Backward compatibility key alias
    extra_learning_material: List[MaterialItemOutput] = Field(default_factory=list)


class LearningMaterialsResponseOutput(BaseModel):
    enabled: bool = True
    status: str = "active"
    canonical_topic: Optional[str] = None
    categories: LearningMaterialsCategoriesOutput
    visible_tabs: List[str] = Field(default_factory=list)
    diagnostic_info: Optional[Dict[str, Any]] = None

    @property
    def materials(self) -> LearningMaterialsCategoriesOutput:
        return self.categories


class StageActionRecommendation(BaseModel):
    key: str  # ppt, teach_me, quiz, youtube_recommendations, extra_learning_materials, coding_resources
    priority: StageActionPriority
    badge_label: Optional[str] = None  # "Top Pick", "Recommended", None
    reason: str


class CodingResourceItemOutput(BaseModel):
    id: str
    title: str
    source: str  # "Python Official Documentation", "GeeksforGeeks", "LeetCode", etc.
    type: str    # "official_docs", "coding_reference", "coding_problem", "practice", "diagnostic_micro_problem"
    url: Optional[str] = None
    related_practice_url: Optional[str] = None
    description: str
    why_recommended: str
    difficulty: Optional[str] = None
    fit_label: str = "Strong fit"
    diagnostic_state: ProviderDiagnosticState = ProviderDiagnosticState.SUCCESS
    exact_section: Optional[str] = None
    time_required_minutes: Optional[int] = None
    source_provenance: str = SourceProvenance.CURATED_CANONICAL_MAPPING.value
    delivery_provenance: str = DeliveryProvenance.FRESH_COMPUTE.value
    provenance: str = SourceProvenance.CURATED_CANONICAL_MAPPING.value
    resource_role: str = "STAGE_SPECIFIC_REFERENCE"


class CodingResourcesResponseOutput(BaseModel):
    enabled: bool = True
    status: str = "active"
    canonical_topic: str
    domain: str = "computer_science"
    specialization: Optional[str] = None
    items: List[CodingResourceItemOutput] = Field(default_factory=list)
    provider_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    diagnostic_info: Optional[Dict[str, Any]] = None
