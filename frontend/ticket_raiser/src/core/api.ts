import { API_BASE_URL, API_TIMEOUT } from './config';
import {
  APIError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ValidationError,
  ConflictError,
  ServerError
} from './errors';

interface FetchOptions extends RequestInit {
  timeout?: number;
  headers?: Record<string, string>;
}

export async function apiFetch(
  endpoint: string,
  options: FetchOptions = {}
): Promise<any> {
  const { timeout = API_TIMEOUT, headers = {}, ...fetchOptions } = options;

  const url = `${API_BASE_URL}${endpoint}`;

  // Check if body is FormData (for file uploads)
  const isFormData = fetchOptions.body instanceof FormData;

  // Add default headers (skip Content-Type for FormData - let browser set it)
  const defaultHeaders: Record<string, string> = {};
  
  if (!isFormData) {
    defaultHeaders['Content-Type'] = 'application/json';
  }
  
  // Merge with provided headers
  Object.assign(defaultHeaders, headers);

  // Add user ID header for authentication (localStorage-based)
  const userId = localStorage.getItem('userId');
  if (userId) {
    defaultHeaders['X-User-Id'] = userId;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers: defaultHeaders,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.status === 204) {
      return null;
    }

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      handleErrorResponse(response.status, data);
    }

    return data;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new ServerError('Network error - unable to reach server');
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ServerError(`Request timeout after ${timeout}ms`);
    }

    throw new ServerError(
      error instanceof Error ? error.message : 'Unknown error occurred'
    );
  }
}

function handleErrorResponse(status: number, data: any): never {
  let message = 'Unknown error';

  // Handle validation errors with detail array
  if (status === 422 && Array.isArray(data?.detail)) {
    const errors = data.detail.map((err: any) => {
      const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : 'field';
      return `${field}: ${err.msg}`;
    }).join(', ');
    message = errors || 'Validation error';
  } else {
    message = typeof data === 'string' ? data : data?.detail || 'Unknown error';
  }

  switch (status) {
    case 401:
      throw new AuthenticationError(message);
    case 403:
      throw new AuthorizationError(message);
    case 404:
      throw new NotFoundError(message);
    case 409:
      throw new ConflictError(message, data);
    case 422:
      throw new ValidationError(message, data);
    case 500:
    case 502:
    case 503:
    case 504:
      throw new ServerError(message);
    default:
      throw new APIError(status, message, data);
  }
}