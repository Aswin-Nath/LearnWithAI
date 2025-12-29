"""
Chat/Tutoring API endpoint - Uses LangGraph for context-aware AI responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import Problem

router = APIRouter(prefix="/chat", tags=["CHAT"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request with intent selection."""
    problem_id: int
    user_code: str
    user_query: str
    intent: str  # One of: how_to_solve_this, why_my_code_failed, explain_my_code, validate_my_approach, clarification_request


class ChatResponse(BaseModel):
    """Chat response from AI tutor."""
    answer: str
    intent: str
    problem_id: int


# ============================================================================
# POST /chat/ask - Send message to AI tutor
# ============================================================================

@router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_tutor(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI tutor about a problem using LangGraph.
    
    Supports 5 intents:
    1. how_to_solve_this - General approach guidance
    2. why_my_code_failed - Debug help for wrong answers
    3. explain_my_code - Understand your solution
    4. validate_my_approach - Verify approach before coding
    5. clarification_request - Ask about problem statement
    
    Args:
        request: Chat request with problem_id, code, query, intent
        current_user: Authenticated user
        db: Database session
    
    Returns:
        AI response answer
    
    Raises:
        HTTPException 404: Problem not found
        HTTPException 400: Invalid intent
    """
    # Validate intent
    valid_intents = {
        "how_to_solve_this",
        "why_my_code_failed",
        "explain_my_code",
        "validate_my_approach",
        "clarification_request"
    }
    
    if request.intent not in valid_intents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid intent. Must be one of: {', '.join(valid_intents)}"
        )
    
    # Verify problem exists
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    try:
        # Import LangGraph here to avoid import issues
        from app.graphs.main.LearnWithAI_ import run_graph
        
        # Map intent to LangGraph format
        intent_mapping = {
            "how_to_solve_this": "how_to_solve_this",
            "why_my_code_failed": "why_my_code_failed",
            "explain_my_code": "explain_my_code",
            "validate_my_approach": "validate_my_approach",
            "clarification_request": "clarification_request"
        }
        
        graph_intent = intent_mapping[request.intent]
        
        # Build input for graph
        graph_input = {
            "user_intent": graph_intent,
            "user_query": request.user_query,
            "user_code": request.user_code,
            "problem_id": request.problem_id,
        }
        
        # Run LangGraph to get response
        result = run_graph(graph_input)
        
        return ChatResponse(
            answer=result.get("answer", "Unable to process your query"),
            intent=request.intent,
            problem_id=request.problem_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )
