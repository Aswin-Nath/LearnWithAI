import React from 'react';
import './AdminSidebar.css';

interface AdminSidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
}

const ProblemIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const IssueIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ activeSection, onSectionChange }) => {
  return (
    <aside className="admin-sidebar">
      <div className="sidebar-header">
        <h3>Admin Panel</h3>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`sidebar-item ${activeSection === 'problems' ? 'active' : ''}`}
          onClick={() => onSectionChange('problems')}
        >
          <ProblemIcon />
          <span>Problem Management</span>
        </button>

        <button
          className={`sidebar-item ${activeSection === 'issues' ? 'active' : ''}`}
          onClick={() => onSectionChange('issues')}
        >
          <IssueIcon />
          <span>Issues</span>
        </button>
      </nav>
    </aside>
  );
};
