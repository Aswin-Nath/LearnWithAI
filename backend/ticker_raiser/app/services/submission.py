from sqlalchemy.orm import Session
from app.crud.submission import (
    create_submission as crud_create_submission,
    get_submission_by_id,
    get_submissions_by_user,
    is_submission_owner,
    update_submission_status as crud_update_submission_status
)
from app.crud.problem import get_problem_by_id, get_test_cases_by_problem
from app.schemas.submission import SubmissionCreate, SubmissionResponse, SubmissionListResponse
from app.models.models import Submission
from typing import List, Optional
from fastapi import HTTPException, status
import redis
import json


class RedisClient:
    """Redis client for queue management"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
    
    def enqueue_submission(self, submission_id: int) -> bool:
        """Push submission_id to submissions_queue"""
        try:
            self.client.lpush("submissions_queue", submission_id)
            return True
        except Exception as e:
            print(f"Redis enqueue error: {e}")
            return False
    
    def dequeue_submission(self, timeout: int = 0) -> Optional[int]:
        """BRPOP submission from queue (blocking pop from right)"""
        try:
            result = self.client.brpop("submissions_queue", timeout=timeout)
            if result:
                return int(result[1])
            return None
        except Exception as e:
            print(f"Redis dequeue error: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            self.client.ping()
            return True
        except:
            return False


# Initialize Redis client
redis_client = RedisClient()


class SubmissionService:
    """Service layer for submission operations"""

    @staticmethod
    def create_and_queue_submission(
        db: Session,
        user_id: int,
        problem_id: int,
        code: str,
        language: str
    ) -> SubmissionResponse:
        """
        Create a new submission and enqueue it for judging.
        
        Steps:
        1. Verify problem exists
        2. Get test case count
        3. Create submission (PENDING)
        4. Push submission_id to Redis queue
        5. Return submission response
        """
        # Verify problem exists
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Get test case count
        test_cases = get_test_cases_by_problem(db, problem_id)
        total_test_cases = len(test_cases)
        
        if total_test_cases == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Problem has no test cases"
            )
        
        # Create submission
        db_submission = crud_create_submission(
            db,
            user_id=user_id,
            problem_id=problem_id,
            code=code,
            language=language,
            total_test_cases=total_test_cases
        )
        
        if not db_submission:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create submission"
            )
        
        # Enqueue to Redis
        enqueued = redis_client.enqueue_submission(db_submission.id)
        if not enqueued:
            # Submission created but failed to enqueue
            # (optional: you could mark as ERROR or delete)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue submission for judging"
            )
        
        return SubmissionResponse.model_validate(db_submission)

    @staticmethod
    def get_submission(db: Session, submission_id: int, current_user_id: int) -> SubmissionResponse:
        """Get submission detail (user can only see their own)"""
        submission = get_submission_by_id(db, submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        if not is_submission_owner(db, submission_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this submission"
            )
        
        return SubmissionResponse.model_validate(submission)

    @staticmethod
    def list_user_submissions(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[SubmissionListResponse]:
        """List all submissions for a user"""
        submissions = get_submissions_by_user(db, user_id, skip, limit)
        return [SubmissionListResponse.model_validate(s) for s in submissions]

    @staticmethod
    def update_submission_after_judge(
        db: Session,
        submission_id: int,
        status: str,
        test_cases_passed: int
    ) -> Optional[Submission]:
        """Update submission with judge results (called by worker)"""
        return crud_update_submission_status(db, submission_id, status, test_cases_passed)
