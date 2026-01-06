"""
Authentication routes - localStorage-based (no JWT tokens).
Frontend stores user ID in localStorage and sends via X-User-Id header.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.auth import RegisterRequest, MessageResponse, UserResponse
from app.services.auth import register_service
from app.crud.auth import UserCRUD
from app.core.security import verify_password
from app.core.exceptions import UserAlreadyExistsException, InvalidCredentialsException
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["AUTH"])



class LoginResponse(BaseModel):
    """User info returned on successful login (stored in localStorage)."""
    id: int
    username: str
    email: str
    role: str
    message: str = "Login successful"



@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    
    Validates email uniqueness and password requirements.
    
    Args:
        request: User registration data (email, password, username)
        db: Database session
    
    Returns:
        Confirmation message
    
    Raises:
        HTTPException 409: If email already exists
        HTTPException 400: If validation fails
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



@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    User login endpoint (localStorage-based).
    
    Validates email/username and password. Returns user info that frontend
    stores in localStorage. No JWT tokens.
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session
    
    Returns:
        User info (id, username, email, role) to store in localStorage
    
    Raises:
        HTTPException 401: If credentials are invalid
    """
    try:
        # Get user by email or username
        user = UserCRUD.get_user_by_email(db, form_data.username)
        if not user:
            user = UserCRUD.get_user_by_username(db, form_data.username)
        
        if not user:
            raise InvalidCredentialsException()
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise InvalidCredentialsException()
        
        return LoginResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role or "USER",
            message="Login successful"
        )
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



@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(current_user = Depends(get_current_user)):
    """
    User logout endpoint.
    
    Frontend should clear localStorage and redirect to login page.
    Backend just confirms logout (actual auth state managed by frontend).
    
    Args:
        current_user: Current authenticated user (validates X-User-Id header)
    
    Returns:
        Confirmation message
    """
    return {"message": f"User {current_user.username} logged out successfully"}



@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Uses X-User-Id header from localStorage.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user info
    
    Raises:
        HTTPException 401: If not authenticated
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role or "USER"
    )
