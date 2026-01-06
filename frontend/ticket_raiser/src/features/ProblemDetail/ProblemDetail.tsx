// ProblemDetail feature component
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { Navbar } from '../../components/Navbar/Navbar';
// import { PDFViewer } from '../PDFViewer/PDFViewer';
import { ChatPanel } from '../ChatPanel/ChatPanel';
import { PDFViewer } from '../PDFViewer/PDFViewer';
import { apiFetch } from '../../core/api';
import './ProblemDetail.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface Submission {
  id: number;
  problem_id: number;
  user_id?: number;
  status: 'PENDING' | 'ACCEPTED' | 'WRONG_ANSWER' | 'RUNTIME_ERROR' | 'TIME_LIMIT_EXCEEDED';
  test_cases_passed: number;
  total_test_cases: number;
  created_at: string;
  language: string;
}

interface TestCase {
  id: number;
  input_data: string;
  expected_output: string;
  is_sample: boolean;
}

interface Problem {
  id: number;
  title: string;
  description: string;
  constraints?: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  time_limit_ms?: number;
  editorial_url_link?: string;
  test_cases?: TestCase[];
}

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

const DifficultyBadge = ({ difficulty }: { difficulty: string }) => (
  <span className={`difficulty-badge ${difficulty.toLowerCase()}`}>
    {difficulty}
  </span>
);

interface SubmissionDetail extends Submission {
  code?: string;
}

