"""
Health Check Endpoints
"""
from fastapi import APIRouter

from backend.core.database import db
from backend.core.config import settings
from backend.services.vector_db import vector_db

router = APIRouter()


@router.get("/")
async def health():
    """Basic health. Includes mongo and vector_db status when available."""
    mongo = "unavailable"
    if db.client is not None:
        try:
            await db.client.admin.command("ping")
            mongo = "ok"
        except Exception:
            mongo = "error"

    vector_db_status = "unavailable"
    if settings.VECTOR_DB_TYPE == "chroma":
        vector_db_status = "ok" if vector_db.initialized else "not_initialized"
    else:
        vector_db_status = "placeholder"

    return {
        "status": "ok",
        "service": "api",
        "mongo": mongo,
        "vector_db": vector_db_status,
    }
