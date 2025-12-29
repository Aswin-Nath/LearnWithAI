import os
from typing import Optional, List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, AIMessage

# RETRIEVER CLASS 

class ChromaRetriever:
    """Handles all semantic retrieval from persistent Chroma store."""
    
    def __init__(self):
        # Point to the app/chroma_db folder
        # File path: app/graphs/main/rag_layer.py
        # Target: app/chroma_db
        current_file = os.path.abspath(__file__)
        # Navigate: rag_layer.py -> main -> graphs -> app
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        self.persist_dir = os.path.join(app_dir, "chroma_db")
        print(f"🔗 RAG Layer connecting to DB at: {self.persist_dir}")
        
        self.embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
        self.problem_collections = {}  # Cache for opened collections
    
    def _get_collection(self, problem_id: int):
        """Get or load a problem's Chroma collection."""
        if problem_id not in self.problem_collections:
            collection_name = f"problem_{problem_id}"
            self.problem_collections[problem_id] = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir
            )
        return self.problem_collections[problem_id]
    
    def retrieve(self, problem_id: int, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve top-k most relevant chunks for a query.
        
        Args:
            problem_id: Problem ID to search within
            query: User query or code to search for
            k: Number of results to return
            
        Returns:
            List of dicts with keys: content, section, distance
        """
        try:
            collection = self._get_collection(problem_id)
            results = collection.similarity_search_with_score(query, k=k)
            
            chunks = []
            for doc, distance in results:
                chunks.append({
                    "content": doc.page_content,
                    "section": doc.metadata.get("section", "Unknown"),
                    "distance": distance,
                    "problem_id": problem_id
                })
            return chunks
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

retriever = ChromaRetriever()
# INTENT-TO-SECTIONS 
INTENT_TO_SECTIONS = {
    "how_to_solve_this": [
        "Intuition",
        "Approach",
        "Explanation",
        "Strategy",
        "Key Insight"
    ],
    
    "why_my_code_failed": [
        "Edge Cases",
        "Pitfalls",
        "Why It Fails",
        "Common Mistakes",
        "When Not to Use"
    ],
    
    "explain_my_code": [
        "Code",
        "Explanation",
        "Time Complexity",
        "Space Complexity",
        "Why It Works"
    ],
    
    "validate_my_approach": [
        "Why It Works",
        "Time Complexity",
        "Space Complexity",
        "Constraints",
        "When to Use",
        "Approach"
    ],
    
    "clarification_request": [
        "Problem Description",
        "Constraints",
        "Example",
        "Input/Output",
        "Observation"
    ]
}


def filter_by_section(chunks: List[dict], allowed_sections: List[str]) -> List[dict]:
    """
    Filter retrieved chunks to only those matching allowed sections.
    
    Matching is fuzzy (substring match, case-insensitive) to handle
    variations like "Edge Cases" vs "Edge Cases & Common Pitfalls"
    
    Args:
        chunks: List of dicts with 'section' key
        allowed_sections: List of section keywords to keep
        
    Returns:
        Filtered list, sorted by distance (relevance)
    """
    filtered = []
    
    for chunk in chunks:
        section = chunk["section"].lower()
        # Fuzzy match: if any allowed section keyword appears in chunk section
        if any(keyword.lower() in section for keyword in allowed_sections):
            filtered.append(chunk)
    
    # Sort by distance (lower = better match)
    filtered.sort(key=lambda x: x["distance"])
    return filtered


# PROMPT TEMPLATES (Teaching Style per Intent)
# Key: Different intents need different teaching styles
# how_to_solve → Progressive hints (don't give away)
# why_failed → Debug explanation (identify + guide fix)
# explain → Walkthrough (line by line)
# validate → Confirmation (yes/no + reasoning)
# clarification → Factual (answer directly)

PROMPT_TEMPLATES = {
    "how_to_solve_this": {
        "system": """You're a friendly coding tutor helping someone solve a problem.

Give hints, not solutions. Keep it conversational and natural.
Ignore casual language, frustration, slang - just focus on helping them think through the problem.

- Start with what approach they should think about
- Ask guiding questions to help them think through it  
- If they ask for more help, go deeper
- Use simple language, be encouraging
- Respond naturally even if they're frustrated or casual with their tone

Never hand them code. Help them learn to think like a programmer.""",
        
        "user_template": """Someone's working on a problem and needs a hint.

Problem: {problem_description}

They're asking: {user_query}

Give them a helpful hint. Be warm and encouraging. Help them think through the approach without giving away the solution. Ignore their tone/language - respond helpfully regardless."""
    },
    
    "why_my_code_failed": {
        "system": """You're a friendly code debugging tutor. Help them understand what went wrong with their code.

Ignore frustrated tone, casual language, profanity - just focus on being helpful.
Keep it conversational and natural:

- First, explain what the issue is in simple terms
- Then walk through why it happens using their code
- Give a concrete example showing the problem
- Finally suggest how to fix it

Don't be robotic or formal. Be warm, encouraging, and helpful regardless of how they ask.""",
        
        "user_template": """Their code has a bug. Let's figure out what it is.

Problem: {problem_description}

Their code:
```
{user_code}
```

They're saying: {user_query}

Constraints: 1 ≤ N ≤ 100, inputs are valid integers

Help them understand what went wrong. Be natural and conversational. Respond helpfully even if they're using casual/frustrated language. If you can't find a real bug, just let them know."""
    },
    
    "explain_my_code": {
        "system": """You're explaining someone's code to them in a friendly, natural way.

Ignore casual language, slang, or frustrated tone - just focus on being helpful.

Walk them through what their code does:
- What's the overall strategy?
- How does each part work?
- Is it correct? Why?
- How fast/efficient is it?

Be conversational, not robotic. Use simple terms. Be encouraging. Respond helpfully regardless of their tone.""",
        
        "user_template": """Someone wants you to explain their code.

Problem: {problem_description}

Their code:
```
{user_code}
```

They want to know: {user_query}

Explain how their code works in a natural, friendly way. Walk through the logic and help them understand why it works. Respond helpfully even if they're casual/frustrated with their language."""
    },
    
    "validate_my_approach": {
        "system": """You're helping someone validate if their approach solves the problem correctly.

IMPORTANT: Only VALIDATE and CRITIQUE - do NOT provide solutions or alternative code.

Ignore casual language, frustration, or slang - just focus on being honest and helpful.

Check:
- Does it solve the problem correctly?
- Will it handle all the constraints?
- Is it fast enough?
- Are there obvious edge cases it misses?

If the approach is wrong:
- Explain why it doesn't work
- Point out what's missing or incorrect
- Suggest what to think about (but don't code it for them)

If the approach is right:
- Affirm that it works
- Mention why it's good

CRITICAL: Never provide working code or complete solutions. Just validate/critique their approach.""",
        
        "user_template": """Someone wants you to review if their approach works.

Problem: {problem_description}

Their code/approach:
{user_code}

They're asking: {user_query}

Tell them honestly: does this approach solve the problem? Will it work for all cases? Is it efficient enough?
If it's wrong, explain why and what they should think about instead.
DO NOT provide alternative code or solutions - just validate/critique their approach.
Be natural and friendly. Respond helpfully even if they're casual/frustrated."""
    },
    
    "clarification_request": {
        "system": """Someone's confused about the problem and needs clarification.

Ignore casual language, frustration, or slang - just answer their question clearly.
Answer their question directly and clearly. Use examples if it helps explain.
Keep it simple and friendly. Don't give away the solution - just clarify what the problem is asking.

Respond helpfully regardless of their tone.""",
        
        "user_template": """Someone's asking about the problem.

Problem: {problem_description}

Their question: {user_query}

Answer their question clearly and directly. Use a simple example if it helps explain. Respond helpfully even if they're casual/frustrated with their language."""
    }
}


