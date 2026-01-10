from app.ai.graph.state import GraphState
from app.ai.rag.prompts import build_prompt
from app.core.logger import get_logger

logger=get_logger("prompt_node")


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
        logger.error(f"[PROMPT]  Prompt building failed: {str(e)}", exc_info=True)
        return {"prompt_text": ""}