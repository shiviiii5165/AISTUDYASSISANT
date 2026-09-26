"""
LearnByGenie Notes Generation Engine — Domain Schemas & Contracts
===============================================================
Contracts for Step 3 of the Notes Intelligence Layer.
Takes CanonicalNotesContext and NotesGenerationPlan to produce NotesDocument.
Defines explicit generation modes, deficits, and source grounding models.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class GenerationMode(str, Enum):
    AI_GENERATED = "ai_generated"
    AI_GENERATED_REPAIRED = "ai_generated_repaired"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"
    GENERATION_FAILED = "generation_failed"
    GENERATION_INCOMPLETE = "generation_incomplete"


class GroundedSourceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str
    title: str = ""
    chunk_id: Optional[str] = None
    content: str
    relevance: float = 1.0
    badge: Optional[str] = None
    page: Optional[int] = None
    slide: Optional[int] = None


class GroundedSources(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: List[GroundedSourceItem] = Field(default_factory=list)

    @classmethod
    def from_context(cls, ctx: Any) -> "GroundedSources":
        """Extracts and standardizes grounded evidence from CanonicalNotesContext."""
        items: List[GroundedSourceItem] = []
        raw_evidence = getattr(ctx, "source_evidence", []) or []
        for i, ev in enumerate(raw_evidence):
            if isinstance(ev, dict):
                items.append(GroundedSourceItem(
                    source_id=ev.get("source_id") or ev.get("source_name") or f"src_{i+1}",
                    title=ev.get("source_name") or ev.get("title") or "Verified Curriculum Source",
                    content=ev.get("snippet") or ev.get("content") or "",
                    badge=ev.get("badge") or "Source",
                    page=ev.get("page"),
                    slide=ev.get("slide")
                ))
        return cls(items=items)


class PracticeQuestionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str
    question_type: str = "recall"  # "recall" | "application" | "tricky_cases" | "diagnostic"
    difficulty: str = "basic"
    answer: str
    explanation: Optional[str] = None
    target_concept: Optional[str] = None


class SemanticDeficit(BaseModel):
    """Tracks missing semantic requirements that warrant bounded regeneration."""
    model_config = ConfigDict(populate_by_name=True)

    missing_sections: List[str] = Field(default_factory=list)
    practice_shortfall: int = 0
    missing_visual: bool = False
    unaddressed_misconceptions: List[str] = Field(default_factory=list)

    @property
    def has_deficits(self) -> bool:
        return (
            bool(self.missing_sections) or
            self.practice_shortfall > 0 or
            self.missing_visual or
            bool(self.unaddressed_misconceptions)
        )


class GenerationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    document: Any
    generation_mode: str = GenerationMode.AI_GENERATED.value
    structural_repairs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    model_identifier: Optional[str] = None
