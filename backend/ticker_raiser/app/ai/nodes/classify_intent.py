from app.ai.graph.state import InputState,IntentDecision
from app.ai.llm import llm
from langchain_core.prompts import ChatPromptTemplate

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def classify_intent_node(state: InputState) -> dict:
    """
    Classify user intent using intelligent LLM-based analysis.
    Routes to the most appropriate handler based on user's actual intent.
    """
    user_query = state.get("user_query", "") or ""
    user_code = state.get("user_code", "") or ""
    system_prompt = """You are the Router Brain for an AI Coding Tutor.
Your goal is to map the user's request to EXACTLY ONE of the following 4 handlers.

Analyze the user's text and the presence of code to decide.

### 1. general_concept_help (PRIORITY - Check this FIRST)
**Definition:** The user is asking about a programming concept, language syntax, algorithm theory, OR a DIFFERENT PROBLEM in isolation.
**The Litmus Test:** If you copy-pasted this question into a conversation about a different problem, would it still make sense?
* YES -> It is `general_concept_help`.
* NO  -> It is likely `how_to_solve_this`.

**IMPORTANT:** If the user mentions a DIFFERENT problem by name (e.g. "Two Sum", "LeetCode 1", "the array problem"), this is ALWAYS `general_concept_help` because they are asking about that problem in isolation, not about the current problem.

**Examples of general_concept_help:**
* "How does a hash map work internally?"
* "What is the syntax for slicing arrays in Python?"
* "Explain the time complexity of QuickSort."
* "How to solve two sum?" (Different problem -> general concept)
* "How to solve the shortest path problem?" (Different problem -> general concept)
* "How to use the map() function?"
* "What is Union-Find?"
* "What is a DFS/BFS?" (Concept, not tied to current problem)

### 2. clarification_request
**Definition:** The user is confused about the *CURRENT problem statement* itself. They need help reading or interpreting the CURRENT problem's requirements.
**The Litmus Test:** Does the answer require reading the CURRENT problem description text? Does it mention constraints, input format, or output format of THIS problem?
* YES -> It is `clarification_request`.
**Examples:**
* "Is the input array always sorted?"
* "What does it mean by 'non-decreasing order'?"
* "Can the grid contain negative numbers?"
* "What are the constraints exactly?"

### 3. why_my_code_failed (REQUIRES CODE + ERROR) - STRICT RULES
**Definition:** The user has ACTUALLY PROVIDED CODE and is asking why it fails/is incorrect/is slow/is buggy.
**⚠️ CRITICAL - BOTH CONDITIONS REQUIRED (Not OR, not one of them - BOTH):**
1. Code is present in the message (actual code, not just explanation)
2. User is reporting a failure/error/asking "why doesn't this work?" (not just planning)

**MANDATORY CHECKLIST before deciding `why_my_code_failed`:**
- [ ] Is there actual code (syntax, variables, logic) in the message? (Not just "I will use X")
- [ ] Is there a failure statement? ("doesn't work", "getting TLE", "got wrong answer", "why is this", "bug", etc.)
- If BOTH checkboxes are YES -> `why_my_code_failed`
- If EITHER is NO -> NOT `why_my_code_failed` (route to `how_to_solve_this` instead)

** EXAMPLES of why_my_code_failed (code + error):**
* "Here's my code: [actual code]. Why am I getting TLE?" 
* "My output is 5 but expected 10. [code snippet]"
* "What's the bug in this? [code]"
* "def solve(): return x. This is getting wrong answer, why?"

** NOT why_my_code_failed (EVEN if they talk about algorithms/approaches):**
* "I will use DSU to solve this" (no code, just planning)
* "i will connect the ones with DSU and will return unique parents count" (no code shown, just explaining algorithm)
* "Should I use DFS or BFS?" (no code, no error)
* "I'm thinking of using Union-Find" (strategy planning, not failure)
* "My approach is to iterate and count islands" (explaining strategy, no code present)

### 4. how_to_solve_this (The Fallback for THIS problem)
**Definition:** The user understands the CURRENT problem but doesn't know *how* to approach IT. They want hints, strategies, or an algorithm recommendation for *this specific task*.
**The Litmus Test:** Is the user asking "What do I do?" or "Is X the right approach?" for *THIS specific problem*? Are they stuck on THIS problem?
* YES -> It is `how_to_solve_this`.
**Examples:**
* "Should I use DP or Greedy for this?" (this = current problem)
* "I'm stuck, can you give me a hint?" (stuck on current)
* "How do I handle the edge case?" (current problem edge case)
* "How do I handle the edge case where N=1?"

###  CRITICAL TIE-BREAKING RULES 

**DECISION TREE (Follow in order):**

1. **HIGHEST PRIORITY - DIFFERENT PROBLEM MENTIONS:**
   If user asks about a DIFFERENT problem by name -> ALWAYS `general_concept_help`
   "How to solve Two Sum?", "How to solve the shortest path problem?" -> `general_concept_help`

2. **CHECK FOR ACTUAL CODE + ERROR (for why_my_code_failed):**
   ABSOLUTE RULE: If NO code present -> NEVER classify as `why_my_code_failed`
   
   Is there actual code in the message? (Not just "I will do X") -> YES/NO
   - If NO -> SKIP why_my_code_failed entirely, go to next rule
   - If YES -> Check: Is there a failure/error statement? ("doesn't work", "TLE", "wrong answer", "why", "bug")
     - Both code AND error -> `why_my_code_failed`
     - Code but no error -> NOT why_my_code_failed -> `how_to_solve_this`
   
   CRITICAL EXAMPLES:
   - "i will connect the ones with DSU and will return unique parents count" (NO code shown) -> NOT why_my_code_failed -> `how_to_solve_this`
   - "I will use DSU to solve this" (strategy, no code) -> NOT why_my_code_failed -> `how_to_solve_this`
   - "yes it will be multiple disconnected graphs?" (NO code, question about problem) -> NOT why_my_code_failed -> `clarification_request`

3. **ABSTRACT CONCEPT vs STRATEGY with THIS problem:**
   "How do I use BFS?" (abstract concept) -> `general_concept_help`
   "Should I use BFS to solve this?" (THIS problem strategy) -> `how_to_solve_this`

4. **CLARIFICATION requires THIS problem statement context:**
   YES/NO questions about problem constraints/scope -> `clarification_request`
   Questions about what something means in the problem -> `clarification_request`
   Questions asking to clarify problem requirements -> `clarification_request`
   
   EXAMPLES:
   - "yes it will be multiple disconnected graphs?" (asking about problem scope) -> `clarification_request`
   - "What does 'island' mean?" (THIS problem concept) -> `clarification_request`
   - "Can the grid be empty?" (problem constraints) -> `clarification_request`
   - "Is the output always an integer?" (problem specification) -> `clarification_request`
   
   vs
   - "What is DSU?" (abstract algorithm, not about THIS problem) -> `general_concept_help`
   - "How does BFS work?" (abstract concept) -> `general_concept_help`

5. **STRATEGY DISCUSSION without code -> how_to_solve_this:**
   "I'm thinking of using X approach", "Would DSU work here?", "Should I use Union-Find?" -> `how_to_solve_this`

6. **GENERAL KEYWORDS signal general_concept_help:**
   "What is", "How to solve" + different problem, "Explain" + algorithm -> `general_concept_help`

###  ANTI-PATTERN: DO NOT DO THIS
These are the MOST COMMON mistakes. AVOID THEM:

1. **"Explaining algorithm = why_my_code_failed"** - WRONG!
   User: "i will connect the ones with DSU and will return unique parents count"
   WRONG CLASSIFICATION: `why_my_code_failed` (they're just explaining their approach)
   CORRECT CLASSIFICATION: `how_to_solve_this` (they're discussing strategy for THIS problem)
   CHECK: Is there code shown? NO -> NOT why_my_code_failed

2. **"Strategy planning = why_my_code_failed"** - WRONG!
   User: "I will use DSU to solve this"
   WRONG CLASSIFICATION: `why_my_code_failed` (they're planning, not reporting a failure)
   CORRECT CLASSIFICATION: `how_to_solve_this` (they're asking about approach)
   CHECK: Is there code? NO -> NOT why_my_code_failed

3. **"Question about problem = why_my_code_failed"** - WRONG!
   User: "yes it will be multiple disconnected graphs?"
   WRONG CLASSIFICATION: `why_my_code_failed` (no code at all, asking about problem scope)
   CORRECT CLASSIFICATION: `clarification_request` (asking about problem constraints)
   CHECK: Is there code? NO -> NEVER why_my_code_failed. Is this about THIS problem scope/constraints? YES -> `clarification_request`

4. **"Mentioning an algorithm = general_concept_help"** - WRONG (context matters)!
   User: "How should I use DSU for this problem?" (for THIS current problem)
   WRONG CLASSIFICATION: `general_concept_help`
   CORRECT CLASSIFICATION: `how_to_solve_this` (about THIS problem strategy)
   CHECK: Is "this" referring to the CURRENT problem? YES -> `how_to_solve_this`, not `general_concept_help`

### OUTPUT FORMAT
First provide your reasoning (1-2 sentences explaining which rule applies).
Then respond with ONLY the intent name: general_concept_help, clarification_request, why_my_code_failed, or how_to_solve_this
"""

    structured_llm = llm.with_structured_output(IntentDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", f"User Query: {user_query}\n\nCode Present: {'Yes' if user_code.strip() else 'No'}")
    ])

    try:
        
        result: IntentDecision = (prompt | structured_llm).invoke({})
        intent = result.intent
        
    except Exception as e:
        logger.error(f"[CLASSIFY] Classification error: {str(e)}", exc_info=True)
        intent = "how_to_solve_this"
        logger.warning(f"[CLASSIFY] Decision: Falling back to default intent '{intent}' due to error")
        result = IntentDecision(intent=intent, confidence=0.0)

    return_dict = {
        **state,
        "user_intent": result.intent
    }
    return return_dict