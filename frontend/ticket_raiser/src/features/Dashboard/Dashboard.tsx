// Dashboard feature component
import React from 'react';
import { useAuth } from '../../hooks/useAuth';
// import { Navbar } from '../../components/Navbar';
import { Navbar } from '../../components/Navbar/Navbar';
import { AdminProblems } from '../AdminProblems/AdminProblems';
import { ProblemList } from '../ProblemList/ProblemList';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const activeSection = 'problems';

  // Customer view
  if (user?.role === 'USER') {
    return <ProblemList />;
  }

  // Admin view
  return (
    <div className="admin-dashboard-wrapper">
      <Navbar />
      <div className="admin-dashboard-container">
        <main className="admin-dashboard-content">
          {activeSection === 'problems' && <AdminProblems />}
        </main>
      </div>
    </div>
  );
};