# DEDUPLICATION (Prevent repetition in context)

def deduplicate_context(chunks: List[dict]) -> List[dict]:
    """
    Remove duplicate or near-identical chunks from context.
    
    This prevents the LLM from seeing the same idea repeated
    across multiple chunks, which causes it to repeat itself.
    
    Args:
        chunks: List of context chunks
        
    Returns:
        Deduplicated list, preserving order
    """
    seen_content = set()
    deduplicated = []
    for chunk in chunks:
        content = chunk["content"].strip()
        content_hash = hash(content)
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            deduplicated.append(chunk)
    return deduplicated


# PROMPT BUILDER (Assembles prompt with context)

def format_chat_history(messages: list) -> str:
    """Convert message objects into a string for the LLM prompt."""
    history_str = []
    # Take last 6 turns (3 User + 3 AI) for context
    relevant_history = messages[:-1][-6:] 

    for msg in relevant_history:
        if isinstance(msg, HumanMessage):
            history_str.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history_str.append(f"AI: {msg.content}")

    return "\n".join(history_str)

def build_prompt(intent: str, problem: dict, user_query: str, user_code: Optional[str], context_chunks: List[dict], conversation_context: list = None) -> str:
    """
    Build a complete prompt with context chunks and user input.
    
    Args:
        intent: User's intent (determines template)
        problem: Problem description dict
        user_query: User's question/request
        user_code: User's code (if applicable)
        context_chunks: Retrieved context from knowledge base
        conversation_context: Optional past conversation context for continuity
        
    Returns:
        Formatted prompt string ready for LLM
    """
    
    if intent not in PROMPT_TEMPLATES:
        intent = "clarification_request"  # Fallback
    
    # 1. Format History
    history_text = ""
    if conversation_context:
        history_text = format_chat_history(conversation_context)
    
    template = PROMPT_TEMPLATES[intent]
    
    # Deduplicate context chunks to prevent repetition
    deduplicated = deduplicate_context(context_chunks)
    
    # Build context string from chunks
    context_text = "\n\n".join([
        f"[{chunk['section']}]\n{chunk['content']}"
        for chunk in deduplicated[:3]  # Use top 3 chunks
    ])
    
    if not context_text:
        context_text = "(No specific context found - answer from general knowledge)"
    
    # Inject History into System Prompt
    system_prompt = template["system"]
    if history_text:
        system_prompt += f"\n\nCONVERSATION HISTORY:\n{history_text}\n\nUse this history to understand context (e.g. 'it', 'that code')."
    
    # Prepare substitutions
    replacements = {
        "problem_description": problem["description"] if problem else "Unknown",
        "user_query": user_query,
        "user_code": user_code or "(No code provided)",
        "context": context_text
    }
    
    # Format the user prompt
    user_prompt = template["user_template"].format(**replacements)
    # We don't add conversation_note here as it is handled by system prompt injection
    
    return f"{system_prompt}\n\n---\n\n{user_prompt}"


