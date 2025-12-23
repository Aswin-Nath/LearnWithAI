from fastapi import HTTPException, status


class AuthException(HTTPException):
    """Base authentication exception."""
    pass


class InvalidCredentialsException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


class UserAlreadyExistsException(AuthException):
    def __init__(self, field: str = "email"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with this {field} already exists"
        )


class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


class TokenBlacklistedException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )


class SessionExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired"
        )


class NotAuthenticatedException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
