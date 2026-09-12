from typing import List, Dict, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class StageStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    MATERIAL_READY = "material_ready"
    TAUGHT = "taught"
    ASSESSMENT_PENDING = "assessment_pending"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class StageReadiness(str, Enum):
    READY = "ready"
    PREREQUISITE_REQUIRED = "prerequisite_required"
    REVIEW_RECOMMENDED = "review_recommended"
    BLOCKED = "blocked"


class NextBestAction(str, Enum):
    TEACH = "teach"
    PRACTICE = "practice"
    REVIEW = "review"
    RETEACH = "reteach"
    ADVANCE = "advance"
    PREREQUISITE_RECAP = "prerequisite_recap"
    ASSESS = "assess"
    EXTEND = "extend"


class ResourceType(str, Enum):
    PPT = "ppt"
    VIDEO = "video"
    TEACH_ME = "teach_me"
    QUIZ = "quiz"
    NOTES = "notes"
    WORKSHEET = "worksheet"
    HOMEWORK = "homework"
    DIAGRAM = "diagram"
    YOUTUBE_RECOMMENDATIONS = "youtube_recommendations"
    EXTRA_LEARNING_MATERIALS = "extra_learning_materials"


class ResourceStatus(str, Enum):
    NOT_NEEDED = "not_needed"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    SELECTED = "selected"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"
    COMING_SOON = "coming_soon"
    DISABLED = "disabled"


class RoadmapStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ClassType(str, Enum):
    LECTURE = "Lecture"
    INTERACTIVE_LECTURE = "Interactive Lecture"
    TUTORIAL = "Tutorial"
    LAB = "Lab"
    SEMINAR = "Seminar"
    WORKSHOP = "Workshop"
    DISCUSSION = "Discussion"
    FLIPPED_CLASSROOM = "Flipped Classroom"
    ONLINE = "Online"
    HYBRID = "Hybrid"
    REVISION = "Revision"
    EXAM_REVIEW = "Exam Review"
    REMEDIAL = "Remedial"
    PROJECT_BASED = "Project-Based"
    CASE_STUDY = "Case Study"
    VIVA_PREPARATION = "Viva Preparation"


class ProductMode(str, Enum):
    TEACHER_CLASSROOM = "teacher_classroom"
    STUDENT_SELF_STUDY = "student_self_study"
    RESEARCH_ADVANCED = "research_advanced"


class CanonicalDomain(str, Enum):
    COMPUTER_SCIENCE = "computer_science"
    SOFTWARE_ENGINEERING = "software_engineering"
    ECE = "ece"
    ELECTRICAL = "electrical"
    ELECTRONICS = "electronics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    MEDICINE = "medicine"
    MATHEMATICS = "mathematics"
    EDUCATION = "education"
    ECONOMICS = "economics"
    BUSINESS = "business"
    HUMANITIES = "humanities"
    LAW = "law"
    SOCIAL_SCIENCES = "social_sciences"
    LANGUAGES = "languages"
    GENERAL_ACADEMIC = "general_academic"


class HierarchicalDomain(BaseModel):
    domain_family: str = "engineering"  # engineering, sciences, humanities, medicine, business
    domain: CanonicalDomain = CanonicalDomain.COMPUTER_SCIENCE
    specialization: Optional[str] = None


class InstructionalMode(str, Enum):
    STANDARD = "standard"
    LAB = "lab"
    FLIPPED = "flipped"
    REMEDIAL = "remedial"
    SOCRATIC = "socratic"
    SEMINAR = "seminar"
    MICRO_LESSON = "micro_lesson"
    DEEP_DIVE = "deep_dive"
    PROJECT_KICKOFF = "project_kickoff"


class TeachingIntent(str, Enum):
    INTRODUCE = "introduce"
    UNDERSTAND = "understand"
    TEACH = "teach"
    REVISE = "revise"
    PRACTICE = "practice"
    IMPLEMENT = "implement"
    ASSESS = "assess"
    EXAM_PREP = "exam_prep"
    RESEARCH = "research"
    PROJECT = "project"
    INTERVIEW_PREP = "interview_prep"


