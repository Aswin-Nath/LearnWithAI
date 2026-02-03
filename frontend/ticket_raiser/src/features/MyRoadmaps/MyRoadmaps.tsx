import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Navbar } from '../../components/Navbar/Navbar';
import './MyRoadmaps.css';

interface RoadmapItem {
    id: number;
    topic: string;
    created_at: string;
    phase_count: number;
    current_phase_order: number;
    status: string;
}

export const MyRoadmaps: React.FC = () => {
    const navigate = useNavigate();
    const { user } = useAuth();

    const [roadmaps, setRoadmaps] = useState<RoadmapItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchRoadmaps();
    }, []);

    const fetchRoadmaps = async () => {
        if (!user) {
            setError('User not authenticated');
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const response = await fetch('http://localhost:8000/roadmap/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Id': user.id.toString()
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch roadmaps: ${response.statusText}`);
            }

            const data: RoadmapItem[] = await response.json();
            setRoadmaps(data);
        } catch (err) {
            console.error('Error fetching roadmaps:', err);
            setError(err instanceof Error ? err.message : 'Failed to load roadmaps');
        } finally {
            setLoading(false);
        }
    };

    const handleRoadmapClick = (roadmapId: number) => {
        navigate(`/roadmaps/${roadmapId}`);
    };

    const handleDeleteRoadmap = async (e: React.MouseEvent, roadmapId: number) => {
        e.stopPropagation(); // Prevent navigation
        
        if (!window.confirm("Are you sure you want to delete this roadmap? This action cannot be undone.")) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/roadmap/${roadmapId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Id': user?.id.toString() || ''
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete roadmap');
            }

            // Remove from state
            setRoadmaps(prev => prev.filter(r => r.id !== roadmapId));
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete roadmap");
        }
    };

    const handleCreateNew = () => {
        navigate('/generate-roadmap');
    };

    const getCompletionPercentage = (currentPhaseOrder: number, phaseCount: number) => {
        if(currentPhaseOrder==phaseCount){
            return 100;
        }
        // currentPhaseOrder represents the NEXT phase to work on
        // So completed phases = currentPhaseOrder - 1, capped at phaseCount
        const completedPhases = Math.min(currentPhaseOrder - 1, phaseCount);
        return Math.round((completedPhases / phaseCount) * 100);
    };

    if (loading) {
        return (
            <div className="my-roadmaps-container">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading your roadmaps...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="my-roadmaps-container">
            <Navbar />
            <div className="my-roadmaps-content">
            {/* Header */}
            <div className="my-roadmaps-header">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <button className="back-btn" onClick={() => navigate('/')} style={{ marginBottom: '10px' }}>
                            ← Back to Dashboard
                        </button>
                        <h1 className="my-roadmaps-title">My Learning Roadmaps</h1>
                        <p className="my-roadmaps-subtitle">Track your learning journey across different topics</p>
                    </div>
                    <button className="btn-create-roadmap-round" onClick={handleCreateNew} title="Create New Roadmap">
                        +
                    </button>
                </div>
            </div>

            {/* Roadmaps Grid or Empty State */}
            {roadmaps.length === 0 ? (
                <div className="empty-state">

                    <h2>No Roadmaps Yet</h2>
                    <p>Create your first learning roadmap to get started!</p>
                </div>
            ) : (
                <div className="roadmaps-grid">
                    {roadmaps.map((roadmap) => {
                        const completionPercentage = getCompletionPercentage(
                            roadmap.current_phase_order,
                            roadmap.phase_count
                        );
                        const createdDate = new Date(roadmap.created_at);
                        const daysAgo = Math.floor(
                            (new Date().getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24)
                        );

                        return (
                            <div
                                key={roadmap.id}
                                className="roadmap-card"
                                onClick={() => handleRoadmapClick(roadmap.id)}
                            >
                                <div className="roadmap-card-header">
                                    <h3 className="roadmap-card-title">{roadmap.topic}</h3>
                                    <span className="roadmap-status-badge">{roadmap.status}</span>
                                    <button 
                                        className="btn-delete-roadmap"
                                        onClick={(e) => handleDeleteRoadmap(e, roadmap.id)}
                                        title="Delete Roadmap"
                                        aria-label="Delete Roadmap"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="trash-icon">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                </div>

                                <p className="roadmap-card-meta">
                                    Created {daysAgo === 0 ? 'Today' : `${daysAgo} day${daysAgo > 1 ? 's' : ''} ago`}
                                </p>

                                <div className="roadmap-progress-section">
                                    <div className="progress-info">
                                        <span className="progress-label">Progress</span>
                                        <span className="progress-percentage">{completionPercentage}%</span>
                                    </div>
                                    <div className="progress-bar-background">
                                        <div
                                            className="progress-bar-fill"
                                            style={{ width: `${completionPercentage}%` }}
                                        ></div>
                                    </div>
                                    <p className="roadmap-phase-info">
                                        Phase {roadmap.current_phase_order} of {roadmap.phase_count}
                                    </p>
                                </div>

                                <div className="roadmap-card-action">
                                    <span className="action-text">Continue Learning →</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {error && (
                <div className="error-banner">
                    <p>{error}</p>
                    <button className="btn-retry" onClick={fetchRoadmaps}>
                        Try Again
                    </button>
                </div>
            )}
        </div>
        </div>
    );
};

export default MyRoadmaps;
