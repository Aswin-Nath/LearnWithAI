import { apiFetch } from '../core/api';
import type {
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  MessageResponse,
  User
} from '../schemas/auth';
import { ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY, USER_KEY } from '../core/config';

export const authService = {
  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<MessageResponse> {
    return apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  /**
   * Login user and store tokens (OAuth2 form-encoded)
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    // Convert to form-encoded data for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await apiFetch('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString()
    });

    // Store access token and expiry (refresh token is in HttpOnly cookie)
    this.setTokens(response.access_token, response.expires_at);

    return response;
  },

  /**
   * Refresh access token using HttpOnly cookie
   */
  async refresh(): Promise<TokenResponse> {
    // No need to send refresh token - it's in the HttpOnly cookie
    const response = await apiFetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include' // Include cookies in request
    });

    // Update stored access token and expiry
    this.setTokens(response.access_token, response.expires_at);

    return response;
  },

  /**
   * Logout from current session
   */
  async logout(): Promise<MessageResponse> {
    try {
      // Removed <MessageResponse> generic
      const response = await apiFetch('/auth/logout', {
        method: 'POST'
      });

      // Clear stored tokens
      this.clearTokens();

      return response;
    } catch (error) {
      // Clear tokens even if request fails
      this.clearTokens();
      throw error;
    }
  },

  /**
   * Logout from all sessions
   */
  async logoutAll(): Promise<MessageResponse> {
    try {
      // Removed <MessageResponse> generic
      const response = await apiFetch('/auth/logout-all', {
        method: 'POST'
      });

      // Clear stored tokens
      this.clearTokens();

      return response;
    } catch (error) {
      // Clear tokens even if request fails
      this.clearTokens();
      throw error;
    }
  },

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<User> {
    return apiFetch('/users/me', {
      method: 'GET'
    });
  },

  /**
   * Change password
   */
  async changePassword(data: {
    currentPassword: string;
    newPassword: string;
  }): Promise<MessageResponse> {
    return apiFetch('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  /**
   * Store access token and expiry in localStorage
   */
  setTokens(accessToken: string, expiresAt: number): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(ACCESS_TOKEN_EXPIRY_KEY, expiresAt.toString());
  },

  /**
   * Get stored access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  /**
   * Get stored access token expiry timestamp
   */
  getAccessTokenExpiry(): number | null {
    const expiry = localStorage.getItem(ACCESS_TOKEN_EXPIRY_KEY);
    return expiry ? parseInt(expiry, 10) : null;
  },

  /**
   * Store user in localStorage
   */
  setUser(user: User): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  /**
   * Get stored user
   */
  getUser(): User | null {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  /**
   * Clear all stored auth data
   */
  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(ACCESS_TOKEN_EXPIRY_KEY);
    localStorage.removeItem(USER_KEY);
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
};