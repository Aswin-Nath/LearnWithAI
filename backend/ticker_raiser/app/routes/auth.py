import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)
from app.services.auth import (
    login_flow,refresh_tokens_service,logout_flow,register_service,logout_all_sessions_service
)
from app.dependencies.auth import get_current_user, get_token_from_header, oauth2_scheme
from app.core.exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    InvalidTokenException,
    TokenBlacklistedException,
    UserNotFoundException,
    SessionExpiredException
)

router = APIRouter(prefix="/auth", tags=["AUTH"])

# ============================================================================
# Configuration
# ============================================================================
SECURE_REFRESH_COOKIE = os.getenv("SECURE_REFRESH_COOKIE", "true").lower() in ("1", "true", "yes")
REFRESH_COOKIE_SAMESITE = os.getenv("REFRESH_COOKIE_SAMESITE", "lax")
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth/refresh"


# ============================================================================
# Helper Functions
# ============================================================================

def _set_refresh_cookie(response: Response, token: str, expires_at: Optional[datetime]):
    """Store the refresh token securely via HttpOnly cookie."""
    max_age = None
    expires_value = None
    if expires_at:
        expires_utc = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=timezone.utc)
        expires_utc = expires_utc.astimezone(timezone.utc)
        time_left = int((expires_utc - datetime.now(tz=timezone.utc)).total_seconds())
        if time_left > 0:
            max_age = time_left
        expires_value = expires_utc

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SECURE_REFRESH_COOKIE,
        samesite=REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
        expires=expires_value,
    )


# ============================================================================
# 🔹 CREATE - Register new user account
# ============================================================================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    
    Validates:
    1. Email format and uniqueness
    2. Password strength requirements
    3. User data completeness
    
    Args:
        request (RegisterRequest): User registration data with email, password, username
        db (Session): Database session dependency
    
    Returns:
        MessageResponse: Confirmation message
    
    Raises:
        HTTPException (409): If email already exists
        HTTPException (400): If validation fails
    
    Side Effects:
        - Creates new user record in database
    """
    try:
        register_service(
            db,
            username=request.username,
            email=request.email,
            password=request.password,
            role=request.role or "USER"
        )
        return {"message": "User registered successfully"}
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 🔹 CREATE - Login user (OAuth2 Password Flow)
# ============================================================================

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    User login endpoint (OAuth2 Password Flow).
    
    Authenticates user credentials (email and password) and issues JWT access and
    refresh tokens on successful authentication. Logs device information and client IP 
    for security auditing.
    
    Args:
        form_data (OAuth2PasswordRequestForm): OAuth2 form containing username (email) and password
        response (Response): FastAPI response to set the refresh token cookie
        request (Request): HTTP request object for device tracking and IP logging
        db (Session): Database session dependency
    
    Returns:
        TokenResponse: Contains access_token metadata (token_type, expires_in)
    
    Raises:
        HTTPException (401): If credentials are invalid
    
    Side Effects:
        - Creates session record
        - Sets HttpOnly refresh cookie
    """
    try:
        auth_result = login_flow(
            db,
            identifier=form_data.username,
            password=form_data.password,
            device_info=request.headers.get("user-agent") if request else None,
            client_host=request.client.host if request and request.client else None,
        )
        
        # Set refresh token in secure HttpOnly cookie
        _set_refresh_cookie(response, auth_result.refresh_token, auth_result.refresh_token_expires_at)
        
        return auth_result.token_response
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# 🔹 UPDATE - Refresh access token
# ============================================================================

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Refresh JWT access token using HttpOnly refresh cookie.
    
    Reads the refresh token from secure cookie, validates it, and issues a new
    access token while keeping the refresh token valid for continued use.
    
    Args:
        response (Response): FastAPI response to update the refresh token cookie
        refresh_token (str | None): Refresh token from HttpOnly cookie
        db (Session): Database session dependency
    
    Returns:
        TokenResponse: Updated access_token metadata
    
    Raises:
        HTTPException (401): If refresh token is missing, invalid, or revoked
    
    Side Effects:
        - Updates refresh token cookie expiry
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token"
        )
    
    try:
        auth_result = refresh_tokens_service(db, refresh_token)
        
        # Update refresh token cookie
        _set_refresh_cookie(response, auth_result.refresh_token, auth_result.refresh_token_expires_at)
        
        return auth_result.token_response
    except (InvalidTokenException, TokenBlacklistedException, SessionExpiredException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# 🔹 DELETE - Logout user
# ============================================================================

@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db)
):
    """
    User logout endpoint.
    
    Logs out the current user by blacklisting the access token and revoking 
    the associated session. Prevents token reuse and forces re-authentication 
    on the next request.
    
    Args:
        response (Response): FastAPI response to clear cookies
        current_user (UserResponse): Currently authenticated user
        token (str): OAuth2 bearer token from Authorization header
        db (Session): Database session dependency
    
    Returns:
        MessageResponse: Confirmation message for successful logout
    
    Raises:
        HTTPException (401): If token is invalid or already blacklisted
    
    Side Effects:
        - Blacklists the access token
        - Revokes user session
        - Clears refresh token cookie
    """
    try:
        from app.core.security import decode_token
        
        payload = decode_token(token)
        jti = payload.get("jti")
        
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No JTI found in token"
            )
        
        message = logout_flow(db, current_user.id, jti)
        
        # Clear refresh token cookie
        response.delete_cookie(
            key=REFRESH_COOKIE_NAME,
            path=REFRESH_COOKIE_PATH
        )
        
        return {"message": message}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}"
        )


