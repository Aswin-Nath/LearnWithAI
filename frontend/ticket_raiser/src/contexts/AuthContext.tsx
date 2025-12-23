import React, { createContext, useEffect, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { authService } from '../services/auth';
import type { User, RegisterRequest, LoginRequest } from '../schemas/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  register: (data: RegisterRequest) => Promise<void>;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  changePassword: (data: { currentPassword: string; newPassword: string }) => Promise<void>;
  clearError: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize auth state once on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
          authService.setUser(currentUser);
        }
      } catch (err) {
        authService.clearTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []); // Only run once on mount

  const register = useCallback(async (data: RegisterRequest) => {
    try {
      setIsLoading(true);
      setError(null);
      await authService.register(data);
      // Auto-login after registration
      await authService.login({
        username: data.email,
        password: data.password
      });
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      authService.setUser(currentUser);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    try {
      setIsLoading(true);
      setError(null);
      await authService.login(data);
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      authService.setUser(currentUser);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await authService.logout();
      setUser(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Logout failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await authService.logoutAll();
      setUser(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Logout failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const changePassword = useCallback(async (data: { currentPassword: string; newPassword: string }) => {
    try {
      setIsLoading(true);
      setError(null);
      await authService.changePassword(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to change password';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    register,
    login,
    logout,
    logoutAll,
    changePassword,
    clearError
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
