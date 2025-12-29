import { apiFetch } from '../core/api';
import type {
  RegisterRequest,
  LoginRequest,
  MessageResponse,
  User
} from '../schemas/auth';

const USER_KEY = 'user';
const USER_ID_KEY = 'userId';

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
   * Login user and store in localStorage
   */
  async login(data: LoginRequest): Promise<User> {
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

    // Store user info in localStorage
    this.setUser(response);

    return response;
  },

  /**
   * Logout from session (clear localStorage)
   */
  async logout(): Promise<MessageResponse> {
    try {
      const response = await apiFetch('/auth/logout', {
        method: 'POST'
      });

      // Clear localStorage
      this.clearUser();

      return response;
    } catch (error) {
      // Clear localStorage even if request fails
      this.clearUser();
      throw error;
    }
  },

  /**
   * Store user in localStorage
   */
  setUser(user: User): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.setItem(USER_ID_KEY, user.id.toString());
  },

  /**
   * Get stored user
   */
  getUser(): User | null {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  /**
   * Get stored user ID
   */
  getUserId(): string | null {
    return localStorage.getItem(USER_ID_KEY);
  },

  /**
   * Clear all stored auth data
   */
  clearUser(): void {
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(USER_ID_KEY);
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.getUser();
  }
};