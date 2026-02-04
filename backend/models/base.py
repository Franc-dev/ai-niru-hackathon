"""
Base Models
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseDocument(BaseModel):
    """Base document model"""
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
