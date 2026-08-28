"""
Orchestrator API Endpoint
==========================
Standalone POST /orchestrator/route that accepts a user message + optional
conversation history and returns the structured OrchestratorOutput as JSON.

This endpoint is additive — it does NOT modify chat.py, teach.py, or any
existing route. It exists purely for independent testing of the Orchestrator
agent before wiring it into the main conversation flow.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.orchestrator import classify_and_route, OrchestratorOutput

router = APIRouter()


class OrchestratorRequest(BaseModel):
    """Request body for the orchestrator route endpoint."""
    message: str = Field(..., description="The raw user message to classify.")
    history: Optional[list[dict]] = Field(
        None,
        description="Optional conversation history as [{role: 'user'|'assistant', content: '...'}].",
    )


@router.post("/route", response_model=OrchestratorOutput)
async def route_message(request: OrchestratorRequest):
    """
    Classify a user message and return the routing decision.
    Returns structured JSON with intent, topic, confidence, routed_to,
    and an optional direct_reply.
    """
    result = await classify_and_route(
        user_input=request.message,
        conversation_history=request.history,
    )
    return result
