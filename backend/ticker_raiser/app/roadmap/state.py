from typing import TypedDict, List, Dict, Any

class RoadMapState(TypedDict):
    topic: str
    user_query: str
    mcqs: List[dict]
    user_answers: List[int]
    knowledge_state: Dict[str, List[str]]
    phases: List[dict]
    phase_content: Dict[str, Any]
    error: str
    skip_assessment: bool