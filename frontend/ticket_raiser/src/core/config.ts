// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_TIMEOUT = 10000; // 10 seconds

// Token Storage Keys
export const ACCESS_TOKEN_KEY = 'accessToken';
export const ACCESS_TOKEN_EXPIRY_KEY = 'accessTokenExpiry';
export const USER_KEY = 'user';

// Token Expiration Buffers
export const ACCESS_TOKEN_BUFFER = 60; // Refresh 60 seconds before expiry
