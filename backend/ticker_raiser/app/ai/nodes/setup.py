from app.ai.graph.state import GraphState,InputState
from langchain_core.messages import HumanMessage

def setup_node(state: InputState) -> GraphState:
    problem = state.get("problem")
    sample_test_cases = problem.get("sample_test_cases", []) if problem else []
    user_query = state.get("user_query") or ""
    user_code = state.get("user_code") or ""
    problem_id = state.get("problem_id", 0)
    user_intent = state.get("user_intent", "")
    previous_messages = state.get("previous_messages") or []  # NEW: From API layer
    
    if not isinstance(user_query, str):
        user_query = ""
    else:
        user_query = user_query.strip()
    
    if not isinstance(user_code, str):
        user_code = ""
    else:
        user_code = user_code.strip()
    
    messages = list(previous_messages) if previous_messages else []
    
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