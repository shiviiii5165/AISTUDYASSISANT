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


class DesignSystem(str, Enum):
    ACADEMIC_CLEAN  = "academic"        # University lecture & teaching
    MODERN_MINIMAL  = "minimal"         # Premium Canva/NotebookLM clean
    TECHNICAL_GRID  = "technical"       # CSE, Architecture, Engineering
    EDITORIAL       = "editorial"       # Magazine / Research report
    VISUAL_LEARNING = "visual"          # Diagram-first visual pedagogy


class VisualKind(str, Enum):
    NONE         = "none"
    DIAGRAM      = "diagram"
    ARCHITECTURE = "architecture"
    FLOW         = "flow"
    TIMELINE     = "timeline"
    COMPARISON   = "comparison"
    HIERARCHY    = "hierarchy"
    IMAGE        = "image"
    TABLE        = "table"
    CODE         = "code"


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

    model_config = {"arbitrary_types_allowed": True}


class SlideSourceRef(BaseModel):
    source_type: str = "pdf"
    document_id: str = ""
    page: Optional[int] = None
    slide: Optional[int] = None
    snippet: str = ""


class SlideSpec(BaseModel):
    slide_no: int
    type: SlideType = SlideType.CONCEPT
    title: str
    subtitle: str = ""
    key_message: str = ""
    body_bullets: List[str] = Field(default_factory=list)
    example: str = ""
    speaker_notes: str = ""
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
        if v not in [10, 11, 12, 13, 14, 15]:
            raise ValueError(f"slide_count must be exactly 10, 11, 12, 13, 14, or 15 (got {v})")
        return v


class PresentationSpec(BaseModel):
    title: str
    subtitle: str = ""
    config: PresentationConfig
    key_takeaways: List[str] = Field(default_factory=list)
    slides: List[SlideSpec] = Field(default_factory=list)

    def validate_exact_count(self) -> bool:
        return len(self.slides) == self.config.slide_count
