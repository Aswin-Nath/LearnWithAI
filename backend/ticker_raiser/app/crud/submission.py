from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.models import Submission, Problem, TestCase
from app.schemas.submission import SubmissionCreate
from typing import Optional, List


def create_submission(
    db: Session,
    user_id: int,
    problem_id: int,
    code: str,
    language: str,
    total_test_cases: int
) -> Optional[Submission]:
    """Create a new submission (PENDING status)"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        return None

    db_submission = Submission(
        user_id=user_id,
        problem_id=problem_id,
        code=code,
        language=language,
        status="PENDING",
        test_cases_passed=0,
        total_test_cases=total_test_cases
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def get_submission_by_id(db: Session, submission_id: int) -> Optional[Submission]:
    """Get a submission by ID"""
    return db.query(Submission).filter(Submission.id == submission_id).first()


def get_submissions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Submission]:
    """Get all submissions for a user with pagination"""
    return db.query(Submission).filter(
        Submission.user_id == user_id
    ).order_by(desc(Submission.created_at)).offset(skip).limit(limit).all()


def get_submissions_by_problem(db: Session, problem_id: int, skip: int = 0, limit: int = 100) -> List[Submission]:
    """Get all submissions for a problem with pagination"""
    return db.query(Submission).filter(
        Submission.problem_id == problem_id
    ).order_by(desc(Submission.created_at)).offset(skip).limit(limit).all()


def update_submission_status(
    db: Session,
    submission_id: int,
    status: str,
    test_cases_passed: int
) -> Optional[Submission]:
    """Update submission status and test cases passed (used by judge worker)"""
    db_submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not db_submission:
        return None

    db_submission.status = status
    db_submission.test_cases_passed = test_cases_passed
    db.commit()
    db.refresh(db_submission)
    return db_submission


def is_submission_owner(db: Session, submission_id: int, user_id: int) -> bool:
    """Check if user owns the submission"""
    submission = db.query(Submission).filter(
        and_(
            Submission.id == submission_id,
            Submission.user_id == user_id
        )
    ).first()
    return submission is not None
