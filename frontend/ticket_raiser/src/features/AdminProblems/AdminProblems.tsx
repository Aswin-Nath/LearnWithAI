// AdminProblems feature component
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../../core/api';
import './AdminProblems.css';

interface Problem {
  id: number;
  title: string;
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  category: string;
  created_at: string;
}

const EditIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
  </svg>
);

const BeakerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5h.01M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const DocumentIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const DifficultyBadge = ({ difficulty }: { difficulty: string }) => (
  <span className={`admin-difficulty-badge ${difficulty.toLowerCase()}`}>
    {difficulty}
  </span>
);

export const AdminProblems: React.FC = () => {
  const navigate = useNavigate();
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProblems();
  }, []);

  const fetchProblems = async () => {
    try {
      setLoading(true);
      const data = await apiFetch('/problems', {
        method: 'GET',
      });
      setProblems(data.data || data || []);
    } catch (error) {
      console.error('Failed to fetch problems:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (problemId: number) => {
    navigate(`/admin/problems/${problemId}/edit`);
  };

  const handleTestCases = (problemId: number) => {
    navigate(`/admin/problems/${problemId}/test-cases`);
  };

  const handleEditorial = (problemId: number) => {
    navigate(`/admin/problems/${problemId}/editorial`);
  };

  const handleCreateNew = () => {
    navigate('/admin/problems/create');
  };

  return (
    <div className="admin-problems">
      <div className="admin-problems-header">
        <h2>Problem Management</h2>
        <button className="btn-create-new" onClick={handleCreateNew}>
          + Create New Problem
        </button>
      </div>

      {loading ? (
        <div className="admin-loading">
          <div className="admin-spinner"></div>
          <p>Loading problems...</p>
        </div>
      ) : problems.length === 0 ? (
        <div className="admin-empty">
          <p>No problems created yet</p>
          <button className="btn-create-new-alt" onClick={handleCreateNew}>
            Create Your First Problem
          </button>
        </div>
      ) : (
        <div className="admin-problems-table-wrapper">
          <table className="admin-problems-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Difficulty</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {problems.map((problem) => (
                <tr key={problem.id}>
                  <td className="title-cell">
                    <div>
                      <p className="problem-title">{problem.title}</p>
                      <p className="problem-desc">{problem.description}</p>
                    </div>
                  </td>
                  <td>
                    <DifficultyBadge difficulty={problem.difficulty} />
                  </td>
                  <td className="date-cell">
                    {problem.created_at ? new Date(problem.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'}
                  </td>
                  <td className="action-cell">
                    <div className="action-buttons">
                      <button
                        className="btn-action btn-edit"
                        onClick={() => handleEdit(problem.id)}
                        title="Edit problem"
                      >
                        <EditIcon />
                        Edit
                      </button>
                      <button
                        className="btn-action btn-test"
                        onClick={() => handleTestCases(problem.id)}
                        title="Manage test cases"
                      >
                        <BeakerIcon />
                        Test Cases
                      </button>
                      <button
                        className="btn-action btn-editorial"
                        onClick={() => handleEditorial(problem.id)}
                        title="Upload editorial"
                      >
                        <DocumentIcon />
                        Editorial
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
