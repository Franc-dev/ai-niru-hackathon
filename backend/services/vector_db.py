"""Chroma-backed vector store for chat retrieval."""
import asyncio
import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings

logger = logging.getLogger(__name__)


class VectorDBService:
    def __init__(self):
        self.initialized = False
        self._collection = None

    async def initialize(self) -> bool:
        if self.initialized:
            return True
        if settings.VECTOR_DB_TYPE != "chroma":
            return False

        try:
            import chromadb
        except ImportError:
            logger.warning("VECTOR_DB_TYPE=chroma but 'chromadb' is not installed.")
            return False

        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)

        try:
            client = chromadb.PersistentClient(path=str(persist_dir))
            self._collection = client.get_or_create_collection(name=settings.RAG_COLLECTION_NAME)
            self.initialized = True
        except Exception:
            logger.exception("Failed to initialize Chroma collection '%s'", settings.RAG_COLLECTION_NAME)
            return False

        return True

    async def upsert_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        if not ids or not embeddings or not documents:
            return
        if len(ids) != len(embeddings) or len(ids) != len(metadatas) or len(ids) != len(documents):
            return
        if not await self.initialize():
            return

        await asyncio.to_thread(
            self._collection.upsert,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    async def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        if not query_vector or top_k <= 0:
            return []
        if not await self.initialize():
            return []

        results = await asyncio.to_thread(
            self._collection.query,
            query_embeddings=[query_vector],
            n_results=max(1, top_k),
            include=["documents", "metadatas", "distances"],
        )

        ids = (results.get("ids") or [[]])[0]
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        matches: list[dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            distance = distances[idx] if idx < len(distances) else None
            score = None if distance is None else max(0.0, 1.0 - float(distance))
            matches.append(
                {
                    "id": item_id,
                    "document": documents[idx] if idx < len(documents) else "",
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "score": score,
                }
            )

        return matches


vector_db = VectorDBService()
