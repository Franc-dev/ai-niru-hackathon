"""
Application Configuration
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Elevana Hackathon"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # MongoDB (Atlas in production)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_niru"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://ai-niru-hackathon.vercel.app",
    ]

    # Local model (optional — set to your model server URL when running)
    LOCAL_MODEL_URL: str = ""
    LOCAL_EMBEDDING_URL: str = ""

    # ElevenLabs Voice
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID_EN: str = ""
    ELEVENLABS_VOICE_ID_SW: str = ""
    ELEVENLABS_TTS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_STT_MODEL: str = "scribe_v1"
    ELEVENLABS_AGENT_ID_EN: str = ""
    ELEVENLABS_AGENT_ID_SW: str = ""

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
