from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.dependencies.auth import get_current_user
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
from app.utils.md_upload_util import upload_markdown_editorial
from app.utils.ingestion_pdf import ingest_pdf_from_file
import tempfile
import os

router = APIRouter(prefix="/problems", tags=["PROBLEMS"])



@router.post(
    "",
    response_model=ProblemCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new problem",
    description="Create a new problem with title, description, constraints, and difficulty",
    dependencies=[Depends(get_current_user)]
)
async def create_problem(
    problem: ProblemCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new problem.
    
    Returns:
        - Problem ID
    """
    return ProblemService.create_problem(db, problem, current_user.id)



@router.put(
    "/{problem_id}",
    response_model=ProblemDetailResponse,
    summary="Update a problem",
    description="Update problem details",
    dependencies=[Depends(get_current_user)]
)
async def update_problem(
    problem_id: int,
    problem_update: ProblemUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a problem.
    
    Parameters:
        - problem_id: Problem ID to update
        - problem_update: Fields to update (title, description, constraints, difficulty)
    
    Returns:
        - Updated problem with full details
    """
    return ProblemService.update_problem(db, problem_id, problem_update, current_user.id)



@router.delete(
    "/{problem_id}",
    response_model=MessageResponse,
    summary="Delete a problem",
    description="Delete a problem if no submissions exist",
    dependencies=[Depends(get_current_user)]
)
async def delete_problem(
    problem_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a problem.
    
    Rule: Only allowed if no submissions exist for this problem.
    
    Parameters:
        - problem_id: Problem ID to delete
    """
    return ProblemService.delete_problem(db, problem_id, current_user.id)



@router.get(
    "",
    response_model=List[ProblemListResponse],
    summary="List all problems",
    description="Get minimal problem list with solved status"
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



@router.post(
    "/{problem_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case",
    description="Add a test case to a problem",
    dependencies=[Depends(get_current_user)]
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



@router.delete(
    "/test-cases/{test_case_id}",
    response_model=MessageResponse,
    summary="Delete a test case",
    description="Delete a test case from a problem",
    dependencies=[Depends(get_current_user)]
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



@router.put(
    "/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update a test case",
    description="Update a test case in a problem",
    dependencies=[Depends(get_current_user)]
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







@router.post(
    "/{problem_id}/editorial/pdf",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload PDF editorial, store in Cloudinary, and ingest into knowledge base",
    description="Upload a PDF file, save it to Cloudinary, and ingest it into Chroma for RAG",
    dependencies=[Depends(get_current_user)]
)
async def upload_and_ingest_pdf(
    problem_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF file, store in Cloudinary, and ingest into Chroma vector DB.
    
    This endpoint:
    1. Validates the file is a PDF
    2. Uploads it to Cloudinary
    3. Saves the Cloudinary URL to problem editorial_url_link
    4. Saves PDF temporarily
    5. Converts PDF to Markdown
    6. Fixes markdown headers
    7. Splits by headers
    8. Uploads chunks to Chroma with problem_id metadata
    
    Parameters:
        - problem_id: Problem ID to attach PDF to
        - file: PDF file to upload
    
    Returns:
        - Success message with PDF URL and chunk count
    """
    # Verify file is PDF
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content
    content = await file.read()
    
    # Step 1: Upload to Cloudinary
    try:
        result = await upload_pdf_to_cloudinary(content, file.filename)
        pdf_url = result["url"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF to Cloudinary: {str(e)}"
        )
    
    # Step 2: Save PDF URL to problem editorial_url_link
    try:
        editorial_result = ProblemService.update_editorial(db, problem_id, pdf_url, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save editorial link: {str(e)}"
        )
    
    # Step 3: Ingest PDF into Chroma for RAG
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_file_path, 'wb') as f:
            f.write(content)
        # Ingest PDF into Chroma
        ingest_result = ingest_pdf_from_file(temp_file_path, problem_id)
        chunks_count = ingest_result.get("chunks_uploaded", 0)
        return {
            "message": f"PDF uploaded successfully. Stored in knowledge base with {chunks_count} indexed sections. View at: {pdf_url}"
        }
        
    except Exception as e:
        # PDF was uploaded to Cloudinary but ingestion failed - still return success
        return {
            "message": f"PDF uploaded successfully to Cloudinary, but indexing had issues. URL: {pdf_url}"
        }
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            os.rmdir(temp_dir)
        except:
            pass

