from app.ai.graph.state import GraphState
from langchain_core.messages import HumanMessage
from app.ai.llm import llm

from app.core.logger import get_logger
logger=get_logger("invoke_llm")


def invoke_llm_node(state: GraphState) -> dict:    
    prompt_text = state.get("prompt_text", "")
    if not prompt_text:
        return {"answer": "Error: Empty prompt"}
    
    try:
        response = llm.invoke([HumanMessage(content=prompt_text)])
        answer = response.content
        return {"answer": answer}
    except Exception as e:
        logger.error(f"[LLM]  LLM invocation failed: {str(e)}", exc_info=True)
        return {"answer": f"Error generating response: {str(e)}"}