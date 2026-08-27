"""
AI Video Generation Engine — Canonical Scene Graph & Schema Contracts
=====================================================================
Defines strict Pydantic models for the canonical Scene Graph, Visual Budget,
Cost Telemetry, Resumable Job State Machine, and Multi-Source Provenance.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from ..knowledge.sources import SourceType, EvidenceItem


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
    MINIMAL  = "minimal"     # Mostly Python Graphics & Stock
    BALANCED = "balanced"    # Selective AI Images & Hero AI Video
    MAXIMUM  = "maximum"     # Richer AI Media up to Quality Budget


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT  = "9:16"


class JobState(str, Enum):
    QUEUED           = "queued"
    PLANNING         = "planning"
    SCENE_PLANNING   = "scene_planning"
    ASSET_RESOLUTION = "asset_resolution"
    GENERATING       = "generating"
    AUDIO            = "audio"
    COMPOSITING      = "compositing"
    QA               = "qa"
    COMPLETED        = "completed"
    FAILED           = "failed"


class SourceRef(BaseModel):
    source_type: str = "topic"              # "pdf", "ppt", "notes", "youtube", "topic"
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
    provider: str                           # "python", "pexels", "pixabay", "imagen", "veo", "local_cache"
    media_url: Optional[str] = None
    creator: str = "TeachGenie"
    license: str = "Educational Fair Use / CC0"
    attribution_text: str = ""
    duration_seconds: float = 0.0
    width: int = 1280
    height: int = 720


class AudioSpec(BaseModel):
    voice: str = "en-US-GuyNeural"
    language: str = "english"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    music_track: Optional[str] = None
    ducking_db: float = -14.0               # Lower music volume under narration
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0


class VisualSpec(BaseModel):
    diagram_type: Optional[str] = None      # "flow", "architecture", "timeline", "comparison", "cards", "formula"
    title: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    formula: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    edges: List[List[str]] = Field(default_factory=list)
    stock_keywords: List[str] = Field(default_factory=list)
    ai_prompt: Optional[str] = None
    theme: str = "academic"
    asset: Optional[AssetSpec] = None


class SceneSpec(BaseModel):
    scene_id: str
    order: int
    concept_id: str = ""
    purpose: str = "concept"                # "hook", "definition", "mechanism", "diagram", "example", "summary", "quiz"
    duration: int = 15                      # Target duration in seconds
    actual_duration: float = 0.0            # Real rendered duration
    narration: str                          # Teacher script
    visual_type: VisualAssetType = VisualAssetType.PYTHON_GRAPHICS
    visual_spec: VisualSpec = Field(default_factory=VisualSpec)
    audio_spec: AudioSpec = Field(default_factory=AudioSpec)
    caption: str = ""
    source_refs: List[SourceRef] = Field(default_factory=list)
    ai_video_score: float = 0.10            # 0.0 (static) to 1.0 (dynamic physical process / cinematic)
    scene_hash: Optional[str] = None
    rendered_media_path: Optional[str] = None
    rendered_audio_path: Optional[str] = None
    status: str = "pending"
    generation_attempts: int = 0
    error_message: Optional[str] = None


class Storyboard(BaseModel):
    topic: str
    style: VideoStyle = VideoStyle.ACADEMIC
    language: str = "english"
    total_duration: int = 300
    scenes: List[SceneSpec] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    summary_notes: str = ""


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
    ai_generation_ratio: float = 0.0        # ai_video_sec / total_sec


class VideoMetrics(UsageReport):
    pass


class VideoConfig(BaseModel):
    topic: str
    source_type: SourceType = SourceType.TOPIC
    source_ids: List[str] = Field(default_factory=list)
    youtube_url: Optional[str] = None
    lesson_session_id: Optional[str] = None
    
    duration: int = 300                     # Total seconds (60, 180, 300, 600, 900)
    quality: VideoQuality = VideoQuality.STANDARD
    ai_intensity: AIIntensity = AIIntensity.BALANCED
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    language: str = "english"
    style: VideoStyle = VideoStyle.ACADEMIC
    audience: str = "btech"
    depth: str = "normal"
    
    include_narration: bool = True
    include_captions: bool = True
    include_diagrams: bool = True
    include_stock: bool = True
    include_ai_video: bool = True
    include_music: bool = False
    include_sources: bool = True


class VideoProject(BaseModel):
    id: str
    user_id: str
    topic: str
    config: VideoConfig
    storyboard: Storyboard
    state: JobState = JobState.QUEUED
    status: str = "processing"              # Backwards compatible alias
    progress: int = 0                       # 0 to 100
    final_video_url: Optional[str] = None
    transcript_url: Optional[str] = None
    captions_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metrics: VideoMetrics = Field(default_factory=VideoMetrics)
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
