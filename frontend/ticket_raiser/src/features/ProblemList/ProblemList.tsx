// ProblemList feature component
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
// import { Navbar } from '../../components/Navbar';
import { Navbar
  
 } from '../../components/Navbar/Navbar';
import { apiFetch } from '../../core/api';
import './ProblemList.css';

interface Problem {
  id: number;
  title: string;
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  category?: string;
  created_at?: string;
  acceptance_rate?: number;
}

const DifficultyBadge = ({ difficulty }: { difficulty: string }) => (
  <span className={`problem-difficulty-badge ${difficulty.toLowerCase()}`}>
    {difficulty}
  </span>
);

const ChevronRightIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ClockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

interface ProblemWithStatus extends Problem {
  submission_status?: 'ACCEPTED' | 'ATTEMPTED' | 'NOT_ATTEMPTED';
}

export const ProblemList: React.FC = () => {
  const navigate = useNavigate();
  const [problems, setProblems] = useState<ProblemWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<'ALL' | 'EASY' | 'MEDIUM' | 'HARD'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SOLVED' | 'ATTEMPTED' | 'TODO'>('ALL');
  const { user } = useAuth();

  useEffect(() => {
    fetchProblems();
  }, []);

  const fetchProblems = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch('/problems', {
        method: 'GET',
      });
      const problemsData = data.data || data || [];
      setProblems(problemsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load problems';
      setError(message);
      console.error('Error fetching problems:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredProblems = problems.filter((problem) => {
    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        problem.title.toLowerCase().includes(query) ||
        problem.description?.toLowerCase().includes(query) ||
        problem.category?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }

    // Difficulty filter
    if (difficultyFilter !== 'ALL' && problem.difficulty !== difficultyFilter) {
      return false;
    }

    // Status filter
    if (statusFilter !== 'ALL') {
      if (statusFilter === 'SOLVED' && problem.submission_status !== 'ACCEPTED') {
        return false;
      }
      if (statusFilter === 'ATTEMPTED' && problem.submission_status !== 'ATTEMPTED') {
        return false;
      }
      if (statusFilter === 'TODO' && problem.submission_status !== 'NOT_ATTEMPTED') {
        return false;
      }
    }

    return true;
  });

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'ACCEPTED':
        return <CheckCircleIcon />;
      case 'ATTEMPTED':
        return <ClockIcon />;
      default:
        return null;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'ACCEPTED':
        return 'solved';
      case 'ATTEMPTED':
        return 'attempted';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <div className="problem-list-wrapper">
        <Navbar />
        <div className="problem-list-container">
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading problems...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="problem-list-wrapper">
      <Navbar />
      <div className="problem-list-container">
        <div className="problem-list-header">
          <h1>Problems</h1>
          <p className="subtitle">Master coding challenges and track your progress</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Filters */}
        <div className="filters-section">
          <div className="filters-header">
            <h2 className="filters-title">Filter & Search</h2>
          </div>
          <div className="problem-filters">
            <div className="filter-group search-group">
              
              <input
                type="text"
                placeholder="Search by title, description or category..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
              {searchQuery && (
                <button
                  className="clear-search"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Problems List */}
        {filteredProblems.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <p className="empty-state-title">No problems found</p>
            <p className="empty-state-desc">Try adjusting your filters or search terms</p>
            <button
              onClick={() => {
                setSearchQuery('');
                setDifficultyFilter('ALL');
                setStatusFilter('ALL');
              }}
              className="btn-reset"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="problems-section">
            <div className="problems-header">
              <h2>All Problems</h2>
              <span className="problems-count">{filteredProblems.length} problems</span>
            </div>
            <div className="problems-grid">
              {filteredProblems.map((problem) => (
                <div
                  key={problem.id}
                  className={`problem-card ${getStatusColor(problem.submission_status)}`}
                  onClick={() => navigate(`/problems/${problem.id}`)}
                >
                  <div className="problem-card-content">
                    <div className="problem-card-header">
                      <div className="problem-status">
                        {getStatusIcon(problem.submission_status)}
                      </div>
                      <div className="problem-title-section">
                        <h3 className="problem-title">{problem.title}</h3>
                        <p className="problem-description">{problem.description}</p>
                      </div>
                    </div>

                    <div className="problem-footer">
                      <div className="problem-meta">
                        <DifficultyBadge difficulty={problem.difficulty} />
                        {problem.category && <span className="category-tag">{problem.category}</span>}
                      </div>
                      {problem.acceptance_rate !== undefined && (
                        <span className="acceptance-rate">
                          {problem.acceptance_rate.toFixed(1)}% AC
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="chevron-icon">
                    <ChevronRightIcon />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProblemList;
