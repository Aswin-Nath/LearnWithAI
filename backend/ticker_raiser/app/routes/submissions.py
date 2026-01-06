from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionListResponse,
)
from app.services.submission import SubmissionService

router = APIRouter(prefix="/submissions", tags=["SUBMISSIONS"])



@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for judging",
    description="Create a submission and enqueue it for judge worker"
)
async def create_submission(
    submission: SubmissionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new submission.
    
    Steps:
    1. Validate problem exists
    2. Create submission with PENDING status
    3. Push submission_id to Redis queue
    4. Return submission (client polls GET /submissions/{id} for status)
    
    Returns:
        - Submission object with status=PENDING
    """
    return SubmissionService.create_and_queue_submission(
        db=db,
        user_id=current_user.id,
        problem_id=submission.problem_id,
        code=submission.code,
        language=submission.language
    )



@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission status",
    description="Get submission details (polling endpoint for judge status)"
)
async def get_submission(
    submission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get submission details.
    
    Returns current status (PENDING, ACCEPTED, WRONG_ANSWER, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED).
    
    Client should poll this endpoint to check judge results.
    
    Parameters:
        - submission_id: Submission ID
    
    Returns:
        - Submission object with current status
    """
    return SubmissionService.get_submission(db, submission_id, current_user.id)



@router.get(
    "/me/submissions",
    response_model=List[SubmissionListResponse],
    summary="List my submissions",
    description="Get all submissions for current user"
)
async def list_my_submissions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all submissions for current user with pagination.
    
    Parameters:
        - skip: Offset (default 0)
        - limit: Max results (default 100)
    
    Returns:
        - List of submissions (latest first)
    """
    return SubmissionService.list_user_submissions(db, current_user.id, skip, limit)
