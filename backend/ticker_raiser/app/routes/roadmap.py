from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.logger import get_logger
from app.dependencies.auth import get_current_user
from app.models.models import User, Roadmap, RoadmapPhase, RoadmapPhaseProblem, Problem as DBProblem, Submission
from app.roadmap.graph import graph
from app.roadmap.verification import verify_solution_methodology

router = APIRouter(prefix="/roadmap", tags=["roadmap"])
logger = get_logger("routes.roadmap")

# --- Request Schemas ---

class RoadmapInitRequest(BaseModel):
    topic: str
    user_query: Optional[str] = ""

class RoadmapAssessRequest(BaseModel):
    thread_id: str
    user_answers: List[int]

class RoadmapInitResponse(BaseModel):
    thread_id: str
    mcqs: List[dict]

class KnowledgeStateResponse(BaseModel):
    strong_topics: List[str]
    weak_topics: List[str]

class RoadmapAssessResponse(BaseModel):
    roadmap_id: int | None = None
    message: str
    knowledge_state: KnowledgeStateResponse | None = None

class ProblemSchema(BaseModel):
    id: int
    title: str
    difficulty: str

class Phase(BaseModel):
    phase_id: int
    phase_name: str
    phase_goal: str
    focus_topics: List[str]
    problems: List[ProblemSchema] = []
    
    class Config:
        from_attributes = True

class PhaseContentSchema(BaseModel):
    phase_id: int
    phase_name: str
    full_markdown: Optional[str] = None

class SolveRequest(BaseModel):
    submission_id: int

class RoadmapGenerateResponse(BaseModel):
    thread_id: str
    phases: List[Phase]
    phase_problems: Dict[int, List[ProblemSchema]]  # phase_id -> list of problems
    phase_content: Dict[str, PhaseContentSchema] = {}  # phase_id (as string) -> content

# --- Endpoints ---

