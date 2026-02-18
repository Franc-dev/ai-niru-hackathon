"""
User persistence for authentication.
"""
from datetime import datetime
from typing import Any

from bson import ObjectId

from backend.core.database import get_database


USERS_COLLECTION = "users"


def _normalize_language(value: str | None) -> str:
    return "sw" if value == "sw" else "en"


def _to_public_user(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "email": doc.get("email", ""),
        "display_name": doc.get("display_name"),
        "preferred_language": _normalize_language(doc.get("preferred_language")),
    }


async def ensure_user_indexes() -> None:
    """Create required indexes."""
    database = get_database()
    await database[USERS_COLLECTION].create_index("email", unique=True)


async def create_user(
    email: str,
    password_hash: str,
    display_name: str | None = None,
    preferred_language: str = "en",
) -> dict[str, Any]:
    """Create user document and return public user fields."""
    database = get_database()
    now = datetime.utcnow()
    doc = {
        "email": email,
        "password_hash": password_hash,
        "display_name": display_name,
        "preferred_language": _normalize_language(preferred_language),
        "created_at": now,
        "updated_at": now,
    }
    result = await database[USERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_public_user(doc)


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Get full user doc by email."""
    database = get_database()
    return await database[USERS_COLLECTION].find_one({"email": email})


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Get full user doc by id."""
    database = get_database()
    try:
        return await database[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


async def update_user_preferred_language(user_id: str, preferred_language: str) -> bool:
    """Update user preferred language."""
    database = get_database()
    try:
        result = await database[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "preferred_language": _normalize_language(preferred_language),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0
    except Exception:
        return False


def serialize_public_user(doc: dict[str, Any]) -> dict[str, Any]:
    """Map raw user document to API-safe shape."""
    return _to_public_user(doc)