export const ProblemDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [leftWidth, setLeftWidth] = useState(50);
  const [code, setCode] = useState<string>('# Write your solution here\n\n');
  const [submitting, setSubmitting] = useState(false);
  const [currentSubmission, setCurrentSubmission] = useState<Submission | null>(null);
  const [activeTab, setActiveTab] = useState<'description' | 'editorial' | 'submissions'>('description');
  const [showChat, setShowChat] = useState(true);
  const [editorWidth, setEditorWidth] = useState(70);
  const [isDraggingEditor, setIsDraggingEditor] = useState(false);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | null>(null);
  const [selectedSubmissionDetail, setSelectedSubmissionDetail] = useState<SubmissionDetail | null>(null);
  const [submissionDetailLoading, setSubmissionDetailLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchProblem();
    fetchSubmissions();
  }, [id]);

  const fetchSubmissionDetail = async (submissionId: number) => {
    setSubmissionDetailLoading(true);
    try {
      const data = await apiFetch(`/submissions/${submissionId}`, { method: 'GET' });
      const submission = data.data || data;
      setSelectedSubmissionDetail(submission);
    } catch (err) {
      console.error('Error fetching submission detail:', err);
      setError('Failed to load submission details');
    } finally {
      setSubmissionDetailLoading(false);
    }
  };

  const handleSubmissionClick = (submissionId: number) => {
    setSelectedSubmissionId(submissionId);
    fetchSubmissionDetail(submissionId);
  };

  // Polling effect
  useEffect(() => {
    if (!currentSubmission || currentSubmission.status !== 'PENDING') return;

    const poll = setInterval(async () => {
      try {
        const data = await apiFetch(`/submissions/${currentSubmission.id}`, {
          method: 'GET',
        });
        const submission = data.data || data;
        setCurrentSubmission(submission);

        // Update in submissions list too
        setSubmissions((prev: Submission[]) =>
          prev.map((s) => (s.id === submission.id ? submission : s))
        );

        // Stop polling if status changed
        if (submission.status !== 'PENDING') {
          clearInterval(poll);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1000); // Poll every 1 second

    return () => clearInterval(poll);
  }, [currentSubmission]);

  const fetchProblem = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`/problems/${id}`, {
        method: 'GET',
      });
      setProblem(data.data || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch problem');
    } finally {
      setLoading(false);
    }
  };

  const fetchSubmissions = async () => {
    try {
      // Fetch all user submissions
      const data = await apiFetch(`/submissions/me/submissions?limit=100`, {
        method: 'GET',
      });
      // Handle different response formats
      const allSubmissions = Array.isArray(data) ? data : (data.data || data.submissions || []);
      // Filter to only submissions for this problem
      const problemSubmissions = allSubmissions.filter((s: Submission) => s.problem_id === parseInt(id!));
      setSubmissions(problemSubmissions);
    } catch (err) {
      console.error('Failed to fetch submissions:', err);
      setSubmissions([]); // Set empty array on error
    }
  };

  const handleSubmit = async () => {
    if (!code.trim()) {
      setError('Please write some code');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const data = await apiFetch('/submissions', {
        method: 'POST',
        body: JSON.stringify({
          problem_id: parseInt(id!),
          code: code,
          language: 'python',
        }),
      });

      const submission = data.data || data;
      setCurrentSubmission(submission);
      setSubmissions((prev) => [submission, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit code');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Handle left-right divider for main panels
      if (isDragging && containerRef.current) {
        const container = containerRef.current;
        const rect = container.getBoundingClientRect();
        const newLeftWidth = ((e.clientX - rect.left) / rect.width) * 100;

        if (newLeftWidth > 20 && newLeftWidth < 80) {
          setLeftWidth(newLeftWidth);
        }
      }

      // Handle vertical divider between code editor and chat
      if (isDraggingEditor) {
        const rightPanelElements = document.querySelectorAll('.editor-chat-layout');
        if (rightPanelElements.length > 0) {
          const rightPanel = rightPanelElements[0] as HTMLElement;
          const rect = rightPanel.getBoundingClientRect();
          const newEditorWidth = ((e.clientX - rect.left) / rect.width) * 100;

          if (newEditorWidth > 30 && newEditorWidth < 80) {
            setEditorWidth(newEditorWidth);
          }
        }
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsDraggingEditor(false);
    };

    if (isDragging || isDraggingEditor) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isDraggingEditor]);

  if (loading) {
    return (
      <div className="problem-detail-wrapper">
        <Navbar />
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading problem...</p>
        </div>
      </div>
    );
  }

  if (error || !problem) {
    return (
      <div className="problem-detail-wrapper">
        <Navbar />
        <div className="error-container">
          <button className="back-btn" onClick={() => navigate('/problems')}>
            <ChevronLeftIcon />
            Back
          </button>
          <p className="error-message">{error || 'Problem not found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="problem-detail-wrapper">
      <Navbar />
      <div className="problem-detail-header">
        <button className="back-btn" onClick={() => navigate('/')} title="Go back to problems">
          <ChevronLeftIcon />
          <span className="back-text">Back</span>
        </button>
        <div className="header-info">
          <h1>{problem.title}</h1>
          <DifficultyBadge difficulty={problem.difficulty} />
        </div>
        <div className="header-actions">
          <button 
            className="chat-toggle-floating"
            onClick={() => setShowChat(!showChat)}
            title={showChat ? "Hide chat" : "Show chat"}
          >
            💬
          </button>
        </div>
      </div>

      <div className="problem-detail-container" ref={containerRef}>
        {/* Left Panel - Problem Description */}
        <div className="left-panel" style={{ width: `${leftWidth}%` }}>
          {/* Tab Navigation */}
          <div className="tabs-navigation">
            <button
              className={`tab-button ${activeTab === 'description' ? 'active' : ''}`}
              onClick={() => setActiveTab('description')}
            >
              Description
            </button>
            <span className="tab-separator">|</span>
            <button
              className={`tab-button ${activeTab === 'editorial' ? 'active' : ''}`}
              onClick={() => setActiveTab('editorial')}
            >
              Editorial
            </button>
            <span className="tab-separator">|</span>
            <button
              className={`tab-button ${activeTab === 'submissions' ? 'active' : ''}`}
              onClick={() => setActiveTab('submissions')}
            >
              Submissions
            </button>
          </div>

          {/* Tab Content */}
          <div className="panel-content">
            {error && <div className="error-banner">{error}</div>}

            {/* Description Tab */}
            {activeTab === 'description' && (
              <>
                <div className="description-section">
                  <h2>Description</h2>
                  <div className="description-text">{problem.description}</div>
                </div>

                {problem.constraints && (
                  <div className="constraints-section">
                    <h3>Constraints</h3>
                    <div className="constraints-text">{problem.constraints}</div>
                  </div>
                )}

                {problem.time_limit_ms && (
                  <div className="time-limit-section">
                    <h3>Time Limit</h3>
                    <p>{problem.time_limit_ms}ms</p>
                  </div>
                )}

                {problem.test_cases && problem.test_cases.length > 0 && (
                  <div className="test-cases-section">
                    <h3>Sample Test Cases</h3>
                    <div className="test-cases-list">
                      {problem.test_cases.filter(tc => tc.is_sample).map((testCase) => (
                        <div key={testCase.id} className="test-case">
                          <div className="test-case-input">
                            <strong>Input:</strong>
                            <pre>{testCase.input_data}</pre>
                          </div>
                          <div className="test-case-output">
                            <strong>Output:</strong>
                            <pre>{testCase.expected_output}</pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Editorial Tab */}
            {activeTab === 'editorial' && (
              <div className="editorial-section">
                {problem.editorial_url_link ? (
                  <>
                    <h2>Editorial Solution</h2>
                    <div className="pdf-viewer-wrapper">
                      <PDFViewer url={problem.editorial_url_link} />
                    </div>
                  </>
                ) : (
                  <div className="no-editorial">
                    <p>Editorial not available yet</p>
                  </div>
                )}
              </div>
            )}

            {/* Submissions Tab */}
            {activeTab === 'submissions' && !selectedSubmissionId && (
              <div className="submissions-section">
                <h2>Your Submissions</h2>
                {submissions.length > 0 ? (
                  <div className="submissions-list">
                    {submissions.slice(0, 10).map((submission) => (
                      <div
                        key={submission.id}
                        className={`submission-item status-${submission.status.toLowerCase()}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => handleSubmissionClick(submission.id)}
                      >
                        <div className="submission-header">
                          <span className="submission-id">#{submission.id}</span>
                          <span className={`status-badge ${submission.status.toLowerCase()}`}>
                            {submission.status}
                          </span>
                        </div>
                        <div className="submission-info">
                          <span>{submission.test_cases_passed}/{submission.total_test_cases} tests passed</span>
                          <span className="submission-time">{new Date(submission.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-submissions">
                    <p>No submissions yet</p>
                  </div>
                )}
              </div>
            )}

            {/* Submission Detail View */}
            {activeTab === 'submissions' && selectedSubmissionId && selectedSubmissionDetail && (
              <div className="submission-detail-inline">
                <div className="submission-detail-header">
                  <button 
                    className="back-btn-inline"
                    onClick={() => {
                      setSelectedSubmissionId(null);
                      setSelectedSubmissionDetail(null);
                    }}
                    title="Back to submissions"
                  >
                    <ChevronLeftIcon />
                    Back
                  </button>
                  <h2>Submission #{selectedSubmissionDetail.id}</h2>
                </div>

                {submissionDetailLoading ? (
                  <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading submission...</p>
                  </div>
                ) : (
                  <>
                    <div className="submission-info-grid">
                      <div className="info-card">
                        <label>Status</label>
                        <span className={`status-badge ${selectedSubmissionDetail.status.toLowerCase()}`}>
                          {selectedSubmissionDetail.status}
                        </span>
                      </div>
                      <div className="info-card">
                        <label>Test Cases</label>
                        <span>{selectedSubmissionDetail.test_cases_passed}/{selectedSubmissionDetail.total_test_cases}</span>
                      </div>
                      <div className="info-card">
                        <label>Language</label>
                        <span>{selectedSubmissionDetail.language}</span>
                      </div>
                      <div className="info-card">
                        <label>Submitted At</label>
                        <span>{new Date(selectedSubmissionDetail.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="submission-code-section">
                      <h3>Your Code</h3>
                      <Editor
                        height="400px"
                        language={selectedSubmissionDetail.language?.toLowerCase() || 'python'}
                        value={selectedSubmissionDetail.code || ''}
                        theme="vs-dark"
                        options={{
                          minimap: { enabled: false },
                          fontSize: 12,
                          lineNumbers: 'on',
                          scrollBeyondLastLine: false,
                          readOnly: true,
                          automaticLayout: true,
                        }}
                      />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Draggable Divider */}
        <div
          className={`resize-handle ${isDragging ? 'dragging' : ''}`}
          onMouseDown={handleMouseDown}
          title="Drag to resize"
        >
          <div className="resize-icon"></div>
        </div>

        {/* Right Panel - Code Editor & Chat */}
        <div className="right-panel" style={{ width: `${100 - leftWidth}%` }}>
          <div className="editor-chat-layout">
            {/* Code Editor Section */}
            <div className="editor-section" style={{ width: showChat ? `${editorWidth}%` : '100%' }}>
              <div className="editor-header">
                <h2>Solution</h2>
                <button 
                  className="btn-submit"
                  onClick={handleSubmit}
                  disabled={submitting || !code.trim()}
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>

              {currentSubmission && (
                <div className={`submission-status status-${currentSubmission.status.toLowerCase()}`}>
                  <strong>{currentSubmission.status}</strong>
                  <span>{currentSubmission.test_cases_passed}/{currentSubmission.total_test_cases} tests</span>
                </div>
              )}

              <Editor
                height="100%"
                language="python"
                value={code}
                onChange={(value: string | undefined) => setCode(value || '')}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </div>

            {/* Chat Section */}
            {showChat && (
              <ChatPanel
                problemId={parseInt(id!)}
                userCode={code}
                width={`${100 - editorWidth}%`}
                onDragStart={() => setIsDraggingEditor(true)}
                onCloseChat={() => setShowChat(false)}
                chatMessages={chatMessages}
                onChatMessagesChange={setChatMessages}
                chatInput={chatInput}
                onChatInputChange={setChatInput}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
