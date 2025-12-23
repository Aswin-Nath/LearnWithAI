import React from 'react';
import { Navigate} from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  isAuthenticated: boolean;
  requiredRole?: 'USER' | 'PROBLEM_SETTER';
}

/**
 * ProtectedRoute Component
 * 
 * Wraps routes that require authentication.
 * - Checks if user is authenticated
 * - Checks if user has required role (optional)
 * - Redirects to login if not authenticated
 * - Shows error if user lacks required role
 * 
 * Usage:
 * <Route
 *   path="/dashboard"
 *   element={
 *     <ProtectedRoute isAuthenticated={isAuthenticated}>
 *       <DashboardPage />
 *     </ProtectedRoute>
 *   }
 * />
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  isAuthenticated,
  requiredRole
}) => {
  const { user, isLoading } = useAuth();

  // Show loading state while fetching user data
  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  // Check if user has required role
  if (requiredRole && user.role !== requiredRole) {
    return (
      <div className="error-container">
        <h2>Access Denied</h2>
        <p>You don't have permission to access this page.</p>
        <p>Required role: {requiredRole}</p>
      </div>
    );
  }

  // Render protected content
  return <>{children}</>;
};

/**
 * Example Usage in App.tsx:
 * 
 * <Route
 *   path="/dashboard"
 *   element={
 *     <ProtectedRoute 
 *       isAuthenticated={isAuthenticated}
 *       requiredRole="USER"
 *     >
 *       <DashboardPage />
 *     </ProtectedRoute>
 *   }
 * />
 * 
 * <Route
 *   path="/admin"
 *   element={
 *     <ProtectedRoute 
 *       isAuthenticated={isAuthenticated}
 *       requiredRole="PROBLEM_SETTER"
 *     >
 *       <AdminPage />
 *     </ProtectedRoute>
 *   }
 * />
 */
