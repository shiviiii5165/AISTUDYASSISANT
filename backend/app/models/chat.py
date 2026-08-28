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

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    model: str

class PipelineRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None
