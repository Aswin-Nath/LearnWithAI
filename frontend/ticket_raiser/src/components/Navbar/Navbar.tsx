import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './Navbar.css';

const MenuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="24" height="24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
  </svg>
);

const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="24" height="24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);

const LogoutIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0110.5 3h6a2.25 2.25 0 012.25 2.25v13.5A2.25 2.25 0 0116.5 21h-6a2.25 2.25 0 01-2.25-2.25V15M12 9l3 3m0 0l-3 3m3-3H2.25" />
  </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" width="24" height="24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);



export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      setDropdownOpen(false);
      setMobileMenuOpen(false);
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  const handleProfileClick = () => {
    navigate('/profile');
    setDropdownOpen(false);
    setMobileMenuOpen(false);
  };

  if (!user) {
    return null;
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo */}
        <Link to="/" className="navbar-logo">
          <span className="logo-text">LearnWithAI</span>
        </Link>

        {/* Desktop Menu */}
        <div className="navbar-desktop">
          {/* Navigation Links */}
          <div className="navbar-nav">
            <button 
              className="nav-btn-create-roadmap"
              onClick={() => navigate('/generate-roadmap')}
            >
              + Create Roadmap
            </button>
            <Link to="/my-roadmaps" className="nav-link">
              Roadmaps
            </Link>
            <Link to="/custom-problems" className="nav-link">
              Custom Problems
            </Link>
          </div>

          {/* User Menu */}
          <div className="user-menu">
            <button
              className="user-button"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              disabled={isLoading}
            >
              <UserIcon />
              <span className="user-name">{user.email}</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                width="16"
                height="16"
                className={`dropdown-arrow ${dropdownOpen ? 'open' : ''}`}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {/* Dropdown Menu */}
            {dropdownOpen && (
              <div className="dropdown-menu">
                <button
                  className="dropdown-item"
                  onClick={handleProfileClick}
                  disabled={isLoading}
                >
                  <UserIcon />
                  <span>Profile</span>
                </button>
                <div className="dropdown-divider"></div>
                <button
                  className="dropdown-item danger"
                  onClick={handleLogout}
                  disabled={isLoading}
                >
                  <LogoutIcon />
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Menu Button */}
        <div className="mobile-controls">
          <button
            className="mobile-menu-button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="mobile-menu">
          <button
            className="mobile-nav-link mobile-create-btn"
            onClick={() => {
              navigate('/generate-roadmap');
              setMobileMenuOpen(false);
            }}
            disabled={isLoading}
          >
            + Create Roadmap
          </button>
          <div className="mobile-divider"></div>
          <Link to="/my-roadmaps" className="mobile-nav-link" onClick={() => setMobileMenuOpen(false)}>
            Roadmaps
          </Link>
          <div className="mobile-divider"></div>
          <button
            className="mobile-nav-link"
            onClick={handleProfileClick}
            disabled={isLoading}
          >
            Profile
          </button>
          <button
            className="mobile-nav-link danger"
            onClick={handleLogout}
            disabled={isLoading}
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
};
