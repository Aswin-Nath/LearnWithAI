// AdminIssues feature component
import React, { useState, useEffect } from 'react';
import { Navbar } from '../../components/Navbar';
import { apiFetch } from '../../core/api';
import './AdminIssues.css';

interface Issue {
  id: number;
  title: string;
  description: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED';
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at: string;
  created_by: string;
}

const StatusBadge = ({ status }: { status: string }) => (
  <span className={`issue-status ${status.toLowerCase()}`}>
    {status}
  </span>
);

const PriorityBadge = ({ priority }: { priority: string }) => (
  <span className={`issue-priority ${priority.toLowerCase()}`}>
    {priority}
  </span>
);

export const AdminIssues: React.FC = () => {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'in_progress' | 'closed'>('all');

  useEffect(() => {
    fetchIssues();
  }, []);

  const fetchIssues = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API endpoint
      setIssues([]);
    } catch (error) {
      console.error('Failed to fetch issues:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredIssues = issues.filter((issue) => {
    if (filter === 'all') return true;
    return issue.status.toLowerCase() === filter.toUpperCase();
  });

  return (
    <div className="admin-issues">
      <div className="admin-issues-header">
        <h2>Issues Management</h2>
        <div className="issues-filters">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filter === 'open' ? 'active' : ''}`}
            onClick={() => setFilter('open')}
          >
            Open
          </button>
          <button
            className={`filter-btn ${filter === 'in_progress' ? 'active' : ''}`}
            onClick={() => setFilter('in_progress')}
          >
            In Progress
          </button>
          <button
            className={`filter-btn ${filter === 'closed' ? 'active' : ''}`}
            onClick={() => setFilter('closed')}
          >
            Closed
          </button>
        </div>
      </div>

      {loading ? (
        <div className="issues-loading">
          <div className="issues-spinner"></div>
          <p>Loading issues...</p>
        </div>
      ) : filteredIssues.length === 0 ? (
        <div className="issues-empty">
          <p>
            {filter === 'all' 
              ? 'No issues reported yet' 
              : `No ${filter.replace('_', ' ')} issues`}
          </p>
        </div>
      ) : (
        <div className="issues-list">
          {filteredIssues.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <div className="issue-title-section">
                  <h3>{issue.title}</h3>
                  <StatusBadge status={issue.status} />
                </div>
                <PriorityBadge priority={issue.priority} />
              </div>

              <p className="issue-description">{issue.description}</p>

              <div className="issue-footer">
                <span className="issue-meta">Reported by: {issue.created_by}</span>
                <span className="issue-meta">
                  {new Date(issue.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
