"""
Chat/Tutoring API endpoint - Uses LangGraph for context-aware AI responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from app.core.database import get_db
from app.models.models import Problem
from app.ai.run import run_graph
from app.services.chat import ChatService
from app.dependencies.auth import get_current_user
from sqlalchemy import text
from app.core.logger import get_logger

logger=get_logger("chat_route")

router = APIRouter(prefix="/chat", tags=["CHAT"])


def get_problem_by_id(db: Session, problem_id: int):
    result = db.execute(
        text("""
            SELECT 
                id, title, description, constraints,
                difficulty, time_limit_ms
            FROM problems
            WHERE id = :pid
        """),
        {"pid": problem_id}
    )
    row = result.fetchone()
    if not row:
        return None

    test_cases = db.execute(
        text("""
            SELECT input_data, expected_output
            FROM test_cases
            WHERE problem_id = :pid
              AND is_sample = true
            ORDER BY id
            LIMIT 3
        """),
        {"pid": problem_id}
    ).fetchall()

    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "constraints": row.constraints,
        "difficulty": row.difficulty,
        "time_limit": row.time_limit_ms,
        "sample_test_cases": [
            {"input": tc.input_data, "expected_output": tc.expected_output}
            for tc in test_cases
        ]
    }

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
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Chat with AI tutor about a problem using LangGraph.
    
    Supports 4 intents (auto-classified):
    1. how_to_solve_this - General approach guidance
    2. why_my_code_failed - Debug help for wrong answers
    3. clarification_request - Ask about problem statement
    4. general_concept_help - Standalone programming concepts
    
    Flow:
    1. Fetch conversation history from DB
    2. Pass to graph as input (no DB operations in nodes)
    3. Get AI response
    4. Save both user and AI messages to DB
    
    Args:
        request: Chat request with problem_id, code, query
        db: Database session
        current_user: Authenticated user from dependency
    
    Returns:
        AI response answer with auto-classified intent
    
    Raises:
        HTTPException 404: Problem not found
    """
    
    user_id = current_user.id
    logger.info(f"[ENDPOINT] POST /chat/ask - problem_id={request.problem_id}, user_id={user_id}")

    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    problem_data = get_problem_by_id(db, request.problem_id)
    
    try:
        previous_chat_messages = ChatService.get_conversation_history(
            db=db,
            user_id=user_id,
            problem_id=request.problem_id,
            limit=10
        )
        
        previous_messages = []
        for msg in previous_chat_messages:
            if msg.role == "user":
                previous_messages.append(HumanMessage(content=msg.content))
            else:
                previous_messages.append(AIMessage(content=msg.content))
        
        logger.info(f"[ENDPOINT] ✓ Loaded {len(previous_messages)} previous messages from DB")
    except Exception as e:
        logger.warning(f"[ENDPOINT]  Failed to fetch chat history: {str(e)}")
        previous_messages = []
    
    graph_input = {
        "user_query": request.user_query,
        "user_code": request.user_code,
        "problem_id": request.problem_id,
        "problem": problem_data,
        "previous_messages": previous_messages
    }

    result = run_graph(graph_input)
    logger.debug(
        f"[ENDPOINT] Result - answer_len={len(result.get('answer', ''))}, "
        f"intent={result.get('user_intent', 'unknown')}"
    )
    
    try:
        ChatService.insert_conversation_pair(
            db=db,
            user_id=user_id,
            problem_id=request.problem_id,
            user_content=request.user_query,
            ai_content=result.get("answer", "Unable to process your query")
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Failed to save conversation: {str(e)}")
    
    return ChatResponse(
        answer=result.get("answer", "Unable to process your query"),
        intent=result.get("intent", "unknown"),
        problem_id=request.problem_id
    )
        
