"""
Librarian API Endpoint
========================
Standalone POST /api/librarian/retrieve that accepts a topic, user_id, and
optional top_k, then returns the structured LibrarianOutput as JSON.

Purely additive — does NOT modify chat.py, teach.py, or the Orchestrator.
"""

from fastapi import APIRouter, Depends, Request
from app.core.security import limiter
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.librarian import retrieve_context, LibrarianOutput
from app.core.dependencies import get_current_user

router = APIRouter()


class LibrarianRequest(BaseModel):
    """Request body for the librarian retrieve endpoint."""
    topic: str = Field(..., description="The topic or query to retrieve context for.")
    user_id: str = Field(..., description="The student's user ID for scoped retrieval.")
    top_k: Optional[int] = Field(5, description="Number of top chunks to retrieve.")


@router.post("/retrieve", response_model=LibrarianOutput)
@limiter.limit("20/minute")
async def retrieve_endpoint(request: Request, payload: LibrarianRequest, current_user=Depends(get_current_user)):
    """
    Retrieve context for a topic from the student's notes, with optional
    web search fallback. Returns structured JSON with context, related_context,
    sufficient flag, and used_web_fallback flag.
    """
    # Always scope retrieval to the authenticated user, ignoring any
    # client-supplied user_id, to prevent cross-tenant note retrieval.
    result = await retrieve_context(
        topic=payload.topic,
        user_id=current_user.id,
        top_k=payload.top_k or 5,
    )
    return result
