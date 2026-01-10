"""
Authentication service with business logic following LuxuryStay patterns.
"""
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.crud.auth import UserCRUD, SessionCRUD, BlacklistedTokenCRUD
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_jti,
    generate_session_id
)
from app.core.exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidTokenException,
    TokenBlacklistedException,
    SessionExpiredException,
)
from app.models.models import User
from app.schemas.auth import TokenResponse
from app.core.logger import get_logger
_logger = get_logger("auth_service")

@dataclass
class AuthResult:
    """Container for authentication operation results."""
    token_response: TokenResponse
    refresh_token: str
    refresh_token_expires_at: Optional[datetime]


# User Registration

def register_service(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: str = "USER"
) -> User:
    """
    Register a new user.
    
    Validations:
    1. Email uniqueness
    2. Username uniqueness
    3. Password requirements
    
    Args:
        db (Session): Database session
        username (str): User's username (unique)
        email (str): User's email (unique)
        password (str): User's password (plain text)
        role (str): User role (default: "USER")
    
    Returns:
        User: The newly created user record
    
    Raises:
        UserAlreadyExistsException: If email or username already exists
    """
    # Check if user already exists
    if UserCRUD.get_user_by_email(db, email):
        raise UserAlreadyExistsException("email")
    
    if UserCRUD.get_user_by_username(db, username):
        raise UserAlreadyExistsException("username")

    # Hash password and create user
    hashed_pwd = hash_password(password)
    user = UserCRUD.create_user(db, username, email, hashed_pwd, role)
    return user


# Login & Authentication

def login_flow(
    db: Session,
    identifier: str,
    password: str,
    device_info: Optional[str] = None,
    client_host: Optional[str] = None,
) -> AuthResult:
    """
    Authenticate user and create login session.
    
    Security checks:
    1. Email/password validation
    2. User existence check
    3. Password hash verification
    4. Session creation with tokens
    
    Args:
        db (Session): Database session
        identifier (str): Email or username for authentication
        password (str): User's password (plain text)
        device_info (Optional[str]): Device information for tracking
        client_host (Optional[str]): Client IP address for logging
    
    Returns:
        AuthResult: Contains access_token, refresh_token, and expiry info
    
    Raises:
        InvalidCredentialsException: If email/password combination is invalid
    """
    # Get user by email or username
    user = UserCRUD.get_user_by_email(db, identifier)
    if not user:
        user = UserCRUD.get_user_by_username(db, identifier)
    print("user",user.email)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsException()

    # Generate tokens
    jti = generate_jti()
    session_id = generate_session_id()
    
    access_token, access_exp = create_access_token(
        {"sub": str(user.id), "jti": jti}
    )
    refresh_token, refresh_exp = create_refresh_token(
        {"sub": str(user.id), "jti": jti, "type": "refresh"}
    )

    # Create session in database
    SessionCRUD.create_session(
        db,
        session_id=session_id,
        jti=jti,
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_exp,
        refresh_token_expires_at=refresh_exp,
        device_info=device_info,
        ip_address=client_host
    )

    # Calculate expires_in (15 minutes = 900 seconds)
    expires_in = 900
    expires_at = int(access_exp.timestamp())

    token_response = TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
        expires_at=expires_at
    )

    return AuthResult(
        token_response=token_response,
        refresh_token=refresh_token,
        refresh_token_expires_at=refresh_exp,
    )


# Token Refresh

def refresh_tokens_service(db: Session, refresh_token: str) -> AuthResult:
    """
    Refresh access token using refresh token.
    
    Security checks:
    1. Validates that the refresh token hasn't been blacklisted/revoked
    2. Checks if the session is still active
    3. If all checks pass, generates new access token
    
    Args:
        db (Session): Database session
        refresh_token (str): The refresh token to validate
    
    Returns:
        AuthResult: New access_token with same refresh_token, expires_in, etc.
    
    Raises:
        UnauthorizedException: If refresh token is blacklisted, session invalid, or expired
        NotFoundException: If user or session not found
    """
    if not refresh_token:
        raise InvalidTokenException("Refresh token missing")

    try:
        payload = decode_token(refresh_token)
        user_id = int(payload.get("sub"))
    except Exception as e:
        _logger.debug("refresh_tokens_service: invalid refresh token: %s", str(e))
        raise InvalidTokenException("Invalid refresh token")

    # Get session
    session = SessionCRUD.get_session_by_refresh_token(db, refresh_token)
    if not session:
        raise SessionExpiredException("Session not found")

    if not session.is_active:
        raise SessionExpiredException("Session has been revoked")

    # Check if refresh token is blacklisted
    token_hash = hash_token(refresh_token)
    if BlacklistedTokenCRUD.is_token_blacklisted(db, token_hash):
        raise TokenBlacklistedException("Refresh token has been revoked")

    # Get user
    user = UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundException("User not found")

    # Generate new access token (keep same refresh token for simplicity)
    jti = payload.get("jti")
    new_access_token, new_access_exp = create_access_token(
        {"sub": str(user.id), "jti": jti}
    )

    # Update session with new access token
    SessionCRUD.update_session_tokens(
        db,
        session,
        new_access_token,
        refresh_token,  # Keep same refresh token
        new_access_exp,
        session.refresh_token_expires_at
    )

    # Calculate expires_in (15 minutes = 900 seconds)
    expires_in = 900
    expires_at = int(new_access_exp.timestamp())

    token_response = TokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=expires_in,
        expires_at=expires_at
    )

    return AuthResult(
        token_response=token_response,
        refresh_token=refresh_token,
        refresh_token_expires_at=session.refresh_token_expires_at,
    )


