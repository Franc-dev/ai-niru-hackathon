"""
Conversation and Message models for MongoDB.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Input for creating a conversation."""
    title: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class Conversation(BaseModel):
    """Conversation document."""
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    class Config:
        populate_by_name = True


class MessageCreate(BaseModel):
    """Input for adding a message."""
    conversation_id: str
    role: str  # user | assistant | system
    content: str
    metadata: Optional[dict[str, Any]] = None


class Message(BaseModel):
    """Message document."""
    id: Optional[str] = Field(None, alias="_id")
    conversation_id: str = ""
    role: str = ""
    content: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict[str, Any]] = None

    class Config:
        populate_by_name = True
