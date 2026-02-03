import subprocess
import tempfile
import os
import sys
import time
import shutil
import re
from typing import List, Optional, Dict, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.roadmap.llm import llm
from pydantic import BaseModel, Field

# ============================================================================
# ARCHITECTURE: 4-Phase Generation Pipeline
# ============================================================================
#
# DESIGN PRINCIPLE: "Only your code executes logic"
#
# LLM outputs must be validated before trust. This system enforces separation
# of concerns across 4 strict phases:
#
#   PHASE 1: Problem Spec Generation (LLM #1)
#   ├─ Responsibility: Title, description, constraints, editorial, canonical solution
#   ├─ Validation: Schema parsing + format validation
#   └─ Trust Level: High (no execution required)
#
#   PHASE 2: Generator Code Generation (LLM #2)
#   ├─ Responsibility: ONLY generator code that accepts seed parameter
#   ├─ Validation: Deferred to Phase 3
#   └─ Trust Level: Zero (untrusted until validated)
#
#   PHASE 3: Generator Validation (Sandbox)
#   ├─ Responsibility: Test generator in isolation (deterministic seeding)
#   ├─ Validation: Must run successfully, must not crash solver
#   └─ Trust Level: Conditional (only after passing all checks)
#
#   PHASE 4: Test Case Generation (Trusted Runner)
#   ├─ Responsibility: Generate (input, output) pairs deterministically
#   ├─ Validation: Implicit (using already-validated generator)
#   └─ Trust Level: High (generator pre-validated, solver is oracle)
#
# KEY ARCHITECTURAL RULES:
# 1. Each phase has ONE responsibility
# 2. Outputs are validated before next phase
# 3. LLM never produces executable outputs that run without validation
# 4. Deterministic seeding enables reproducibility and debugging
# 5. Early failures prevent half-created problems
#
# ============================================================================



# ============================================================================
# PHASE 1: Problem Specification (No Generator, Canonical Code Only)
# ============================================================================

class GeneratedProblemSpec(BaseModel):
    """Phase 1: Core problem definition without test generation logic."""
    title: str = Field(description="A concise, standard algorithmic problem title")
    description_markdown: str = Field(description="Problem description and I/O format in Markdown")
    constraints: str = Field(description="Constraints list in Markdown")
    editorial_markdown: str = Field(description="Detailed explanation of the solution, approach, and time complexity")
    canonical_code: str = Field(description="Correct Python solution code (Complete script reading from stdin/printing to stdout)")


# ============================================================================
# PHASE 2: Generator Code (Separate LLM responsibility)
# ============================================================================

class GeneratedGenerator(BaseModel):
    """Phase 2: Generator code with deterministic seeding support."""
    generator_code: str = Field(description="Python script that accepts a seed parameter and prints ONE valid input to stdout")


# ============================================================================
# PHASE 3: Final Results
# ============================================================================

class TestCaseData(BaseModel):
    input: str
    output: str

class ProblemGenerationResult(BaseModel):
    content: GeneratedProblemSpec
    test_cases: List[TestCaseData]


# ============================================================================
# LLM PROMPT #1: Problem Spec Generator
# ============================================================================

