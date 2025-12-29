import os
import sys
from typing import TypedDict, Optional, Literal, NotRequired, Annotated, List

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, text

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from handlers_with_rag import (
    handle_why_my_code_failed_with_rag,
    handle_how_to_solve_this_with_rag,
    handle_explain_my_code_with_rag,
    handle_validate_my_approach_with_rag,
    handle_clarification_request_with_rag,
)

load_dotenv()

# 1. SETUP
GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(api_key=GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)

url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="aswinnath@123",
    host="localhost",
    port=1024,
    database="ticket_raiser",
)
engine = create_engine(url)

def get_problem_by_id(problem_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, title, description FROM problems WHERE id = :pid"),
            {"pid": problem_id}
        )
        row = result.fetchone()
        if not row: return None
        return {"id": row.id, "title": row.title, "description": row.description}

# 2. STATE DEFINITIONS
class InputState(TypedDict):
    user_intent: Literal[
        "how_to_solve_this", "why_my_code_failed", "explain_my_code", 
        "validate_my_approach", "clarification_request"
    ]
    user_query: NotRequired[Optional[str]]
    user_code: NotRequired[Optional[str]]
    problem_id: int

class GraphState(TypedDict):
    user_intent: str
    user_query: str
    user_code: str
    problem_id: int
    problem: Optional[dict]
    answer: str
    is_valid: bool
    fallback_message: str
    violation_type: Literal[
        "solution_begging",
        "no_input",
        "off_topic",
        "wrong_button",
        "ambiguous",
        "ok"
    ]
    # NEW: The Memory Log
    messages: Annotated[List[BaseMessage], add_messages]

class OutputState(TypedDict):
    answer: str

# Defined for the parser to know the schema
class GuardDecision(BaseModel):
    is_valid: bool = Field(..., description="true if valid, false if blocked")
    fallback_message: str = Field(..., description="Helpful message if blocked, empty string if valid")
    violation_type: Literal[
        "solution_begging",
        "no_input",
        "off_topic",
        "wrong_button",
        "ambiguous",
        "ok"
    ] = Field(default="ok", description="Type of violation for analytics")



# 3. SETUP NODE
def setup_node(state: InputState) -> GraphState:
    """
    Initialize the graph with fresh data from the user's input.
    Creates a complete GraphState with all required fields initialized.
    """
    problem = get_problem_by_id(state["problem_id"])
    
    # Get input values
    user_intent = state.get("user_intent") or ""
    user_query = state.get("user_query") or ""
    user_code = state.get("user_code") or ""
    problem_id = state.get("problem_id", 0)
    
    # Clean up values by stripping whitespace and handling invalid types
    if not isinstance(user_intent, str) or user_intent.isspace():
        user_intent = ""
    else:
        user_intent = user_intent.strip()
    
    if not isinstance(user_query, str) or user_query.isspace():
        user_query = ""
    else:
        user_query = user_query.strip()
    
    if not isinstance(user_code, str) or user_code.isspace():
        user_code = ""
    else:
        user_code = user_code.strip()
    
    # Create and return a fresh state with all fields initialized
    return {
        "user_intent": user_intent,
        "user_query": user_query,
        "user_code": user_code,
        "problem_id": problem_id,
        "problem": problem,
        "answer": "",
        "is_valid": True,
        "fallback_message": "",
        "violation_type": "ok",
        # NEW: Append user input to history
        "messages": [HumanMessage(content=user_query)]
    }

# 4. GLOBAL GUARDRAIL CONSTANTS
GLOBAL_OFF_TOPIC = (
    "I can only help with this coding problem. "
    "Please ask about the problem, your code, or your approach."
)

AMBIGUOUS_CLARIFY = (
    "Could you clarify what you mean? "
    "For example, are you asking about specific constraints, data properties, or guarantees?"
)

# 5. LLM GUARDRAILS (WITH STRICT FALLBACKS)
def run_guard_llm(system_prompt: str, user_input: str) -> dict:
    structured_llm = llm.with_structured_output(GuardDecision)
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_input)])
    try:
        result: GuardDecision = (prompt | structured_llm).invoke({})
        return {
            "is_valid": result.is_valid,
            "fallback_message": result.fallback_message,
            "violation_type": result.violation_type
        }
    except Exception:
        return {
            "is_valid": False,
            "fallback_message": "I couldn't interpret that clearly. Could you rephrase?",
            "violation_type": "ambiguous"
        }

