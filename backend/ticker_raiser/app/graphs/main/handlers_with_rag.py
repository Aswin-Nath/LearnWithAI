import os
import sys
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from rag_layer import (
    retriever, INTENT_TO_SECTIONS, filter_by_section, 
    build_prompt
)
load_dotenv()
# LLM 
GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(api_key=GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0.5)

# HANDLER 1: why_my_code_failed (FULL EXAMPLE)
def handle_why_my_code_failed_with_rag(state) -> dict:
    """
    Debug handler: Identify bug, explain cause, guide fix.
    
    Flow:
    1. Retrieve all relevant chunks
    2. Filter to edge cases + pitfalls + failure scenarios
    3. Build debug-focused prompt
    4. LLM analyzes their code against these patterns
    5. Return structured debugging guidance
    """
    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    user_code = state["user_code"]
    problem = state["problem"]
    
    # STEP 1: Retrieve relevant chunks
    # Search for their issue in the knowledge base
    all_chunks = retriever.retrieve(
        problem_id=problem_id,
        query=f"{user_query}\n\nCode:\n{user_code}",  # Query includes context
        k=10  # Get more, then filter
    )
    
    # STEP 2: Filter to intent-specific sections
    allowed_sections = INTENT_TO_SECTIONS["why_my_code_failed"]
    filtered_chunks = filter_by_section(all_chunks, allowed_sections)
    
    # Log for debugging
    print(f"[DEBUG] why_failed: Retrieved {len(all_chunks)} chunks, filtered to {len(filtered_chunks)}")
    if filtered_chunks:
        print(f"[DEBUG] Top sections: {[c['section'] for c in filtered_chunks[:3]]}")
    
    # STEP 3: Build the prompt (now with conversation context if available)
    conversation_context = state.get("messages", [])
    prompt_text = build_prompt(
        intent="why_my_code_failed",
        problem=problem,
        user_query=user_query,
        user_code=user_code,
        context_chunks=filtered_chunks,
        conversation_context=conversation_context
    )
    
    # STEP 4: Call LLM
    try:
        response = llm.invoke(prompt_text)
        answer = response.content
    except Exception as e:
        answer = f"Error analyzing your code: {str(e)}\n\nTry describing the error you're seeing (TLE, WA, RE, etc.)"
    
    return {**state, "answer": answer, "messages": [AIMessage(content=answer)]}


# HANDLER 2: how_to_solve_this 
def handle_how_to_solve_this_with_rag(state) -> dict:
    """
    Hint handler: Provide progressive hints without giving solution.
    
    Flow:
    1. Retrieve approach/intuition sections
    2. Build hint-focused prompt
    3. LLM provides Socratic hints
    """
    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    problem = state["problem"]
    
    # Retrieve approach/intuition chunks
    all_chunks = retriever.retrieve(
        problem_id=problem_id,
        query=user_query,
        k=8
    )
    
    # Filter to approach/intuition sections
    allowed_sections = INTENT_TO_SECTIONS["how_to_solve_this"]
    filtered_chunks = filter_by_section(all_chunks, allowed_sections)
    
    print(f"[DEBUG] how_to_solve: Retrieved {len(all_chunks)} chunks, filtered to {len(filtered_chunks)}")
    
    # Build prompt with conversation context
    conversation_context = state.get("messages", [])
    prompt_text = build_prompt(
        intent="how_to_solve_this",
        problem=problem,
        user_query=user_query,
        user_code=None,
        context_chunks=filtered_chunks,
        conversation_context=conversation_context
    )
    
    # Call LLM
    try:
        response = llm.invoke(prompt_text)
        answer = response.content
    except Exception as e:
        answer = f"Error generating hint: {str(e)}\n\nTry asking about a specific part of the problem."
    
    return {**state, "answer": answer, "messages": [AIMessage(content=answer)]}


