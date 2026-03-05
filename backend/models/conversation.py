"""
Conversation and Message models for MongoDB.
"""
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

LanguageCode = Literal["en", "sw"]


class ConversationCreate(BaseModel):
    """Input for creating a conversation."""
    user_id: str
    title: Optional[str] = None
    language: LanguageCode = "en"
    metadata: Optional[dict[str, Any]] = None


class Conversation(BaseModel):
    """Conversation document."""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    title_auto_generated: bool = False
    language: LanguageCode = "en"
    pinned: bool = False
    archived: bool = False
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
        # Note:
        # If your training script errors with:
        # TypeError: SFTTrainer.__init__() got an unexpected keyword argument 'max_seq_len'
        # your installed TRL version expects `max_seq_length` instead.
        # Update in training/scripts/train_mistral_lora.py:
        #
        # trainer = SFTTrainer(
        #     ...
        #     max_seq_length=1024,  # not max_seq_len
        #     ...
        # )
        #
        # Also fix TRL arg names for compatibility:
        # - use `max_seq_length` (not `max_seq_len`) in SFTTrainer
        # - use `warmup_steps` in TrainingArguments (warmup_ratio is deprecated)