def guard_how_to_solve(state: GraphState) -> GraphState:
    # Check if user provided a query
    if not state['user_query'] or not state['user_query'].strip():
        return {**state, "is_valid": False, "fallback_message": "Could you clarify what you'd like help with?", "violation_type": "no_input"}
    
    # Use AI to validate the request - be lenient since user clicked Hint button
    prompt = """
You are a lenient validator for "Get Hint" requests on a coding problem.

User already clicked the "Get Hint" button, so assume they want help understanding the problem/approach.

IGNORE casual language, mild profanity, or frustrated tone - focus on whether they're asking for coding help.

ACCEPT (is_valid=true) if user is asking about:
- Approach, strategy, or hints for solving
- How to think about the problem
- What concepts apply
- Any question about the problem or their thinking process
- Even if phrased casually like "why this shit failing?" or similar things 

ONLY REJECT (is_valid=false) if user explicitly asks for:
- Complete solution code ("give me the code", "write the solution for me")
- Or completely off-topic garbage unrelated to programming/this problem

Default: ACCEPT. Be generous. Ignore tone/language - focus on intent.

If INVALID:
- violation_type = "solution_begging" (if asking for code) or "off_topic" (if irrelevant)
- fallback_message = "I can only help with this coding problem. Please ask about the problem or your approach."

If VALID:
- is_valid = true
- fallback_message = ""
- violation_type = "ok"
"""

    res = run_guard_llm(prompt, f"Query: {state['user_query']}")
    return {**state, **res}

def guard_why_failed(state: GraphState) -> GraphState:
    # Check if code was provided
    code = state['user_code'].strip()
    
    if not code:
        return {**state, "is_valid": False, "fallback_message": "Please paste your code so I can help debug", "violation_type": "no_input"}
    
    # Validate that code is meaningful (not just a few characters)
    lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    is_substantial = len(lines) > 1 or (len(lines) == 1 and len(lines[0]) > 15)
    
    if not is_substantial:
        return {**state, "is_valid": False, "fallback_message": "Please paste your code so I can help debug", "violation_type": "no_input"}
    
    # Use AI to validate the debug request
    prompt = """
Validate if this is a valid debug/analysis request.

Code is substantial. User is asking about it.

IGNORE casual language or frustration - focus on whether they're asking for debugging help.

VALID QUERIES (Accept all of these):
- Error messages: "Stack overflow", "IndexError", "TLE", "Memory error", "Runtime error"
- Analysis: "Why does this fail?", "What's wrong?", "Why wrong answer?"
- Casual: "why this shit failing?", "how does this work?", "wtf is wrong?"
- Performance: "Too slow", "Memory limit exceeded"
- ANY question about their code: "How does this fail?", "Why doesn't this work?"

VALID because code is present and they're asking about it.

INVALID only if:
- "just solve it" or "give me answer" → violation_type = solution_begging
- Completely off-topic and unrelated to code ("what is life?") → violation_type = off_topic

ASSUME GOOD FAITH: User provided code to debug.

Output:
- is_valid: true or false
- fallback_message: (empty if valid; explain why if invalid)
- violation_type: "ok", "solution_begging", or "off_topic"
"""

    input_text = f"Query: {state['user_query']}"
    res = run_guard_llm(prompt, input_text)
    return {**state, **res}

