"""Embeddings — disabled in production (no local model)."""


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return []


async def embed_single(text: str) -> list[float]:
    return []