# HANDLER 3: explain_my_code 
def handle_explain_my_code_with_rag(state) -> dict:
    """
    Explanation handler: Walk through code line by line.
    
    Flow:
    1. Retrieve code + complexity sections
    2. Build explanation-focused prompt
    3. LLM explains with references to approach
    """
    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    user_code = state["user_code"]
    problem = state["problem"]
    
    # Retrieve code + complexity sections
    all_chunks = retriever.retrieve(
        problem_id=problem_id,
        query=user_code,  # Search by their code
        k=8
    )
    
    # Filter to code + explanation sections
    allowed_sections = INTENT_TO_SECTIONS["explain_my_code"]
    filtered_chunks = filter_by_section(all_chunks, allowed_sections)
    
    print(f"[DEBUG] explain_code: Retrieved {len(all_chunks)} chunks, filtered to {len(filtered_chunks)}")
    
    # Build prompt with conversation context
    conversation_context = state.get("messages", [])
    prompt_text = build_prompt(
        intent="explain_my_code",
        problem=problem,
        user_query=user_query or "Please explain my code",
        user_code=user_code,
        context_chunks=filtered_chunks,
        conversation_context=conversation_context
    )
    
    # Call LLM
    try:
        response = llm.invoke(prompt_text)
        answer = response.content
    except Exception as e:
        answer = f"Error explaining code: {str(e)}\n\nTry asking about a specific part of your code."
    
    return {**state, "answer": answer, "messages": [AIMessage(content=answer)]}


# HANDLER 4: validate_my_approach
def handle_validate_my_approach_with_rag(state) -> dict:
    """
    Validation handler: Confirm approach, identify issues, suggest optimizations.
    
    Flow:
    1. Retrieve complexity + correctness sections
    2. Build validation-focused prompt
    3. LLM validates against constraints
    """
    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    user_code = state["user_code"]
    problem = state["problem"]
    
    # Search by their code or query
    search_text = user_code if user_code else user_query
    
    all_chunks = retriever.retrieve(
        problem_id=problem_id,
        query=search_text,
        k=10
    )
    
    # Filter to validation-relevant sections
    allowed_sections = INTENT_TO_SECTIONS["validate_my_approach"]
    filtered_chunks = filter_by_section(all_chunks, allowed_sections)
    
    print(f"[DEBUG] validate: Retrieved {len(all_chunks)} chunks, filtered to {len(filtered_chunks)}")
    
    # Build prompt with conversation context
    conversation_context = state.get("messages", [])
    prompt_text = build_prompt(
        intent="validate_my_approach",
        problem=problem,
        user_query=user_query or "Is my approach correct?",
        user_code=user_code,
        context_chunks=filtered_chunks,
        conversation_context=conversation_context
    )
    
    # Call LLM
    try:
        response = llm.invoke(prompt_text)
        answer = response.content
    except Exception as e:
        answer = f"Error validating approach: {str(e)}\n\nTry sharing your approach idea or code."
    
    return {**state, "answer": answer, "messages": [AIMessage(content=answer)]}


# HANDLER 5: clarification_request 
def handle_clarification_request_with_rag(state) -> dict:
    """
    Clarification handler: Answer factual questions about problem.
    
    Flow:
    1. Retrieve problem description + constraints
    2. Build factual clarification prompt
    3. LLM answers directly without opinion
    """
    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    problem = state["problem"]
    
    all_chunks = retriever.retrieve(
        problem_id=problem_id,
        query=user_query,
        k=8
    )
    
    # Filter to problem statement sections
    allowed_sections = INTENT_TO_SECTIONS["clarification_request"]
    filtered_chunks = filter_by_section(all_chunks, allowed_sections)
    
    # Clarification only needs 1-2 chunks (not deep reasoning, just facts)
    filtered_chunks = filtered_chunks[:2]
    
    print(f"[DEBUG] clarification: Retrieved {len(all_chunks)} chunks, filtered to {len(filtered_chunks)}")
    
    # Build prompt with conversation context
    conversation_context = state.get("messages", [])
    prompt_text = build_prompt(
        intent="clarification_request",
        problem=problem,
        user_query=user_query,
        user_code=None,
        context_chunks=filtered_chunks,
        conversation_context=conversation_context
    )
    
    # Call LLM
    try:
        response = llm.invoke(prompt_text)
        answer = response.content
    except Exception as e:
        answer = f"Error clarifying: {str(e)}\n\nTry asking about problem constraints or definitions."
    
    return {**state, "answer": answer, "messages": [AIMessage(content=answer)]}


