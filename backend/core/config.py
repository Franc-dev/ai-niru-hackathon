"""
Application Configuration
"""
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


VERCEL_ORIGIN = "https://ai-niru-hackathon.vercel.app"


def _parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
    """Parse CORS origins from env: JSON list or comma-separated string."""
    if isinstance(v, list):
        origins = [x.strip() for x in v if x]
    elif isinstance(v, str):
        if v.strip().startswith("["):
            import json
            origins = json.loads(v)
        else:
            origins = [x.strip() for x in v.split(",") if x.strip()]
    else:
        origins = []
    # Always include Vercel frontend
    if VERCEL_ORIGIN not in origins:
        origins.append(VERCEL_ORIGIN)
    return origins


class Settings(BaseSettings):
    PROJECT_NAME: str = "Elevana Hackathon"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # MongoDB (Atlas in production)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_niru"

    # CORS — supports JSON ["a","b"] or comma-separated "a,b"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://ai-niru-hackathon.vercel.app",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if not v:
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                VERCEL_ORIGIN,
            ]
        return _parse_cors_origins(v)

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
