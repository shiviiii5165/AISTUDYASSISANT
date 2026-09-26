"""
LearnByGenie Presentation Design Engine — Pydantic Schemas
=========================================================
Strict type contracts between LLM output and the rendering engine.
The LLM determines SEMANTICS. The design system determines VISUALS.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════

class SlidePurpose(str, Enum):
    """Semantic role of a slide — drives layout selection."""
    COVER          = "cover"
    SECTION        = "section"           # section divider
    CONCEPT        = "concept"           # definition / single-idea explanation
    TWO_COLUMN     = "two_column"        # side-by-side text or text+visual
    IMAGE_INSIGHT  = "image_insight"     # hero image with insight callout
    ARCHITECTURE   = "architecture"      # layered system diagram
    PROCESS_FLOW   = "process_flow"      # numbered step sequence
    TIMELINE       = "timeline"          # milestone progression
    COMPARISON     = "comparison"        # A vs B / pros vs cons
    KPI_METRICS    = "kpi_metrics"       # big numbers with context
    CASE_STUDY     = "case_study"        # problem → intervention → outcome
    QUOTE_INSIGHT  = "quote_insight"     # key insight / memorable quote
    SUMMARY        = "summary"           # takeaways / recap
    CLOSING        = "closing"           # end slide, Q&A


class VisualType(str, Enum):
    """What kind of visual support a slide should have."""
    NONE              = "none"
    AI_IMAGE          = "ai_image"
    ARCHITECTURE_DIAGRAM = "architecture_diagram"
    PROCESS_DIAGRAM   = "process_diagram"
    TIMELINE_GRAPHIC  = "timeline_graphic"
    COMPARISON_TABLE  = "comparison_table"
    CHART_BAR         = "chart_bar"
    CHART_LINE        = "chart_line"
    CHART_PIE         = "chart_pie"
    CALLOUT           = "callout"        # structured text callout (fallback)
    ICON_GRID         = "icon_grid"


class PresetType(str, Enum):
    """Presentation personality — influences prompts and structure."""
    ACADEMIC   = "academic"
    PITCH      = "pitch"
    TECHNICAL  = "technical"
    RESEARCH   = "research"
    TEACHING   = "teaching"


class AudienceLevel(str, Enum):
    UNIVERSITY    = "university"
    HIGH_SCHOOL   = "high_school"
    PROFESSIONAL  = "professional"
    BEGINNER      = "beginner"


class VisualMode(str, Enum):
    STANDARD = "standard"   # clean layouts, minimal visuals
    SMART    = "smart"      # AI picks images, diagrams, charts
    PREMIUM  = "premium"    # maximum visual richness


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE CONTENT — the structured LLM output for a single slide
# ═══════════════════════════════════════════════════════════════════════════

class TimelineMilestone(BaseModel):
    date: str = ""
    label: str = ""
    detail: str = ""

class ComparisonColumn(BaseModel):
    heading: str = ""
    points: List[str] = Field(default_factory=list)

class KPIMetric(BaseModel):
    value: str = ""        # "87%", "$2.4M", "3.2x"
    label: str = ""        # "Accuracy", "Revenue", "Speedup"
    context: str = ""      # why it matters

class ArchitectureLayer(BaseModel):
    name: str = ""
    components: List[str] = Field(default_factory=list)

class ProcessStep(BaseModel):
    number: int = 1
    title: str = ""
    detail: str = ""

class ChartDataPoint(BaseModel):
    label: str = ""
    value: float = 0.0
    series: str = "main"


class SlideContent(BaseModel):
    """Complete structured content for a single slide."""
    id: str = ""
    purpose: SlidePurpose = SlidePurpose.CONCEPT
    content_pattern: Optional[str] = None
    title: str = ""
    subtitle: str = ""

    # Body content
    body_bullets: List[str] = Field(default_factory=list)
    body_text: str = ""                # for paragraph-style content

    # Examples & insights
    example: str = ""
    key_insight: str = ""              # one strong takeaway
    quote: str = ""
    quote_attribution: str = ""

    # Visual
    visual_type: VisualType = VisualType.NONE
    image_prompt: str = ""
    image_bytes: Optional[bytes] = None  # populated at render time

    # Structured data for specialized layouts
    steps: List[ProcessStep] = Field(default_factory=list)
    milestones: List[TimelineMilestone] = Field(default_factory=list)
    columns: List[ComparisonColumn] = Field(default_factory=list)
    metrics: List[KPIMetric] = Field(default_factory=list)
    layers: List[ArchitectureLayer] = Field(default_factory=list)
    chart_data: List[ChartDataPoint] = Field(default_factory=list)
    chart_title: str = ""

    # Presenter support
    speaker_note: str = ""
    transition_note: str = ""     # how to segue to the next slide

    model_config = {"arbitrary_types_allowed": True}


# ═══════════════════════════════════════════════════════════════════════════
# PRESENTATION CONFIG — top-level generation configuration
# ═══════════════════════════════════════════════════════════════════════════

class PresentationConfig(BaseModel):
    """User-facing configuration for a presentation."""
    topic: str
    preset: PresetType = PresetType.ACADEMIC
    audience: AudienceLevel = AudienceLevel.UNIVERSITY
    depth: str = "full"                # "full" or "quick"
    theme_id: str = ""                 # auto-picked if empty
    visual_mode: VisualMode = VisualMode.SMART
    custom_instructions: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# FULL PRESENTATION — the complete deck specification
# ═══════════════════════════════════════════════════════════════════════════

class PresentationPlan(BaseModel):
    """Complete structured plan for a presentation (LLM output)."""
    deck_title: str = ""
    key_takeaways: List[str] = Field(default_factory=list)
    slides: List[SlideContent] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# QA SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DensityLevel(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class SlideQAResult(BaseModel):
    slide_index: int = 0
    density: DensityLevel = DensityLevel.MEDIUM
    word_count: int = 0
    bullet_count: int = 0
    issues: List[str] = Field(default_factory=list)
    passed: bool = True


# Re-export ThemeColors so renderers can import from package root
from .tokens import ThemeColors

