from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.content_creator import (
    create_content,
    ContentRequest,
    ContentCreatorOutput,
    _get_job
)

router = APIRouter()


@router.post("/generate", response_model=ContentCreatorOutput)
async def generate_content_endpoint(request: ContentRequest):
    """
    Submits a request to the Content Creator Agent.
    For flashcards, returns the generated flashcards synchronously.
    For PPT and Video, returns a job_id with status='processing'.
    """
    try:
        output = await create_content(request)
        return output
    except Exception as e:
        # Failsafe catch at the API boundary
        return ContentCreatorOutput(
            content_type=request.content_type,
            status="failed",
            error_message="An unexpected error occurred during request submission."
        )


@router.get("/status/{job_id}", response_model=ContentCreatorOutput)
async def get_job_status(job_id: str):
    """
    Poll the status of a background generation job (PPT / Video).
    Returns the latest ContentCreatorOutput state.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    return job
