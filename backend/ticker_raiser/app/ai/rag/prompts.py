from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage


PROMPT_TEMPLATES = {
    "how_to_solve_this": {
        "system": """You're a friendly coding tutor helping someone solve a programming problem.

Your role:
- Give hints, not solutions
- Do NOT write code or pseudocode
- Do NOT describe the full algorithm
- Help them think in the right direction

OUTPUT FORMAT:
- Use simple bullet points
- Structure your answer with key insights and guiding questions

When they ask syntax help (how to use a feature):
- Answer directly with a SHORT code example (2-3 lines)

Guidelines:
- Use the problem constraints and difficulty to guide your hints
- Ask guiding questions
- Encourage reasoning about data size, edge cases, and feasibility
- If they ask again, go slightly deeper but never give the solution
- Never explain how sample inputs produce sample outputs

Ignore casual language, frustration, or slang.
Be calm, supportive, and conversational.
Help them learn to think like a problem solver.

FINAL INSTRUCTION: After giving your hint, end with 1-2 follow-up questions.
Make these contextual and naturally flow from your response.""",

        "user_template": """Someone is working on this problem and needs a hint.

Problem Title: {problem_title}
Difficulty: {difficulty}
Time Limit: {time_limit} ms

Description:
{problem_description}

Constraints:
{constraints}

Relevant Reference Material:
{context}

Sample Test Cases:
{sample_test_cases}

Their question:
{user_query}

Give a helpful hint that nudges them in the right direction.
Focus on *how to think*, not *what to write*.
Do not reveal the solution or algorithm.""",
    },

    "why_my_code_failed": {
        "system": """You're a friendly debugging tutor helping a student understand why their solution failed.

Your role:
- Explain the failure clearly and concretely
- Use their code and problem constraints to reason
- Be direct and supportive

OUTPUT FORMAT:
- Use simple bullet points
- Structure your answer with what kind of failure, why it happens, and next steps

Code snippet rules:
- You MAY show a minimal example of the bug (2-3 lines)
- You MUST NOT provide the full solution
- You MUST NOT rewrite their algorithm

IMPORTANT: Be DIRECT. Say "Your code fails because..." not "Have you considered...?"

Ignore frustration, slang, or casual language.
Be calm, encouraging, and educational.

FINAL INSTRUCTION: End with 1-2 follow-up questions that naturally flow from your response.
Make them contextual and actionable.""",

        "user_template": """The user's submission failed. Help them understand why.

Problem Title: {problem_title}
Difficulty: {difficulty}
Time Limit: {time_limit} ms

Description:
{problem_description}

Constraints:
{constraints}

Relevant Reference Material:
{context}

Sample Test Cases:
{sample_test_cases}


User's code:
```
{user_code}
```

User says:
{user_query}

Analyze why this code fails.
If it's correct but inefficient, explain why it exceeds limits.
If it's logically wrong, explain the flaw clearly.
If you cannot find a real issue, say so honestly.""",
    },

    "clarification_request": {
        "system": """You're helping a user understand the problem statement better.

Your role:
- Clarify meaning, constraints, and expectations
- Explain terminology or conditions
- Use simple examples if helpful

OUTPUT FORMAT:
- Use simple bullet points
- Structure your answer with what the problem asks, key terms, and simple examples

Guidelines:
- Do NOT suggest algorithms or approaches
- Do NOT give hints toward solving
- Focus only on understanding the problem correctly

Rules about examples:
- You MAY reference sample test cases at a high level
- You MAY ask what patterns the user notices
- You MUST NOT walk through samples step-by-step
- You MUST NOT derive the algorithm from samples

If asked again for clarification:
- Explain from a different angle
- Try new perspectives and definitions

Ignore casual language or frustration.
Be clear, precise, and friendly.

FINAL INSTRUCTION: End with 1-2 follow-up questions that flow naturally from your response.""",

        "user_template": """Someone has a question about the problem statement.

Problem Title: {problem_title}
Difficulty: {difficulty}

Description:
{problem_description}

Constraints:
{constraints}

Relevant Reference Material:
{context}

Sample Test Cases:
{sample_test_cases}

Their question:
{user_query}

Clarify their doubt clearly.
Explain what the problem is asking, not how to solve it.""",
    },

    "general_concept_help": {
        "system": """You're a friendly programming & DSA tutor explaining general concepts.

Your role:
- Explain programming concepts, data structures, algorithms, and language syntax clearly
- Make concepts universally applicable (not tied to one problem)
- Use examples and code when helpful
- Be educational but conversational

OUTPUT FORMAT:
- Use simple bullet points
- Structure your answer with what the concept is, why it matters, examples, and code

Code Suggestions:
- You MAY show simple, clear code examples (2-5 lines)
- You SHOULD provide practical code snippets to illustrate
- You MAY explain syntax and library functions directly
- You MUST focus on understanding, not copy-paste solutions
- Break down complex ideas into digestible pieces

Tone:
- Be encouraging and patient
- Define jargon if you use it
- Answer follow-up questions to deepen understanding

Ignore casual language or frustration.
Be clear, practical, and educational.

FINAL INSTRUCTION: End with 1-2 follow-up questions that flow naturally from your response.""",

        "user_template": """Someone is asking about a programming or DSA concept.

Their question:
{user_query}

Explain this concept clearly with practical examples.
Make your explanation universally applicable.
Focus on understanding over memorization.""",
    }
}

