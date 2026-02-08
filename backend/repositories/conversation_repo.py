"""
Conversation and message persistence using MongoDB.
"""
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId

from backend.core.database import get_database


CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"


async def create_conversation(
    title: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Create a new conversation. Returns conversation_id (str)."""
    database = get_database()
    now = datetime.utcnow()
    doc = {
        "created_at": now,
        "updated_at": now,
        "title": title,
        "metadata": metadata or {},
    }
    result = await database[CONVERSATIONS_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


async def get_or_create_conversation(conversation_id: Optional[str] = None) -> str:
    """Get existing conversation id or create a new one. Returns conversation_id (str)."""
    if conversation_id:
        try:
            database = get_database()
            if await database[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)}):
                return conversation_id
        except Exception:
            pass
    return await create_conversation()


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Append a message to a conversation. Returns message id."""
    database = get_database()
    now = datetime.utcnow()
    doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": now,
        "metadata": metadata or {},
    }
    result = await database[MESSAGES_COLLECTION].insert_one(doc)
    # Update conversation updated_at
    await database[CONVERSATIONS_COLLECTION].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"updated_at": now}},
    )
    return str(result.inserted_id)


async def get_conversation_messages(conversation_id: str) -> list[dict]:
    """Return all messages for a conversation, ordered by timestamp."""
    database = get_database()
    cursor = database[MESSAGES_COLLECTION].find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1)
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],
            "content": doc["content"],
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
        })
    return messages


async def conversation_exists(conversation_id: str) -> bool:
    """Check if a conversation exists."""
    database = get_database()
    try:
        return await database[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)}) is not None
    except Exception:
        return False
