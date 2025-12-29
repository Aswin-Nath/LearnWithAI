import { useCallback } from 'react';

interface UseTokenRefreshReturn {
  refreshToken: () => Promise<boolean>;
  isTokenExpiringSoon: () => boolean;
}

export function useTokenRefresh(): UseTokenRefreshReturn {
  // Token refresh disabled - using manual login/logout only
  const isTokenExpiringSoon = useCallback(() => {
    return false; // Tokens never expire automatically
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    // Token refresh disabled - user must login again manually
    return false;
  }, []);

  return {
    refreshToken,
    isTokenExpiringSoon
  };
}