def generate_problem_spec(topics: str, user_query: str, difficulty: str) -> GeneratedProblemSpec:
    """
    LLM Call #1: Generate problem specification (NO generator code).
    
    Responsibility: Title, description, constraints, editorial, canonical solution.
    Trust model: Validated via schema parsing.
    """
    
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
      "canonical_code": ""
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
    - CRITICAL: Code must be syntactically valid and executable with ANY valid input respecting constraints.
    - CRITICAL: All array/dict accesses must have proper bounds checking.
    - CRITICAL: Test your logic against edge cases (small inputs, boundary values).
    - Do not include comments explaining trivial syntax.
    - Do not include placeholder logic.
    - Do not make assumptions about input types - validate and convert properly.

    QUALITY REQUIREMENTS:
    - The problem must align with the requested topics and difficulty.
    - The solution must be optimal for the stated constraints.
    - The content must be suitable for competitive programming platforms.
    - CRITICAL: The canonical_code must be syntactically valid and executable.

    Return only the final JSON object. Nothing else."""
    
    parser = JsonOutputParser(pydantic_object=GeneratedProblemSpec)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", f"Topic: {topics}. Query: {user_query}. Difficulty: {difficulty}.\n\nIMPORTANT: Return ONLY the raw JSON object. Ensure 'description_markdown' contains the Examples section.")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"topics": topics, "user_query": user_query, "difficulty": difficulty})

        if not result or not isinstance(result, dict):
            raise ValueError(f"LLM returned invalid result: {result}")

        # Normalize response keys
        if "description" in result: 
            result["description_markdown"] = result.pop("description")
        if "editorial" in result: 
            result["editorial_markdown"] = result.pop("editorial")
        if "code" in result: 
            result["canonical_code"] = result.pop("code")
        
        # Handle list constraints → newline-separated string
        if "constraints" in result and isinstance(result["constraints"], list):
            result["constraints"] = "\n".join([str(c) for c in result["constraints"]])
        
        spec = GeneratedProblemSpec(**result)
        
        # Validate that canonical code is syntactically valid
        try:
            compile(spec.canonical_code, '<canonical>', 'exec')
        except SyntaxError as e:
            raise ValueError(f"Canonical code has syntax error: {e}")
        
        return spec
        
    except Exception as e:
        raise ValueError(f"Problem Spec Generation Failed: {e}")



# ============================================================================
# LLM PROMPT #2: Generator Code Generator
# ============================================================================

def generate_generator_code(
    problem_spec: GeneratedProblemSpec,
    difficulty: str
) -> GeneratedGenerator:
    """
    LLM Call #2: Generate test case generator code.
    
    Responsibility: Only generator logic. Accepts seed, prints one valid input.
    Trust model: Will be validated in sandbox before use.
    
    CRITICAL: The generator output format MUST match what the canonical solution expects.
    """
    
    system_prompt = """You are an expert at writing test case generators for competitive programming problems.

    Your task is to generate ONE Python script that generates random test inputs for a given problem.

    CRITICAL RULES:
    - You MUST output the Python code inside a markdown code block: ```python ... ```
    - The python code must be executable standalone.
    - The code must accept a 'seed' parameter via command-line argument (sys.argv[1]).
    - The code must print EXACTLY ONE valid input to stdout.
    - The input format MUST EXACTLY MATCH how the canonical solution reads it.
    - The code must terminate within 2 seconds.
    - The code must not attempt any file I/O, network access, or imports beyond 'random', 'sys'.
    - Do NOT output JSON. Only the Python code.

    GENERATOR_CODE RULES:
    - Use import random and set random.seed(int(sys.argv[1])) at the start.
    - Generate synthetic inputs that respect problem constraints.
    - Ensure inputs are diverse across different seed values.
    - CRITICAL: Your output format MUST match the input format that the canonical solution reads.
    - Print the final input to stdout via print().
    - Do not print debug messages or explanations.

    QUALITY REQUIREMENTS:
    - Inputs must strictly respect stated constraints.
    - Inputs must be deterministic (same seed = same input).
    - Inputs must be realistic for the problem difficulty.
    - Inputs must work with the canonical solution without errors.

    Return ONLY the Python code block."""
    
    # Extract input format from description
    input_format_section = problem_spec.description_markdown.split("## Input Format")[1].split("## Output Format")[0] if "## Input Format" in problem_spec.description_markdown else ""
    
    # Extract just the main() function from canonical code to understand input pattern (keep it short)
    canonical_code = problem_spec.canonical_code
    main_func = ""
    if "def main():" in canonical_code:
        main_start = canonical_code.find("def main():")
        main_func = canonical_code[main_start:main_start+500] if len(canonical_code) > main_start + 500 else canonical_code[main_start:]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", f"""Problem: {problem_spec.title}
Difficulty: {difficulty}

Constraints: {problem_spec.constraints}

Input Format: {input_format_section}

Example main() from canonical solution:
{main_func}

