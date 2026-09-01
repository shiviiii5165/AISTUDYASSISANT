from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    pdf_id: str
    question: str
    mode: str = "Quick Answer"
    history: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    model: str
    session_id: Optional[str] = None

class PipelineRequest(BaseModel):
    message: str
    pdf_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
