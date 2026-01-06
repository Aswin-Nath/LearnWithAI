// UploadEditorial feature component
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Navbar } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './UploadEditorial.css';

interface Problem {
  id: number;
  title: string;
  editorial_url_link?: string;
}

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 16.2L4.8 12m-1.6 1.6A2 2 0 103.6 8.4m12 8V4m0 0l-3 3m3-3l3 3" />
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const FileIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

export const UploadEditorialPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [editorial, setEditorial] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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
      setEditorial(problemData.editorial_url_link || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];

    if (!selectedFile) {
      setFile(null);
      return;
    }

    // Only accept PDF files
    if (selectedFile.type !== 'application/pdf') {
      setError('Only PDF files are allowed');
      return;
    }

    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }

    setFile(selectedFile);
    setError(null);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('problem_id', id!);

      // Upload PDF - will be uploaded to Cloudinary and ingested to Chroma
      const data = await apiFetch(`/problems/${id}/editorial/pdf`, {
        method: 'POST',
        body: formData,
      });

      // Extract URL from response message if available
      const message = data.message || '';
      const urlMatch = message.match(/View at: (.+?)(?:\s|$)/);
      const pdfUrl = urlMatch ? urlMatch[1] : null;

      // Set editorial to the URL or success message
      setEditorial(pdfUrl || 'PDF successfully uploaded and indexed');
      setFile(null);
      setError(null);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      // Refresh problem data to show URL
      if (pdfUrl) {
        setTimeout(() => fetchData(), 1000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setUploading(true);
      await apiFetch(`/problems/${id}/editorial`, {
        method: 'DELETE',
      });

      setEditorial(null);
      setShowDeleteConfirm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="editorial-wrapper">
        <Navbar />
        <div className="editorial-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading editorial...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="editorial-wrapper">
      <Navbar />
      <div className="editorial-container">
        <div className="editorial-header">
          <button className="back-btn" onClick={() => navigate('/admin/problems')}>
            <ChevronLeftIcon />
            Back
          </button>
          <div className="header-title">
            <h1>Editorial</h1>
            {problem && <p className="problem-name">{problem.title}</p>}
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="editorial-content">
          {editorial ? (
            <div className="editorial-card">
              <div className="editorial-header-section">
                <div className="file-info">
                  <FileIcon />
                  <div className="file-details">
                    <h3>Editorial PDF</h3>
                    <p>Uploaded and indexed for knowledge base</p>
                  </div>
                </div>
                <button
                  className="btn-delete"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={uploading}
                  title="Delete editorial"
                >
                  <TrashIcon />
                </button>
              </div>

              <div className="editorial-meta">
                <p>
                  <span>Status:</span>
                  ✓ PDF uploaded to storage and indexed in knowledge base
                </p>
                {editorial && editorial.startsWith('http') && (
                  <p>
                    <span>URL:</span>
                    <a href={editorial} target="_blank" rel="noopener noreferrer" className="editorial-url">
                      View Editorial
                    </a>
                  </p>
                )}
              </div>

              {editorial && !editorial.startsWith('http') && (
                <p className="upload-success">✓ {editorial}</p>
              )}

              <div className="upload-divider">
                <span>Replace with new file</span>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>No editorial uploaded yet.</p>
              <p className="empty-subtitle">Upload a PDF file to add to the problem's knowledge base.</p>
            </div>
          )}

          <form onSubmit={handleUpload} className="upload-form">
            <h2>{editorial ? 'Upload New Editorial PDF' : 'Upload Editorial PDF'}</h2>

            <label className="upload-area">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                disabled={uploading}
                className="file-input"
              />
              <div className="upload-content">
                <UploadIcon />
                <div>
                  <p className="upload-main">
                    {file ? (
                      <>
                        <CheckIcon />
                        {file.name}
                      </>
                    ) : (
                      <>Click to select a PDF file</>
                    )}
                  </p>
                  <p className="upload-sub">or drag and drop your PDF file here</p>
                </div>
                <p className="upload-hint">Max 50MB</p>
              </div>
            </label>

            <button
              type="submit"
              className="btn-primary"
              disabled={!file || uploading}
            >
              {uploading ? 'Uploading...' : editorial ? 'Replace Editorial' : 'Upload Editorial'}
            </button>
          </form>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setShowDeleteConfirm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Editorial?</h2>
            <p>This action cannot be undone. Are you sure you want to delete this editorial?</p>
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={uploading}
              >
                Cancel
              </button>
              <button className="btn-danger" onClick={handleDelete} disabled={uploading}>
                {uploading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
