"""
Knowledge Source Types and Unified Evidence Model
=================================================
Normalizes all source types (PDF, PPT, Handwritten Notes, YouTube, Web, Topic)
into a unified EvidenceItem schema for deterministic retrieval and citation.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


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
    document_id: Optional[str] = None
    source_name: str = ""
    text: str
    page: Optional[int] = None
    page_number: Optional[int] = None
    slide: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_start: Optional[int] = None  # in seconds
    timestamp_end: Optional[int] = None    # in seconds
    confidence: float = 1.0
    relevance_score: float = 0.0
    visual_reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='before')
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "page_number" in data and "page" not in data:
                data["page"] = data["page_number"]
            if "page" in data and "page_number" not in data:
                data["page_number"] = data["page"]
            if "slide_number" in data and "slide" not in data:
                data["slide"] = data["slide_number"]
            if "slide" in data and "slide_number" not in data:
                data["slide_number"] = data["slide"]
            if "document_id" in data and not data.get("source_id"):
                data["source_id"] = data["document_id"]
        return data

    def get_citation_badge(self) -> str:
        """Returns a clean user-facing citation string."""
        p = self.page or self.page_number
        s = self.slide or self.slide_number
        if self.source_type == SourceType.PDF and p:
            return f"Page {p}"
        elif self.source_type == SourceType.PPT and s:
            return f"Slide {s}"
        elif self.source_type == SourceType.HANDWRITTEN_NOTE:
            return f"Notes Page {p or 1}"
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