def guard_explain_code(state: GraphState) -> GraphState:
    # Check if code was provided
    code = state['user_code'].strip()
    query = state['user_query'].strip()
    
    if not code or len(code) == 0:
        return {**state, "is_valid": False, "fallback_message": "Please paste the code you'd like me to explain", "violation_type": "no_input"}
    
    # Reject very short/trivial code
    if len(code) <= 2 or code in ['x', 'y', 'n', 'i', 'j', 'a', 'b']:
        return {**state, "is_valid": False, "fallback_message": "Please paste the code you'd like me to explain", "violation_type": "no_input"}
    
    # If user provided a query, validate it's asking about code explanation
    if query:
        prompt = """
You are a validator for "Explain Code" requests.

User pasted code and is asking a question about it.

IGNORE casual language, slang, or frustrated tone - focus on the actual intent.

VALID (is_valid=true) if user is asking:
- Explanation of how code works
- What specific lines/functions do
- How this approach solves the problem
- Why specific logic is used
- Time/space complexity
- How to optimize code
- Casual versions like "explain this", "what does this do?", "explain the code that i have given"

INVALID (is_valid=false) if user is:
- Asking clarification about PROBLEM itself (ask in Clarify button) - e.g. "what does the constraint mean?"
- Asking about problem format/input (ask in Clarify button) - e.g. "what is the input format?"
- Asking definitions or theory unrelated to their code (ask in Clarify button)
- Asking off-topic question unrelated to their code
- Asking to debug/fix the code (ask in Debug button)

Be lenient with the query. If it's clearly asking for code explanation (even casually), accept it.
Be strict ONLY if it's asking about the PROBLEM itself rather than the code.

Output:
- is_valid: true or false
- fallback_message: "For problem clarification, use the Clarify button" (if clarification) or "Please ask about your code" (if off-topic)
- violation_type: "wrong_button" (if clarification) or "off_topic" (if unrelated)
"""
        res = run_guard_llm(prompt, f"Code: {code}\nQuery: {query}")
        return {**state, **res}
    
    # Code alone is enough - user can explain without a specific question
    return {**state, "is_valid": True, "fallback_message": "", "violation_type": "ok"}

def guard_validate_approach(state: GraphState) -> GraphState:
    query = state['user_query'].strip()
    code = state['user_code'].strip()
    
    # Check if user provided either a query or code
    if not query and not code:
        return {**state, "is_valid": False, "fallback_message": "Please share your approach idea or code", "violation_type": "no_input"}
    
    # If code is provided, we can validate the approach from it
    if code and not query:
        return {**state, "is_valid": True, "fallback_message": "", "violation_type": "ok"}
    
    prompt = """
You are a lenient validator for approach validation requests.

User clicked "Validate" button to check if their idea makes sense for the problem.

ACCEPT (is_valid=true) if user is:
- Proposing an approach ("Can I use...?", "Should I...?")
- Classifying the problem type ("Is this a Graph problem?", "Is this DP?")
- Asking about feasibility of an idea
- Asking about complexity/efficiency
- Any question that shows they're thinking about the problem

ONLY REJECT (is_valid=false) if user:
- Explicitly asks for solution code
- Asks for hints (that's the Hint button)
- Provides no input at all (no_input)
- Completely off-topic

Default: ACCEPT. User clicked Validate button, so accept their approach questions.

If INVALID:
- is_valid = false
- violation_type = "no_input" (if empty), "wrong_button" (if asking for hints), or "solution_begging" (if asking for code)

If VALID:
- is_valid = true
- fallback_message = ""
- violation_type = "ok"
"""


    res = run_guard_llm(prompt, f"Query: {state['user_query']}")
    return {**state, **res}

def guard_clarification(state: GraphState) -> GraphState:
    # Check if user asked a question
    if not state['user_query'] or not state['user_query'].strip():
        return {**state, "is_valid": False, "fallback_message": "Please ask a question about the problem statement.", "violation_type": "no_input"}
    
    # Use AI to validate the clarification request
    prompt = """
You are a lenient validator for problem clarification requests.

User clicked the "Clarify" button to understand the problem better.

ACCEPT (is_valid=true) if user is asking about:
- Problem details, constraints, data properties
- Input/output format
- What terms mean
- Examples or test cases
- Any aspect of understanding the problem statement

ONLY REJECT (is_valid=false) if user explicitly asks for:
- How to solve (that's the Hint button)
- Algorithm or approach advice (that's Validate button)
- Complete solution (that's never allowed)
- Completely off-topic nonsense unrelated to the problem

Default: ACCEPT. User clicked Clarify for a reason.

If INVALID:
- violation_type = "wrong_button" (if asking how to solve)
- fallback_message = "For solution guidance, use the Hint button. Here, I can clarify problem details."

If VALID:
- is_valid = true
- fallback_message = ""
- violation_type = "ok"
"""

    res = run_guard_llm(prompt, f"Query: {state['user_query']}")
    return {**state, **res}