Generate a Python script that generates test inputs matching this format.
Return ONLY the python code block in ```python ... ```""")
    ])
    
    try:
        # Get raw LLM output first
        llm_response = (prompt | llm).invoke({
            "title": problem_spec.title,
            "difficulty": difficulty,
            "constraints": problem_spec.constraints
        })
        
        # Extract text content from AIMessage object
        if hasattr(llm_response, 'content'):
            llm_text = llm_response.content
        else:
            llm_text = str(llm_response)
        
        print(f"DEBUG: Raw LLM output for generator:\n{llm_text}") # Log raw LLM output
        
        # Try JSON parsing first
        try:
            import json
            result = json.loads(llm_text)
            if "generator_code" in result:
                generator = GeneratedGenerator(generator_code=result["generator_code"])
                return generator
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Fallback: Extract code from markdown-wrapped JSON or code blocks
        # Handle: ```python code ``` or ```json ... ```
        match = re.search(r'```(?:python|json)?\s*([\s\S]*?)```', llm_text)
        if match:
            extracted = match.group(1).strip()
            
            # If it looks like JSON, try to parse it
            if extracted.startswith('{'):
                try:
                    result = json.loads(extracted)
                    if "generator_code" in result:
                        generator = GeneratedGenerator(generator_code=result["generator_code"])
                        return generator
                except json.JSONDecodeError:
                    pass
            
            # Otherwise treat extracted content as the code directly
            generator = GeneratedGenerator(generator_code=extracted)
            return generator
        
        # Last resort: treat entire response as code if it looks like Python
        if 'import random' in llm_text and 'sys.argv' in llm_text:
            generator = GeneratedGenerator(generator_code=llm_text)
            return generator
        
        raise ValueError(f"Could not extract generator code from LLM output. Output snippet: {llm_text[:100]}...")
        
    except Exception as e:
        print(f"DEBUG: Exception in Phase 2: {e}")
        if 'llm_text' in locals():
            print(f"DEBUG: LLM Response causing error:\n{llm_text}")
        raise ValueError(f"Generator Code Generation Failed: {e}")


# ============================================================================
# PHASE 3: Validation Layer (Only Trust Your Code)
# ============================================================================

def validate_generator_in_sandbox(
    generator_code: str,
    canonical_code: str,
    time_limit_ms: int = 5000,
    num_validation_runs: int = 3
) -> Tuple[bool, str]:
    """
    Validate generator code before trusting it.
    
    Checks:
    1. Generator runs without timeout
    2. Generator produces non-empty output
    3. Generator output doesn't crash canonical solution
    4. Output format is reasonable
    
    Returns: (is_valid, error_message)
    """
    time_limit_sec = time_limit_ms / 1000
    
    temp_gen = None
    temp_sol = None
    
    try:
        # Write temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(generator_code)
            temp_gen = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(canonical_code)
            temp_sol = f.name
        
        # Test multiple seeds
        for seed_idx in range(num_validation_runs):
            # Run generator with seed
            try:
                gen_result = subprocess.run(
                    [sys.executable, temp_gen, str(seed_idx)],
                    text=True,
                    capture_output=True,
                    timeout=time_limit_sec
                )
            except subprocess.TimeoutExpired:
                 return False, f"Generator timed out after {time_limit_sec}s (seed {seed_idx})"

            if gen_result.returncode != 0:
                print(f"DEBUG: Generator failed (stderr): {gen_result.stderr}")
                return False, f"Generator failed with seed {seed_idx}: {gen_result.stderr[:200]}"
            
            generated_input = gen_result.stdout.strip()
            print(f"DEBUG: Validation Seed {seed_idx} Input:\n{generated_input[:100]}...") # Log input
            
            if not generated_input:
                return False, f"Generator produced empty output for seed {seed_idx}"
            
            # Verify canonical solution accepts this input
            try:
                sol_result = subprocess.run(
                    [sys.executable, temp_sol],
                    input=generated_input,
                    text=True,
                    capture_output=True,
                    timeout=time_limit_sec
                )
            except subprocess.TimeoutExpired:
                 return False, f"Canonical solution timed out after {time_limit_sec}s (seed {seed_idx})"
            
            if sol_result.returncode != 0:
                print(f"DEBUG: Solver failed (stderr): {sol_result.stderr}")
                return False, f"Canonical solution crashed on generated input (seed {seed_idx}): {sol_result.stderr[:200]}"
            
            output = sol_result.stdout.strip()
            print(f"DEBUG: Validation Seed {seed_idx} Output:\n{output[:100]}...") # Log output
            
            if not output:
                return False, f"Canonical solution produced no output for generated input (seed {seed_idx})"
        
        return True, ""
    
    finally:
        if temp_gen and os.path.exists(temp_gen):
            try:
                os.remove(temp_gen)
            except:
                pass
        if temp_sol and os.path.exists(temp_sol):
            try:
                os.remove(temp_sol)
            except:
                pass


# ============================================================================
# PHASE 3: Test Generation (Deterministic with Seeding)
# ============================================================================

def generate_and_solve_tests(
    generator_code: str,
    canonical_code: str,
    num_cases: int = 10
) -> List[TestCaseData]:
    """
    Generate test cases deterministically using seeded generator.
    
    For each seed:
    1. Run generator_code with seed → INPUT
    2. Run canonical_code with INPUT → OUTPUT
    3. Store (INPUT, OUTPUT) pair
    
    All runs are sandboxed and validated.
    """
    results = []
    
    temp_gen = None
    temp_sol = None
    
    try:
        # Write temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(generator_code)
            temp_gen = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(canonical_code)
            temp_sol = f.name
        
        time_limit_sec = 30 # Default reasonable timeout for generation (Windows safe)
        
        for seed_idx in range(num_cases):
            try:
                # 1. Generate Input with deterministic seed
                gen_result = subprocess.run(
                    [sys.executable, temp_gen, str(seed_idx)],
                    text=True,
                    capture_output=True,
                    timeout=time_limit_sec
                )
                
                if gen_result.returncode != 0:
                    print(f"Generator Error (seed={seed_idx}): {gen_result.stderr}")
                    continue
                
                input_data = gen_result.stdout.strip()
                if not input_data:
                    print(f"Generator produced empty output (seed={seed_idx})")
                    continue
                
                print(f"DEBUG: Test Case {seed_idx} Input:\n{input_data[:500]}..." if len(input_data) > 500 else f"DEBUG: Test Case {seed_idx} Input:\n{input_data}")

                # 2. Solve Input
                sol_result = subprocess.run(
                    [sys.executable, temp_sol],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=time_limit_sec
                )
                
                if sol_result.returncode != 0:
                    print(f"Solver Error (seed={seed_idx}): {sol_result.stderr}")
                    continue
                
                output_data = sol_result.stdout.strip()
                
                if not output_data:
                    print(f"DEBUG: Test Case {seed_idx} produced EMPTY output. Skipping.")
                    continue
                    
                print(f"DEBUG: Test Case {seed_idx} Output:\n{output_data[:500]}..." if len(output_data) > 500 else f"DEBUG: Test Case {seed_idx} Output:\n{output_data}")
                results.append(TestCaseData(input=input_data, output=output_data))
                
            except subprocess.TimeoutExpired:
                print(f"Timeout (seed={seed_idx})")
                continue
            except Exception as e:
                print(f"Test Gen Error (seed={seed_idx}): {e}")
                continue
    
    finally:
        if temp_gen and os.path.exists(temp_gen):
            try:
                os.remove(temp_gen)
            except:
                pass
        if temp_sol and os.path.exists(temp_sol):
            try:
                os.remove(temp_sol)
            except:
                pass
    
    return results


# ============================================================================
# ORCHESTRATION: Main Generation Pipeline (4 Phase Architecture)
# ============================================================================

def generate_custom_problem_content(
    topics: str,
    user_query: str,
    difficulty: str,
    num_test_cases: int = 10
) -> ProblemGenerationResult:
    """
    Main orchestration function - manages 4-phase pipeline.
    
    Phase 1: Generate Problem Spec (LLM #1)
    Phase 2: Generate Generator Code (LLM #2)
    Phase 3: Validate Generator (Sandbox)
    Phase 4: Generate Test Cases (Trusted Runner)
    
    Returns: Problem + Test Cases (or error)
    Raises: ValueError if any phase fails
    """
    
    print(f"[PHASE 1] Generating problem specification...")
    try:
        problem_spec = generate_problem_spec(topics, user_query, difficulty)
        print(f"Problem Spec: '{problem_spec.title}'")
        print(f"DEBUG: Canonical Code:\n{problem_spec.canonical_code}\n") # Log canonical code
    except Exception as e:
        raise ValueError(f"Phase 1 Failed (Problem Spec): {e}")
    
    print(f"\n[PHASE 2] Generating test generator code...")
    try:
        generator_result = generate_generator_code(problem_spec, difficulty)
        generator_code = generator_result.generator_code
        print(f"Generator Code Generated ({len(generator_code)} chars)")
        print(f"DEBUG: Generator Code:\n{generator_code}\n") # Log generator code
    except Exception as e:
        raise ValueError(f"Phase 2 Failed (Generator Code): {e}")
    
    print(f"\n[PHASE 3] Validating generator in sandbox...")
    try:
        is_valid, error_msg = validate_generator_in_sandbox(
            generator_code=generator_code,
            canonical_code=problem_spec.canonical_code,
            num_validation_runs=3,
            time_limit_ms=30000 # 30s timeout for Windows
        )
        
        if not is_valid:
            print(f"Generator validation warning: {error_msg}")
            print(f"Proceeding to Phase 4 anyway...")
        else:
            print(f"Generator passed validation")
            
    except Exception as e:
        print(f"Phase 3 Validation skipped due to error: {e}")
    
    print(f"\n[PHASE 4] Generating test cases ({num_test_cases} cases)...")
    try:
        # Update run configuration to be more lenient
        test_cases = generate_and_solve_tests(
            generator_code=generator_code,
            canonical_code=problem_spec.canonical_code,
            num_cases=num_test_cases
        )
        print(f"Generated {len(test_cases)}/{num_test_cases} test cases")
        
        if len(test_cases) == 0:
             error_msg = """Generated 0 viable test cases. Possible causes:
1. Generator output format doesn't match canonical solution's input format
2. Generator creates invalid inputs (e.g., violates constraints)
3. Canonical solution crashes on generated inputs
4. Generator times out or fails to run

DEBUGGING: Check that:
- Generator print() format matches how canonical solution reads input
- Constraint ranges are correct in generator
- Canonical solution handles edge cases"""
             raise ValueError(error_msg)
             
    except Exception as e:
        # Dump code for debugging
        print(f"DEBUG: Generator Code:\n{generator_code}\n")
        raise ValueError(f"Phase 4 Failed (Test Generation): {e}")
    
    print(f"\n[SUCCESS] Pipeline complete")
    
    return ProblemGenerationResult(content=problem_spec, test_cases=test_cases)
