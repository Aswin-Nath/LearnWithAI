from typing import TypedDict, Optional, NotRequired, Annotated, List,Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class InputState(TypedDict):
    user_query: NotRequired[Optional[str]]
    user_code: NotRequired[Optional[str]]
    problem_id: int
    problem: NotRequired[dict]
    user_intent: NotRequired[Optional[str]]
    previous_messages: NotRequired[Optional[List[BaseMessage]]]  # NEW: Passed from API

class GraphState(TypedDict):
    user_intent: str
    user_query: str
    user_code: str
    problem_id: int
    problem: Optional[dict]
    sample_test_cases: Optional[List[dict]]
    answer: str
    messages: Annotated[List[BaseMessage], add_messages]
    retrieved_chunks: NotRequired[List[dict]]
    filtered_chunks: NotRequired[List[dict]]
    prompt_text: NotRequired[str]
    retrieval_k: NotRequired[int]
    sections: NotRequired[List[str]]

class OutputState(TypedDict):
    answer: str
    intent:str

class IntentDecision(BaseModel):
    intent: Literal[
        "how_to_solve_this",
        "why_my_code_failed",
        "clarification_request",
        "general_concept_help"
    ]
    confidence: float = Field(..., ge=0, le=1)