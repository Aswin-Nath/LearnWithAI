import subprocess
import tempfile
import os
import sys
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.roadmap.llm import llm
from pydantic import BaseModel, Field

# Define the structure LLM should return
class GeneratedProblemContent(BaseModel):
    title: str = Field(description="A concise, standard algorithmic problem title")
    description_markdown: str = Field(description="Problem description and I/O format in Markdown")
    constraints: str = Field(description="Constraints list in Markdown")
    editorial_markdown: str = Field(description="Detailed explanation of the solution, approach, and time complexity")
    canonical_code: str = Field(description="Correct Python solution code (Complete script reading from stdin/printing to stdout)")
    generator_code: str = Field(description="Python script that uses 'random' to print a SINGLE valid input to stdout.")

class TestCaseData(BaseModel):
    input: str
    output: str

class ProblemGenerationResult(BaseModel):
    content: GeneratedProblemContent
    test_cases: List[TestCaseData]

def generate_and_solve_tests(generator_code: str, solver_code: str, num_cases: int = 10) -> List[TestCaseData]:
    """
    1. Runs generator_code to create random INPUT.
    2. Runs solver_code with that INPUT to get OUTPUT.
    """
    results = []
    
    # Create temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f_gen:
        f_gen.write(generator_code)
        gen_path = f_gen.name
        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f_sol:
        f_sol.write(solver_code)
        sol_path = f_sol.name
        
    try:
        for i in range(num_cases):
            try:
                # 1. Generate Input
                gen_proc = subprocess.run(
                    [sys.executable, gen_path],
                    text=True, capture_output=True, timeout=2
                )
                if gen_proc.returncode != 0:
                    print(f"Generator Error: {gen_proc.stderr}")
                    continue
                    
                input_data = gen_proc.stdout.strip()
                if not input_data:
                    continue

                # 2. Solve Input
                sol_proc = subprocess.run(
                    [sys.executable, sol_path],
                    input=input_data,
                    text=True, capture_output=True, timeout=2
                )
                if sol_proc.returncode != 0:
                    print(f"Solver Error: {sol_proc.stderr}")
                    continue
                
                output_data = sol_proc.stdout.strip()
                results.append(TestCaseData(input=input_data, output=output_data))
                
            except Exception as e:
                print(f"Test Gen Loop Error: {e}")
                
    finally:
        if os.path.exists(gen_path): os.remove(gen_path)
        if os.path.exists(sol_path): os.remove(sol_path)
            
    return results

def generate_custom_problem_content(topics: str, user_query: str, difficulty: str) -> ProblemGenerationResult:
    """
    Generates problem content (Title, Description, Constraints, Editorial, Code) using LLM.
    Test Case generation is DISABLED as per user request.
    """
    
    # HARDENED SYSTEM PROMPT
    # Note: JSON braces are double-escaped {{ }} to prevent LangChain parsing errors
    system_prompt = """You are an expert competitive programming problem setter and a strict JSON content generator.

    Your task is to generate ONE and ONLY ONE raw JSON object that fully conforms to the required schema.

    CRITICAL RULES:
    - Output ONLY valid JSON. No markdown, no explanations, no comments, no extra text.
    - The JSON must be syntactically valid and directly parseable.
    - All required keys must be present.
    - Never rename, remove, or add keys.
    - Never return null values. Use empty strings where applicable.
    - Do not include trailing commas.
    - Do not wrap the JSON in code fences.
    - Any violation of format or structure is a failure.

    REQUIRED JSON STRUCTURE:
    {{
      "title": "",
      "description_markdown": "",
      "constraints": "",
      "editorial_markdown": "",
      "canonical_code": "",
      "generator_code": ""
    }}

    TITLE RULES:
    - Professional and concise.
    - Title Case only.
    - No punctuation or emojis.
    - Must reflect the core problem accurately.

    DESCRIPTION_MARKDOWN RULES:
    The description_markdown field must be valid Markdown and must contain the following sections in the EXACT order and with the EXACT headers shown below:

    ## Problem Statement
    Provide a clear and unambiguous description of the problem. Do not mention implementation details.

    ## Input Format
    Clearly define all inputs. Use bullet points if there are multiple inputs.

    ## Output Format
    Clearly define the expected output.

    ## Constraints
    Provide constraints as a bullet list only.

    ## Examples
    You must include EXACTLY ONE example, formatted EXACTLY as follows:

    **Example 1**
    Input: <input_here>
    Output: <output_here>

    **Explanation:** <brief explanation of why the output is correct>

    Do not include more than one example.
    Do not include notes, edge cases, or extra commentary.

    CONSTRAINTS FIELD RULES:
    - The constraints field must be a newline-separated string.
    - The constraints must exactly match those listed in description_markdown.
    - Use realistic numeric bounds appropriate to the given difficulty.

    EDITORIAL_MARKDOWN RULES:
    - Must be valid Markdown.
    - Must include the following sections:
      - Intuition
      - Approach
      - Correctness Proof
      - Time Complexity
      - Space Complexity
    - Do not include code blocks or pseudocode.
    - Do not reference the example explicitly.

    CANONICAL_CODE RULES:
    - Language must be Python 3.
    - Must include a solve() function implementing the full logic.
    - Must include driver code that reads from standard input and prints to standard output.
    - Code must be clean, deterministic, and production-ready.
    - Do not include comments explaining trivial syntax.
    - Do not include placeholder logic.

    GENERATOR_CODE RULES:
    - The generator_code field must exist.
    - Its value must be an empty string.

    QUALITY REQUIREMENTS:
    - The problem must align with the requested topics and difficulty.
    - The solution must be optimal for the stated constraints.
    - The content must be suitable for competitive programming platforms.

    Return only the final JSON object. Nothing else."""
    
    parser = JsonOutputParser(pydantic_object=GeneratedProblemContent)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", f"Topic: {topics}. Query: {user_query}. Difficulty: {difficulty}.\n\nIMPORTANT: Return ONLY the raw JSON object. Ensure 'description_markdown' contains the Examples section.")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"topics": topics, "user_query": user_query, "difficulty": difficulty})

        if not result or not isinstance(result, dict):
            raise ValueError(f"LLM returned invalid result: {result}")

        # Fix keys
        if "description" in result: result["description_markdown"] = result["description"]
        if "editorial" in result: result["editorial_markdown"] = result["editorial"]
        if "code" in result: result["canonical_code"] = result["code"]
        
        # Handle list constraints
        if "constraints" in result and isinstance(result["constraints"], list):
            result["constraints"] = "\n".join([str(c) for c in result["constraints"]])
        
        # Ensure generator_code exists for schema even if empty
        if "generator_code" not in result: result["generator_code"] = ""
        
        content = GeneratedProblemContent(**result)
        
        # Skipping Test Case Generation
        print(f"Skipping test case generation.")
        
        return ProblemGenerationResult(content=content, test_cases=[])
        
    except Exception as e:
        print(f"LLM Generation Error: {e}")
        fallback_content = GeneratedProblemContent(
            title="Error", description_markdown=str(e), constraints="", 
            editorial_markdown="", canonical_code="", generator_code=""
        )
        return ProblemGenerationResult(content=fallback_content, test_cases=[])
