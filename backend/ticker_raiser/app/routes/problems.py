from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_current_user_with_scopes
from app.schemas.problem import (
    ProblemCreate,
    ProblemUpdate,
    ProblemListResponse,
    ProblemDetailResponse,
    ProblemCreateResponse,
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    MessageResponse,
)
from app.services.problems import ProblemService, TestCaseService
from app.utils.pdf_upload_util import upload_pdf_to_cloudinary

router = APIRouter(prefix="/problems", tags=["PROBLEMS"])


# ============================================================================
# 1️⃣ CREATE PROBLEM (POST /problems)
# ============================================================================

@router.post(
    "",
    response_model=ProblemCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new problem",
    description="PROBLEM_SETTER only - Create a new problem with title, description, constraints, and difficulty",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def create_problem(
    problem: ProblemCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new problem (PROBLEM_SETTER only).
    
    Returns:
        - Problem ID
    """
    return ProblemService.create_problem(db, problem, current_user.id)


# ============================================================================
# 2️⃣ UPDATE PROBLEM (PUT /problems/{problem_id})
# ============================================================================

@router.put(
    "/{problem_id}",
    response_model=ProblemDetailResponse,
    summary="Update a problem",
    description="PROBLEM_SETTER only (owner) - Update problem details",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def update_problem(
    problem_id: int,
    problem_update: ProblemUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a problem (owner only).
    
    Parameters:
        - problem_id: Problem ID to update
        - problem_update: Fields to update (title, description, constraints, difficulty)
    
    Returns:
        - Updated problem with full details
    """
    return ProblemService.update_problem(db, problem_id, problem_update, current_user.id)


# ============================================================================
# 3️⃣ DELETE PROBLEM (DELETE /problems/{problem_id})
# ============================================================================

@router.delete(
    "/{problem_id}",
    response_model=MessageResponse,
    summary="Delete a problem",
    description="PROBLEM_SETTER only (owner) - Delete a problem if no submissions exist",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def delete_problem(
    problem_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a problem (owner only).
    
    Rule: Only allowed if no submissions exist for this problem.
    
    Parameters:
        - problem_id: Problem ID to delete
    """
    return ProblemService.delete_problem(db, problem_id, current_user.id)


# ============================================================================
# 4️⃣ LIST PROBLEMS (GET /problems)
# ============================================================================

@router.get(
    "",
    response_model=List[ProblemListResponse],
    summary="List all problems",
    description="USER + PROBLEM_SETTER - Get minimal problem list with solved status"
)
async def list_problems(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all problems with minimal fields and solved status.
    
    Returns:
        - List of problems with: id, title, difficulty, is_solved
        - is_solved is computed per problem for current user
    """
    return ProblemService.list_problems(db, current_user.id)


# ============================================================================
# 5️⃣ GET PROBLEM DETAIL (GET /problems/{problem_id})
# ============================================================================

@router.get(
    "/{problem_id}",
    response_model=ProblemDetailResponse,
    summary="Get problem details",
    description="USER + PROBLEM_SETTER - Get full problem with test cases"
)
async def get_problem_detail(
    problem_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full problem details with test cases.
    
    Behavior:
        - USER: See only sample test cases
        - PROBLEM_SETTER (creator): See all test cases
        - Both: See is_solved status
    
    Parameters:
        - problem_id: Problem ID to retrieve
    """
    return ProblemService.get_problem_detail(db, problem_id, current_user.id)


# ============================================================================
# 6️⃣ ADD TEST CASE (POST /problems/{problem_id}/test-cases)
# ============================================================================

@router.post(
    "/{problem_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case",
    description="PROBLEM_SETTER only - Add a test case to a problem",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def add_test_case(
    problem_id: int,
    test_case: TestCaseCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a test case to a problem (problem creator only).
    
    Parameters:
        - problem_id: Problem ID to add test case to
        - test_case: Test case data (input_data, expected_output, is_sample)
    """
    return TestCaseService.create_test_case(db, problem_id, test_case, current_user.id)


# ============================================================================
# 7️⃣ DELETE TEST CASE (DELETE /problems/test-cases/{test_case_id})
# ============================================================================

@router.delete(
    "/test-cases/{test_case_id}",
    response_model=MessageResponse,
    summary="Delete a test case",
    description="PROBLEM_SETTER only - Delete a test case from a problem",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def delete_test_case(
    test_case_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a test case (problem creator only).
    
    Parameters:
        - test_case_id: Test case ID to delete
    """
    return TestCaseService.delete_test_case(db, test_case_id, current_user.id)


# ============================================================================
# 7️⃣B UPDATE TEST CASE (PUT /problems/test-cases/{test_case_id})
# ============================================================================

@router.put(
    "/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update a test case",
    description="PROBLEM_SETTER only - Update a test case in a problem",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def update_test_case(
    test_case_id: int,
    test_case_update: TestCaseUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a test case (problem creator only).
    
    Parameters:
        - test_case_id: Test case ID to update
        - test_case_update: Test case data to update (input_data, expected_output, is_sample)
    """
    return TestCaseService.update_test_case(db, test_case_id, test_case_update, current_user.id)


# ============================================================================
# 8️⃣ UPLOAD EDITORIAL PDF (POST /problems/{problem_id}/editorial)
# ============================================================================

@router.post(
    "/{problem_id}/editorial",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload editorial PDF for a problem",
    description="PROBLEM_SETTER only - Upload editorial PDF solution for a problem",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def upload_editorial(
    problem_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an editorial PDF for a problem (problem creator only).
    
    Parameters:
        - problem_id: Problem ID to attach editorial to
        - file: PDF file to upload
    
    Returns:
        - Success message with editorial URL
    """
    # Verify file is PDF
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content
    content = await file.read()
    
    # Upload to Cloudinary
    try:
        result = await upload_pdf_to_cloudinary(content, file.filename)
        pdf_url = result["url"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {str(e)}"
        )
    
    # Update problem with editorial URL
    return ProblemService.update_editorial(db, problem_id, pdf_url, current_user.id)


# ============================================================================
# 9️⃣ DELETE EDITORIAL PDF (DELETE /problems/{problem_id}/editorial)
# ============================================================================

@router.delete(
    "/{problem_id}/editorial",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete editorial PDF for a problem",
    description="PROBLEM_SETTER only - Delete editorial PDF solution for a problem",
    dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))]
)
async def delete_editorial(
    problem_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an editorial PDF for a problem (problem creator only).
    
    Parameters:
        - problem_id: Problem ID to delete editorial from
    
    Returns:
        - Success message
    """
    return ProblemService.delete_editorial(db, problem_id, current_user.id)

