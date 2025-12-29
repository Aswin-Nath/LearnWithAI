// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_TIMEOUT = 10000; // 10 seconds

// localStorage Keys (Simple localStorage-based auth - no JWT)
export const USER_KEY = 'user';
export const USER_ID_KEY = 'userId';
