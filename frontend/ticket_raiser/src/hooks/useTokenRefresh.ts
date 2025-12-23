import { useCallback } from 'react';
import { authService } from '../services/auth';
import { ACCESS_TOKEN_BUFFER } from '../core/config';

interface UseTokenRefreshReturn {
  refreshToken: () => Promise<boolean>;
  isTokenExpiringSoon: () => boolean;
}

export function useTokenRefresh(): UseTokenRefreshReturn {
  const isTokenExpiringSoon = useCallback(() => {
    const token = authService.getAccessToken();
    const expiryTime = authService.getAccessTokenExpiry();

    if (!token || !expiryTime) return true;

    try {
      const now = Math.floor(Date.now() / 1000); // Current time in seconds
      const expiringIn = expiryTime - now; // Seconds until expiry

      // Consider token expiring if less than buffer (60 seconds by default)
      return expiringIn < ACCESS_TOKEN_BUFFER;
    } catch (error) {
      return true;
    }
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      // No need to pass refresh token - it's in the HttpOnly cookie
      await authService.refresh();
      return true;
    } catch (error) {
      // Clear tokens if refresh fails
      authService.clearTokens();
      return false;
    }
  }, []);

  return {
    refreshToken,
    isTokenExpiringSoon
  };
}
