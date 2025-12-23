import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../../components/Navbar';
import { apiFetch } from '../../core/api';
import './MySubmissions.css';

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

export const MySubmissionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);

  useEffect(() => {
    fetchSubmissions();
  }, [currentPage]);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const skip = (currentPage - 1) * itemsPerPage;
      const data = await apiFetch(`/submissions/me/submissions?skip=${skip}&limit=${itemsPerPage}`, {
        method: 'GET',
      });

      const submissionData = Array.isArray(data) ? data : (data.data || data.submissions || []);
      setSubmissions(submissionData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch submissions');
      setSubmissions([]);
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
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && submissions.length === 0) {
    return (
      <div className="submissions-wrapper">
        <Navbar />
        <div className="submissions-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading submissions...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="submissions-wrapper">
      <Navbar />
      <div className="submissions-container">
        <div className="submissions-header">
          <h1>My Submissions</h1>
          <p className="header-subtitle">Track your problem solutions and results</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {submissions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📝</div>
            <h2>No submissions yet</h2>
            <p>Start solving problems to see your submissions here</p>
            <button className="btn-primary" onClick={() => navigate('/')}>
              Browse Problems
            </button>
          </div>
        ) : (
          <>
            <div className="submissions-table">
              <div className="table-header">
                <div className="col-problem">Problem</div>
                <div className="col-status">Status</div>
                <div className="col-score">Score</div>
                <div className="col-language">Language</div>
                <div className="col-submitted">Submitted</div>
                <div className="col-action">Action</div>
              </div>

              {submissions.map((submission) => (
                <div key={submission.id} className="table-row">
                  <div className="col-problem">
                    <div className="problem-info">
                      <p className="problem-title">{submission.problem?.title || 'Problem ' + submission.problem_id}</p>
                      <span className={`difficulty difficulty-${submission.problem?.difficulty?.toLowerCase()}`}>
                        {submission.problem?.difficulty}
                      </span>
                    </div>
                  </div>

                  <div className="col-status">
                    <span className={`status-badge ${getStatusColor(submission.status)}`}>
                      {getStatusText(submission.status)}
                    </span>
                  </div>

                  <div className="col-score">
                    <div className="score-info">
                      <span className="score-text">
                        {submission.test_cases_passed}/{submission.total_test_cases}
                      </span>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{
                            width: `${(submission.test_cases_passed / submission.total_test_cases) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  <div className="col-language">
                    <span className="language-tag">{submission.language}</span>
                  </div>

                  <div className="col-submitted">
                    <span className="submitted-date">{formatDate(submission.created_at)}</span>
                  </div>

                  <div className="col-action">
                    <button
                      className="btn-view"
                      onClick={() => navigate(`/submissions/${submission.id}`)}
                      title="View submission details"
                    >
                      View
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {submissions.length > 0 && (
              <div className="pagination">
                <button
                  className="btn-pagination"
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span className="pagination-info">Page {currentPage}</span>
                <button
                  className="btn-pagination"
                  onClick={() => setCurrentPage((prev) => prev + 1)}
                  disabled={submissions.length < itemsPerPage}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
