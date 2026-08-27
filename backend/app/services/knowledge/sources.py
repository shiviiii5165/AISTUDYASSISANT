"""
Knowledge Source Types and Unified Evidence Model
=================================================
Normalizes all source types (PDF, PPT, Handwritten Notes, YouTube, Web, Topic)
into a unified EvidenceItem schema for deterministic retrieval and citation.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    TOPIC = "topic"
    PDF = "pdf"
    PPT = "ppt"
    HANDWRITTEN_NOTE = "handwritten_note"
    YOUTUBE = "youtube"
    WEB = "web"
    UPLOADED_MATERIAL = "uploaded_material"
    UPLOADED_MATERIAL_PLUS_WEB = "uploaded_material_plus_web"


class EvidenceItem(BaseModel):
    source_type: SourceType = SourceType.PDF
    source_id: str = ""
    source_name: str = ""
    text: str
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp_start: Optional[int] = None  # in seconds
    timestamp_end: Optional[int] = None    # in seconds
    confidence: float = 1.0
    relevance_score: float = 0.0
    visual_reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_citation_badge(self) -> str:
        """Returns a clean user-facing citation string."""
        if self.source_type == SourceType.PDF and self.page:
            return f"Page {self.page}"
        elif self.source_type == SourceType.PPT and self.slide:
            return f"Slide {self.slide}"
        elif self.source_type == SourceType.HANDWRITTEN_NOTE:
            return f"Notes Page {self.page or 1}"
        elif self.source_type == SourceType.YOUTUBE and self.timestamp_start is not None:
            m1, s1 = divmod(self.timestamp_start, 60)
            if self.timestamp_end:
                m2, s2 = divmod(self.timestamp_end, 60)
                return f"{m1:02d}:{s1:02d}–{m2:02d}:{s2:02d}"
            return f"{m1:02d}:{s1:02d}"
        elif self.source_type == SourceType.WEB:
            return "Web Research"
        return "Source Material"


# Backward compatibility aliases
SourceRef = EvidenceItem
KnowledgeChunk = EvidenceItem
