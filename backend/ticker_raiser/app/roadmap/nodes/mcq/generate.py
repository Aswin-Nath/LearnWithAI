from app.roadmap.state import RoadMapState
from app.roadmap.models import MCQResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.roadmap.llm import llm


def generate_mcqs_node(state: RoadMapState) -> dict:
    """
    Generates 6 MCQs using LLM based on topic and user query.
    """
    try:
        topic = state.get("topic", "")
        user_query = state.get("user_query", "")

        parser = PydanticOutputParser(pydantic_object=MCQResponse)
        system_prompt = """You are an educational assessment generator.

Your task is to generate multiple-choice questions (MCQs) to diagnose a learner’s understanding of a given topic, based on their specific query or confusion.

GOAL:
Create MCQs that identify the learner’s weak and strong conceptual areas, not just factual recall.

INSTRUCTIONS:
1. Generate exactly 6 MCQs.
2. Difficulty distribution:
   - 2 Easy (core concepts / definitions)
   - 2 Medium (application / reasoning)
   - 2 Hard (edge cases, complexity, pitfalls)
3. Each MCQ must target one or more **atomic learning topics**.
4. Topics must be fine-grained skills (e.g., "collision_handling", "time_complexity", "hashing_intro"),
   NOT broad chapter names.
5. Each MCQ MUST include a non-empty `topics` array.
6. Only one option is correct.
7. Options should be plausible and non-trivial.
8. Do NOT include explanations.
9. Do NOT include markdown in the JSON output.

OUTPUT FORMAT:
The output must be a valid JSON object matching the requested schema.
"""
        user_template = """
Topic: {topic}
User Query: {user_query}

{format_instructions}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_template)
        ])

        formatted_prompt = prompt.invoke({
            "topic": topic,
            "user_query": user_query,
            "format_instructions": parser.get_format_instructions()
        })

        structured_llm = llm.with_structured_output(MCQResponse)
        result = structured_llm.invoke(formatted_prompt.to_messages())
        
        if len(result.mcqs) != 6:
            raise ValueError(f"Generated {len(result.mcqs)} MCQs, expected 6.")
            
        for mcq in result.mcqs:
            if len(mcq.options) != 4:
                raise ValueError(f"MCQ {mcq.mcq_id} has {len(mcq.options)} options, expected exactly 4.")
        
        mcqs_dict = [mcq.model_dump() for mcq in result.mcqs]

        return {
            **state,
            "mcqs": mcqs_dict,
            "error": ""
        }

    except Exception as e:
        return {
            **state,
            "mcqs": [],
            "error": str(e)
        }
