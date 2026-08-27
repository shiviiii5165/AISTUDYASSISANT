"""
Pydantic Request & Response Models for Teach Me API (Hardened)
==============================================================
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StartTeachRequest(BaseModel):
    topic: str
    level: str = "btech"
    language: str = "english"
    depth: str = "normal"
    mode: str = "interactive_teacher"
    source_type: str = "topic"
    source_ids: Optional[List[str]] = Field(default_factory=list)
    youtube_url: Optional[str] = None


class TeachMessageRequest(BaseModel):
    session_id: str
    message: str


class TeachCommandRequest(BaseModel):
    session_id: str
    command: str  # "continue" | "explain_again" | "make_simpler" | "go_deeper" | "give_example" | "ask_question" | "exam_points" | "show_visual" | "explain_it_back"


class TeachAnswerRequest(BaseModel):
    session_id: str
    answer: str
    idempotency_key: Optional[str] = None


class YouTubeIngestRequest(BaseModel):
    url: str
    title: Optional[str] = None
    subject: str = "General"


class ExportPPTRequest(BaseModel):
    session_id: str
    slide_count: int = 12
    design: str = "academic"
    theme: str = "blue_professional"


class ExportVideoRequest(BaseModel):
    session_id: str
    duration: int = 300
    quality: str = "standard"
    style: str = "academic"
