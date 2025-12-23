from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# Register Request
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Optional[str] = Field(default="USER", pattern="^(USER|PROBLEM_SETTER)$")


# Login Request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


# Refresh Token Request
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Token Response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # in seconds
    expires_at: int  # unix timestamp for expiry


# User Response
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# Session Response (for admin)
class SessionResponse(BaseModel):
    session_id: str
    user_id: int
    is_active: bool
    login_time: datetime
    last_active: datetime
    device_info: Optional[str]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# Generic Message Response
class MessageResponse(BaseModel):
    message: str


# Error Response
class ErrorResponse(BaseModel):
    detail: str
