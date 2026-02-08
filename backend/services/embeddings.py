"""
Embeddings via our local model (trained on synthetic data).
POST to LOCAL_EMBEDDING_URL with {"input": ["text1", ...]} or {"texts": ["text1", ...]}.
Expects {"embeddings": [[...], ...]} or {"data": [{"embedding": [...]}, ...]}.
"""
import httpx
from backend.core.config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns list of vectors."""
    if not texts or not settings.LOCAL_EMBEDDING_URL:
        return []
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(settings.LOCAL_EMBEDDING_URL, json={"input": texts})
        r.raise_for_status()
        data = r.json()
    if "embeddings" in data:
        return data["embeddings"]
    if "data" in data:
        return [item["embedding"] for item in data["data"]]
    return []


async def embed_single(text: str) -> list[float]:
    """Embed a single string. Returns one vector."""
    vectors = await embed_texts([text])
    return vectors[0] if vectors else []
