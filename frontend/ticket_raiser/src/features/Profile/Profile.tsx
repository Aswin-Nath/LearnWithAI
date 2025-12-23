// Profile feature component
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Navbar } from '../../components/Navbar';
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

const LockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
  </svg>
);

const EyeIcon = ({ show }: { show: boolean }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="20" height="20">
    {show ? (
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
    ) : (
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
    )}
  </svg>
);

const LogoutAllIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M9 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logoutAll, isLoading } = useAuth();

  if (!user) {
    return null;
  }

  const handleLogoutAll = async () => {
    if (window.confirm('This will logout all your sessions. Continue?')) {
      try {
        await logoutAll();
        navigate('/login');
      } catch (err) {
        setErrorMessage('Failed to logout from all devices');
      }
    }
  };



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

              <div className="profile-section" style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '2px solid #e2e8f0' }}>
                <h2>Logout Options</h2>
                <button
                  onClick={handleLogoutAll}
                  disabled={isLoading}
                  style={{
                    padding: '0.75rem 1.5rem',
                    background: '#fee2e2',
                    color: '#dc2626',
                    border: '2px solid #dc2626',
                    borderRadius: '0.5rem',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    opacity: isLoading ? 0.6 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    transition: 'all 0.2s'
                  }}
                >
                  <LogoutAllIcon />
                  Logout from all devices
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
