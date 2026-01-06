"""
Centralized error handling and responses
"""

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional, Any, Dict


class APIError(HTTPException):
    """Base API error with consistent response format"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message,
                "details": self.details
            }
        )


class ValidationError(APIError):
    """Input validation error"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details
        )


class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=message
        )


class AuthenticationError(APIError):
    """Authentication failed error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            message=message
        )


class AuthorizationError(APIError):
    """Authorization denied error"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
            message=message
        )


class ConflictError(APIError):
    """Resource conflict error (e.g., duplicate)"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            message=message,
            details=details
        )


class ServerError(APIError):
    """Internal server error"""
    def __init__(self, message: str = "Internal server error", error_code: str = "SERVER_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            message=message
        )


# Error response templates
def success_response(data: Any, message: str = "Success") -> Dict:
    """Format success response"""
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(error_code: str, message: str, details: Optional[Dict] = None) -> Dict:
    """Format error response"""
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details or {}
    }
