"""
FastAPI Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.database import connect_to_mongo, close_mongo_connection
from backend.api.v1.router import api_router
from backend.repositories.conversation_repo import ensure_conversation_indexes
from backend.repositories.user_repo import ensure_user_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    await connect_to_mongo()
    await ensure_user_indexes()
    await ensure_conversation_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Elevana Hackathon API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "Elevana Hackathon API", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
