// EditProblem feature component
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
// import { Navbar } from '../../components/Navbar';
import { Navbar } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './EditProblem.css';

interface Problem {
  id: number;
  title: string;
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  constraints?: string;
  time_limit_ms?: number;
}

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

export const EditProblemPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [formData, setFormData] = useState<Problem>({
    id: 0,
    title: '',
    description: '',
    difficulty: 'MEDIUM',
    constraints: '',
    time_limit_ms: 1000,
  });

  useEffect(() => {
    fetchProblem();
  }, [id]);

  const fetchProblem = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`/problems/${id}`, {
        method: 'GET',
      });

      setFormData(data.data || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title.trim() || !formData.description.trim()) {
      setError('Title and description are required');
      return;
    }

    try {
      setSaving(true);
      await apiFetch(`/problems/${id}`, {
        method: 'PUT',
        body: JSON.stringify(formData),
      });

      navigate('/admin/problems');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setSaving(true);
      await apiFetch(`/problems/${id}`, {
        method: 'DELETE',
      });

      navigate('/admin/problems');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="edit-problem-wrapper">
        <Navbar />
        <div className="edit-problem-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading problem...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="edit-problem-wrapper">
      <Navbar />
      <div className="edit-problem-container">
        <div className="edit-problem-header">
          <button className="back-btn" onClick={() => navigate('/admin/problems')}>
            <ChevronLeftIcon />
            Back
          </button>
          <h1>Edit Problem</h1>
        </div>

        <form className="edit-problem-form" onSubmit={handleSubmit}>
          {error && <div className="error-banner">{error}</div>}

          <div className="form-section">
            <h2>Basic Information</h2>

            <div className="form-group">
              <label htmlFor="title">Problem Title *</label>
              <input
                id="title"
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                className="form-input"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="difficulty">Difficulty *</label>
                <select
                  id="difficulty"
                  name="difficulty"
                  value={formData.difficulty}
                  onChange={handleChange}
                  className="form-select"
                >
                  <option value="EASY">Easy</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HARD">Hard</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="time_limit_ms">Time Limit (ms)</label>
                <input
                  id="time_limit_ms"
                  type="number"
                  name="time_limit_ms"
                  value={formData.time_limit_ms}
                  onChange={handleChange}
                  className="form-input"
                  min="100"
                  max="60000"
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Problem Description</h2>

            <div className="form-group">
              <label htmlFor="description">Description *</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                className="form-textarea"
                rows={6}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="constraints">Constraints</label>
              <textarea
                id="constraints"
                name="constraints"
                value={formData.constraints || ''}
                onChange={handleChange}
                className="form-textarea"
                rows={4}
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-danger"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={saving}
            >
              <TrashIcon />
              Delete Problem
            </button>
            <div className="actions-right">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => navigate('/admin/problems')}
                disabled={saving}
              >
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {showDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setShowDeleteConfirm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Problem?</h2>
            <p>This action cannot be undone. Are you sure you want to delete this problem?</p>
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button className="btn-danger" onClick={handleDelete} disabled={saving}>
                {saving ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
