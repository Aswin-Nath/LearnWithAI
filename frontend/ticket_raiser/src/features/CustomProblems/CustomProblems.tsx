import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { apiFetch } from '../../core/api';
import { Navbar } from '../../components/Navbar/Navbar';
import './CustomProblems.css';
interface CustomProblem {
    id: number;
    title: string;
    description: string;
    generation_topic: string;
    difficulty: string;
    generation_query: string;
    created_at: string;
}

const CustomProblemsPage: React.FC = () => {
    const navigate = useNavigate();
    
    // State
    const [problems, setProblems] = useState<CustomProblem[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);
    
    // Form State
    const [topicInput, setTopicInput] = useState('');
    const [queryInput, setQueryInput] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    useEffect(() => {
        fetchProblems();
    }, []);

    const fetchProblems = async () => {
        try {
            setLoading(true);
            const response = await apiFetch('/custom-problems/');
            if (response.error) throw new Error(response.error);
            setProblems(response.data || response); // Handle list response
        } catch (err) {
            console.error("Failed to fetch custom problems", err);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        if (!topicInput.trim() || !queryInput.trim()) return;
        
        try {
            setIsGenerating(true);
            const response = await apiFetch('/custom-problems/generate', {
                method: 'POST',
                body: JSON.stringify({
                    topics: topicInput,
                    user_query: queryInput,
                    difficulty: "MEDIUM" // Default for MVP
                })
            });
            
            if (response.error) throw new Error(response.error);
            
            // Add new problem to top of list
            setProblems(prev => [response.data || response, ...prev]);
            setIsCreating(false);
            setTopicInput('');
            setQueryInput('');
            
        } catch (err) {
            console.error("Failed to generate problem", err);
            alert("Failed to generate problem. Please try again.");
        } finally {
            setIsGenerating(false);
        }
    };

    const handleDelete = async (e: React.MouseEvent, id: number) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this problem?")) return;

        try {
            const response = await apiFetch(`/custom-problems/${id}`, { method: 'DELETE' });
            if (response && response.error) {
                throw new Error(response.error);
            }
            setProblems(prev => prev.filter(p => p.id !== id));
        } catch (err) {
            console.error("Failed to delete", err);
            alert("Failed to delete problem");
        }
    };

    return (
        <div className="custom-problems-container">
            <Navbar />
            <div className="custom-problems-content">
                
                {/* Creation Mode View */}
                {isCreating ? (
                    <div className="creation-overlay">
                        <div className="creation-card">
                            <h2 style={{marginTop:0, marginBottom: '10px', fontSize: '24px', color: '#1e293b'}}>Generate New Problem</h2>
                            <p style={{marginBottom: '30px', color: '#64748b'}}>Specify your learning goals and let AI craft the perfect challenge.</p>
                            
                            <div className="form-group">
                                <label>Target Topics</label>
                                <input 
                                    className="form-input"
                                    placeholder="e.g. Recursion, Dynamic Programming, Graph Theory"
                                    value={topicInput}
                                    onChange={(e) => setTopicInput(e.target.value)}
                                />
                            </div>
                            
                            <div className="form-group">
                                <label>Your Goal (Query)</label>
                                <textarea 
                                    className="form-textarea"
                                    placeholder="e.g. I want to master the sliding window pattern with exact complexity constraints..."
                                    value={queryInput}
                                    onChange={(e) => setQueryInput(e.target.value)}
                                />
                            </div>
                            
                            <div className="form-actions">
                                <button 
                                    className="btn-cancel" 
                                    onClick={() => setIsCreating(false)}
                                    disabled={isGenerating}
                                >
                                    Cancel
                                </button>
                                <button 
                                    className="btn-generate"
                                    onClick={handleGenerate}
                                    disabled={!topicInput || !queryInput || isGenerating}
                                >
                                    {isGenerating ? 'Generating...' : '✨ Generate Problem'}
                                </button>
                            </div>
                        </div>
                    </div>
                ) : null}

                {/* Main List View */}
                
                {/* Header */}
                <div className="header-section">
                    <div className="header-top-row">
                        <div>
                            <button className="back-btn" onClick={() => navigate('/')}>
                                ← Back to Dashboard
                            </button>
                            <h1>Custom Problems</h1>
                            <p>Infinite practice tailored to your needs</p>
                        </div>
                        
                        <button className="btn-create-new-round" onClick={() => setIsCreating(true)} title="Create Custom Problem">
                             +
                        </button>
                    </div>
                </div>

                {/* List */}
                {loading ? (
                    <div className="loading-state">
                        <div className="spinner" style={{width: 40, height: 40, border: '3px solid #e2e8f0', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite'}}></div>
                        <p>Loading your personalized library...</p>
                    </div>
                ) : problems.length === 0 ? (
                    <div className="empty-state">
                        <h3>No Custom Problems Yet</h3>
                        <p>Click the + button above to generate your first AI-tailored problem!</p>
                    </div>
                ) : (
                    <div className="problems-grid">
                        {problems.map(problem => (
                            <div 
                                key={problem.id} 
                                className="problem-card"
                                onClick={() => navigate(`/problems/${problem.id}?custom=true`)} 
                            >
                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px'}}>
                                    <span className={`problem-badge ${problem.difficulty.toLowerCase()}`}>
                                        {problem.difficulty}
                                    </span>
                                    <button 
                                        onClick={(e) => handleDelete(e, problem.id)}
                                        title="Delete Problem"
                                        style={{
                                            background: 'none', 
                                            border: 'none', 
                                            cursor: 'pointer', 
                                            color: '#94a3b8', 
                                            padding: '4px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            transition: 'color 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.color = '#ef4444'}
                                        onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}
                                    >
                                       <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                           <polyline points="3 6 5 6 21 6"></polyline>
                                           <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                       </svg>
                                    </button>
                                </div>
                                
                                <h3 className="problem-title">{problem.title}</h3>
                                <div className="problem-topic">{problem.generation_topic}</div>
                                
                                <p className="problem-query">{problem.generation_query}</p>
                                
                                <div className="problem-footer">
                                    <span className="problem-date">{new Date(problem.created_at).toLocaleDateString()}</span>
                                    <span className="problem-action">View Problem →</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CustomProblemsPage;
