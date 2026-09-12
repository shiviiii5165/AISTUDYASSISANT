"""
Core Contracts for Unified Resource Intelligence Layer
======================================================
Defines universal schemas, intent models, provenance standards, and
outcome signals for all Lesson Planner VNext resource engines.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ResourcePurpose(str, Enum):
    """
    Explicit pedagogical purpose for resource recommendation.
    A resource must never be recommended without satisfying one explicit purpose.
    """
    PRIMARY_EXPLANATION = "PRIMARY_EXPLANATION"
    ALTERNATIVE_EXPLANATION = "ALTERNATIVE_EXPLANATION"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    VISUALIZATION = "VISUALIZATION"
    SIMULATION = "SIMULATION"
    IMPLEMENTATION_REFERENCE = "IMPLEMENTATION_REFERENCE"
    PRACTICE = "PRACTICE"
    DIAGNOSTIC_PRACTICE = "DIAGNOSTIC_PRACTICE"
    AUTHORITATIVE_REFERENCE = "AUTHORITATIVE_REFERENCE"
    STANDARD = "STANDARD"
    RESEARCH_OVERVIEW = "RESEARCH_OVERVIEW"
    SEMINAL_RESEARCH = "SEMINAL_RESEARCH"
    FRONTIER_RESEARCH = "FRONTIER_RESEARCH"
    COURSE_LECTURE = "COURSE_LECTURE"
    DEEP_DIVE = "DEEP_DIVE"
    REVISION = "REVISION"
    REMEDIATION = "REMEDIATION"


class ResourceFeedbackType(str, Enum):
    HELPFUL = "Helpful"
    TOO_EASY = "Too Easy"
    TOO_DIFFICULT = "Too Difficult"
    OUTDATED = "Outdated"
    BROKEN_LINK = "Broken Link"
    POOR_EXPLANATION = "Poor Explanation"
    EXCELLENT_EXPLANATION = "Excellent Explanation"


class ResourceIntent(BaseModel):
    """
    Pedagogical intent specification for finding stage resources.
    """
    purpose: ResourcePurpose = ResourcePurpose.PRIMARY_EXPLANATION
    stage_id: str
    stage_sequence: int = 0
    objective_ids: List[str] = Field(default_factory=list)
    canonical_concept_ids: List[str] = Field(default_factory=list)
    learner_level: str = "B.Tech"
    domain: str = "computer_science"
    target_duration_minutes: Optional[int] = None
    modality_preferences: List[str] = Field(default_factory=list)


class ResourceProvenance(BaseModel):
    """
    Verified authority and provenance backing.
    """
    authority_name: str
    authority_score: int = 90  # 0 to 100
    source_category: str  # "university_course", "official_documentation", "peer_reviewed_journal", "reputable_educator"
    ranking_system: Optional[str] = None  # "SJR", "CORE", "NPTEL_Tier"
    ranking_source: Optional[str] = None
    ranking_year_or_version: Optional[str] = None
    raw_rank: Optional[str] = None  # "Q1", "A*", "Elite"
    normalized_rank: Optional[str] = None
    last_verified_at: Optional[str] = None
    is_stale: bool = False
    retraction_status: str = "clear"  # "clear", "retracted", "concern"


class ResourceQualityScore(BaseModel):
    """
    Transparent breakdown of 100-point resource quality score.
    """
    total_score: int = 90
    concept_match: int = 90
    objective_match: int = 90
    level_fit: int = 90
    authority: int = 90
    freshness: int = 90
    evidence_quality: int = 90
    accessibility: int = 95
    outcome_effectiveness: Optional[int] = None


class ResourceSegment(BaseModel):
    """
    Precise section, timestamp, or module within a larger learning resource.
    """
    start_seconds: Optional[int] = None
    end_seconds: Optional[int] = None
    formatted_range: Optional[str] = None  # e.g. "07:42–13:05" or "Section 3 — Method"
    segment_label: Optional[str] = None
    segment_confidence: float = 0.0  # 0.0 to 1.0
    timestamp_source: str = "whole_video"  # "video_chapters", "transcript", "paper_section", "course_lecture", "whole_video"
    time_required_minutes: Optional[int] = None
    concept_coverage: float = 0.0
    objective_coverage: float = 0.0


class CourseResource(BaseModel):
    """
    Deep course lecture recommendation mapped down to module and lecture.
    """
    provider: str  # "NPTEL", "MIT OCW", "Stanford", "Harvard", "SWAYAM", "Coursera", "edX"
    course_title: str
    institution: str  # "IIT Madras", "MIT", "Stanford"
    instructor: Optional[str] = None
    course_level: str = "UG"  # "School", "UG", "PG", "Research"
    course_url: str
    module_title: str
    week_number: Optional[int] = None
    lecture_title: str
    lecture_url: str
    objective_ids: List[str] = Field(default_factory=list)
    canonical_concept_ids: List[str] = Field(default_factory=list)
    estimated_duration: int = 20  # minutes
    difficulty: str = "intermediate"
    why_recommended: str = ""
    authority_score: int = 95
    quality_score: int = 90
    access_type: str = "open"  # "open", "free_registration", "subscription"
    last_verified_at: Optional[str] = None


class NormalizedResource(BaseModel):
    """
    Universal internal normalized resource contract.
    """
    id: str
    title: str
    url: str
    provider: str
    intent_purpose: ResourcePurpose
    provenance: ResourceProvenance
    quality_score: ResourceQualityScore
    segment: Optional[ResourceSegment] = None
    estimated_duration_minutes: Optional[int] = None
    why_recommended: str
    why_now: str
    what_exact_objective: str
    why_trusted: str
    what_to_do_after: str
    learner_level: str
    access_type: str = "open"
    course_metadata: Optional[CourseResource] = None
    paper_section: Optional[str] = None


class ResourceCandidate(BaseModel):
    """
    Raw extracted candidate before normalization and scoring.
    """
    candidate_id: str
    provider: str
    raw_title: str
    raw_url: str
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    source_type: str


class ResourceOutcomeSignal(BaseModel):
    """
    Longitudinal feedback and outcome evidence for adaptive ranking.
    """
    signal_id: str
    resource_id: str
    concept_id: str
    learner_level: str
    pre_resource_state: str = "novice"  # "novice", "misconception", "partial"
    post_resource_state: str = "mastered"  # "mastered", "progressing", "struggling"
    misconception_before: Optional[str] = None
    misconception_after: Optional[str] = None
    time_spent_seconds: int = 0
    teacher_feedback: Optional[ResourceFeedbackType] = None
    student_feedback: Optional[ResourceFeedbackType] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProviderHealthRecord(BaseModel):
    """
    Telemetry and health monitoring for external resource providers.
    """
    provider: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 1.0
    latencies_ms: List[float] = Field(default_factory=list)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    rate_limit_status: str = "healthy"  # "healthy", "throttled", "circuit_broken"
    last_success: Optional[str] = None
    last_failure: Optional[str] = None


class ResourceBundle(BaseModel):
    """
    Stage-level resource bundle enforcing minimum effective set and diversity.
    """
    stage_id: str
    intent: ResourceIntent
    resources: List[NormalizedResource] = Field(default_factory=list)
    redundancies_pruned: int = 0
