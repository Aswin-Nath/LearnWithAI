import os
import sys
import logging
from typing import TypedDict, Optional, Literal, NotRequired, Annotated, List
from urllib.parse import quote_plus
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from rag_layer import (
    build_prompt,
    retriever,
)
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(api_key=GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)


# STATE

class InputState(TypedDict):
    user_query: NotRequired[Optional[str]]
    user_code: NotRequired[Optional[str]]
    problem_id: int
    user_intent: NotRequired[Optional[str]]

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

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = quote_plus(os.getenv("POSTGRES_PASSWORD"))
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "1024")
DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
url = DATABASE_URL
engine = create_engine(url)

def estimate_tokens(text: str) -> int:
    """
    Rough token estimator.
    1 token ≈ 4 characters (safe heuristic).
    """
    return max(1, len(text) // 4)


def trim_messages_to_token_limit(
    messages: List[BaseMessage],
    max_tokens: int
) -> List[BaseMessage]:
    """
    Keeps the MOST RECENT messages within token budget.
    """
    trimmed: List[BaseMessage] = []
    used_tokens = 0

    # iterate from latest → oldest
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.content)
        if used_tokens + msg_tokens > max_tokens:
            break
        trimmed.append(msg)
        used_tokens += msg_tokens

    return list(reversed(trimmed))


def get_problem_by_id(problem_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id, 
                    title, 
                    description, 
                    constraints, 
                    difficulty, 
                    time_limit_ms
                FROM problems 
                WHERE id = :pid
            """),
            {"pid": problem_id}
        )
        row = result.fetchone()
        if not row:
            return None

        test_cases_result = conn.execute(
            text("""
                SELECT input_data, expected_output
                FROM test_cases
                WHERE problem_id = :pid
                  AND is_sample = true
                ORDER BY id
                LIMIT 3
            """),
            {"pid": problem_id}
        )

        sample_test_cases = [
            {"input": tc.input_data, "expected_output": tc.expected_output}
            for tc in test_cases_result.fetchall()
        ]
        return {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "constraints": row.constraints,
            "difficulty": row.difficulty,
            "time_limit": row.time_limit_ms,
            "sample_test_cases": sample_test_cases
        }

def get_previous_messages(
    user_id: int,
    problem_id: int,
    limit: int = 10
) -> List[BaseMessage]:
    """
    DEMO MODE:
    Fetch last N messages for a user-problem pair and convert
    them into LangChain message objects.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT role, content
                FROM chat_messages
                WHERE user_id = :uid
                  AND problem_id = :pid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {
                "uid": user_id,
                "pid": problem_id,
                "limit": limit
            }
        ).fetchall()

    messages: List[BaseMessage] = []

    for row in reversed(rows):
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))

    return messages

def filter_by_section(chunks: List[dict], allowed_sections: List[str]) -> List[dict]:
    """
    Filter retrieved chunks to only those matching allowed sections.
    
    Matching is fuzzy (substring match, case-insensitive) to handle
    variations like "Edge Cases" vs "Edge Cases & Common Pitfalls"
    
    Args:
        chunks: List of dicts with 'section' key
        allowed_sections: List of section keywords to keep
        
    Returns:
        Filtered list, sorted by distance (relevance)
    """
    filtered = []
    
    for chunk in chunks:
        section = chunk["section"].lower()
        if any(keyword.lower() in section for keyword in allowed_sections):
            filtered.append(chunk)
    
    filtered.sort(key=lambda x: x["distance"])
    return filtered

# NODES

def retrieve_and_filter(state: GraphState) -> dict:    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    user_code = state.get("user_code", "")
    intent = state["user_intent"]
    k = state.get("retrieval_k", 10)
    
    query_text = f"{user_query}\n\nCode:\n{user_code}" if user_code else user_query
    
    try:
        # RETRIEVE
        chunks = retriever.retrieve(problem_id=problem_id, query=query_text, k=k)
        
        # FILTER
        allowed_sections = state.get("sections")
        
        if not chunks or not allowed_sections:
            return {"filtered_chunks": []}
        
        filtered = filter_by_section(chunks, allowed_sections)
        
        # Limit based on intent
        if intent == "clarification_request":
            filtered = filtered[:2]
        
        return {"filtered_chunks": filtered}
        
    except Exception as e:
        logger.error(f"[RAG] ✗ Retrieval/Filter failed: {str(e)}", exc_info=True)
        return {"filtered_chunks": []}

