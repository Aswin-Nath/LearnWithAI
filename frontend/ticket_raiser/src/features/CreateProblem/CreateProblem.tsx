// CreateProblem feature component
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// import { Navbar } from '../../components/Navbar';
import { Navbar } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './CreateProblem.css';

interface CreateProblemForm {
  title: string;
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  constraints: string;
  time_limit_ms: number;
}

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

export const CreateProblemPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CreateProblemForm>({
    title: '',
    description: '',
    difficulty: 'MEDIUM',
    constraints: '',
    time_limit_ms: 1000,
  });

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
      setLoading(true);
      const response = await apiFetch('/problems', {
        method: 'POST',
        body: JSON.stringify(formData),
      });

      navigate(`/admin/problems/${response.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-problem-wrapper">
      <Navbar />
      <div className="create-problem-container">
        <div className="create-problem-header">
          <button className="back-btn" onClick={() => navigate('/admin/problems')}>
            <ChevronLeftIcon />
            Back
          </button>
          <h1>Create New Problem</h1>
        </div>

        <form className="create-problem-form" onSubmit={handleSubmit}>
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
                placeholder="e.g., Two Sum Problem"
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
                placeholder="Detailed problem description..."
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
                value={formData.constraints}
                onChange={handleChange}
                placeholder="e.g., 1 <= nums.length <= 10^4"
                className="form-textarea"
                rows={4}
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/admin/problems')}
              disabled={loading}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Problem'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
