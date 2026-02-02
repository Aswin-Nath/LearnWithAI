from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GenerateProblemRequest(BaseModel):
    topics: str
    user_query: str
    difficulty: str = "MEDIUM"

class CustomProblemResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    editorial_markdown: Optional[str] = None
    generation_topic: Optional[str] = None
    generation_query: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