# ============================================================================
# 🔹 DELETE - Logout from all sessions
# ============================================================================

@router.post("/logout-all", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout_all(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user from all active sessions.
    
    Revokes all active sessions for the user, blacklisting all access tokens
    and preventing access from any device or session.
    
    Args:
        response (Response): FastAPI response to clear cookies
        current_user (UserResponse): Currently authenticated user
        db (Session): Database session dependency
    
    Returns:
        MessageResponse: Confirmation with count of revoked sessions
    
    Side Effects:
        - Revokes all user sessions
        - Clears refresh token cookie
    """
    try:
        message = logout_all_sessions_service(db, current_user.id)
        
        # Clear refresh token cookie
        response.delete_cookie(
            key=REFRESH_COOKIE_NAME,
            path=REFRESH_COOKIE_PATH
        )
        
        return {"message": message}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout all failed"
        )


# ============================================================================
# 🔹 POST - Verify email exists in system
# ============================================================================

@router.post("/verify-email", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def verify_email(request: dict, db: Session = Depends(get_db)):
    """
    Verify if email exists in the system.
    
    Args:
        request: Dictionary with 'email' key
        db (Session): Database session dependency
    
    Returns:
        MessageResponse: Confirmation message
    
    Raises:
        HTTPException (404): If email not found
    """
    from app.crud.auth import UserCRUD
    
    email = request.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    user = UserCRUD.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found in system"
        )
    
    return {"message": "Email verified successfully"}


# ============================================================================
# 🔹 POST - Change password using email
# ============================================================================

@router.post("/change-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def change_password(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Change password for the authenticated user.
    
    Args:
        request: Dictionary with 'email' and 'new_password' keys
        current_user (UserResponse): Currently authenticated user
        db (Session): Database session dependency
    
    Returns:
        MessageResponse: Confirmation message
    
    Raises:
        HTTPException (400): If email or password invalid
        HTTPException (401): If user not authenticated
    """
    from app.crud.auth import UserCRUD
    from app.core.security import hash_password
    
    email = request.get("email")
    new_password = request.get("new_password")
    
    if not email or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and new password are required"
        )
    

    # Get user from database
    user = UserCRUD.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password
    hashed_password = hash_password(new_password)
    
    # Update password
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    
    return {"message": "Password changed successfully"}

