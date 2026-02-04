"""
API V1 Router
"""
from fastapi import APIRouter
from backend.api.v1.endpoints import health, chat

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
