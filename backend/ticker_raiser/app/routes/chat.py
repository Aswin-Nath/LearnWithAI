"""
Chat/Tutoring API endpoint - Uses LangGraph for context-aware AI responses.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import Problem
from app.graphs.LearnWithAI_ import run_graph
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/chat", tags=["CHAT"])

class ChatRequest(BaseModel):
    problem_id: int
    user_code: str
    user_query: str


class ChatResponse(BaseModel):
    answer: str
    intent: str
    problem_id: int


@router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_tutor(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with AI tutor about a problem using LangGraph.
    
    Supports 4 intents (auto-classified):
    1. how_to_solve_this - General approach guidance
    2. why_my_code_failed - Debug help for wrong answers
    3. clarification_request - Ask about problem statement
    4. general_concept_help - Standalone programming concepts
    
    Args:
        request: Chat request with problem_id, code, query
        db: Database session
    
    Returns:
        AI response answer with auto-classified intent
    
    Raises:
        HTTPException 404: Problem not found
    """
    
    logger.info(f"[ENDPOINT] POST /chat/ask - problem_id={request.problem_id}")

    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    
    graph_input = {
        "user_query": request.user_query,
        "user_code": request.user_code,
        "problem_id": request.problem_id,
    }
    
    result = run_graph(graph_input)
    logger.debug(f"[ENDPOINT] Result - answer_len={len(result.get('answer', ''))}, intent={result.get('user_intent', 'unknown')}")
    
    return ChatResponse(
        answer=result.get("answer", "Unable to process your query"),
        intent=result.get("intent", "unknown"),
        problem_id=request.problem_id
    )
        
