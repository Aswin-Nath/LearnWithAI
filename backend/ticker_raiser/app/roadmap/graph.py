from langgraph.graph import StateGraph, START, END
from app.roadmap.state import RoadMapState
from app.roadmap.nodes.mcq.generate import generate_mcqs_node
from app.roadmap.nodes.mcq.present import present_mcqs_node
from app.roadmap.nodes.mcq.evaluate import evaluate_knowledge_node
from app.roadmap.nodes.phases.generate import generate_phases_node
from app.roadmap.nodes.phases.assign_problems import assign_problems_node
from app.roadmap.nodes.phases.phase_content import generate_phase_content_node
workflow = StateGraph(RoadMapState)

workflow.add_node("generate_mcqs", generate_mcqs_node)
workflow.add_node("present_mcqs", present_mcqs_node)
workflow.add_node("evaluate_knowledge", evaluate_knowledge_node)
workflow.add_node("generate_phases", generate_phases_node)
workflow.add_node("generate_phase_content", generate_phase_content_node)
workflow.add_node("generate_problem", assign_problems_node)
workflow.add_edge(START, "generate_mcqs")
workflow.add_edge("generate_mcqs", "present_mcqs")
workflow.add_edge("present_mcqs", "evaluate_knowledge")
workflow.add_edge("evaluate_knowledge", "generate_phases")
workflow.add_edge("generate_phases", "generate_problem")
workflow.add_edge("generate_problem", "generate_phase_content")
workflow.add_edge("generate_phase_content", END)

from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer,interrupt_after=["evaluate_knowledge"])
