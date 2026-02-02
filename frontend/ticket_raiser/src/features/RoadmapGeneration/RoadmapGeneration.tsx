import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import './RoadmapGeneration.css';
import { Navbar } from '../../components/Navbar/Navbar';

// --- Types ---
interface MCQ {
    mcq_id: number;
    question: string;
    options: string[];
    topics: string[];
}

interface RoadmapInitResponse {
    thread_id: string;
    mcqs: MCQ[];
}

interface RoadmapAssessResponse {
    roadmap_id: number | null;
    message: string;
    knowledge_state?: {
        strong_topics: string[];
        weak_topics: string[];
    };
}

interface RoadmapPhase {
    phase_id: number;
    phase_name: string;
    phase_goal: string;
    focus_topics: string[];
    problems?: Problem[];
}

interface Problem {
    id: number;
    title: string;
    difficulty: string;
    description_snippet?: string;
    match_reason?: string;
}

interface PhaseContent {
    phase_id: number;
    phase_name: string;
    full_markdown?: string;
}

interface RoadmapGenerateResponse {
    thread_id: string;
    phases: RoadmapPhase[];
    phase_problems: Record<number, Problem[]>;
    phase_content?: Record<string, PhaseContent>;
}

// --- Component ---
const RoadmapGeneration: React.FC = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    
    // Process Steps: 'INPUT' -> 'LOADING_MCQ' -> 'ASSESSMENT' -> 'LOADING_ROADMAP' -> 'COMPLETE' -> 'ROADMAP_VIEW'
    const [step, setStep] = useState<'INPUT' | 'LOADING_MCQ' | 'ASSESSMENT' | 'LOADING_ROADMAP' | 'COMPLETE' | 'ROADMAP_VIEW'>('INPUT');
    
    // Data States
    const [topic, setTopic] = useState('');
    const [query, setQuery] = useState('');
    const [threadId, setThreadId] = useState<string>('');
    const [mcqs, setMcqs] = useState<MCQ[]>([]);
    
    // Assessment State
    const [answers, setAnswers] = useState<number[]>([]); 
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

    const [analysis, setAnalysis] = useState<{strong: string[], weak: string[]} | null>(null);
    const [roadmapData, setRoadmapData] = useState<RoadmapGenerateResponse | null>(null);
    const [selectedPhaseId, setSelectedPhaseId] = useState<number | null>(null);

    // --- Actions ---

    const handleGenerateMCQs = async () => {
        if (!user) {
            alert("Please log in to generate a roadmap.");
            return;
        }
        if (!topic.trim()) {
            alert("Please enter a topic.");
            return;
        }

        setStep('LOADING_MCQ');
        
        try {
            console.log("Generating MCQs for topic:", topic, "Query:", query);
            
            const response = await fetch('http://localhost:8000/roadmap/init', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-User-Id': user.id.toString()
                },
                body: JSON.stringify({ topic, user_query: query })
            });

            console.log("MCQ generation response status:", response.status);
            
            if (!response.ok) throw new Error('Failed to generate MCQs');

            const data: RoadmapInitResponse = await response.json();
            
            console.log("Generated MCQs:", data.mcqs);
            console.log("Sample MCQ topics:", data.mcqs[0]?.topics);
            
            setThreadId(data.thread_id);
            setMcqs(data.mcqs);
            setAnswers(new Array(data.mcqs.length).fill(-1)); // Initialize answers
            setStep('ASSESSMENT');
        } catch (error) {
            console.error("MCQ generation error:", error);
            alert("Error generating questions. Please try again.");
            setStep('INPUT');
        }
    };

    const handleAnswerSelect = (optionIndex: number) => {
        const newAnswers = [...answers];
        newAnswers[currentQuestionIndex] = optionIndex;
        setAnswers(newAnswers);
    };

    const handleNextQuestion = () => {
        if (currentQuestionIndex < mcqs.length - 1) {
            setCurrentQuestionIndex(prev => prev + 1);
        }
    };

    const handlePrevQuestion = () => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(prev => prev - 1);
        }
    };

    const handleSubmitAssessment = async () => {
        if (!user) {
            alert("Session expired. Please log in again.");
            return;
        }
        if (answers.includes(-1)) {
            alert("Please answer all questions before submitting.");
            return;
        }

        setStep('LOADING_ROADMAP');

        try {
            console.log("Submitting assessment with:");
            console.log("Thread ID:", threadId);
            console.log("Answers:", answers);
            console.log("MCQs:", mcqs);
            
            const response = await fetch('http://localhost:8000/roadmap/assess', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-User-Id': user.id.toString()
                },
                body: JSON.stringify({ 
                    thread_id: threadId, 
                    user_answers: answers 
                })
            });

            console.log("Response status:", response.status);
            
            if (!response.ok) throw new Error('Failed to assess knowledge');

            const data: RoadmapAssessResponse = await response.json();
            
            console.log("Assessment response:", data);
            console.log("Knowledge state:", data.knowledge_state);
            
            if (data.knowledge_state) {
                setAnalysis({
                    strong: data.knowledge_state.strong_topics,
                    weak: data.knowledge_state.weak_topics
                });
                setStep('COMPLETE');
            } else {
                alert("Unexpected response format");
                setStep('ASSESSMENT');
            }

        } catch (error) {
            console.error("Assessment error:", error);
            alert("Error assessing knowledge. Please try again.");
            setStep('ASSESSMENT');
        }
    };

    const handleGenerateRoadmap = async () => {
        if (!user || !threadId) {
            alert("Session error. Please start over.");
            return;
        }

        setStep('LOADING_ROADMAP');

        try {
            console.log("Generating roadmap phases...");
            
            const response = await fetch('http://localhost:8000/roadmap/generate', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-User-Id': user.id.toString()
                },
                body: JSON.stringify({ 
                    thread_id: threadId, 
                    user_answers: answers 
                })
            });

            console.log("Generate response status:", response.status);
            
            if (!response.ok) throw new Error('Failed to generate phases');

            const data: RoadmapGenerateResponse = await response.json();
            
            console.log("=== ROADMAP RESPONSE DEBUG ===");
            console.log("Full response:", data);
            console.log("Phases count:", data.phases?.length);
            data.phases?.forEach((phase, idx) => {
                console.log(`Phase ${idx}:`, {
                    id: phase.phase_id,
                    name: phase.phase_name,
                    goal: phase.phase_goal,
                    topics: phase.focus_topics,
                    problems: phase.problems,
                    problemsCount: phase.problems?.length
                });
            });
            console.log("Phase problems map:", data.phase_problems);
            console.log("=== END DEBUG ===");
            
            setRoadmapData(data);
            setStep('ROADMAP_VIEW');
        } catch (error) {
            console.error("Roadmap generation error:", error);
            alert("Error generating roadmap. Please try again.");
            setStep('COMPLETE');
        }
    };

    const handleViewProblem = (problemId: number) => {
        console.log(`Opening problem ${problemId} in new tab`);
        window.open(`/problems/${problemId}`, '_blank');
    };

    const handleSaveAndNavigate = async () => {
        if (!roadmapData || !topic) {
            alert("No roadmap data to save");
            return;
        }

        setStep('LOADING_ROADMAP');

        try {
            console.log("Saving roadmap to database...");
            
            const response = await fetch('http://localhost:8000/roadmap/save', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-User-Id': user?.id.toString() || ''
                },
                body: JSON.stringify({
                    topic: topic,
                    phases: roadmapData.phases,
                    phase_problems: roadmapData.phase_problems,
                    phase_content: roadmapData.phase_content || {}
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to save roadmap: ${response.statusText}`);
            }

            const saveData = await response.json();
            console.log("Roadmap saved successfully:", saveData);
            
            
            // Navigate to individual roadmap page
            navigate(`/roadmaps/${saveData.roadmap_id}`);
        } catch (error) {
            console.error("Error saving roadmap:", error);
            alert(`Error saving roadmap: ${error instanceof Error ? error.message : 'Unknown error'}`);
            setStep('ROADMAP_VIEW');
        }
    };
    

    // --- Renderers ---

    const renderInputStep = () => (
        <div className="roadmap-input-container">
            <button className="back-btn" onClick={() => navigate('/problems')} style={{ alignSelf: 'flex-start', marginBottom: '-1rem' }}>
                ← Back to Problems
            </button>

            {/* Hero / Left Column */}
            <div className="input-hero-section">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <h1 className="roadmap-title">Build Your Knowledge Path</h1>
                    <p className="roadmap-subtitle">
                        Tell us what you want to learn, and we'll craft a personalized path just for you.
                    </p>
                </div>
            </div>
            
            {/* Form / Right Column */}
            <div className="input-form-section">
                <div className="input-group">
                    <label>What Topic Do You Want to Learn?</label>
                    <input 
                        type="text" 
                        placeholder="e.g. Dynamic Programming, React, System Design..." 
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        className="roadmap-input"
                    />
                </div>
                
                <div className="input-group">
                    <label>Specific Goal or Query (Optional)</label>
                    <textarea 
                        placeholder="e.g. I struggle with recursion. I want to solve hard problems." 
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="roadmap-textarea"
                    />
                </div>

                <button className="roadmap-primary-btn glow-effect" onClick={handleGenerateMCQs}>
                    Start Your Journey
                </button>
            </div>
        </div>
    );

    const renderAssessmentStep = () => {
        const currentMCQ = mcqs[currentQuestionIndex];
        const progress = ((currentQuestionIndex + 1) / mcqs.length) * 100;

        return (
            <div className="roadmap-assessment-container">
                <div className="progress-bar-container">
                    <div className="progress-bar" style={{ width: `${progress}%` }}></div>
                </div>
                
                <h2 className="question-header">Question {currentQuestionIndex + 1} of {mcqs.length}</h2>
                <div className="question-card">
                    <p className="question-text">{currentMCQ.question}</p>
                    
                    <div className="options-list">
                        {currentMCQ.options.map((option, idx) => (
                            <div 
                                key={idx} 
                                className={`option-item ${answers[currentQuestionIndex] === idx ? 'selected' : ''}`}
                                onClick={() => handleAnswerSelect(idx)}
                            >
                                <span className="option-marker">{String.fromCharCode(65 + idx)}</span>
                                <span className="option-text">{option}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="navigation-buttons">
                    <button 
                        className="nav-btn" 
                        disabled={currentQuestionIndex === 0} 
                        onClick={handlePrevQuestion}
                    >
                        Previous
                    </button>
                    
                    {currentQuestionIndex === mcqs.length - 1 ? (
                        <button className="roadmap-primary-btn finish-btn" onClick={handleSubmitAssessment}>
                            Generate Roadmap
                        </button>
                    ) : (
                        <button className="nav-btn next-btn" onClick={handleNextQuestion}>
                            Next
                        </button>
                    )}
                </div>
            </div>
        );
    };

    const renderLoading = (message: string) => (
        <div className="roadmap-loading-container">
            <div className="spinner"></div>
            <h2 className="loading-text">{message}</h2>
            <p className="loading-subtext">AI is analyzing your request...</p>
        </div>
    );

    const renderCompleteStep = () => {
        if (!analysis) return null;
        return (
            <div className="roadmap-analysis-container">
                <h1 className="roadmap-title">Knowledge Analysis</h1>
                <p className="roadmap-subtitle">Here is what we understood about your current level.</p>
                
                <div className="analysis-card strong">
                    <h3>💪 Strong Topics</h3>
                    <div className="tags">
                        {analysis.strong.length > 0 ? (
                            analysis.strong.map(t => <span key={t} className="tag strong">{t}</span>)
                        ) : <p>None identified yet.</p>}
                    </div>
                </div>

                <div className="analysis-card weak">
                    <h3>🎯 Areas for Improvement</h3>
                    <div className="tags">
                        {analysis.weak.length > 0 ? (
                            analysis.weak.map(t => <span key={t} className="tag weak">{t}</span>)
                        ) : <p>None identified yet.</p>}
                    </div>
                </div>
                
                <div className="action-buttons">
                    <button className="roadmap-primary-btn" onClick={handleGenerateRoadmap}>
                        Generate Roadmap
                    </button>
                    <button className="roadmap-secondary-btn" onClick={() => window.location.reload()}>
                        Start Over
                    </button>
                </div>
            </div>
        );
    };

    const renderRoadmapView = () => {
        if (!roadmapData || !roadmapData.phases || roadmapData.phases.length === 0) {
            return <div>No phases generated yet.</div>;
        }

        if (selectedPhaseId !== null) {
            const selectedPhase = roadmapData.phases.find(p => p.phase_id === selectedPhaseId);
            if (!selectedPhase) return null;

            return (
                <div className="phase-detail-container">
                    <button className="back-btn" onClick={() => setSelectedPhaseId(null)}>
                        ← Back to Phases
                    </button>

                    <div className="phase-detail-content">
                        <div className="phase-detail-header">
                            <h1>Phase {selectedPhase.phase_id}: {selectedPhase.phase_name}</h1>
                            <p className="phase-detail-goal">{selectedPhase.phase_goal}</p>
                        </div>

                        <div className="phase-focus-topics">
                            <h3>📌 Focus Topics:</h3>
                            <div className="topics-badges">
                                {selectedPhase.focus_topics.map(topic => (
                                    <span key={topic} className="topic-badge-large">{topic}</span>
                                ))}
                            </div>
                        </div>

                        {roadmapData.phase_content && (
                            <div className="phase-content-section">
                                <div className="phase-markdown">
                                    <ReactMarkdown>
                                        {roadmapData.phase_content[String(selectedPhase.phase_id)]?.full_markdown || 
                                         roadmapData.phase_content[selectedPhase.phase_id]?.full_markdown ||
                                         "Content not available"}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        )}

                        {selectedPhase.problems && selectedPhase.problems.length > 0 && (
                            <div className="phase-problems-section">
                                <h3>🎯 Recommended Problems ({selectedPhase.problems.length}):</h3>
                                <div className="problems-list">
                                    {selectedPhase.problems.map((problem) => (
                                        <div 
                                            key={problem.id} 
                                            className="problem-item"
                                            onClick={() => handleViewProblem(problem.id)}
                                            role="button"
                                            tabIndex={0}
                                            onKeyDown={(e) => e.key === 'Enter' && handleViewProblem(problem.id)}
                                        >
                                            <div className="problem-header">
                                                <h4 className="problem-title">{problem.title}</h4>
                                                <span className={`difficulty-badge ${problem.difficulty?.toLowerCase()}`}>
                                                    {problem.difficulty || 'MEDIUM'}
                                                </span>
                                            </div>
                                            {problem.description_snippet && (
                                                <p className="problem-description">{problem.description_snippet}</p>
                                            )}
                                            {problem.match_reason && (
                                                <p className="problem-reason">💡 {problem.match_reason}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="action-buttons">
                            <button className="roadmap-primary-btn" onClick={() => setSelectedPhaseId(null)}>
                                Back to All Phases
                            </button>
                            <button className="roadmap-secondary-btn" onClick={() => window.location.reload()}>
                                Start New Roadmap
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return (
            <div className="roadmap-view-container">
                <h1 className="roadmap-title">Your Learning Roadmap</h1>
                <p className="roadmap-subtitle">A personalized path based on your strengths and weaknesses.</p>
                
                <div className="phases-container">
                    {roadmapData.phases.map((phase) => (
                        <div 
                            key={phase.phase_id} 
                            className="phase-card"
                            onClick={() => setSelectedPhaseId(phase.phase_id)}
                            role="button"
                            tabIndex={0}
                        >
                            <div className="phase-header">
                                <h3 className="phase-name">Phase {phase.phase_id}: {phase.phase_name}</h3>
                            </div>
                            <p className="phase-goal">{phase.phase_goal}</p>
                            <div className="phase-topics">
                                <strong>Focus Topics:</strong>
                                <div className="topics-list">
                                    {phase.focus_topics.map(topic => (
                                        <span key={topic} className="topic-badge">{topic}</span>
                                    ))}
                                </div>
                            </div>
                            {phase.problems && phase.problems.length > 0 && (
                                <div className="phase-problems-count">
                                    <small>📚 {phase.problems.length} problems</small>
                                </div>
                            )}
                            <div className="phase-card-footer">
                                <small className="click-to-expand">Click to expand →</small>
                            </div>
                        </div>
                    ))}
                </div>

                <button className="roadmap-secondary-btn" onClick={() => window.location.reload()}>
                    Start New Roadmap
                </button>

                <button className="roadmap-primary-btn" style={{ marginLeft: '10px' }} onClick={handleSaveAndNavigate}>
                    Save Roadmap & View Progress
                </button>
            </div>
        );
    };

    return (
        <div className="roadmap-page-wrapper">
             <div className="background-shapes">
                <div className="shape shape-1"></div>
                <div className="shape shape-2"></div>
            </div>
            
            <Navbar />
            <div className="roadmap-content-wrapper">
                <div className="roadmap-content">
                    {step === 'INPUT' && renderInputStep()}
                    {step === 'LOADING_MCQ' && renderLoading("Generating Assessment...")}
                    {step === 'ASSESSMENT' && renderAssessmentStep()}
                    {step === 'LOADING_ROADMAP' && renderLoading("Analyzing your results...")}
                    {step === 'COMPLETE' && renderCompleteStep()}
                    {step === 'ROADMAP_VIEW' && renderRoadmapView()}
                </div>
            </div>
        </div>
    );
};

export default RoadmapGeneration;
