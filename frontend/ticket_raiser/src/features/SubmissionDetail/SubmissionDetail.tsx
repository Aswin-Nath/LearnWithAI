import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { Navbar } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './SubmissionDetail.css';

interface Problem {
  id: number;
  title: string;
  difficulty: string;
}

interface Submission {
  id: number;
  problem_id: number;
  problem?: Problem;
  code: string;
  language: string;
  status: 'PENDING' | 'ACCEPTED' | 'WRONG_ANSWER' | 'RUNTIME_ERROR' | 'TIME_LIMIT_EXCEEDED';
  test_cases_passed: number;
  total_test_cases: number;
  created_at: string;
}

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

export const SubmissionDetailPage: React.FC = () => {
  const { submissionId } = useParams<{ submissionId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubmission();
  }, [submissionId]);

  const fetchSubmission = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`/submissions/${submissionId}`, {
        method: 'GET',
      });

      const submissionData = data.data || data;
      setSubmission(submissionData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch submission');
      setSubmission(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ACCEPTED':
        return 'status-accepted';
      case 'PENDING':
        return 'status-pending';
      case 'WRONG_ANSWER':
        return 'status-wrong';
      case 'RUNTIME_ERROR':
        return 'status-error';
      case 'TIME_LIMIT_EXCEEDED':
        return 'status-timeout';
      default:
        return 'status-unknown';
    }
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'WRONG_ANSWER':
        return 'Wrong Answer';
      case 'RUNTIME_ERROR':
        return 'Runtime Error';
      case 'TIME_LIMIT_EXCEEDED':
        return 'Time Limit Exceeded';
      default:
        return status;
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="submission-detail-wrapper">
        <Navbar />
        <div className="submission-detail-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading submission...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !submission) {
    return (
      <div className="submission-detail-wrapper">
        <Navbar />
        <div className="submission-detail-container">
          <button className="back-btn" onClick={() => navigate(-1)}>
            <ChevronLeftIcon />
            Back
          </button>
          <div className="error-state">
            <h2>Error</h2>
            <p>{error || 'Submission not found'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="submission-detail-wrapper">
      <Navbar />
      <div className="submission-detail-container">
        <div className="submission-header">
          <button className="back-btn" onClick={() => navigate(-1)}>
            <ChevronLeftIcon />
            Back
          </button>
          <div className="header-content">
            <div className="header-title">
              <h1>{submission.problem?.title || 'Problem ' + submission.problem_id}</h1>
              {submission.problem?.difficulty && (
                <span className={`difficulty difficulty-${submission.problem.difficulty.toLowerCase()}`}>
                  {submission.problem.difficulty}
                </span>
              )}
            </div>
            <span className={`status-badge ${getStatusColor(submission.status)}`}>
              {getStatusText(submission.status)}
            </span>
          </div>
        </div>

        <div className="submission-info-grid">
          <div className="info-card">
            <div className="info-label">Submission ID</div>
            <div className="info-value">#{submission.id}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Language</div>
            <div className="info-value">
              <span className="language-tag">{submission.language}</span>
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Test Cases</div>
            <div className="info-value">
              {submission.test_cases_passed}/{submission.total_test_cases}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Success Rate</div>
            <div className="info-value">
              {Math.round((submission.test_cases_passed / submission.total_test_cases) * 100)}%
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Submitted At</div>
            <div className="info-value">{formatDate(submission.created_at)}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Status</div>
            <div className="info-value">
              <span className={`status-inline ${getStatusColor(submission.status)}`}>
                {getStatusText(submission.status)}
              </span>
            </div>
          </div>
        </div>

        <div className="progress-section">
          <h3>Test Cases Progress</h3>
          <div className="progress-bar-large">
            <div
              className="progress-fill"
              style={{
                width: `${(submission.test_cases_passed / submission.total_test_cases) * 100}%`,
              }}
            ></div>
          </div>
          <p className="progress-text">
            Passed {submission.test_cases_passed} out of {submission.total_test_cases} test cases
          </p>
        </div>

        <div className="code-section">
          <h3>Submitted Code</h3>
          <div className="code-editor-container">
            <Editor
              height="500px"
              language={submission.language.toLowerCase()}
              value={submission.code}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
              }}
              defaultValue={submission.code}
            />
          </div>
        </div>

        <div className="action-buttons">
          <button className="btn-secondary" onClick={() => navigate(-1)}>
            Back
          </button>
          <button
            className="btn-primary"
            onClick={() => navigate(`/problems/${submission.problem_id}`)}
          >
            View Problem
          </button>
        </div>
      </div>
    </div>
  );
};
