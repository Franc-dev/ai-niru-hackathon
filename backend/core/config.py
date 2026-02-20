"""
Application Configuration
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Elevana Hackathon"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_niru"
    
    # Vector DB (placeholder | chroma)
    VECTOR_DB_TYPE: str = "placeholder"
    VECTOR_DB_URL: str = ""
    VECTOR_DB_API_KEY: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    RAG_COLLECTION_NAME: str = "rag_docs"
    RAG_TOP_K: int = 5

    # Local model (trained on our synthetic data)
    LOCAL_MODEL_URL: str = "http://localhost:8001/v1/chat"
    LOCAL_EMBEDDING_URL: str = "http://localhost:8001/v1/embeddings"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # ElevenLabs Voice
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID_EN: str = "pNInz6obpgDQGcFmaJgB"
    ELEVENLABS_VOICE_ID_SW: str = "EXAVITQu4vr4xnSDxMaL"
    ELEVENLABS_TTS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_STT_MODEL: str = "scribe_v1"

    # ElevenLabs Conversational AI agent IDs (create at elevenlabs.io/app/conversational-ai)
    ELEVENLABS_AGENT_ID_EN: str = ""
    ELEVENLABS_AGENT_ID_SW: str = ""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
