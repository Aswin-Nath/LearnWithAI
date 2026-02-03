from app.roadmap.state import RoadMapState
from app.core.logger import get_logger

logger = get_logger("roadmap.mcq.evaluate")

def evaluate_knowledge_node(state: RoadMapState) -> dict:
    """
    Deterministically computes strong and weak topics based on user answers.
    """
    print("EVALUATE KNOWLEDGE NODE CALLED")  # This will always show
    
    mcqs = state.get("mcqs", [])
    user_answers = state.get("user_answers", [])
    
    print(f"MCQs count: {len(mcqs)}, Answers count: {len(user_answers)}")
    print(f"MCQs: {mcqs}")
    print(f"Answers: {user_answers}")
    
    if not mcqs or not user_answers or len(mcqs) != len(user_answers):
        print(f"Mismatch: {len(mcqs)} MCQs vs {len(user_answers)} answers")
        logger.warning(f"Mismatch: {len(mcqs)} MCQs vs {len(user_answers)} answers")
        return {
            **state,
            "knowledge_state": {"strong_topics": [], "weak_topics": []},
            "error": "Mismatch between MCQs and answers count"
        }
    strong_topics_set = set()
    weak_topics_set = set()
    for i, mcq in enumerate(mcqs):
        if i < len(user_answers):
            correct_answer = mcq["answer"]
            topics = mcq.get("topics", [])
            given_answer = user_answers[i]
            
            logger.debug(f"MCQ {i}: Topics={topics}, Correct={correct_answer}, Given={given_answer}")
            
            if not isinstance(given_answer, int) or not (0 <= given_answer < len(mcq["options"])):
                for t in topics:
                    weak_topics_set.add(t)
                logger.debug(f"  Invalid answer, marked as weak")
                continue
            if given_answer == correct_answer:
                for t in topics:
                    strong_topics_set.add(t)
                logger.debug(f"  Correct answer, marked as strong")
            else:
                for t in topics:
                    weak_topics_set.add(t)
                print(f"❌ MCQ {i}: Given {given_answer} vs Correct {correct_answer} - Marked as WEAK")
                logger.debug(f"  Incorrect answer, marked as weak")
    final_weak = list(weak_topics_set - strong_topics_set)
    final_strong = list(strong_topics_set)
    
    print(f"✅ Final result - Strong: {final_strong}, Weak: {final_weak}")
    logger.info(f"Final result - Strong: {final_strong}, Weak: {final_weak}")
    
    return {
        **state,
        "knowledge_state": {
            "strong_topics": final_strong,
            "weak_topics": final_weak
        }
    }