def build_prompt_node(state: GraphState) -> dict:    
    intent = state["user_intent"]
    problem = state.get("problem", {})
    user_query = state["user_query"]
    user_code = state.get("user_code")
    context_chunks = state.get("filtered_chunks", [])
    messages = state.get("messages", [])
    samples = state.get("sample_test_cases", [])
    
    try:
        prompt_text = build_prompt(
            intent=intent,
            problem=problem,
            user_query=user_query,
            user_code=user_code,
            context_chunks=context_chunks,
            conversation_context=messages,
            sample_test_cases=samples
        )
        return {"prompt_text": prompt_text}
    except Exception as e:
        logger.error(f"[PROMPT] ✗ Prompt building failed: {str(e)}", exc_info=True)
        return {"prompt_text": ""}

def invoke_llm_node(state: GraphState) -> dict:    
    prompt_text = state.get("prompt_text", "")
    if not prompt_text:
        return {"answer": "Error: Empty prompt"}
    
    try:
        # Use message objects for role separation and tool compatibility
        response = llm.invoke([HumanMessage(content=prompt_text)])
        answer = response.content
        return {"answer": answer}
    except Exception as e:
        logger.error(f"[LLM] ✗ LLM invocation failed: {str(e)}", exc_info=True)
        return {"answer": f"Error generating response: {str(e)}"}



def general_concept_prompt(state: GraphState) -> dict:    
    user_query = state["user_query"]
    messages = state.get("messages", [])
    try:
        prompt_text = build_prompt(
            intent="general_concept_help",
            problem={}, 
            user_query=user_query,
            user_code=None, 
            context_chunks=[], 
            conversation_context=messages,
            sample_test_cases=None
        )
        return {"prompt_text": prompt_text}
    except Exception as e:
        logger.error(f"[GENERAL] ✗ Prompt building failed: {str(e)}", exc_info=True)
        return {"prompt_text": ""}

def general_concept_subgraph() -> StateGraph:
    graph = StateGraph(GraphState, output_nodes=["answer"])
    
    graph.add_node("build_prompt", general_concept_prompt)
    graph.add_node("invoke_llm", invoke_llm_node)
    
    graph.add_edge("build_prompt", "invoke_llm")
    graph.add_edge("invoke_llm", END)
    
    graph.set_entry_point("build_prompt")
    
    return graph.compile()

def rag_subgraph() -> StateGraph:
    graph = StateGraph(GraphState, output_nodes=["answer"])
    
    graph.add_node("retrieve_and_filter", retrieve_and_filter)
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("invoke_llm", invoke_llm_node)
    

    graph.add_edge("retrieve_and_filter", "build_prompt")
    graph.add_edge("build_prompt", "invoke_llm")
    graph.add_edge("invoke_llm", END)
    
    graph.set_entry_point("retrieve_and_filter")
    
    return graph.compile()


def setup_node(state: InputState) -> GraphState:
    user_query = state.get("user_query") or ""
    user_code = state.get("user_code") or ""
    problem_id = state.get("problem_id", 0)
    problem=get_problem_by_id(problem_id)
    sample_test_cases = problem.get("sample_test_cases", []) if problem else []
    user_intent = state.get("user_intent", "")
    previous_messages = get_previous_messages(user_id=1,problem_id=problem_id,limit=8)
    
    if not isinstance(user_query, str):
        user_query = ""
    else:
        user_query = user_query.strip()
    
    if not isinstance(user_code, str):
        user_code = ""
    else:
        user_code = user_code.strip()
    
    messages = list(previous_messages) if previous_messages else []
    
    MAX_HISTORY_TOKENS = 1000
    messages = trim_messages_to_token_limit(
        previous_messages,
        max_tokens=MAX_HISTORY_TOKENS
    )
    if user_query:
        messages.append(HumanMessage(content=user_query))

    if user_code:
        messages.append(HumanMessage(content=f"User code:\n{user_code}"))
    
    retrieval_k = 10
    sections = []
    
    if user_intent == "why_my_code_failed":
        retrieval_k = 10
        sections = ["error_analysis", "debugging"]
    elif user_intent == "how_to_solve_this":
        retrieval_k = 10
        sections = ["approach", "intuition"]
    elif user_intent == "clarification_request":
        retrieval_k = 5
        sections = ["definition", "constraints"]
    
    return_state = {
        "user_intent": user_intent,
        "user_query": user_query,
        "user_code": user_code,
        "problem_id": problem_id,
        "problem": problem,
        "sample_test_cases": sample_test_cases,
        "answer": "",
        "messages": messages,
        "retrieval_k": retrieval_k,
        "sections": sections
    }
    
    
    return return_state


