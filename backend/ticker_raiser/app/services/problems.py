from sqlalchemy.orm import Session
from app.crud.problem import (
    create_problem as crud_create_problem,
    get_problem_by_id,
    get_all_problems,
    update_problem as crud_update_problem,
    delete_problem as crud_delete_problem,
    is_problem_solved_by_user,
    create_test_case as crud_create_test_case,
    get_test_case_by_id,
    get_test_cases_by_problem,
    get_sample_test_cases_by_problem,
    delete_test_case as crud_delete_test_case,
    verify_problem_owner,
    verify_test_case_owner,
)
from app.schemas.problem import (
    ProblemCreate,
    ProblemUpdate,
    ProblemListResponse,
    ProblemDetailResponse,
    ProblemCreateResponse,
    TestCaseCreate,
    TestCaseResponse,
)
from app.models.models import Problem, TestCase
from typing import List, Optional
from fastapi import HTTPException, status


# Problem Service Operations

class ProblemService:
    """Service layer for problem operations"""

    @staticmethod
    def create_problem(db: Session, problem: ProblemCreate, creator_id: int) -> ProblemCreateResponse:
        """Create a new problem (PROBLEM_SETTER only)"""
        db_problem = crud_create_problem(db, problem, creator_id)
        return ProblemCreateResponse.model_validate(db_problem)

    @staticmethod
    def list_problems(db: Session, current_user_id: int) -> List[ProblemListResponse]:
        """
        List all problems with is_solved status.
        is_solved is computed for the current user.
        """
        problems = get_all_problems(db)
        result = []
        
        for problem in problems:
            is_solved = is_problem_solved_by_user(db, problem.id, current_user_id)
            result.append(
                ProblemListResponse(
                    id=problem.id,
                    title=problem.title,
                    difficulty=problem.difficulty,
                    time_limit_ms=problem.time_limit_ms,
                    is_solved=is_solved,
                    editorial_url_link=problem.editorial_url_link,
                    created_at=problem.created_at
                )
            )
        
        return result

    @staticmethod
    def get_problem_detail(db: Session, problem_id: int, current_user_id: int) -> ProblemDetailResponse:
        """
        Get problem details with test cases.
        - USER: only sample test cases
        - PROBLEM_SETTER (owner): all test cases
        """
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Determine test cases to return
        is_owner = problem.created_by == current_user_id
        if is_owner:
            test_cases = get_test_cases_by_problem(db, problem_id)
        else:
            test_cases = get_sample_test_cases_by_problem(db, problem_id)
        
        # Check if user has solved this problem
        is_solved = is_problem_solved_by_user(db, problem_id, current_user_id)
        
        test_case_responses = [TestCaseResponse.model_validate(tc) for tc in test_cases]
        
        return ProblemDetailResponse(
            id=problem.id,
            title=problem.title,
            description=problem.description,
            constraints=problem.constraints,
            difficulty=problem.difficulty,
            time_limit_ms=problem.time_limit_ms,
            is_solved=is_solved,
            editorial_url_link=problem.editorial_url_link,
            test_cases=test_case_responses,
            created_at=problem.created_at
        )

    @staticmethod
    def update_problem(db: Session, problem_id: int, problem_update: ProblemUpdate, current_user_id: int) -> ProblemDetailResponse:
        """Update a problem (owner only)"""
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        if problem.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can update it"
            )
        
        updated_problem = crud_update_problem(db, problem_id, problem_update, current_user_id)
        
        is_solved = is_problem_solved_by_user(db, problem_id, current_user_id)
        test_cases = get_test_cases_by_problem(db, problem_id)
        test_case_responses = [TestCaseResponse.model_validate(tc) for tc in test_cases]
        
        return ProblemDetailResponse(
            id=updated_problem.id,
            title=updated_problem.title,
            description=updated_problem.description,
            constraints=updated_problem.constraints,
            difficulty=updated_problem.difficulty,
            time_limit_ms=updated_problem.time_limit_ms,
            is_solved=is_solved,
            editorial_url_link=updated_problem.editorial_url_link,
            test_cases=test_case_responses,
            created_at=updated_problem.created_at
        )

    @staticmethod
    def delete_problem(db: Session, problem_id: int, current_user_id: int) -> dict:
        """
        Delete a problem (owner only).
        Only allowed if no submissions exist.
        """
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        if problem.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can delete it"
            )
        
        success = crud_delete_problem(db, problem_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete problem with existing submissions"
            )
        
        return {"message": "Problem deleted successfully"}

    @staticmethod
    def update_editorial(db: Session, problem_id: int, editorial_url: str, current_user_id: int) -> dict:
        """Update problem editorial PDF URL (owner only)"""
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        if problem.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can upload editorial"
            )
        
        # Update the editorial_url_link in database
        problem.editorial_url_link = editorial_url
        db.commit()
        db.refresh(problem)
        
        return {"message": f"Editorial uploaded successfully", "editorial_url": editorial_url}

    @staticmethod
    def delete_editorial(db: Session, problem_id: int, current_user_id: int) -> dict:
        """Delete problem editorial PDF (owner only)"""
        from app.utils.pdf_upload_util import delete_pdf_from_cloudinary
        
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        if problem.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can delete editorial"
            )
        
        if not problem.editorial_url_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No editorial PDF found for this problem"
            )
        
        # Extract public_id from the URL
        # URL format: https://res.cloudinary.com/.../upload/v.../ticket_raiser/editorials/public_id
        try:
            public_id = problem.editorial_url_link.split("/v")[1].split("/", 1)[1]
            delete_pdf_from_cloudinary(public_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete PDF from Cloudinary: {str(e)}"
            )
        
        # Update the database to clear editorial URL
        problem.editorial_url_link = None
        db.commit()
        db.refresh(problem)
        
        return {"message": "Editorial PDF deleted successfully"}


# Test Case Service Operations

class TestCaseService:
    """Service layer for test case operations"""

    @staticmethod
    def create_test_case(
        db: Session,
        problem_id: int,
        test_case: TestCaseCreate,
        current_user_id: int
    ) -> TestCaseResponse:
        """Add a test case (PROBLEM_SETTER/owner only)"""
        problem = get_problem_by_id(db, problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        if problem.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can add test cases"
            )
        
        db_test_case = crud_create_test_case(
            db,
            problem_id,
            test_case.input_data,
            test_case.expected_output,
            test_case.is_sample
        )
        
        return TestCaseResponse.model_validate(db_test_case)

    @staticmethod
    def delete_test_case(db: Session, test_case_id: int, current_user_id: int) -> dict:
        """Delete a test case (problem owner only)"""
        
        if not verify_test_case_owner(db, test_case_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can delete test cases"
            )
        
        success = crud_delete_test_case(db, test_case_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete test case"
            )
        
        return {"message": "Test case deleted successfully"}

    @staticmethod
    def update_test_case(db: Session, test_case_id: int, test_case_update, current_user_id: int) -> TestCaseResponse:
        """Update a test case (problem owner only)"""
        
        if not verify_test_case_owner(db, test_case_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the problem creator can update test cases"
            )
        
        from app.crud.problem import update_test_case as crud_update_test_case
        
        db_test_case = crud_update_test_case(
            db,
            test_case_id,
            input_data=test_case_update.input_data,
            expected_output=test_case_update.expected_output,
            is_sample=test_case_update.is_sample
        )
        
        if not db_test_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found"
            )
        
        return TestCaseResponse.model_validate(db_test_case)
