import os
from app.roadmap.state import RoadMapState
import time
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import app

from app.roadmap.llm import llm

PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(app.__file__)),
    "chroma_db"
)

def generate_phase_content_node(state: RoadMapState) -> dict:
    """
    ROBUST VERSION: Generates Markdown first as plain text, then chunks it using Python.
    This bypasses 'groq.APIError' caused by large JSON payloads.
    """
    try:
        topic = state.get("topic", "")
        phases = state.get("phases", [])
        knowledge_state = state.get("knowledge_state", {})
        strong_topics = knowledge_state.get("strong_topics", [])
        weak_topics = knowledge_state.get("weak_topics", [])
        
        if not phases:
            return {**state, "phase_content": {}}
            
        phase_content_map = {}
        
        current_file = os.path.abspath(__file__)
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        persist_dir = os.path.join(app_dir, "chroma_db")
        embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
        
        
        for phase in phases:
            phase_id = phase["phase_id"]
            phase_name = phase["phase_name"]
            focus_topics = phase["focus_topics"]
            phase_goal = phase.get("phase_goal", "")
            problems = phase.get("problems", [])
            problems_text = "\n".join([f"- {p['title']} ({p['difficulty']})" for p in problems])
            
            time.sleep(2)
            
            system_msg = """You are a technical curriculum writer. 
Generate detailed, high-quality learning content in strict Markdown format.
Do NOT output JSON. Do NOT output introductory text. Start directly with the # Phase Title."""

            user_msg = f"""TOPIC: {topic}
PHASE: {phase_name} (ID: {phase_id})
GOAL: {phase_goal}
FOCUS TOPICS: {", ".join(focus_topics)}
RECOMMENDED PRACTICE PROBLEMS:
{problems_text}

CONTEXT: Strong: {", ".join(strong_topics)}, Weak: {", ".join(weak_topics)}

REQUIREMENTS:
1. Write ~2 pages of depth.
2. Use this EXACT structure:
   # Phase {phase_id}: {phase_name}
   ## Phase Goal
   ## Prerequisites
   ## Core Concepts
   ## Worked Examples (include python code)
   ## Pattern Templates
   ## Edge Cases & Pitfalls
   ## Complexity Analysis
   ## Practice Guidance
   ## Mental Models

3. CRITICAL: Use ## for main sections and ### for subsections.
"""
            
            full_markdown = ""
            for attempt in range(2):
                try:
                    response = llm.invoke([
                        SystemMessage(content=system_msg),
                        HumanMessage(content=user_msg)
                    ])
                    full_markdown = response.content
                    break
                except Exception as e:
                    if attempt == 1: 
                        full_markdown = f"# Phase {phase_id}: {phase_name}\n\nError generating content."

            parts = re.split(r'(^##\s+.*$)', full_markdown, flags=re.MULTILINE)
            
            chunks = []
            
            if len(parts) > 1:
                if parts[0].strip():
                    intro_content = parts[0].strip()
                    chunks.append({
                        "chunk_id": f"phase{phase_id}_intro",
                        "section_title": "Introduction",
                        "content": intro_content,
                        "focus_topics": focus_topics
                    })

                for i in range(1, len(parts), 2):
                    header = parts[i].strip()
                    body = parts[i+1] if i+1 < len(parts) else ""
                    
                    section_title = header.replace("#", "").strip()
                    chunk_content = f"{header}\n{body}".strip()
                    
                    if not chunk_content: continue

                    chunks.append({
                        "chunk_id": f"phase{phase_id}_chunk_{len(chunks)+1}",
                        "phase_id": phase_id,
                        "phase_name": phase_name,
                        "section_title": section_title,
                        "content": chunk_content,
                        "focus_topics": focus_topics,
                        "topic": topic
                    })
            else:
                chunks.append({
                    "chunk_id": f"phase{phase_id}_full",
                    "section_title": "Full Content",
                    "content": full_markdown,
                    "focus_topics": focus_topics
                })

            phase_content_map[str(phase_id)] = {
                "phase_id": phase_id,
                "phase_name": phase_name,
                "full_markdown": full_markdown,
            }
            
            if chunks:
                sanitized_topic = re.sub(r'[^a-zA-Z0-9]', '_', topic).lower()
                unique_collection_name = f"roadmap_{sanitized_topic}_phase_{phase_id}"
                
                docs_to_add = []
                for chunk in chunks:
                    doc = Document(
                        page_content=chunk["content"],
                        metadata={
                            "chunk_id": str(chunk.get("chunk_id", "")),
                            "phase_id": phase_id,
                            "phase_name": phase_name,
                            "section_title": chunk.get("section_title", "Section"),
                            "focus_topics": ", ".join(chunk.get("focus_topics", [])),
                            "topic": topic
                        }
                    )
                    docs_to_add.append(doc)
                
                try:
                    vector_store = Chroma(
                        collection_name=unique_collection_name,
                        embedding_function=embeddings,
                        persist_directory=PERSIST_DIR
                    )
                    vector_store.add_documents(docs_to_add)
                except Exception as e:
                    print(f"⚠️ Failed to index Phase {phase_id}: {e}")

        return {
            **state,
            "phase_content": phase_content_map
        }
        
    except Exception as e:
        return {
            **state,
            "error": f"Content generation failed: {str(e)}"
        }