class IntentDecision(BaseModel):
    intent: Literal[
        "how_to_solve_this",
        "why_my_code_failed",
        "clarification_request",
        "general_concept_help"
    ]
    confidence: float = Field(..., ge=0, le=1)


def classify_intent_node(state: InputState) -> dict:
    """
    Classify user intent using intelligent LLM-based analysis.
    Routes to the most appropriate handler based on user's actual intent.
    """
    user_query = state.get("user_query", "") or ""
    user_code = state.get("user_code", "") or ""
    system_prompt = """You are the Router Brain for an AI Coding Tutor.
Your goal is to map the user's request to EXACTLY ONE of the following 4 handlers.

Analyze the user's text and the presence of code to decide.

### 1. general_concept_help (PRIORITY - Check this FIRST)
**Definition:** The user is asking about a programming concept, language syntax, algorithm theory, OR a DIFFERENT PROBLEM in isolation.
**The Litmus Test:** If you copy-pasted this question into a conversation about a different problem, would it still make sense?
* YES -> It is `general_concept_help`.
* NO  -> It is likely `how_to_solve_this`.

**IMPORTANT:** If the user mentions a DIFFERENT problem by name (e.g. "Two Sum", "LeetCode 1", "the array problem"), this is ALWAYS `general_concept_help` because they are asking about that problem in isolation, not about the current problem.

**Examples of general_concept_help:**
* "How does a hash map work internally?"
* "What is the syntax for slicing arrays in Python?"
* "Explain the time complexity of QuickSort."
* "How to solve two sum?" (Different problem -> general concept)
* "How to solve the shortest path problem?" (Different problem -> general concept)
* "How to use the map() function?"
* "What is Union-Find?"
* "What is a DFS/BFS?" (Concept, not tied to current problem)

### 2. clarification_request
**Definition:** The user is confused about the *CURRENT problem statement* itself. They need help reading or interpreting the CURRENT problem's requirements.
**The Litmus Test:** Does the answer require reading the CURRENT problem description text? Does it mention constraints, input format, or output format of THIS problem?
* YES -> It is `clarification_request`.
**Examples:**
* "Is the input array always sorted?"
* "What does it mean by 'non-decreasing order'?"
* "Can the grid contain negative numbers?"
* "What are the constraints exactly?"

### 3. why_my_code_failed (REQUIRES CODE + ERROR) - STRICT RULES
**Definition:** The user has ACTUALLY PROVIDED CODE and is asking why it fails/is incorrect/is slow/is buggy.
**⚠️ CRITICAL - BOTH CONDITIONS REQUIRED (Not OR, not one of them - BOTH):**
1. Code is present in the message (actual code, not just explanation)
2. User is reporting a failure/error/asking "why doesn't this work?" (not just planning)

**MANDATORY CHECKLIST before deciding `why_my_code_failed`:**
- [ ] Is there actual code (syntax, variables, logic) in the message? (Not just "I will use X")
- [ ] Is there a failure statement? ("doesn't work", "getting TLE", "got wrong answer", "why is this", "bug", etc.)
- If BOTH checkboxes are YES -> `why_my_code_failed`
- If EITHER is NO -> NOT `why_my_code_failed` (route to `how_to_solve_this` instead)

** EXAMPLES of why_my_code_failed (code + error):**
* "Here's my code: [actual code]. Why am I getting TLE?" 
* "My output is 5 but expected 10. [code snippet]"
* "What's the bug in this? [code]"
* "def solve(): return x. This is getting wrong answer, why?"

** NOT why_my_code_failed (EVEN if they talk about algorithms/approaches):**
* "I will use DSU to solve this" (no code, just planning)
* "i will connect the ones with DSU and will return unique parents count" (no code shown, just explaining algorithm)
* "Should I use DFS or BFS?" (no code, no error)
* "I'm thinking of using Union-Find" (strategy planning, not failure)
* "My approach is to iterate and count islands" (explaining strategy, no code present)

### 4. how_to_solve_this (The Fallback for THIS problem)
**Definition:** The user understands the CURRENT problem but doesn't know *how* to approach IT. They want hints, strategies, or an algorithm recommendation for *this specific task*.
**The Litmus Test:** Is the user asking "What do I do?" or "Is X the right approach?" for *THIS specific problem*? Are they stuck on THIS problem?
* YES -> It is `how_to_solve_this`.
**Examples:**
* "Should I use DP or Greedy for this?" (this = current problem)
* "I'm stuck, can you give me a hint?" (stuck on current)
* "How do I handle the edge case?" (current problem edge case)
* "How do I handle the edge case where N=1?"

###  CRITICAL TIE-BREAKING RULES 

**DECISION TREE (Follow in order):**

1. **HIGHEST PRIORITY - DIFFERENT PROBLEM MENTIONS:**
   If user asks about a DIFFERENT problem by name -> ALWAYS `general_concept_help`
   "How to solve Two Sum?", "How to solve the shortest path problem?" -> `general_concept_help`

2. **CHECK FOR ACTUAL CODE + ERROR (for why_my_code_failed):**
   ABSOLUTE RULE: If NO code present -> NEVER classify as `why_my_code_failed`
   
   Is there actual code in the message? (Not just "I will do X") -> YES/NO
   - If NO -> SKIP why_my_code_failed entirely, go to next rule
   - If YES -> Check: Is there a failure/error statement? ("doesn't work", "TLE", "wrong answer", "why", "bug")
     - Both code AND error -> `why_my_code_failed`
     - Code but no error -> NOT why_my_code_failed -> `how_to_solve_this`
   
   CRITICAL EXAMPLES:
   - "i will connect the ones with DSU and will return unique parents count" (NO code shown) -> NOT why_my_code_failed -> `how_to_solve_this`
   - "I will use DSU to solve this" (strategy, no code) -> NOT why_my_code_failed -> `how_to_solve_this`
   - "yes it will be multiple disconnected graphs?" (NO code, question about problem) -> NOT why_my_code_failed -> `clarification_request`

3. **ABSTRACT CONCEPT vs STRATEGY with THIS problem:**
   "How do I use BFS?" (abstract concept) -> `general_concept_help`
   "Should I use BFS to solve this?" (THIS problem strategy) -> `how_to_solve_this`

4. **CLARIFICATION requires THIS problem statement context:**
   YES/NO questions about problem constraints/scope -> `clarification_request`
   Questions about what something means in the problem -> `clarification_request`
   Questions asking to clarify problem requirements -> `clarification_request`
   
   EXAMPLES:
   - "yes it will be multiple disconnected graphs?" (asking about problem scope) -> `clarification_request`
   - "What does 'island' mean?" (THIS problem concept) -> `clarification_request`
   - "Can the grid be empty?" (problem constraints) -> `clarification_request`
   - "Is the output always an integer?" (problem specification) -> `clarification_request`
   
   vs
   - "What is DSU?" (abstract algorithm, not about THIS problem) -> `general_concept_help`
   - "How does BFS work?" (abstract concept) -> `general_concept_help`

5. **STRATEGY DISCUSSION without code -> how_to_solve_this:**
   "I'm thinking of using X approach", "Would DSU work here?", "Should I use Union-Find?" -> `how_to_solve_this`

6. **GENERAL KEYWORDS signal general_concept_help:**
   "What is", "How to solve" + different problem, "Explain" + algorithm -> `general_concept_help`

###  ANTI-PATTERN: DO NOT DO THIS
These are the MOST COMMON mistakes. AVOID THEM:

1. **"Explaining algorithm = why_my_code_failed"** - WRONG!
   User: "i will connect the ones with DSU and will return unique parents count"
   WRONG CLASSIFICATION: `why_my_code_failed` (they're just explaining their approach)
   CORRECT CLASSIFICATION: `how_to_solve_this` (they're discussing strategy for THIS problem)
   CHECK: Is there code shown? NO -> NOT why_my_code_failed

2. **"Strategy planning = why_my_code_failed"** - WRONG!
   User: "I will use DSU to solve this"
   WRONG CLASSIFICATION: `why_my_code_failed` (they're planning, not reporting a failure)
   CORRECT CLASSIFICATION: `how_to_solve_this` (they're asking about approach)
   CHECK: Is there code? NO -> NOT why_my_code_failed

3. **"Question about problem = why_my_code_failed"** - WRONG!
   User: "yes it will be multiple disconnected graphs?"
   WRONG CLASSIFICATION: `why_my_code_failed` (no code at all, asking about problem scope)
   CORRECT CLASSIFICATION: `clarification_request` (asking about problem constraints)
   CHECK: Is there code? NO -> NEVER why_my_code_failed. Is this about THIS problem scope/constraints? YES -> `clarification_request`

4. **"Mentioning an algorithm = general_concept_help"** - WRONG (context matters)!
   User: "How should I use DSU for this problem?" (for THIS current problem)
   WRONG CLASSIFICATION: `general_concept_help`
   CORRECT CLASSIFICATION: `how_to_solve_this` (about THIS problem strategy)
   CHECK: Is "this" referring to the CURRENT problem? YES -> `how_to_solve_this`, not `general_concept_help`

### OUTPUT FORMAT
First provide your reasoning (1-2 sentences explaining which rule applies).
Then respond with ONLY the intent name: general_concept_help, clarification_request, why_my_code_failed, or how_to_solve_this
"""

    structured_llm = llm.with_structured_output(IntentDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", f"User Query: {user_query}\n\nCode Present: {'Yes' if user_code.strip() else 'No'}")
    ])

    try:
        
        # Invoke structured LLM
        result: IntentDecision = (prompt | structured_llm).invoke({})
        intent = result.intent
        
    except Exception as e:
        logger.error(f"[CLASSIFY] Classification error: {str(e)}", exc_info=True)
        intent = "how_to_solve_this"
        logger.warning(f"[CLASSIFY] Decision: Falling back to default intent '{intent}' due to error")
        result = IntentDecision(intent=intent, confidence=0.0)

    return_dict = {
        **state,
        "user_intent": result.intent
    }
    return return_dict


