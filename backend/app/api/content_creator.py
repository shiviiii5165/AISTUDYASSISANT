from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.content_creator import (
    create_content,
    ContentRequest,
    ContentCreatorOutput,
    _get_job,
    _get_job_owner,
)
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("/generate", response_model=ContentCreatorOutput)
async def generate_content_endpoint(request: ContentRequest, current_user=Depends(get_current_user)):
    """
    Submits a request to the Content Creator Agent.
    For flashcards, returns the generated flashcards synchronously.
    For PPT and Video, returns a job_id with status='processing'.
    """
    try:
        output = await create_content(request, user_id=current_user.id)
        return output
    except HTTPException:
        raise
    except Exception as e:
        # Failsafe catch at the API boundary — surface as a real error status
        # rather than a 200 body that masks the failure.
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during request submission."
        )


@router.get("/status/{job_id}", response_model=ContentCreatorOutput)
async def get_job_status(job_id: str, current_user=Depends(get_current_user)):
    """
    Poll the status of a background generation job (PPT / Video).
    Returns the latest ContentCreatorOutput state.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")

    # Enforce ownership: a job can only be polled by the user who created it.
    if _get_job_owner(job_id) != current_user.id:
        raise HTTPException(status_code=404, detail="Job ID not found")

    return job
