from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime


# Test Case Schemas

class TestCaseCreate(BaseModel):
    """Schema for creating a test case with input validation"""
    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_sample: bool = False
    
    @field_validator('input_data', 'expected_output', mode='before')
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        """Strip leading/trailing whitespace from test case data"""
        if isinstance(value, str):
            return value.strip()
        return value


class TestCaseResponse(BaseModel):
    """Schema for test case response"""
    id: int
    input_data: str
    expected_output: str
    is_sample: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case"""
    input_data: Optional[str] = Field(None, min_length=1)
    expected_output: Optional[str] = Field(None, min_length=1)
    is_sample: Optional[bool] = None
    
    @field_validator('input_data', 'expected_output', mode='before')
    @classmethod
    def strip_whitespace(cls, value):
        """Strip leading/trailing whitespace from test case data"""
        if isinstance(value, str):
            return value.strip()
        return value


# Problem Schemas

class ProblemCreate(BaseModel):
    """Schema for creating a problem"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    constraints: str = Field(..., min_length=1)
    difficulty: str = Field(..., pattern="^(EASY|MEDIUM|HARD)$")
    time_limit_ms: int = Field(1000, ge=100, le=60000)  # 100ms to 60s


class ProblemUpdate(BaseModel):
    """Schema for updating a problem"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    constraints: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(EASY|MEDIUM|HARD)$")
    time_limit_ms: Optional[int] = Field(None, ge=100, le=60000)
    editorial_url_link: Optional[str] = None


class ProblemListResponse(BaseModel):
    """Schema for problem in list endpoint (minimal fields)"""
    id: int
    title: str
    difficulty: str
    time_limit_ms: int
    is_solved: bool
    editorial_url_link: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemDetailResponse(BaseModel):
    """Schema for problem detail endpoint (full + test cases)"""
    id: int
    title: str
    description: str
    constraints: Optional[str]
    difficulty: str
    time_limit_ms: int
    is_solved: bool
    editorial_url_link: Optional[str] = None
    test_cases: List[TestCaseResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemCreateResponse(BaseModel):
    """Schema for problem creation response"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