@router.post("/init", response_model=RoadmapInitResponse)
async def init_roadmap(request: RoadmapInitRequest):
    """
    Initializes the roadmap generation process.
    Generates MCQs based on the topic and query.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "topic": request.topic,
        "user_query": request.user_query,
        "mcqs": [],
        "user_answers": [],
        "knowledge_state": {"strong_topics": [], "weak_topics": []},
        "phases": [],
        "phase_content": {},
        "error": "",
        "skip_assessment": False
    }

    try:
        # Run graph until interrupt (after mcq generation)
        for event in graph.stream(initial_state, config=config):
            pass
            
        # Get current state snapshot
        snapshot = graph.get_state(config)
        if not snapshot.values:
             raise HTTPException(status_code=500, detail="Graph execution failed execution (empty state)")
             
        state_values = snapshot.values
        if "error" in state_values and state_values["error"]:
             raise HTTPException(status_code=500, detail=f"Graph Error: {state_values['error']}")
             
        if not state_values.get("mcqs"):
             raise HTTPException(status_code=500, detail="Generated MCQs list is empty")

        return {
            "thread_id": thread_id,
            "mcqs": state_values["mcqs"]
        }
    except Exception as e:
        logger.error(f"Error initializing roadmap: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess", response_model=RoadmapAssessResponse)
async def assess_knowledge(
    request: RoadmapAssessRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts MCQ answers, evaluates knowledge, and returns the analysis.
    Stopped before Phase Generation for verification.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # Get current state before updating
    snapshot = graph.get_state(config)
    current_state = snapshot.values
    
    print(f"🔗 ASSESS ENDPOINT CALLED - Thread ID: {request.thread_id}")
    print(f"📊 Current MCQs: {current_state.get('mcqs', [])}")
    print(f"✍️  User answers: {request.user_answers}")
    
    logger.info(f"Current MCQs: {current_state.get('mcqs', [])}")
    logger.info(f"User answers: {request.user_answers}")
    
    # Update state with user answers AND signal to skip the interrupt
    print("🔄 Updating state with skip_assessment=True")
    graph.update_state(config, {
        "user_answers": request.user_answers,
        "skip_assessment": True  # This tells present_mcqs_node to skip the interrupt
    })
    
    try:
        # Resume graph execution
        # The graph will resume from the interrupt in present_mcqs and continue to evaluate_knowledge
        # Then stop at the interrupt_after=['evaluate_knowledge']
        print("▶️ Resuming graph execution...")
        for event in graph.stream(None, config=config, stream_mode="updates"):
            print(f"📌 Graph Event: {event}")
            logger.info(f"Event: {event}")
            
        snapshot = graph.get_state(config)
        final_state = snapshot.values
        
        print(f"💾 Final state knowledge: {final_state.get('knowledge_state', {})}")
        print(f"⚠️  Final state error: {final_state.get('error', '')}")
        
        logger.info(f"Final state knowledge: {final_state.get('knowledge_state', {})}")
        logger.info(f"Final state error: {final_state.get('error', '')}")
        
        knowledge = final_state.get("knowledge_state", {})
        
        return {
            "message": "Knowledge assessed successfully",
            "knowledge_state": {
                "strong_topics": knowledge.get("strong_topics", []),
                "weak_topics": knowledge.get("weak_topics", [])
            }
        }

    except Exception as e:
        print(f"❌ Error evaluating knowledge: {str(e)}")
        logger.error(f"Error evaluating knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate", response_model=RoadmapGenerateResponse)
async def generate_roadmap(
    request: RoadmapAssessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates phases and problems based on assessed knowledge state.
    Continues graph execution from evaluate_knowledge to generate_phases and generate_phase_content.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    
    try:
        # Continue graph execution from current state to generate phases
        print(f"🚀 GENERATE ENDPOINT - Continuing graph execution for thread: {request.thread_id}")
        
        for event in graph.stream(None, config=config, stream_mode="updates"):
            print(f"📌 Generate Event: {event}")
            logger.info(f"Generate Event: {event}")
        
        # Get final state
        snapshot = graph.get_state(config)
        final_state = snapshot.values
        
        print(f"💾 Final state phases: {final_state.get('phases', [])}")
        print(f"💾 Final state phase_content: {final_state.get('phase_content', {})}")
        
        phases_data = final_state.get("phases", [])
        phase_content_data = final_state.get("phase_content", {})
        
        if not phases_data:
            raise HTTPException(status_code=500, detail="No phases generated")
        
        # Build response with phases and problems
        phases_response = []
        phase_problems_map = {}
        
        for phase_data in phases_data:
            phase_id = phase_data.get("phase_id", 0)
            
            # Get problems from the phase_data (they're already included from generate_problem node)
            problems_for_phase = phase_data.get("problems", [])
            
            # Convert problems to ProblemSchema objects
            problems_objs = [
                ProblemSchema(
                    id=p.get("id", 0),
                    title=p.get("title", ""),
                    difficulty=p.get("difficulty", "MEDIUM")
                )
                for p in problems_for_phase
            ]
            
            # Create phase object with problems attached
            phase_obj = Phase(
                phase_id=phase_id,
                phase_name=phase_data.get("phase_name", ""),
                phase_goal=phase_data.get("phase_goal", ""),
                focus_topics=phase_data.get("focus_topics", []),
                problems=problems_objs
            )
            
            phases_response.append(phase_obj)
            phase_problems_map[phase_id] = problems_objs
        
        print(f"📤 Returning {len(phases_response)} phases with problems")
        for phase in phases_response:
            print(f"   - Phase {phase.phase_id}: {len(phase.problems)} problems")
        
        # Build phase_content map from final state
        phase_content_map = {}
        for phase_id_str, content_data in phase_content_data.items():
            if isinstance(content_data, dict):
                phase_content_map[phase_id_str] = PhaseContentSchema(
                    phase_id=content_data.get("phase_id", 0),
                    phase_name=content_data.get("phase_name", ""),
                    full_markdown=content_data.get("full_markdown", "")
                )
        
        print(f"📚 Phase content items: {len(phase_content_map)}")
        
        return RoadmapGenerateResponse(
            thread_id=request.thread_id,
            phases=phases_response,
            phase_problems=phase_problems_map,
            phase_content=phase_content_map
        )
        
    except Exception as e:
        print(f"❌ Error generating phases: {str(e)}")
        logger.error(f"Error generating phases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class RoadmapSaveRequest(BaseModel):
    """Request to save generated roadmap to database"""
    topic: str
    phases: List[Phase]
    phase_problems: Dict[int, List[ProblemSchema]]
    phase_content: Dict[str, PhaseContentSchema]


class RoadmapSaveResponse(BaseModel):
    """Response after saving roadmap"""
    roadmap_id: int
    topic: str
    message: str


@router.post("/save", response_model=RoadmapSaveResponse)
async def save_roadmap(
    request: RoadmapSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Saves the generated roadmap and its phases to the database.
    Creates roadmap record, phases, and phase-problem relationships.
    """
    try:
        # Create roadmap record
        roadmap = Roadmap(
            topic=request.topic,
            user_id=current_user.id,
            status="ACTIVE",
            current_phase_order=1
        )
        db.add(roadmap)
        db.flush()  # Get the roadmap ID without committing
        
        # Create phases and problem associations
        for phase_idx, phase in enumerate(request.phases, 1):
            # Get content for this phase
            phase_content_key = str(phase.phase_id)
            content_data = request.phase_content.get(phase_content_key, {})
            
            # Create phase record
            db_phase = RoadmapPhase(
                roadmap_id=roadmap.id,
                phase_order=phase_idx,
                phase_name=phase.phase_name,
                phase_goal=phase.phase_goal,
                content_markdown=content_data.full_markdown or "",
                is_completed=False,
                completed_at=None
            )
            db.add(db_phase)
            db.flush()
            
            # Create problem associations for this phase
            problems_for_phase = request.phase_problems.get(phase.phase_id, [])
            for problem_data in problems_for_phase:
                # Verify problem exists in database
                db_problem = db.query(DBProblem).filter(DBProblem.id == problem_data.id).first()
                if db_problem:
                    phase_problem = RoadmapPhaseProblem(
                        phase_id=db_phase.id,
                        problem_id=problem_data.id,
                        match_reason=problem_data.title  # Use title as placeholder reason
                    )
                    db.add(phase_problem)
        
        db.commit()
        logger.info(f"Roadmap {roadmap.id} saved successfully for user {current_user.id}")
        
        return RoadmapSaveResponse(
            roadmap_id=roadmap.id,
            topic=roadmap.topic,
            message=f"Roadmap '{request.topic}' saved successfully with {len(request.phases)} phases"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving roadmap: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save roadmap: {str(e)}")


@router.get("/list")
async def list_roadmaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all roadmaps for the current user.
    """
    try:
        roadmaps = db.query(Roadmap).filter(
            Roadmap.user_id == current_user.id,
            Roadmap.status == "ACTIVE"
        ).order_by(Roadmap.created_at.desc()).all()
        
        result = []
        for roadmap in roadmaps:
            result.append({
                "id": roadmap.id,
                "topic": roadmap.topic,
                "created_at": roadmap.created_at,
                "phase_count": len(roadmap.phases),
                "current_phase_order": roadmap.current_phase_order,
                "status": roadmap.status
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing roadmaps: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a specific roadmap with all its phases and problems.
    """
    try:
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.user_id == current_user.id
        ).first()
        
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        
        # Construct response with nested phases and problems
        response = {
            "id": roadmap.id,
            "topic": roadmap.topic,
            "created_at": roadmap.created_at,
            "status": roadmap.status,
            "current_phase_order": roadmap.current_phase_order,
            "phases": []
        }
        
        # Sort phases by order
        sorted_phases = sorted(roadmap.phases, key=lambda p: p.phase_order)
        
        for p in sorted_phases:
            phase_data = {
                "id": p.id,
                "phase_order": p.phase_order,
                "phase_name": p.phase_name,
                "phase_goal": p.phase_goal,
                "content_markdown": p.content_markdown,
                "is_completed": p.is_completed,
                "completed_at": p.completed_at,
                "problems": []
            }
            
            for pp in p.problems:
                if pp.problem:
                    phase_data["problems"].append({
                        "id": pp.problem.id,
                        "title": pp.problem.title,
                        "difficulty": pp.problem.difficulty,
                        "match_reason": pp.match_reason,
                        "is_solved": pp.is_solved
                    })
            
            response["phases"].append(phase_data)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching roadmap: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{roadmap_id}/phase/{phase_id}/complete")
