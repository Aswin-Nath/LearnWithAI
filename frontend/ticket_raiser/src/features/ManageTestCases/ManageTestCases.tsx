// ManageTestCases feature component
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
// import { Navbar } from '../../components/Navbar';
import { Navbar } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './ManageTestCases.css';

interface TestCase {
  id: number;
  input_data: string;
  expected_output: string;
  is_sample: boolean;
  created_at: string;
}

interface Problem {
  id: number;
  title: string;
  test_cases?: TestCase[];
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

const PlusIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
  </svg>
);

export const ManageTestCasesPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ input_data: '', expected_output: '', is_sample: false });
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`/problems/${id}`, {
        method: 'GET',
      });

      const problemData = data.data || data;
      setProblem(problemData);
      setTestCases(problemData.test_cases || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.input_data.trim() || !formData.expected_output.trim()) {
      setError('Both input and expected output are required');
      return;
    }

    try {
      setSubmitting(true);
      const newTestCase = await apiFetch(`/problems/${id}/test-cases`, {
        method: 'POST',
        body: JSON.stringify(formData),
      });

      setTestCases((prev) => [...prev, newTestCase.data || newTestCase]);
      setFormData({ input_data: '', expected_output: '', is_sample: false });
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (testCaseId: number) => {
    try {
      setSubmitting(true);
      await apiFetch(`/problems/test-cases/${testCaseId}`, {
        method: 'DELETE',
      });

      setTestCases((prev) => prev.filter((tc) => tc.id !== testCaseId));
      setDeletingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSubmitting(false);
    }
  };

  const handleEdit = (testCase: TestCase) => {
    setFormData({
      input_data: testCase.input_data,
      expected_output: testCase.expected_output,
      is_sample: testCase.is_sample,
    });
    setEditingId(testCase.id);
    setShowForm(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.input_data.trim() || !formData.expected_output.trim()) {
      setError('Both input and expected output are required');
      return;
    }

    try {
      setSubmitting(true);
      const updatedTestCase = await apiFetch(`/problems/test-cases/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify(formData),
      });

      setTestCases((prev) =>
        prev.map((tc) => (tc.id === editingId ? updatedTestCase.data || updatedTestCase : tc))
      );
      setFormData({ input_data: '', expected_output: '', is_sample: false });
      setEditingId(null);
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="test-cases-wrapper">
        <Navbar />
        <div className="test-cases-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading test cases...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="test-cases-wrapper">
      <Navbar />
      <div className="test-cases-container">
        <div className="test-cases-header">
          <button className="back-btn" onClick={() => navigate('/admin/problems')}>
            <ChevronLeftIcon />
            Back
          </button>
          <div className="header-title">
            <h1>Test Cases</h1>
            {problem && <p className="problem-name">{problem.title}</p>}
          </div>
          <button className="btn-primary add-btn" onClick={() => setShowForm(!showForm)}>
            <PlusIcon />
            Add Test Case
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {showForm && (
          <div className="form-card">
            <h2>{editingId ? 'Edit Test Case' : 'New Test Case'}</h2>
            <form onSubmit={editingId ? handleUpdate : handleSubmit} className="test-case-form">
              <div className="form-group">
                <label htmlFor="input_data">Input *</label>
                <textarea
                  id="input_data"
                  name="input_data"
                  value={formData.input_data}
                  onChange={handleChange}
                  className="form-textarea"
                  rows={4}
                  placeholder="Enter the test case input"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="expected_output">Expected Output *</label>
                <textarea
                  id="expected_output"
                  name="expected_output"
                  value={formData.expected_output}
                  onChange={handleChange}
                  className="form-textarea"
                  rows={4}
                  placeholder="Enter the expected output"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="is_sample">
                  <input
                    type="checkbox"
                    id="is_sample"
                    name="is_sample"
                    checked={formData.is_sample}
                    onChange={handleChange}
                  />
                  <span>Mark as Sample Test Case</span>
                </label>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowForm(false);
                    setEditingId(null);
                    setFormData({ input_data: '', expected_output: '', is_sample: false });
                  }}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? (editingId ? 'Updating...' : 'Adding...') : (editingId ? 'Update Test Case' : 'Add Test Case')}
                </button>
              </div>
            </form>
          </div>
        )}

        {testCases.length === 0 ? (
          <div className="empty-state">
            <p>No test cases yet.</p>
            <p className="empty-subtitle">Create your first test case to get started.</p>
          </div>
        ) : (
          <div className="test-cases-grid">
            {testCases.map((testCase, index) => (
              <div key={testCase.id} className="test-case-card">
                <div className="test-case-header">
                  <span className="test-case-number">Test Case #{index + 1}</span>
                  <div className="test-case-actions">
                    <button
                      className="btn-edit"
                      onClick={() => handleEdit(testCase)}
                      disabled={submitting}
                      title="Edit test case"
                    >
                      ✎
                    </button>
                    <button
                      className="btn-delete"
                      onClick={() => setDeletingId(testCase.id)}
                      disabled={submitting}
                      title="Delete test case"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                </div>

                <div className="test-case-content">
                  <div className="case-section">
                    <h4>Input</h4>
                    <pre className="case-value">{testCase.input_data}</pre>
                  </div>

                  <div className="case-section">
                    <h4>Expected Output</h4>
                    <pre className="case-value">{testCase.expected_output}</pre>
                  </div>

                  {testCase.is_sample && (
                    <div className="case-badge">
                      <span className="badge-sample">Sample</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {deletingId && (
        <div className="modal-overlay" onClick={() => setDeletingId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Test Case?</h2>
            <p>This action cannot be undone. Are you sure you want to delete this test case?</p>
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setDeletingId(null)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                className="btn-danger"
                onClick={() => handleDelete(deletingId)}
                disabled={submitting}
              >
                {submitting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