# Logout

def logout_flow(db: Session, user_id: int, jti: str) -> str:
    """
    Logout user by revoking current session.
    
    Security operations:
    1. Find session by JTI
    2. Blacklist access tokens
    3. Mark session as inactive
    
    Args:
        db (Session): Database session
        user_id (int): User ID to logout
        jti (str): JWT ID from token
    
    Returns:
        str: Confirmation message
    
    Raises:
        SessionExpiredException: If session not found
        TokenBlacklistedException: If already blacklisted
    """
    # Get session by JTI
    session = SessionCRUD.get_session_by_jti(db, jti)
    
    if not session:
        raise SessionExpiredException("Session not found")
    else:
        print("Session found")
    # Mark session as inactive
    SessionCRUD.mark_session_inactive(db, str(session.session_id), "User logout")

    # Blacklist tokens
    BlacklistedTokenCRUD.add_token_to_blacklist(
        db,
        user_id=user_id,
        token_hash=hash_token(session.access_token),
        token_type="ACCESS",
        reason="User logout",
        revoked_type="LOGOUT"
    )

    BlacklistedTokenCRUD.add_token_to_blacklist(
        db,
        user_id=user_id,
        token_hash=hash_token(session.refresh_token),
        token_type="REFRESH",
        reason="User logout",
        revoked_type="LOGOUT"
    )

    return "Logged out successfully"


def logout_all_sessions_service(db: Session, user_id: int) -> str:
    """
    Logout user from all sessions.
    
    Revokes all active sessions and blacklists all tokens for the user.
    
    Args:
        db (Session): Database session
        user_id (int): User ID to logout
    
    Returns:
        str: Confirmation message with count of revoked sessions
    """
    # Revoke all active sessions
    revoked_count = SessionCRUD.revoke_all_user_sessions(
        db,
        user_id,
        "User revoked all sessions"
    )

    # Blacklist all refresh tokens
    BlacklistedTokenCRUD.blacklist_user_refresh_tokens(
        db,
        user_id,
        "User revoked all sessions"
    )

    return f"All {revoked_count} sessions revoked successfully"


# Wrapper for AuthService (maintains compatibility)

class AuthService:
    """Authentication service maintaining backward compatibility."""

    @staticmethod
    def register(db: Session, username: str, email: str, password: str, role: str = "USER") -> User:
        return register_service(db, username, email, password, role)

    @staticmethod
    def login(db: Session, email: str, password: str, device_info: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[str, str, int]:
        result = login_flow(db, email, password, device_info, ip_address)
        return result.token_response.access_token, result.refresh_token, result.token_response.expires_in

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, str, int]:
        result = refresh_tokens_service(db, refresh_token)
        return result.token_response.access_token, result.refresh_token, result.token_response.expires_in

    @staticmethod
    def logout(db: Session, user_id: int, jti: str) -> str:
        return logout_flow(db, user_id, jti)

    @staticmethod
    def logout_all_sessions(db: Session, user_id: int) -> str:
        return logout_all_sessions_service(db, user_id)

    @staticmethod
    def get_current_user(db: Session, user_id: int) -> User:
        """Get current user by ID."""
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundException()
        return user

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, str, int]:
        result = refresh_tokens_service(db, refresh_token)
        return result.token_response.access_token, result.refresh_token, result.token_response.expires_in

    @staticmethod
    def logout(db: Session, user_id: int, jti: str) -> str:
        return logout_flow(db, user_id, jti)

    @staticmethod
    def logout_all_sessions(db: Session, user_id: int) -> str:
        return logout_all_sessions_service(db, user_id)

    @staticmethod
    def get_current_user(db: Session, user_id: int) -> User:
        """Get current user by ID."""
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundException()
        return user
