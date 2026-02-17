"""
User models for authentication.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


LanguageCode = Literal["en", "sw"]


class UserCreate(BaseModel):
    """Input model for user creation."""
    email: str
    password_hash: str
    display_name: Optional[str] = None
    preferred_language: LanguageCode = "en"


class User(BaseModel):
    """User document model."""
    id: Optional[str] = Field(None, alias="_id")
    email: str = ""
    password_hash: str = ""
    display_name: Optional[str] = None
    preferred_language: LanguageCode = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
