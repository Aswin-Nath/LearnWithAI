from app.roadmap.state import RoadMapState


from langgraph.types import interrupt

def present_mcqs_node(state: RoadMapState) -> dict:
    """
    Interrupts execution to present MCQs to the user and waits for answers.
    
    If skip_assessment=True, skip the interrupt and use user_answers directly from state.
    When resumed, it returns the provided user answers.
    """
    mcqs = state.get("mcqs", [])
    skip_assessment = state.get("skip_assessment", False)
    if skip_assessment:
        user_answers = state.get("user_answers", [])
        return {
            **state,
            "user_answers": user_answers
        }
    resume_payload = interrupt({
        "type": "MCQ_PRESENTATION",
        "mcqs": mcqs
    }) or {}
    user_answers = resume_payload.get("user_answers", [])
    return {
        **state,
        "user_answers": user_answers
    }