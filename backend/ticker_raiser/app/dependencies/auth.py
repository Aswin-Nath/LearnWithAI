from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging
from typing import List

from app.core.database import get_db
from app.services.auth import AuthService
from app.core.security import decode_token

_logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user from OAuth2 JWT token.
    
    Validates:
    1. JWT token signature and expiration
    2. User exists in database
    
    Args:
        token (str): OAuth2 bearer token
        db (Session): Database session
    
    Returns:
        User: Current authenticated user
    
    Raises:
        HTTPException (401): If token is invalid or user not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
    except Exception as e:
        _logger.debug("Token validation failed: %s", str(e))
        raise credentials_exception

    try:
        user = AuthService.get_current_user(db, int(user_id))
        if not user:
            raise credentials_exception
        return user
    except Exception as e:
        _logger.debug("User retrieval failed: %s", str(e))
        raise credentials_exception


def get_token_from_header(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extract and return OAuth2 bearer token from authorization header.
    
    Args:
        token (str): OAuth2 bearer token
    
    Returns:
        str: The bearer token
    
    Raises:
        HTTPException (401): If token is missing
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return token


def get_current_user_with_scopes(required_scopes: List[str]):
    """
    Dependency factory to get current user and check if their role is in required scopes.
    
    Args:
        required_scopes: List of allowed roles/scopes (e.g., ["USER", "PROBLEM_SETTER"])
    
    Returns:
        A dependency function that validates user role against scopes
    
    Raises:
        HTTPException (403): If user's role is not in required scopes
    
    Usage:
        @router.post("/problems", dependencies=[Depends(get_current_user_with_scopes(["PROBLEM_SETTER"]))])
        async def create_problem(...):
            ...
    """
    async def check_role(current_user = Depends(get_current_user)):
        if current_user.role not in required_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized. Required scopes: {', '.join(required_scopes)}"
            )
        return current_user
    
    return check_role

