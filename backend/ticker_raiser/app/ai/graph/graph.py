from app.ai.graph.state import InputState,GraphState,OutputState
from langgraph.graph import START,END,StateGraph
from app.ai.graph.subgraph.rag_subgraph import rag_subgraph
from app.ai.graph.subgraph.general_subgraph import general_concept_subgraph
from app.ai.nodes.classify_intent import classify_intent_node
from app.ai.nodes.setup import setup_node


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
