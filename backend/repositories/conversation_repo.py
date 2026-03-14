"""
Conversation and message persistence using MongoDB.
"""
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId

from backend.core.database import get_database


CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"


def _serialize_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


def _normalize_language(value: str | None) -> str:
    return "sw" if value == "sw" else "en"


def _serialize_conversation(doc: dict[str, Any]) -> dict[str, Any]:
    conversation_id = str(doc["_id"])
    return {
        "conversation_id": conversation_id,
        "title": doc.get("title"),
        "language": _normalize_language(doc.get("language")),
        "created_at": _serialize_datetime(doc.get("created_at")),
        "updated_at": _serialize_datetime(doc.get("updated_at")),
        "pinned": doc.get("pinned", False),
        "archived": doc.get("archived", False),
    }


async def ensure_conversation_indexes() -> None:
    """Create indexes needed by chat queries."""
    database = get_database()
    await database[CONVERSATIONS_COLLECTION].create_index([("user_id", 1), ("updated_at", -1)])
    await database[MESSAGES_COLLECTION].create_index([("conversation_id", 1), ("timestamp", 1)])


async def create_conversation(
    user_id: str,
    title: Optional[str] = None,
    language: str = "en",
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Create a new conversation. Returns conversation_id (str)."""
    database = get_database()
    now = datetime.utcnow()
    doc = {
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "title": title,
        "title_auto_generated": False,
        "language": _normalize_language(language),
        "metadata": metadata or {},
    }
    result = await database[CONVERSATIONS_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


async def get_or_create_conversation(
    user_id: str,
    conversation_id: Optional[str] = None,
    language: str = "en",
) -> str:
    """Get existing conversation id or create a new one. Returns conversation_id (str)."""
    if conversation_id:
        try:
            database = get_database()
            if await database[CONVERSATIONS_COLLECTION].find_one(
                {"_id": ObjectId(conversation_id), "user_id": user_id}
            ):
                return conversation_id
        except Exception:
            pass
    return await create_conversation(user_id=user_id, language=language)


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
            "message_id": str(doc["_id"]),
            "role": doc["role"],
            "content": doc["content"],
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "metadata": doc.get("metadata") or {},
        })
    return messages


async def conversation_exists(conversation_id: str, user_id: str) -> bool:
    """Check if a conversation exists for a user."""
    database = get_database()
    try:
        return await database[CONVERSATIONS_COLLECTION].find_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        ) is not None
    except Exception:
        return False


async def get_conversation(conversation_id: str, user_id: str) -> dict[str, Any] | None:
    """Get conversation metadata for a user."""
    database = get_database()
    try:
        doc = await database[CONVERSATIONS_COLLECTION].find_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )
    except Exception:
        return None
    if not doc:
        return None
    return _serialize_conversation(doc)


async def list_conversations(
    user_id: str, limit: int = 50, include_archived: bool = False
) -> list[dict[str, Any]]:
    """List user conversations with latest preview text. Pinned first, then by updated_at."""
    database = get_database()
    query: dict[str, Any] = {"user_id": user_id}
    if not include_archived:
        query["$or"] = [{"archived": {"$ne": True}}, {"archived": {"$exists": False}}]

    cursor = (
        database[CONVERSATIONS_COLLECTION]
        .find(query)
        .sort([("pinned", -1), ("updated_at", -1)])
        .limit(limit)
    )

    conversations: list[dict[str, Any]] = []
    async for doc in cursor:
        conversation_id = str(doc["_id"])
        latest_message = await (
            database[MESSAGES_COLLECTION]
            .find({"conversation_id": conversation_id})
            .sort("timestamp", -1)
            .limit(1)
            .to_list(length=1)
        )
        preview = latest_message[0]["content"] if latest_message else ""
        item = _serialize_conversation(doc)
        item["preview"] = preview
        conversations.append(item)
    return conversations


async def update_conversation_language(conversation_id: str, user_id: str, language: str) -> bool:
    """Update conversation language for a user."""
    database = get_database()
    try:
        result = await database[CONVERSATIONS_COLLECTION].update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {
                "$set": {
                    "language": _normalize_language(language),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0
    except Exception:
        return False


async def set_conversation_title_if_empty(conversation_id: str, user_id: str, title: str) -> bool:
    """Set generated title once, if the conversation title is empty."""
    database = get_database()
    if not title:
        return False
    try:
        result = await database[CONVERSATIONS_COLLECTION].update_one(
            {
                "_id": ObjectId(conversation_id),
                "user_id": user_id,
                "$or": [
                    {"title": None},
                    {"title": ""},
                ],
            },
            {
                "$set": {
                    "title": title,
                    "title_auto_generated": True,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0
    except Exception:
        return False


async def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """Delete a conversation and all its messages."""
    database = get_database()
    try:
        result = await database[CONVERSATIONS_COLLECTION].delete_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )
        if result.deleted_count > 0:
            await database[MESSAGES_COLLECTION].delete_many(
                {"conversation_id": conversation_id}
            )
            return True
        return False
    except Exception:
        return False


async def update_conversation_title(conversation_id: str, user_id: str, title: str) -> bool:
    """Manually update conversation title."""
    database = get_database()
    try:
        result = await database[CONVERSATIONS_COLLECTION].update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {
                "$set": {
                    "title": title,
                    "title_auto_generated": False,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0
    except Exception:
        return False


async def pin_conversation(conversation_id: str, user_id: str, pinned: bool) -> bool:
    """Toggle pin status on a conversation."""
    database = get_database()
    try:
        result = await database[CONVERSATIONS_COLLECTION].update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {"$set": {"pinned": pinned, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0
    except Exception:
        return False


async def archive_conversation(conversation_id: str, user_id: str, archived: bool) -> bool:
    """Toggle archive status on a conversation."""
    database = get_database()
    try:
        result = await database[CONVERSATIONS_COLLECTION].update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {"$set": {"archived": archived, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0
    except Exception:
        return False


async def delete_message(message_id: str, conversation_id: str) -> bool:
    """Delete a single message."""
    database = get_database()
    try:
        result = await database[MESSAGES_COLLECTION].delete_one(
            {"_id": ObjectId(message_id), "conversation_id": conversation_id}
        )
        return result.deleted_count > 0
    except Exception:
        return False


async def update_message_content(message_id: str, conversation_id: str, content: str) -> bool:
    """Edit message content."""
    database = get_database()
    try:
        result = await database[MESSAGES_COLLECTION].update_one(
            {"_id": ObjectId(message_id), "conversation_id": conversation_id},
            {"$set": {"content": content}},
        )
        return result.modified_count > 0
    except Exception:
        return False