# 6. HANDLERS 
def handle_how_to_solve_this(state: GraphState):
    return  handle_how_to_solve_this_with_rag(state)

def handle_why_my_code_failed(state: GraphState):
    return handle_why_my_code_failed_with_rag(state)

def handle_explain_my_code(state: GraphState):
    return handle_explain_my_code_with_rag(state)

def handle_validate_my_approach(state: GraphState):
    return handle_validate_my_approach_with_rag(state)

def handle_clarification_request(state: GraphState):
    return handle_clarification_request_with_rag(state)

def handle_fallback(state: GraphState) -> GraphState:
    return {**state, "answer": state["fallback_message"]}

# 7. GRAPH BUILD
build = StateGraph(GraphState, input_schema=InputState, output_schema=OutputState)

build.add_node("setup", setup_node)

# Guards
build.add_node("guard_how_to_solve", guard_how_to_solve)
build.add_node("guard_why_failed", guard_why_failed)
build.add_node("guard_explain_code", guard_explain_code)
build.add_node("guard_validate", guard_validate_approach)
build.add_node("guard_clarification", guard_clarification)

# Handlers
build.add_node("handle_how_to_solve", handle_how_to_solve_this)
build.add_node("handle_why_failed", handle_why_my_code_failed)
build.add_node("handle_explain", handle_explain_my_code)
build.add_node("handle_validate", handle_validate_my_approach)
build.add_node("handle_clarification", handle_clarification_request)
build.add_node("handle_fallback", handle_fallback)

build.add_edge(START, "setup")

INTENT_TO_GUARD = {
    "how_to_solve_this": "guard_how_to_solve",
    "why_my_code_failed": "guard_why_failed",
    "explain_my_code": "guard_explain_code",
    "validate_my_approach": "guard_validate",
    "clarification_request": "guard_clarification",
}

def route_to_guard(state: GraphState):
    return state["user_intent"]

build.add_conditional_edges("setup", route_to_guard, INTENT_TO_GUARD)

def check_validity(state: GraphState):
    return "proceed" if state["is_valid"] else "fallback"

guards_to_handlers = {
    "guard_how_to_solve": "handle_how_to_solve",
    "guard_why_failed": "handle_why_failed",
    "guard_explain_code": "handle_explain",
    "guard_validate": "handle_validate",
    "guard_clarification": "handle_clarification"
}

for guard, handler in guards_to_handlers.items():
    build.add_conditional_edges(
        guard,
        check_validity,
        {"proceed": handler, "fallback": "handle_fallback"}
    )
    build.add_edge(handler, END)

build.add_edge("handle_fallback", END)

# 8. COMPILE GRAPH
# LangGraph uses POSTGRES_URI environment variable for built-in persistence
# DB_URI = "postgresql://postgres:aswinnath@123@localhost:1024/ticket_raiser"
# from langgraph.checkpoint.postgres import PostgresSaver
# from psycopg_pool import ConnectionPool
# connection_pool = ConnectionPool(
#     conninfo=DB_URI,
#     max_size=5,
#     timeout=30
# )

# checkpointer = PostgresSaver(connection_pool)

# graph = build.compile(checkpointer=checkpointer)

graph=build.compile()


# ============================================================================
# 9. RUN GRAPH FUNCTION - Entry point for chat endpoint
# ============================================================================

def run_graph(input_dict: dict) -> dict:
    """
    Run the LangGraph and return the response.
    
    Args:
        input_dict: Dict with keys:
            - user_intent: One of the 5 intents
            - user_query: User's question/message
            - user_code: User's code
            - problem_id: Problem ID
    
    Returns:
        Dict with 'answer' key containing the AI response
    """
    try:
        # Invoke the graph with the input
        result = graph.invoke(input_dict)
        
        # Extract the answer from the result
        answer = result.get("answer", "I couldn't generate a response. Please try again.")
        
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}