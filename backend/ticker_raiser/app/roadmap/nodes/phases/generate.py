from app.roadmap.state import RoadMapState
from app.roadmap.models import RoadmapPhases


from langchain_core.prompts import ChatPromptTemplate


from app.roadmap.llm import llm

def generate_phases_node(state: RoadMapState) -> dict:
    """
    Generates 4 learning phases based on the user's knowledge state using the Phase Generator Prompt.
    """
    try:
        topic = state.get("topic", "")
        user_query = state.get("user_query", "")
        knowledge_state = state.get("knowledge_state", {})
        strong_topics = knowledge_state.get("strong_topics", [])
        weak_topics = knowledge_state.get("weak_topics", [])

        if not isinstance(strong_topics, list): strong_topics = []
        if not isinstance(weak_topics, list): weak_topics = []

        system_prompt = """SYSTEM PROMPT — ROADMAP PHASE PLANNER
You are a curriculum planner for a technical learning platform.

Your responsibility is to design a structured learning roadmap made of phases.
You do NOT teach concepts, do NOT generate explanations, and do NOT select problems.

Your job is ONLY to decide:
- What the learner should focus on
- In what order
- Based on their current knowledge gaps

You must adapt the roadmap to the learner’s strengths and weaknesses.
"""

        user_template = """ USER PROMPT — PHASE GENERATION
TOPIC:
{topic}

LEARNER QUERY / CONFUSION:
{user_query}

LEARNER KNOWLEDGE STATE:
Strong topics (array of strings):
{strong_topics}

Weak topics (array of strings):
{weak_topics}

TASK:
Generate exactly 4 learning phases for this learner.

IMPORTANT CONSTRAINTS (STRICT):
1. Generate exactly 4 phases — no more, no less.
2. Weak topics must appear earlier and receive more focus.
3. Strong topics should be used only as prerequisites or reinforcement.
4. Each phase MUST have at least one focus topic.
5. focus_topics MUST be chosen ONLY from the union of [strong_topics, weak_topics, AND the main TOPIC].
6. focus_topics can NEVER be empty.
7. Topics MAY appear in multiple phases if needed.
8. Later phases should REVISIT earlier topics with higher depth or application focus.
9. Do NOT invent new topics outside the allowed list.
10. Do NOT include teaching content, examples, or problem statements.
11. Output must be valid JSON only.

OUTPUT FORMAT (STRICT JSON):
{{
  "phases": [
    {{
      "phase_id": 1,
      "phase_name": "...",
      "focus_topics": ["..."],
      "phase_goal": "..."
    }}
  ]
}}
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_template)
        ])

        formatted_prompt = prompt.invoke({
            "topic": topic,
            "user_query": user_query,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics
        })

        structured_llm = llm.with_structured_output(RoadmapPhases)
        
        last_error = None
        for attempt in range(2):
            try:
                result = structured_llm.invoke(formatted_prompt.to_messages())
                
                if len(result.phases) != 4:
                    raise ValueError(f"Phase generator returned {len(result.phases)} phases, expected exactly 4.")
                    
                all_allowed_topics = set(strong_topics + weak_topics)
                all_allowed_topics.add(topic)
                
                for phase in result.phases:
                    if not phase.focus_topics:
                        raise ValueError(f"Phase {phase.phase_id} ({phase.phase_name}) has empty focus_topics.")

                phases_dict = [phase.model_dump() for phase in result.phases]
                return {
                    **state,
                    "phases": phases_dict
                }
                
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise last_error
        else:
            raise ValueError("Phase generation failed for unknown reason.")

    except Exception as e:
        return {
            **state,
            "phases": [],
            "error": f"Phase generation failed: {str(e)}"
        }
