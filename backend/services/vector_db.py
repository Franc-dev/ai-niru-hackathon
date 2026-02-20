"""Vector database — disabled in production (no chromadb/SQLite)."""
from typing import Any


class VectorDBService:
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def upsert_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        return

    async def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        return []


vector_db = VectorDBService()
