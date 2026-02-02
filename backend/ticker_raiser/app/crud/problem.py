from sqlalchemy.orm import Session
from sqlalchemy import and_, exists, or_
from app.models.models import Problem, TestCase, Submission, User
from app.schemas.problem import ProblemCreate, ProblemUpdate
from app.utils.text_processor import (
    prepare_test_case_for_storage,
    WhitespaceNormalizationMode,
)
from typing import Optional, List
from enum import Enum

class WhitespaceNormalizationMode(Enum):
    """Whitespace normalization strategies"""
    STRICT = "strict"  # Only normalize line endings, preserve internal spaces
    TRIM_LINES = "trim_lines"  # Trim trailing spaces from each line
    COMPACT = "compact"  # Normalize all consecutive spaces


# Problem CRUD Operations

def create_problem(db: Session, problem: ProblemCreate, creator_id: int) -> Problem:
    """Create a new problem"""
    db_problem = Problem(
        title=problem.title,
        description=problem.description,
        constraints=problem.constraints,
        difficulty=problem.difficulty,
        created_by=creator_id
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    return db_problem


def get_problem_by_id(db: Session, problem_id: int) -> Optional[Problem]:
    """Get a problem by ID"""
    return db.query(Problem).filter(Problem.id == problem_id).first()


def get_all_problems(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Problem]:
    """Get visible problems (Global Public only, excluding Custom Problems)"""
    # Always exclude custom problems from the main list
    query = db.query(Problem).filter(Problem.is_custom == False)
    
    # Note: If we had 'private' standard problems, we'd check created_by permissions here.
    # For now, all standard problems are public.
        
    return query.offset(skip).limit(limit).all()


def update_problem(db: Session, problem_id: int, problem_update: ProblemUpdate, creator_id: int) -> Optional[Problem]:
    """Update a problem (owner only)"""
    db_problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not db_problem:
        return None
    
    if db_problem.created_by != creator_id:
        return None  # Not owner
    
    update_data = problem_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_problem, field, value)
    
    db.commit()
    db.refresh(db_problem)
    return db_problem


def delete_problem(db: Session, problem_id: int, creator_id: int) -> bool:
    """Delete a problem (owner only, only if no submissions exist)"""
    db_problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not db_problem:
        return False
    
    if db_problem.created_by != creator_id:
        return False  # Not owner
    
    # Check if submissions exist
    submission_exists = db.query(exists(Submission.id)).filter(
        Submission.problem_id == problem_id
    ).scalar()
    
    if submission_exists:
        return False  # Cannot delete if submissions exist
    
    db.delete(db_problem)
    db.commit()
    return True


def is_problem_solved_by_user(db: Session, problem_id: int, user_id: int) -> bool:
    """Check if user has solved the problem (has ACCEPTED submission)"""
    submission = db.query(Submission).filter(
        and_(
            Submission.problem_id == problem_id,
            Submission.user_id == user_id,
            Submission.status == "ACCEPTED"
        )
    ).first()
    return submission is not None


# Test Case CRUD Operations

