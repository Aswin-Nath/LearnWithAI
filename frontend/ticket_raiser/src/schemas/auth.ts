// Auth Requests
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  role?: 'USER' | 'PROBLEM_SETTER';
}

export interface LoginRequest {
  username: string;
  password: string;
}

// Auth Responses
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  expires_at: number;
}

export interface MessageResponse {
  message: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'USER' | 'PROBLEM_SETTER';
  created_at: string;
}

export interface UserResponse extends User {}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  accessTokenExpiry: number | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
