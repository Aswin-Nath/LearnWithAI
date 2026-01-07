from app.ai.graph.graph import graph

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)



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