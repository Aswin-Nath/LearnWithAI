// Profile feature component
import React from 'react';
// import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
// import { Navbar } from '../../components/Navbar';
import { Navbar } from '../../components/Navbar/Navbar';
import './Profile.css';

const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="48" height="48">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);



export const ProfilePage: React.FC = () => {
  // const navigate = useNavigate();
  const { user} = useAuth();

  if (!user) {
    return null;
  }





  return (
    <div className="profile-wrapper">
      <Navbar />
      <div className="profile-container">
        <div className="profile-content">
          {/* Profile Header */}
          <div className="profile-header">
            <div className="profile-avatar">
              <UserIcon />
            </div>
            <div className="profile-info">
              <h1 className="profile-name">User Profile</h1>
              <p className="profile-email">{user.email}</p>
            </div>
          </div>

          {/* Account Information Section */}
          <div className="profile-tab-content">
            <div className="tab-pane active">
              <div className="profile-section">
                <h2>Account Information</h2>
                <div className="info-grid">
                  <div className="info-item">
                    <label className="info-label">Email Address</label>
                    <p className="info-value">{user.email}</p>
                  </div>
                  <div className="info-item">
                    <label className="info-label">Role</label>
                    <p className="info-value">
                      <span className={`role-badge ${user.role?.toLowerCase() || 'user'}`}>
                        {user.role || 'User'}
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              <div className="profile-section">
                <h2>Account Status</h2>
                <div className="status-item">
                  <div className="status-label">
                    <CheckIcon />
                    <span>Email Verified</span>
                  </div>
                  <span className="status-value verified">Active</span>
                </div>
              </div>


            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
