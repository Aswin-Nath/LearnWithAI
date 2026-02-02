from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.logger import get_logger
from app.dependencies.auth import get_current_user
from app.models.models import User, Problem
from app.schemas.custom_problem import GenerateProblemRequest, CustomProblemResponse
from app.roadmap.simple_generator import generate_custom_problem_content

router = APIRouter(prefix="/custom-problems", tags=["Custom Problems"])
logger = get_logger(__name__)

from app.crud.problem import create_test_case

@router.post("/generate", response_model=CustomProblemResponse)
async def generate_problem(
    request: GenerateProblemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a new custom problem based on topic/query and saves it to DB as a Problem.
    """
    logger.info(f"User {current_user.id} requesting custom problem: {request.topics}")
    
    # 1. Call LLM to generate content AND executable test cases
    generation_result = generate_custom_problem_content(
        topics=request.topics,
        user_query=request.user_query,
        difficulty=request.difficulty
    )
    
    content = generation_result.content
    
    # 2. Save to DB as a Problem
    new_problem = Problem(
        created_by=current_user.id,
        title=content.title,
        description=content.description_markdown,
        constraints=content.constraints,
        difficulty=request.difficulty,
        is_custom=True,
        generation_topic=request.topics,
        generation_query=request.user_query,
        editorial_markdown=content.editorial_markdown,
        canonical_code=content.canonical_code
    )
    
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    
    # 3. Save Generated Test Cases
    if generation_result.test_cases:
        logger.info(f"Saving {len(generation_result.test_cases)} test cases for problem {new_problem.id}")
        for idx, tc in enumerate(generation_result.test_cases):
            create_test_case(
                db=db,
                problem_id=new_problem.id,
                input_data=tc.input,
                expected_output=tc.output,
                is_sample=(idx == 0) # Make the first one a sample for UI visibility
            )
    
    return new_problem

@router.get("/", response_model=List[CustomProblemResponse])
async def list_my_custom_problems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all custom problems created by the current user.
    """
    problems = db.query(Problem).filter(
        Problem.created_by == current_user.id,
        Problem.is_custom == True
    ).order_by(Problem.created_at.desc()).all()
    
    return problems

@router.get("/{problem_id}", response_model=CustomProblemResponse)
async def get_custom_problem_detail(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single custom problem by ID (owner only).
    """
    problem = db.query(Problem).filter(
        Problem.id == problem_id,
        Problem.created_by == current_user.id,
        Problem.is_custom == True
    ).first()
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom problem not found or access denied"
        )
        
    return problem

@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a custom problem (Owner only).
    """
    problem = db.query(Problem).filter(
        Problem.id == problem_id,
        Problem.created_by == current_user.id,
        Problem.is_custom == True
    ).first()
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found or unauthorized"
        )
        
    db.delete(problem)
    db.commit()
    return None