async def complete_phase(
    roadmap_id: int,
    phase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a phase as completed and updates roadmap's current phase order.
    """
    try:
        # Verify ownership
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.user_id == current_user.id
        ).first()
        
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        
        phase = db.query(RoadmapPhase).filter(
            RoadmapPhase.id == phase_id,
            RoadmapPhase.roadmap_id == roadmap_id
        ).first()
        
        if not phase:
            raise HTTPException(status_code=404, detail="Phase not found")
        
        from datetime import datetime, timezone
        phase.is_completed = True
        phase.completed_at = datetime.now(timezone.utc)
        
        # Update roadmap's current phase to next one
        if phase.phase_order < len(roadmap.phases):
            roadmap.current_phase_order = phase.phase_order + 1
        
        db.commit()
        
        return {
            "message": f"Phase {phase.phase_name} marked as completed",
            "roadmap_id": roadmap_id,
            "phase_id": phase_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing phase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{roadmap_id}/phase/{phase_id}/problem/{problem_id}/solve")
async def mark_problem_solved(
    roadmap_id: int,
    phase_id: int,
    problem_id: int,
    request: SolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a problem in a roadmap phase as solved (idempotent).
    Verifies if the user followed the phase methodology.
    """
    try:
        # Verify ownership
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.user_id == current_user.id
        ).first()
        
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
            
        phase_problem = db.query(RoadmapPhaseProblem).filter(
            RoadmapPhaseProblem.phase_id == phase_id,
            RoadmapPhaseProblem.problem_id == problem_id
        ).first()
        
        if not phase_problem:
            raise HTTPException(status_code=404, detail="Problem not associated with this phase")
            
        # 1. Fetch Context for Verification
        submission = db.query(Submission).filter(
            Submission.id == request.submission_id,
            Submission.user_id == current_user.id
        ).first()
        
        if not submission:
             raise HTTPException(status_code=404, detail="Submission not found")
             
        phase = db.query(RoadmapPhase).filter(RoadmapPhase.id == phase_id).first()
        problem = db.query(DBProblem).filter(DBProblem.id == problem_id).first()
        
        # 2. Run Verification (ONLY if not already solved to save LLM calls)
        if not phase_problem.is_solved:
            verification_result = verify_solution_methodology(
                user_code=submission.code,
                phase_content=phase.content_markdown,
                problem_description=problem.description
            )
            
            if not verification_result.is_compliant:
                # REJECT -> Do not update DB
                return {
                    "success": False,
                    "is_solved": False,
                    "message": "Methodology Mismatch",
                    "feedback": verification_result.feedback
                }

        # 3. Mark as Solved (Idempotent) - Only reachable if compliant or already solved
        phase_problem.is_solved = True
        db.flush()
        
        is_solved = True
        phase_completed = False
        
        # Check if all problems in the phase are now solved
        if not phase.is_completed:
            all_solved = db.query(RoadmapPhaseProblem).filter(
                RoadmapPhaseProblem.phase_id == phase_id,
                RoadmapPhaseProblem.is_solved == False
            ).count() == 0
            
            if all_solved:
                # Import here to avoid circular dependency if moved, though models are standard
                from datetime import datetime, timezone
                phase.is_completed = True
                phase.completed_at = datetime.now(timezone.utc)
                
                 # Update roadmap's current phase to next one if not already ahead
                if phase.phase_order < len(roadmap.phases):
                     if roadmap.current_phase_order <= phase.phase_order:
                         roadmap.current_phase_order = phase.phase_order + 1
                         
                phase_completed = True
        
        db.commit()
        
        return {
            "success": True,
            "is_solved": is_solved,
            "phase_completed": phase_completed,
            "message": "Problem solved! Methodology verified.",
            "feedback": "Great job applying the concept!"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling problem status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{roadmap_id}")
async def delete_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a roadmap and all its associated phases/data.
    """
    try:
        # Verify ownership
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.user_id == current_user.id
        ).first()
        
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        
        # Delete (Cascades should handle children if set up correctly, but let's be safe)
        db.delete(roadmap)
        db.commit()
        
        logger.info(f"Roadmap {roadmap_id} deleted by user {current_user.id}")
        return {"message": "Roadmap deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting roadmap: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
