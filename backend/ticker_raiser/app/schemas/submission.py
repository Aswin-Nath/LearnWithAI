from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


class SubmissionCreate(BaseModel):
    """Schema for creating a submission"""
    problem_id: int = Field(..., gt=0, description="Problem ID must be positive")
    code: str = Field(..., min_length=1, max_length=100000, description="Code length must be 1-100KB")
    language: str = Field("python", pattern="^(python)$", description="Only Python is supported")
    
    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        """Validate code content"""
        if not v or not v.strip():
            raise ValueError("Code cannot be empty or whitespace only")
        if len(v) > 100000:
            raise ValueError("Code too large (max 100KB)")
        return v
    
    @field_validator("problem_id")
    @classmethod
    def validate_problem_id(cls, v):
        """Validate problem ID"""
        if v <= 0:
            raise ValueError("Problem ID must be positive")
        return v


class SubmissionResponse(BaseModel):
    """Schema for submission response"""
    id: int
    user_id: int
    problem_id: int
    code: str
    language: str
    status: str  # PENDING, ACCEPTED, WRONG_ANSWER, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED
    test_cases_passed: int
    total_test_cases: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """Schema for submission in list endpoint"""
    id: int
    problem_id: int
    language: str
    status: str
    test_cases_passed: int
    total_test_cases: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
