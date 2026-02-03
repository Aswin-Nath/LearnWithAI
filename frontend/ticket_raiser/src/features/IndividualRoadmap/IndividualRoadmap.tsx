import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../../hooks/useAuth';
import { Navbar } from '../../components/Navbar/Navbar';
import './IndividualRoadmap.css';

interface Phase {
    id: number;
    phase_order: number;
    phase_name: string;
    phase_goal: string;
    content_markdown: string;
    is_completed: boolean;
    completed_at?: string;
    problems: Problem[];
}

interface Problem {
    id: number;
    title: string;
    difficulty: string;
    match_reason?: string;
    is_solved?: boolean;
}

interface Roadmap {
    id: number;
    topic: string;
    created_at: string;
    status: string;
    current_phase_order: number;
    phases: Phase[];
}

export const IndividualRoadmap: React.FC = () => {
    const { roadmapId } = useParams<{ roadmapId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
    const [selectedPhaseId, setSelectedPhaseId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchRoadmap();
    }, [roadmapId]);

    const fetchRoadmap = async () => {
        if (!roadmapId || !user) {
            setError('Invalid roadmap ID or user not authenticated');
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`http://localhost:8000/roadmap/${roadmapId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Id': user.id.toString()
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch roadmap: ${response.statusText}`);
            }

            const data: Roadmap = await response.json();
            setRoadmap(data);

            // Auto-select the first uncompleted phase, or the last phase if all completed
            if (data.phases && data.phases.length > 0) {
                const firstUncompletedPhase = data.phases.find(p => !p.is_completed);
                if (firstUncompletedPhase) {
                    setSelectedPhaseId(firstUncompletedPhase.id);
                } else {
                    // All phases completed - will show congratulations screen
                    setSelectedPhaseId(null);
                }
            }
        } catch (err) {
            console.error('Error fetching roadmap:', err);
            setError(err instanceof Error ? err.message : 'Failed to load roadmap');
        } finally {
            setLoading(false);
        }
    };





    const handleViewProblem = (problem: Problem, phase: Phase) => {
        // Navigate to problem with tracking context
        window.open(`/problems/${problem.id}?source=roadmap&roadmapId=${roadmap?.id}&phaseId=${phase.id}`, '_blank');
    };

    const handleMarkPhaseAsCompleted = async (phase: Phase) => {
        if (!roadmap) return;

        try {
            const response = await fetch(
                `http://localhost:8000/roadmap/${roadmap.id}/phase/${phase.id}/complete`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': user?.id.toString() || ''
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to mark phase as completed');
            }

            // Refresh roadmap to update phase completion status
            await fetchRoadmap();
        } catch (err) {
            console.error('Error marking phase as completed:', err);
            setError(err instanceof Error ? err.message : 'Failed to mark phase as completed');
        }
    };

    if (loading) {
        return (
            <div className="individual-roadmap-container">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading roadmap...</p>
                </div>
            </div>
        );
    }

    if (error || !roadmap) {
        return (
            <div className="individual-roadmap-container">
                <button className="back-btn" onClick={() => navigate('/my-roadmaps')}>
                    ← Back to My Roadmaps
                </button>
                <div className="error-container">
                    <p className="error-message">{error || 'Failed to load roadmap'}</p>
                    <button className="btn-retry" onClick={fetchRoadmap}>
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    const selectedPhase = roadmap.phases.find(p => p.id === selectedPhaseId);

    
    // Find the index of the first phase that is NOT completed.
    // If all are completed, this will be -1.
    const firstUnfinishedIndex = roadmap.phases.findIndex(p => !p.is_completed);
    // If all completed, current max reachable is the last one.
    // If none completed, 0 is the current.
    const currentPhaseIndex = firstUnfinishedIndex === -1 ? roadmap.phases.length - 1 : firstUnfinishedIndex;

    return (
        <div className="individual-roadmap-container">
            <Navbar />
            <div className="individual-roadmap-content-wrapper">
                {/* Header */}
                <div className="roadmap-header">
                    <button className="back-btn" onClick={() => navigate('/my-roadmaps')}>
                        ← Back to My Roadmaps
                    </button>
                    <div className="roadmap-title-section">
                        <h1 className="roadmap-title">{roadmap.topic}</h1>
                        <p className="roadmap-meta">
                            Created on {new Date(roadmap.created_at).toLocaleDateString()}
                        </p>
                    </div>
                </div>



                {/* Horizontal Phase Timeline */}
                <div className="roadmap-timeline">
                    {roadmap.phases.map((phase, idx) => {
                        const isLocked = idx > currentPhaseIndex;
                        const isCurrent = idx === currentPhaseIndex;
                        const isSelected = selectedPhaseId === phase.id;
                        const isNextLocked = idx + 1 > currentPhaseIndex;
                        
                        return (
                            <React.Fragment key={phase.id}>
                                <div 
                                    className={`timeline-node-wrapper 
                                        ${isSelected ? 'active' : ''} 
                                        ${phase.is_completed ? 'completed' : ''} 
                                        ${isLocked ? 'locked' : ''}
                                        ${isCurrent ? 'current' : ''}
                                    `}
                                    onClick={() => !isLocked && setSelectedPhaseId(phase.id)}
                                >
                                    <div className="timeline-node">
                                        {phase.is_completed ? 'Done' : idx + 1}
                                    </div>
                                    <div className="timeline-label">Phase {idx + 1}</div>
                                </div>
                                {idx < roadmap.phases.length - 1 && (
                                    <div className={`timeline-connector ${isNextLocked ? 'locked' : ''} ${phase.is_completed ? 'completed' : ''}`}>
                                        <div className="connector-line"></div>
                                        <div className="connector-arrow">►</div>
                                    </div>
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>

            <div className="roadmap-content">
                {/* Congratulations Screen - Show if all phases completed */}
                {selectedPhaseId === null && roadmap?.phases.every(p => p.is_completed) && (
                    <div className="congratulations-container">
                        <div className="congratulations-content">
                            <div className="confetti-animation"></div>
                            <div className="trophy-icon">🏆</div>
                            <h2 className="congratulations-title">Congratulations!</h2>
                            <p className="congratulations-subtitle">You have successfully completed the</p>
                            <p className="roadmap-name-highlight">{roadmap?.topic}</p>
                            <p className="congratulations-description">
                                You've mastered all phases and demonstrated exceptional learning. Keep up the great work!
                            </p>
                            
                            <div className="completion-stats">
                                <div className="stat-item">
                                    <span className="stat-number">{roadmap?.phases.length}</span>
                                    <span className="stat-label">Phases Completed</span>
                                </div>
                                <div className="stat-divider"></div>
                                <div className="stat-item">
                                    <span className="stat-number">100%</span>
                                    <span className="stat-label">Progress</span>
                                </div>
                            </div>

                            <div className="action-buttons">
                                <button 
                                    className="btn-back-roadmaps"
                                    onClick={() => navigate('/my-roadmaps')}
                                >
                                    ← Back to My Roadmaps
                                </button>
                                <button 
                                    className="btn-create-new"
                                    onClick={() => navigate('/generate-roadmap')}
                                >
                                    + Create New Roadmap
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Phase Detail Content - Show if phase is selected */}
                {selectedPhaseId !== null && (
                    <div className="phase-detail-main">
                        {selectedPhase ? (
                            <>
                                <div className="phase-detail-header">
                                    <h2 className="phase-name">
                                        Phase {selectedPhase.phase_order}: {selectedPhase.phase_name}
                                    </h2>
                                    <p className="phase-goal">{selectedPhase.phase_goal}</p>
                                </div>

                                {/* Phase Content */}
                                <div className="phase-content">
                                    <div className="phase-markdown">
                                        {selectedPhase.content_markdown ? (
                                            <ReactMarkdown className="markdown-body">
                                                {selectedPhase.content_markdown}
                                            </ReactMarkdown>
                                        ) : (
                                            <p>No content available for this phase.</p>
                                        )}
                                    </div>
                                </div>

                                {/* Problems Section */}
                                {selectedPhase.problems && selectedPhase.problems.length > 0 && (
                                    <div className="problems-section">
                                        <h3 className="problems-title">
                                            🎯 Recommended Problems ({selectedPhase.problems.length})
                                        </h3>
                                        <div className="problems-grid">
                                            {selectedPhase.problems.map((problem) => (
                                                <div
                                                    key={problem.id}
                                                    className={`problem-card ${problem.is_solved ? 'solved' : ''}`}
                                                    onClick={() => handleViewProblem(problem, selectedPhase)}
                                                >
                                                    <div className="problem-card-header">
                                                        <h4 className="problem-title">{problem.title}</h4>
                                                        <span className={`difficulty-badge ${problem.difficulty?.toLowerCase()}`}>
                                                            {problem.difficulty}
                                                        </span>
                                                    </div>
                                                    
                                                    <div className="problem-action">
                                                        {problem.is_solved ? (
                                                            <span className="problem-solved">Solved</span>
                                                        ) : (
                                                            <small>Click to solve →</small>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* No Problems Section - Show Mark as Completed Button */}
                                {(!selectedPhase.problems || selectedPhase.problems.length === 0) && !selectedPhase.is_completed && (
                                    <div className="no-problems-section">
                                        <div className="no-problems-message">
                                            <p>📚 No problems assigned to this phase yet.</p>
                                            <p className="subtitle">You can mark this phase as completed and move to the next one.</p>
                                        </div>
                                        <button
                                            className="btn-mark-completed"
                                            onClick={() => handleMarkPhaseAsCompleted(selectedPhase)}
                                        >
                                            ✓ Mark Phase as Completed
                                        </button>
                                    </div>
                                )}

                                {/* Already Completed Message */}
                                {(!selectedPhase.problems || selectedPhase.problems.length === 0) && selectedPhase.is_completed && (
                                    <div className="phase-completed-section">
                                        <div className="completed-message">
                                            <p>✅ This phase has been completed!</p>
                                            <p className="subtitle">Great job! Move to the next phase to continue learning.</p>
                                        </div>
                                    </div>
                                )}

                                {/* Action Buttons */}
                                <div className="phase-actions">
                                    {selectedPhase.phase_order > 1 && (
                                        <button
                                            className="btn-prev-phase"
                                            onClick={() => {
                                                const prevPhase = roadmap.phases.find(
                                                    p => p.phase_order === selectedPhase.phase_order - 1
                                                );
                                                if (prevPhase) setSelectedPhaseId(prevPhase.id);
                                            }}
                                        >
                                            ← Previous Phase
                                        </button>
                                    )}
                                    

                                    {selectedPhase.phase_order < roadmap.phases.length && (
                                        <button
                                            className="btn-next-phase"
                                            disabled={selectedPhase.phase_order >= currentPhaseIndex + 1}
                                            style={{ opacity: selectedPhase.phase_order >= currentPhaseIndex + 1 ? 0.5 : 1, cursor: selectedPhase.phase_order >= currentPhaseIndex + 1 ? 'not-allowed' : 'pointer' }}
                                            onClick={() => {
                                                const nextPhase = roadmap.phases.find(
                                                    p => p.phase_order === selectedPhase.phase_order + 1
                                                );
                                                if (nextPhase && (nextPhase.phase_order - 1) <= currentPhaseIndex) {
                                                     setSelectedPhaseId(nextPhase.id);
                                                }
                                            }}
                                        >
                                            Next Phase →
                                        </button>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="no-phase-selected">
                                <p>Select a phase to view details</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
            </div>
        </div>
    );
};

export default IndividualRoadmap;
