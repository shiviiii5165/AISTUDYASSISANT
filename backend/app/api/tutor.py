"""
Tutor API Endpoint
====================
Standalone POST /api/tutor/turn that accepts the topic, librarian context,
conversation history, and student message, then returns TutorTurn as JSON.

Purely additive — does NOT modify chat.py, teach.py, or the Orchestrator.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from app.agents.librarian import LibrarianOutput
from app.agents.tutor import tutor_turn, TutorTurn
from app.core.dependencies import get_current_user

router = APIRouter()


class TutorRequest(BaseModel):
    """Request body for the tutor turn endpoint."""
    topic: str = Field(..., description="The concept being taught.")
    librarian_context: LibrarianOutput = Field(
        ..., description="Structured context from the Librarian agent."
    )
    conversation_history: List[dict] = Field(
        default_factory=list,
        description="Prior turns as [{role, content}, ...].",
    )
    student_message: Optional[str] = Field(
        None,
        description="The student's latest reply. Null for the very first turn.",
    )


@router.post("/turn", response_model=TutorTurn)
async def tutor_turn_endpoint(request: TutorRequest, current_user=Depends(get_current_user)):
    """
    Run one turn of the Socratic tutor. Returns the Tutor's response
    and updated learning state as structured JSON.
    """
    result = await tutor_turn(
        topic=request.topic,
        librarian_context=request.librarian_context,
        conversation_history=request.conversation_history,
        student_message=request.student_message,
    )
    return result
