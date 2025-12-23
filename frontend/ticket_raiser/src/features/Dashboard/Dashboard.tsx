// Dashboard feature component
import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Navbar } from '../../components/Navbar';
import { AdminSidebar } from '../../components/AdminSidebar';
import { AdminProblems } from '../AdminProblems/AdminProblems';
import { AdminIssues } from '../AdminIssues/AdminIssues';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeSection, setActiveSection] = useState<'problems' | 'issues'>('problems');

  // Customer view
  if (user?.role === 'USER') {
    return <ProblemsListPage />;
  }

  // Admin view
  return (
    <div className="admin-dashboard-wrapper">
      <Navbar />
      <div className="admin-dashboard-container">
        <AdminSidebar activeSection={activeSection} onSectionChange={(section) => setActiveSection(section as 'problems' | 'issues')} />
        <main className="admin-dashboard-content">
          {activeSection === 'problems' && <AdminProblems />}
          {activeSection === 'issues' && <AdminIssues />}
        </main>
      </div>
    </div>
  );
};