def route_by_intent(state: GraphState) -> str:
    intent = state.get("user_intent", "").strip()
    if intent == "general_concept_help":
        return "general_concept_help"
    else:
        return "rag_pipeline"


rag_subgraph = rag_subgraph()
general_concept_subgraph = general_concept_subgraph()

build = StateGraph(GraphState,input_schema=InputState,output_schema=OutputState)

build.add_node("classify_intent", classify_intent_node)
build.add_node("setup", setup_node)

build.add_node("rag_pipeline", rag_subgraph)
build.add_node("general_concept_help", general_concept_subgraph)

build.add_edge(START, "classify_intent")
build.add_edge("classify_intent", "setup")
build.add_conditional_edges(
    "setup",
    route_by_intent,
    {
        "rag_pipeline": "rag_pipeline",
        "general_concept_help": "general_concept_help",
    }
)

build.add_edge("rag_pipeline", END)
build.add_edge("general_concept_help", END)

graph = build.compile()

def run_graph(input_dict: dict) -> dict:
    try:
        result = graph.invoke(input_dict)
        answer = result.get("answer", "I couldn't generate a response. Please try again.")
        intent = result.get("user_intent", "")
        logger.info(f"[GRAPH] Decision: Execution completed successfully - Intent: {intent}")
        return {
            "answer": answer,
            "intent": intent
        }
    except Exception as e:
        logger.error(f"[GRAPH] Decision: Execution failed with error - {str(e)}")
        return {
            "answer": f"Error: {str(e)}",
            "intent": ""
        }
    # vv