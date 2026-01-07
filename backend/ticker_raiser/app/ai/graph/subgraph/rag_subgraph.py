from langgraph.graph import StateGraph,END
from app.ai.graph.state import GraphState
from app.ai.nodes.llm import invoke_llm_node
from app.ai.nodes.prompt import build_prompt_node
from app.ai.nodes.retrieve import retrieve_and_filter
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