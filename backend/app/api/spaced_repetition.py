from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, AuthenticatedUser
from app.services.spaced_repetition.service import SpacedRepetitionService
from app.services.spaced_repetition.schemas import (
    QueueSummaryResponse,
    ReviewSubmissionRequest,
    ReviewFeedbackResponse
)

router = APIRouter()


@router.get("/queue", response_model=QueueSummaryResponse)
def get_review_queue(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the spaced repetition cards due for review today."""
    return SpacedRepetitionService.get_queue(current_user.id)


@router.post("/review", response_model=ReviewFeedbackResponse)
def submit_card_review(payload: ReviewSubmissionRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Submits a student's review of a flashcard and updates the SM-2 interval schedule."""
    try:
        return SpacedRepetitionService.process_review(current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

