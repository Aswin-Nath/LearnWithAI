// API Error types
export class APIError extends Error {
  public status: number; // Explicit property declaration
  public data?: any;     // Explicit property declaration

  constructor(
    status: number,      // Regular parameter (no 'public' modifier here)
    message: string,
    data?: any
  ) {
    super(message);
    this.status = status; // Explicit assignment
    this.data = data;     // Explicit assignment
    this.name = 'APIError';
  }
}

export class AuthenticationError extends APIError {
  constructor(message = 'Authentication failed') {
    super(401, message);
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends APIError {
  constructor(message = 'Access denied') {
    super(403, message);
    this.name = 'AuthorizationError';
  }
}

export class NotFoundError extends APIError {
  constructor(message = 'Resource not found') {
    super(404, message);
    this.name = 'NotFoundError';
  }
}

export class ValidationError extends APIError {
  constructor(message = 'Validation failed', data?: any) {
    super(422, message, data);
    this.name = 'ValidationError';
  }
}

export class ConflictError extends APIError {
  constructor(message = 'Resource conflict', data?: any) {
    super(409, message, data);
    this.name = 'ConflictError';
  }
}

export class ServerError extends APIError {
  constructor(message = 'Server error') {
    super(500, message);
    this.name = 'ServerError';
  }
}