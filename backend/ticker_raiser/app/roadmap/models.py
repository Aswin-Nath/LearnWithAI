from typing import Literal,List
from pydantic import BaseModel, Field

class MCQ(BaseModel):
    mcq_id: int = Field(description="Unique identifier for the MCQ")
    question: str = Field(description="The question text")
    options: List[str] = Field(description="List of exactly 4 plausible options")
    answer: int = Field(description="Index of the correct option (0-based)")
    topics: List[str] = Field(description="List of atomic learning topics targeted by this question", min_length=1)
    difficulty: Literal["easy", "medium", "hard"] = Field(description="Difficulty level of the question")

class MCQResponse(BaseModel):
    mcqs: List[MCQ] = Field(description="List of exactly 6 generated MCQs")

class Phase(BaseModel):
    phase_id: int = Field(description="1-based phase identifier")
    phase_name: str = Field(description="Name of the learning phase")
    focus_topics: List[str] = Field(description="List of topics focused on in this phase")
    phase_goal: str = Field(description="Goal of this learning phase")

class RoadmapPhases(BaseModel):
    phases: List[Phase] = Field(description="List of exactly 4 learning phases")

class SelectedProblem(BaseModel):
    problem_id: int = Field(description="The ID of the selected problem")
    reason: str = Field(description="A brief explanation (1 sentence) of why this problem STRICTLY matches the focus topics.")

class ProblemSelection(BaseModel):
    selected_problems: List[SelectedProblem] = Field(description="List of relevant problems. Empty if none are strict matches.")
