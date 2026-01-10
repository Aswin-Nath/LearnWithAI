from langgraph.graph import StateGraph,END
from app.ai.graph.state import GraphState
from app.ai.rag.prompts import build_prompt
from app.ai.nodes.llm import invoke_llm_node


from app.core.logger import get_logger

logger=get_logger("general_subgraph")


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
        logger.error(f"[GENERAL]  Prompt building failed: {str(e)}", exc_info=True)
        return {"prompt_text": ""}

def general_concept_subgraph() -> StateGraph:
    graph = StateGraph(GraphState, output_nodes=["answer"])
    
    graph.add_node("build_prompt", general_concept_prompt)
    graph.add_node("invoke_llm", invoke_llm_node)
    
    graph.add_edge("build_prompt", "invoke_llm")
    graph.add_edge("invoke_llm", END)
    
    graph.set_entry_point("build_prompt")
    
    return graph.compile()