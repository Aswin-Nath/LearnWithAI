from app.ai.graph.state import GraphState
from app.ai.rag.retriever import retriever
from typing import List
from app.core.logger import get_logger

logger=get_logger("retrieve_node")


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

def retrieve_and_filter(state: GraphState) -> dict:    
    problem_id = state["problem_id"]
    user_query = state["user_query"]
    user_code = state.get("user_code", "")
    intent = state["user_intent"]
    k = state.get("retrieval_k", 10)
    
    query_text = f"{user_query}\n\nCode:\n{user_code}" if user_code else user_query
    
    try:
        chunks = retriever.retrieve(problem_id=problem_id, query=query_text, k=k)
        
        allowed_sections = state.get("sections")

        if not chunks or not allowed_sections:
            return {"filtered_chunks": []}
        filtered = filter_by_section(chunks, allowed_sections)
        
        if intent == "clarification_request":
            filtered = filtered[:2]
        
        return {"filtered_chunks": filtered}
        
    except Exception as e:
        logger.error(f"[RAG]  Retrieval/Filter failed: {str(e)}", exc_info=True)
        return {"filtered_chunks": []}