def create_test_case(
    db: Session,
    problem_id: int,
    input_data: str,
    expected_output: str,
    is_sample: bool = False
) -> Optional[TestCase]:
    """
    Create a test case with automatic text normalization.
    
    This function:
    1. Validates test case data for integrity
    2. Normalizes whitespace (removes BOM, non-ASCII spaces, trailing spaces)
    3. Normalizes line endings (converts all to \n)
    4. Stores in database with prepared statements (prevents SQL injection)
    
    Args:
        db: Database session
        problem_id: ID of the problem
        input_data: Test input (will be normalized)
        expected_output: Expected output (will be normalized)
        is_sample: Whether this is a sample test case
        
    Returns:
        Created TestCase or None if problem doesn't exist
    """
    # Verify problem exists
    problem = get_problem_by_id(db, problem_id)
    if not problem:
        return None
    
    # IMPORTANT: Pre-process to remove trailing spaces before passing to text processor
    # This handles cases where input has format: "1 2 3     \n5" (trailing spaces before newline)
    input_data = input_data.replace('\r\n', '\n')  # Normalize Windows line endings first
    input_data_lines = input_data.split('\n')
    input_data_lines = [line.rstrip() for line in input_data_lines]  # Remove trailing spaces from each line
    input_data = '\n'.join(input_data_lines)
    
    expected_output = expected_output.replace('\r\n', '\n')
    expected_output_lines = expected_output.split('\n')
    expected_output_lines = [line.rstrip() for line in expected_output_lines]
    expected_output = '\n'.join(expected_output_lines)
    
    # Prepare and validate test case data
    clean_input, clean_output, error_msg = prepare_test_case_for_storage(
        input_data,
        expected_output,
        normalize=True,
        normalization_mode=WhitespaceNormalizationMode.TRIM_LINES
    )
    
    if error_msg:
        raise ValueError(f"Invalid test case data: {error_msg}")
    
    # Create with normalized data using ORM (parameterized queries)
    db_test_case = TestCase(
        problem_id=problem_id,
        input_data=clean_input,
        expected_output=clean_output,
        is_sample=is_sample
    )
    
    db.add(db_test_case)
    db.commit()
    db.refresh(db_test_case)
    return db_test_case


def get_test_case_by_id(db: Session, test_case_id: int) -> Optional[TestCase]:
    """Get a test case by ID"""
    return db.query(TestCase).filter(TestCase.id == test_case_id).first()


def get_test_cases_by_problem(db: Session, problem_id: int) -> List[TestCase]:
    """Get all test cases for a problem"""
    return db.query(TestCase).filter(TestCase.problem_id == problem_id).all()


def get_sample_test_cases_by_problem(db: Session, problem_id: int) -> List[TestCase]:
    """Get only sample test cases for a problem"""
    return db.query(TestCase).filter(
        and_(TestCase.problem_id == problem_id, TestCase.is_sample == True)
    ).all()


def delete_test_case(db: Session, test_case_id: int) -> bool:
    """Delete a test case"""
    db_test_case = get_test_case_by_id(db, test_case_id)
    if not db_test_case:
        return False
    
    db.delete(db_test_case)
    db.commit()
    return True


def update_test_case(
    db: Session,
    test_case_id: int,
    input_data: Optional[str] = None,
    expected_output: Optional[str] = None,
    is_sample: Optional[bool] = None
) -> Optional[TestCase]:
    """
    Update a test case with optional fields.
    
    Args:
        db: Database session
        test_case_id: ID of the test case to update
        input_data: New input data (optional)
        expected_output: New expected output (optional)
        is_sample: Whether this is a sample test case (optional)
        
    Returns:
        Updated TestCase or None if not found
    """
    db_test_case = get_test_case_by_id(db, test_case_id)
    if not db_test_case:
        return None
    
    # Update input_data if provided
    if input_data is not None:
        input_data = input_data.replace('\r\n', '\n')
        input_data_lines = input_data.split('\n')
        input_data_lines = [line.rstrip() for line in input_data_lines]
        input_data = '\n'.join(input_data_lines)
        db_test_case.input_data = input_data
    
    # Update expected_output if provided
    if expected_output is not None:
        expected_output = expected_output.replace('\r\n', '\n')
        expected_output_lines = expected_output.split('\n')
        expected_output_lines = [line.rstrip() for line in expected_output_lines]
        expected_output = '\n'.join(expected_output_lines)
        db_test_case.expected_output = expected_output
    
    # Update is_sample if provided
    if is_sample is not None:
        db_test_case.is_sample = is_sample
    
    db.commit()
    db.refresh(db_test_case)
    return db_test_case


def verify_problem_owner(db: Session, problem_id: int, user_id: int) -> bool:
    """Verify if user is the owner of the problem"""
    problem = get_problem_by_id(db, problem_id)
    if not problem:
        return False
    return problem.created_by == user_id


def verify_test_case_owner(db: Session, test_case_id: int, user_id: int) -> bool:
    """Verify if user is the owner of the problem that the test case belongs to"""
    test_case = get_test_case_by_id(db, test_case_id)
    if not test_case:
        return False
    return verify_problem_owner(db, test_case.problem_id, user_id)
