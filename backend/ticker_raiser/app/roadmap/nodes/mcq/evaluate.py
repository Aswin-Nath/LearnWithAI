from app.roadmap.state import RoadMapState
def evaluate_knowledge_node(state: RoadMapState) -> dict:
    """
    Deterministically computes strong and weak topics based on user answers.
    """
    mcqs = state.get("mcqs", [])
    user_answers = state.get("user_answers", [])
    
    if not mcqs or not user_answers or len(mcqs) != len(user_answers):
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
            topics = mcq["topics"]
            given_answer = user_answers[i]
            if not isinstance(given_answer, int) or not (0 <= given_answer < len(mcq["options"])):
                for t in topics:
                    weak_topics_set.add(t)
                continue
            if given_answer == correct_answer:
                for t in topics:
                    strong_topics_set.add(t)
            else:
                for t in topics:
                    weak_topics_set.add(t)
    final_weak = list(weak_topics_set - strong_topics_set)
    final_strong = list(strong_topics_set)
    return {
        **state,
        "knowledge_state": {
            "strong_topics": final_strong,
            "weak_topics": final_weak
        }
    }