class TopicVolatility(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StageArchetype(str, Enum):
    HOOK = "hook"
    PREREQUISITE_CHECK = "prerequisite_check"
    CONCEPT_INTRO = "concept_intro"
    MENTAL_MODEL = "mental_model"
    EXPLANATION = "explanation"
    DEMONSTRATION = "demonstration"
    WORKED_EXAMPLE = "worked_example"
    GUIDED_PRACTICE = "guided_practice"
    DISCUSSION = "discussion"
    SIMULATION = "simulation"
    CODING = "coding"
    CASE_STUDY = "case_study"
    RESEARCH_REVIEW = "research_review"
    INDEPENDENT_PRACTICE = "independent_practice"
    DIAGNOSTIC_CHECK = "diagnostic_check"
    REMEDIATION = "remediation"
    RETRIEVAL = "retrieval"
    REFLECTION = "reflection"
    SUMMARY = "summary"
    EXTENSION = "extension"


class PrerequisiteMasteryState(str, Enum):
    MASTERED = "mastered"
    LIKELY_MASTERED = "likely_mastered"
    UNKNOWN = "unknown"
    WEAK = "weak"
    BLOCKING = "blocking"


class PaperType(str, Enum):
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    REVIEW = "review"
    SYSTEMATIC_REVIEW = "systematic_review"
    SURVEY = "survey"
    PREPRINT = "preprint"
    STANDARD = "standard"
    BOOK_CHAPTER = "book_chapter"
    WORKING_PAPER = "working_paper"


class JournalQuartile(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    UNRANKED = "unranked"


class ConferenceTier(str, Enum):
    A_STAR = "A*"
    A = "A"
    B = "B"
    C = "C"
    UNRANKED = "unranked"


class ResourceScoreBreakdown(BaseModel):
    concept_match: int = 90
    level_fit: int = 90
    authority: int = 90
    freshness: int = 90
    evidence_quality: int = 90
    accessibility: int = 90
    outcome_effectiveness: Optional[int] = None


class AcademicProvenance(BaseModel):
    metadata_sources: List[str] = Field(default_factory=list)  # e.g. ["crossref", "arxiv", "openalex", "semantic_scholar"]
    ranking_system: Optional[str] = None  # e.g. "SJR", "CORE", "CCF"
    ranking_source: Optional[str] = None  # e.g. "Scimago", "Computing Research and Education Association of Australasia"
    ranking_year_or_version: Optional[str] = None  # e.g. "2024", "v2023.1"
    raw_rank: Optional[str] = None  # e.g. "Q1", "Q2", "A*", "A", "unranked", "unknown"
    normalized_rank: Optional[str] = None  # e.g. "tier_1", "tier_2"
    last_verified_at: Optional[datetime] = None
    is_stale: bool = False


class UniversalResourceCard(BaseModel):
    id: str
    title: str
    type: str  # video_segment, paper, coding_problem, docs, textbook
    why_recommended: str
    what_it_covers: str
    learner_level: str
    use_during: str = "explanation"  # hook, concept_intro, worked_example, practice, deep_dive
    exact_section: Optional[str] = None
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None
    time_required_minutes: Optional[int] = None
    source_authority: str = "Verified Authority"
    quality_score: int = 90  # 0 to 100
    score_breakdown: ResourceScoreBreakdown = Field(default_factory=ResourceScoreBreakdown)
    year: Optional[int] = None
    access_type: str = "open"  # open, subscription, paywall
    url: str
    is_preprint: bool = False
    has_retraction_notice: bool = False
    venue_label: Optional[str] = None
    confidence: float = 0.90
    academic_provenance: Optional[AcademicProvenance] = None
    timestamp_source: str = "whole_video"  # transcript, video_chapters, description_timestamps, whole_video
    transcript_available: bool = False
    segment_confidence: float = 0.0
    resource_purpose: Optional[str] = None
    why_now: Optional[str] = None
    what_to_do_after: Optional[str] = None
    course_metadata: Optional[Dict[str, Any]] = None
    paper_section: Optional[str] = None
    outcome_effectiveness: Optional[int] = None


class TeacherLockItem(BaseModel):
    stage_id: Optional[str] = None
    lock_type: str  # objective, stage, duration, resource, assessment, activity
    target_identifier: str
    is_locked: bool = True
    notes: str = ""


class LearningEvidenceRecord(BaseModel):
    id: Optional[str] = None
    student_id: str = "anonymous"
    roadmap_id: Optional[str] = None
    concept_id: str
    canonical_concept_id: Optional[str] = None
    objective_id: Optional[str] = None
    source_type: str = "checkpoint"  # quiz, live_quiz, teach_me, checkpoint, observation
    source_id: Optional[str] = None
    question_id: Optional[str] = None
    event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    correctness: bool
    confidence: float = 0.80
    attempt: int = 1
    response_time_seconds: Optional[float] = None
    misconception_candidate: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentConceptState(BaseModel):
    student_id: str
    canonical_concept_id: str
    curriculum_scope: str = "standard"
    curriculum_version: str = "1.0"
    mastery_state: PrerequisiteMasteryState = PrerequisiteMasteryState.UNKNOWN
    confidence: float = 0.50
    evidence_count: int = 0
    success_count: int = 0
    last_evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanRecompileDiff(BaseModel):
    reason: str
    evidence_summary: str = ""
    stages_added: List[Dict[str, Any]] = Field(default_factory=list)
    stages_modified: List[Dict[str, Any]] = Field(default_factory=list)
    stages_compressed: List[Dict[str, Any]] = Field(default_factory=list)
    net_duration_change: int = 0
    requires_teacher_approval: bool = True


class LearningObjective(BaseModel):
    id: str
    description: str
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class StageActivity(BaseModel):
    id: Optional[str] = None
    type: str  # hook, explanation, example, guided_practice, independent_practice, checkpoint, lab_demo, student_task, debugging, summary
    title: str = ""
    description: str
    duration_minutes: int


class ResourceRecommendation(BaseModel):
    resource_type: ResourceType
    usefulness_score: float = 0.5  # 0.0 to 1.0
    status: ResourceStatus = ResourceStatus.OPTIONAL
    reason: str = ""
    resource_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    lineage_version: int = 1


class StageDifferentiation(BaseModel):
    core: str = ""
    support: str = ""
    extension: str = ""


class SourceReference(BaseModel):
    source_type: str = "general"  # pdf, ppt, notes, youtube, web, syllabus, general
    title: str
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None


class StageAction(BaseModel):
    type: str  # ppt, teachme, quiz, youtube_recommendations, extra_learning_materials
    enabled: bool
    status: str = "active"  # active, coming_soon, disabled
    title: str = ""
    description: str = ""


class YouTubeVideoRecommendation(BaseModel):
    title: str
    channel: str
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    url: str
    relevance: float = 0.9
    difficulty: str = "intermediate"
    source: str = "YouTube"
    reason: str = ""


class YouTubeRecommendationResponse(BaseModel):
    enabled: bool = True
    status: str = "active"
    items: List[YouTubeVideoRecommendation] = Field(default_factory=list)


class ExtraLearningMaterialItem(BaseModel):
    title: str
    url: str
    description: str
    source: str
    type: str
    relevance: float = 0.9
    difficulty: str = "intermediate"


class ExtraLearningMaterialsCategories(BaseModel):
    academic_references: List[ExtraLearningMaterialItem] = Field(default_factory=list)
    research_papers: List[ExtraLearningMaterialItem] = Field(default_factory=list)
    documentation: List[ExtraLearningMaterialItem] = Field(default_factory=list)
    extra_learning_material: List[ExtraLearningMaterialItem] = Field(default_factory=list)


class ExtraLearningMaterialsResponse(BaseModel):
    enabled: bool = True
    status: str = "active"
    categories: ExtraLearningMaterialsCategories = Field(default_factory=ExtraLearningMaterialsCategories)


class RoadmapStage(BaseModel):
    id: str
    concept_id: str
    title: str
    description: str
    sequence: int = 0
    duration_minutes: int
    status: StageStatus = StageStatus.LOCKED
    readiness: StageReadiness = StageReadiness.BLOCKED
    mastery: int = 0  # 0 to 100
    confidence: int = 0
    
    # Core pedagogy
    objective_ids: List[str] = Field(default_factory=list)
    objectives: List[LearningObjective] = Field(default_factory=list)
    prerequisite_ids: List[str] = Field(default_factory=list)
    
    # Actions & Execution
    teacher_actions: List[str] = Field(default_factory=list)
    student_actions: List[str] = Field(default_factory=list)
    evidence_of_learning: str = ""
    activities: List[StageActivity] = Field(default_factory=list)
    checkpoint_questions: List[str] = Field(default_factory=list)
    expected_misconceptions: List[str] = Field(default_factory=list)
    
    # Differentiation & Resources
    differentiation: StageDifferentiation = Field(default_factory=StageDifferentiation)
    resource_recommendations: List[ResourceRecommendation] = Field(default_factory=list)
    actions: List[StageAction] = Field(default_factory=list)
    source_refs: List[SourceReference] = Field(default_factory=list)
    
    # VNext Stage Extensions
    archetype: StageArchetype = StageArchetype.EXPLANATION
    why_this_stage: str = ""
    why_now: str = ""
    teaching_goal: str = ""
    pedagogy_method: str = ""
    visual_requirements: List[str] = Field(default_factory=list)
    assessment_requirement: str = ""
    is_locked: bool = False
    universal_resources: List[UniversalResourceCard] = Field(default_factory=list)
    canonical_concept_id: Optional[str] = None
    
    next_best_action: NextBestAction = NextBestAction.TEACH
    version: int = 1
    is_optional: bool = False
    is_remedial: bool = False


class DependencyEdge(BaseModel):
    source: str
    target: str
    edge_type: str = "prerequisite_of"  # prerequisite_of, depends_on, follows, assesses, supported_by, related_to
    strength: float = 1.0


class ConceptNode(BaseModel):
    id: str
    title: str
    description: str
    unit_id: Optional[str] = None
    prerequisite_ids: List[str] = Field(default_factory=list)
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class CourseUnit(BaseModel):
    id: str
    unit_number: int
    title: str
    description: str = ""
    topics: List[str] = Field(default_factory=list)
    estimated_hours: float = 4.0
    coverage_percentage: int = 0  # 0 to 100


class CourseGraph(BaseModel):
    course_id: str
    title: str
    code: Optional[str] = None
    units: List[CourseUnit] = Field(default_factory=list)
    nodes: List[ConceptNode] = Field(default_factory=list)
    edges: List[DependencyEdge] = Field(default_factory=list)


class CourseCoverage(BaseModel):
    total_units: int = 0
    covered_units: int = 0
    coverage_percentage: int = 0
    unit_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


class PlanRecompileRequest(BaseModel):
    expected_plan_version: int = 1
    reason: str = "Diagnostic Checkpoint Evaluation"
    trigger_source: str = "checkpoint"
    evidence: List[LearningEvidenceRecord] = Field(default_factory=list)
    auto_apply: bool = False


class LearningRoadmap(BaseModel):
    id: str
    course_id: str = "default_course"
    topic: str
    title: Optional[str] = None
    description: Optional[str] = None
    level: str = "B.Tech"
    language: str = "english"
    class_type: ClassType = ClassType.INTERACTIVE_LECTURE
    target_duration_minutes: int = 60
    status: RoadmapStatus = RoadmapStatus.DRAFT
    
    stages: List[RoadmapStage] = Field(default_factory=list)
    next_best_action: NextBestAction = NextBestAction.TEACH
    overall_progress: int = 0  # 0 to 100
    health_score: int = 100
    
    course_coverage: Optional[CourseCoverage] = None
    version: int = 1
    current_version: int = 1
    
    # VNext Roadmap Extensions
    mode: ProductMode = ProductMode.TEACHER_CLASSROOM
    domain: CanonicalDomain = CanonicalDomain.GENERAL_ACADEMIC
    intent: TeachingIntent = TeachingIntent.TEACH
    volatility: TopicVolatility = TopicVolatility.LOW
    knowledge_pack_id: Optional[str] = None
    adaptive_reserve_minutes: int = 0
    teacher_locks: List[TeacherLockItem] = Field(default_factory=list)
    plan_versions_count: int = 1
    
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SemesterScheduledLesson(BaseModel):
    week_number: int
    session_number: int
    date_str: str
    unit_title: str
    topic_title: str
    duration_minutes: int
    is_practical: bool = False
    is_exam: bool = False
    is_holiday: bool = False


class SemesterPlan(BaseModel):
    course_id: str
    total_weeks: int = 14
    classes_per_week: int = 3
    minutes_per_class: int = 60
    scheduled_lessons: List[SemesterScheduledLesson] = Field(default_factory=list)
    coverage_percentage: int = 100


class RoadmapEvent(BaseModel):
    id: Optional[str] = None
    roadmap_id: str
    stage_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgePack(BaseModel):
    id: str
    topic: str
    subject: str = "General"
    grade: str = "B.Tech"
    curriculum: str = "Standard"
    curriculum_version: str = "1.0"
    language: str = "english"
    difficulty: str = "intermediate"
    source_hash: Optional[str] = None
    schema_version: str = "2.0"
    learning_objectives: List[LearningObjective] = Field(default_factory=list)
    concepts: List[Dict[str, Any]] = Field(default_factory=list)
    definitions: Dict[str, str] = Field(default_factory=dict)
    prerequisites: List[str] = Field(default_factory=list)
    concept_dependencies: List[DependencyEdge] = Field(default_factory=list)
    common_misconceptions: List[Dict[str, Any]] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    counterexamples: List[str] = Field(default_factory=list)
    visual_opportunities: List[str] = Field(default_factory=list)
    practice_targets: List[str] = Field(default_factory=list)
    assessment_targets: List[str] = Field(default_factory=list)
    resource_queries: List[str] = Field(default_factory=list)
    trusted_sources: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


# Re-export Unified Resource Intelligence Contracts
from .vnext.resources.contracts import (
    ResourcePurpose, ResourceFeedbackType, ResourceIntent,
    ResourceProvenance, ResourceQualityScore, ResourceSegment,
    CourseResource, NormalizedResource, ResourceCandidate,
    ResourceOutcomeSignal, ProviderHealthRecord, ResourceBundle
)


