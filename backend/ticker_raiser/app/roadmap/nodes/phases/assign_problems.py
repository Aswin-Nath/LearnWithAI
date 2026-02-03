
from app.roadmap.state import RoadMapState
from app.roadmap.models import ProblemSelection
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import text
from app.core.database import SessionLocal
from app.roadmap.llm import llm

def assign_problems_node(state: RoadMapState) -> dict:
    """
    Two-Stage Retrieval:
    1. Vector Search: Fetches top 20 candidates based on technical keywords.
    2. LLM Reranking: Filters those 20 down to the best 5 relevant to the specific phase.
    """
    topic = state.get("topic", "")
    phases = state.get("phases", [])

    if not phases:
        return state

    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
    except Exception as e:
        return {**state, "error": f"Failed to load embedding model: {e}"}

    db = SessionLocal()
    final_phases = []

    try:
        for phase in phases:
            current_phase = phase.copy()
            phase_name = current_phase.get("phase_name", "")
            focus_topics = current_phase.get("focus_topics", [])
            technical_query = f"{topic} {phase_name} {', '.join(focus_topics)} data structure algorithm problem"
            query_embedding = embeddings.embed_query(technical_query)
            embedding_str = str(query_embedding)
            stmt = text("""
                SELECT id, title, difficulty, description 
                FROM problems 
                WHERE is_custom = false
                ORDER BY description_embedding <=> :embedding 
                LIMIT 20
            """)
            
            candidates = db.execute(stmt, {"embedding": embedding_str}).fetchall()
            
            if not candidates:
                current_phase["problems"] = []
                final_phases.append(current_phase)
                continue
            candidate_text = "\n".join([
                f"ID: {row.id} | Title: {row.title} | Diff: {row.difficulty} | Desc: {row.description[:250]}..." 
                for row in candidates
            ])
            rerank_system = """You are a strict technical judge (Algorithm Expert).
Your task is to select problems that are solved PRIMARILY using the "Focus Topics".

CRITICAL RULES:
1. **NO HALLUCINATIONS**: Do not invent a connection.
2. **Standard Solution Check**: Ask yourself, "What is the standard LeetCode solution?".
   - 3Sum -> Two Pointers (YES)
   - Two Sum -> Hash Map (NO, unless specified)
   - Merge Sorted Array -> Two Pointers (YES)
3. **Strict Match**: The Focus Topic must be the MAIN driver of the solution.

OUTPUT:
- Return a JSON object with `selected_problems`.
- If NO problems are strict matches, return empty list `[]`.
"""

            rerank_user = f"""
PHASE: {phase_name}
FOCUS TOPICS: {', '.join(focus_topics)}
DOMAIN (User Intent): {topic}

CANDIDATE PROBLEMS:
{candidate_text}

TASK: Select max 5 problems that use the FOCUS TOPICS as their *primary* solution pattern.
"""
            try:
                parser = PydanticOutputParser(pydantic_object=ProblemSelection)
                rerank_user_with_format = rerank_user + "\n\n" + parser.get_format_instructions()
                response = llm.invoke([
                    SystemMessage(content=rerank_system),
                    HumanMessage(content=rerank_user_with_format)
                ])
                content = response.content.strip()
                if content.find("{") != -1 and content.rfind("}") != -1:
                    content = content[content.find("{"):content.rfind("}")+1]
                selection = parser.parse(content)
                selected_objects = selection.selected_problems
                selected_id_map = {item.problem_id: item.reason for item in selected_objects}
                final_problems = []
                for row in candidates:
                    if row.id in selected_id_map:
                        final_problems.append({
                            "id": row.id,
                            "title": row.title,
                            "difficulty": row.difficulty,
                            "description_snippet": row.description[:100] + "...",
                            "match_reason": selected_id_map[row.id]
                        })
                
                current_phase["problems"] = final_problems


            except Exception as e:
                fallback_probs = []
                for row in candidates[:3]:
                    fallback_probs.append({
                        "id": row.id,
                        "title": row.title,
                        "difficulty": row.difficulty,
                        "description_snippet": row.description[:100] + "..."
                    })
                current_phase["problems"] = fallback_probs
            final_phases.append(current_phase)

    except Exception as e:
        return {**state, "error": f"Problem assignment crashed: {str(e)}"}
    finally:
        db.close()

    return {
        **state,
        "phases": final_phases,
        "error": ""
    }
