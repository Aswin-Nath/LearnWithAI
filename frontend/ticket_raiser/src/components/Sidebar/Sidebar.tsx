import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './Sidebar.css';

interface MenuItem {
  path: string;
  label: string;
  icon: string;
  roles?: string[];
}

const MENU_ITEMS: MenuItem[] = [
  { path: '/', label: 'Problems', icon: '📋' },
  { path: '/roadmap', label: 'Roadmap', icon: '🗺️' },
  { path: '/dashboard', label: 'Dashboard', icon: '📊', roles: ['admin'] },
  { path: '/profile', label: 'Profile', icon: '👤' },
];

export function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(true);

  const isAdmin = user?.role === 'PROBLEM_SETTER';

  const filteredMenuItems = MENU_ITEMS.filter(item => {
    if (item.roles && !item.roles.includes(user?.role || '')) {
      return false;
    }
    return true;
  });

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname.includes('/problem');
    }
    return location.pathname.includes(path);
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      {/* Toggle Button */}
      <button
        className="sidebar-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title={isOpen ? 'Collapse' : 'Expand'}
      >
        {isOpen ? '◀' : '▶'}
      </button>

      {/* Sidebar Content */}
      <div className="sidebar-content">
        {/* Logo/Brand */}
        {isOpen && (
          <div className="sidebar-header">
            <h2>LearnWithAI</h2>
          </div>
        )}

        {/* Navigation Menu */}
        <nav className="sidebar-menu">
          {filteredMenuItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`menu-item ${isActive(item.path) ? 'active' : ''}`}
              title={!isOpen ? item.label : ''}
            >
              <span className="menu-icon">{item.icon}</span>
              {isOpen && <span className="menu-label">{item.label}</span>}
            </Link>
          ))}
        </nav>
      </div>

      {/* User Section */}
      <div className="sidebar-footer">
        {isOpen && (
          <div className="user-info">
            <div className="user-avatar">{user?.email?.[0].toUpperCase() || 'U'}</div>
            <div className="user-details">
              <div className="user-name">{user?.email?.split('@')[0]}</div>
              <div className="user-role">{isAdmin ? 'Admin' : 'User'}</div>
            </div>
          </div>
        )}
        <button className="logout-btn" onClick={logout} title="Logout">
          {isOpen ? '🚪 Logout' : '🚪'}
        </button>
      </div>
    </div>
  );
}