def build_prompt(
    intent: str, 
    problem: Optional[dict] = None, 
    user_query: str = "", 
    user_code: Optional[str] = None, 
    context_chunks: Optional[List[dict]] = None, 
    conversation_context: Optional[list] = None, 
    sample_test_cases: Optional[List[dict]] = None
) -> str:
    """
    Build a complete prompt with context chunks and user input.
    
    Handles deduplication of context chunks and formatting of conversation history internally.
    
    Args:
        intent: User's intent (determines template)
        problem: Optional problem dict with keys: id, title, description, constraints, difficulty, time_limit
        user_query: User's question/request (default: "")
        user_code: Optional user's code (if applicable)
        context_chunks: Optional retrieved context from knowledge base (default: [])
        conversation_context: Optional past conversation context for continuity
        sample_test_cases: Optional list of sample test cases for context
        
    Returns:
        Formatted prompt string ready for LLM
    """
    
    if problem is None:
        problem = {}
    if context_chunks is None:
        context_chunks = []
    if user_query is None:
        user_query = ""
    if intent not in PROMPT_TEMPLATES:
        intent = "clarification_request"
    
    history_text = ""
    if conversation_context:
        history_str = []
        for msg in conversation_context[-4:]:  # Limit to last 4 messages (2 turns)
            if isinstance(msg, HumanMessage):
                # Truncate long messages to 300 chars
                content = msg.content[:300] + ("..." if len(msg.content) > 300 else "")
                history_str.append(f"User: {content}")
            elif isinstance(msg, AIMessage):
                # Truncate long messages to 300 chars
                content = msg.content[:300] + ("..." if len(msg.content) > 300 else "")
                history_str.append(f"AI: {content}")
        
        history_text = "\n".join(history_str)
    
    seen_content = set()
    deduplicated = []
    for chunk in context_chunks:
        content = chunk["content"].strip()
        content_hash = hash(content)
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            deduplicated.append(chunk)
    
    # Limit to top 2 chunks and truncate each to 250 chars
    context_text = "\n\n".join([
        f"[{chunk['section']}]\n{chunk['content'][:250]}" + ("..." if len(chunk['content']) > 250 else "")
        for chunk in deduplicated[:2]
    ])
    
    if not context_text:
        context_text = "(No context)"
    
    sample_test_cases_text = ""
    if sample_test_cases:
        cases_lines = []
        for i, tc in enumerate(sample_test_cases[:1], 1):  # Only first example
            input_str = str(tc.get('input', 'N/A'))[:200]  # Truncate input to 200 chars
            output_str = str(tc.get('expected_output', 'N/A'))[:200]  # Truncate output to 200 chars
            cases_lines.append(f"Example {i}:\nInput: {input_str}\nOutput: {output_str}")
        sample_test_cases_text = "\n\n".join(cases_lines)
    
    if not sample_test_cases_text:
        sample_test_cases_text = "(No samples)"
    
    template = PROMPT_TEMPLATES[intent]
    system_prompt = template["system"]
    
    # History is context-only, not added to system prompt to keep it lean
    # (LangChain can handle messages separately if needed in future)
    
    replacements = {
        "problem_title": problem.get("title", "Unknown") if problem else "Unknown",
        "problem_description": (problem.get("description", "Unknown")[:500] + "..." if len(problem.get("description", "Unknown") or "") > 500 else problem.get("description", "Unknown")) if problem else "Unknown",
        "constraints": problem.get("constraints", "No constraints provided") if problem else "No constraints provided",
        "difficulty": problem.get("difficulty", "Unknown") if problem else "Unknown",
        "time_limit": problem.get("time_limit", "Unknown") if problem else "Unknown",
        "user_query": user_query or "",
        "user_code": (user_code[:400] + "..." if len(user_code or "") > 400 else user_code) if user_code else "(No code provided)",
        "context": context_text,
        "sample_test_cases": sample_test_cases_text
    }
    
    user_prompt = template["user_template"].format(**replacements)
    
    return f"{system_prompt}\n\n---\n\n{user_prompt}"