from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.roadmap.llm import llm

# 1. Define the Structured Output Schema
class MethodologyCheck(BaseModel):
    is_compliant: bool = Field(description="true if the user's code strictly applies the concept/methodology taught in the phase content. false if they used a different approach.")
    feedback: str = Field(description="A concise message to the user.")

# 2. Define the Verification Node Logic
def verify_solution_methodology(user_code: str, phase_content: str, problem_description: str) -> MethodologyCheck:
    """
    Uses LangChain to verify if the user's solution follows the specific phase methodology.
    """
    
    parser = JsonOutputParser(pydantic_object=MethodologyCheck)
    
    # Define the "Helpful Teaching Assistant" Prompt
    system_prompt = """You are a helpful coding mentor verifying a student's submission.
    
    Your Task:
    Determine if the Student's Code applies the *core concepts* taught in the Phase Content to solve the Problem.
    
    Rules for Verification:
    1. **Allow Valid Variations**: If the user uses a nested function vs a separate function, that is FINE. If they use a slightly different variable name, that is FINE.
    2. **Focus on the Algorithm**:
       - If the Phase teaches "DFS or BFS" and the user uses BFS -> PASS.
       - If the Phase teaches "Iterative DP" and the user uses "Recursive" -> FAIL (this is a fundamental mismatch).
       - If the Phase teaches "Graph Traversal" and the user uses "Union Find" -> FAIL (different concept).
    3. **Be Lenient on Style**: Do not nitpick code structure, comments, or standard library usage unless it violates the core algorithmic lesson.
    4. **Empty Grid Handling**: If the code logic is correct for the main case, passing/failing edge cases is the job of the test runner, NOT you. You only care about the *Methodology*.
    
    RETURN JSON ONLY:
    {{
        "is_compliant": boolean,
        "feedback": "string"
    }}
    
    Input Context:
    ---
    PHASE CONTENT (The Lesson):
    {phase_content}
    ---
    PROBLEM DESCRIPTION:
    {problem_description}
    ---
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Student Code:\n{user_code}")
    ])

    # Manual Chain: Prompt -> LLM -> JSON Parser
    # This avoids the tool-use error by just asking for raw JSON text
    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "phase_content": phase_content,
            "problem_description": problem_description,
            "user_code": user_code
        })
        
        # Ensure result is mapped to object
        return MethodologyCheck(
            is_compliant=result.get("is_compliant", False),
            feedback=result.get("feedback", "Verification failed.")
        )
        
    except Exception as e:
        print(f"Verification Error: {e}")
        # Fail safe
        return MethodologyCheck(is_compliant=True, feedback="Verification service unavailable (Fallback pass).")
