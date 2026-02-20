"""
Vector Database Service (Chroma or placeholder).
"""
import asyncio
from typing import Any

from backend.core.config import settings


def _chroma_upsert(ids: list[str], embeddings: list[list[float]], metadatas: list[dict], documents: list[str]) -> None:
    try:
        import chromadb
    except ImportError:
        return
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=settings.RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)


def _chroma_search(query_embedding: list[float], top_k: int) -> list[dict]:
    try:
        import chromadb
    except ImportError:
        return []
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=settings.RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k, include=["documents", "metadatas"])
    out = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            meta = (results["metadatas"][0] or [{}])[i] if results.get("metadatas") else {}
            out.append({"content": doc, "metadata": meta or {}})
    return out


class VectorDBService:
    """Chroma or placeholder vector database operations."""

    def __init__(self):
        self.db_type = settings.VECTOR_DB_TYPE
        self.initialized = False

    async def initialize(self):
        """Initialize vector database connection."""
        if self.db_type == "chroma":
            try:
                await asyncio.to_thread(
                    lambda: __import__("chromadb").PersistentClient(path=settings.CHROMA_PERSIST_DIR)
                )
            except ImportError:
                self.db_type = "placeholder"
        self.initialized = True

    async def upsert_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        """Upsert vectors into the database."""
        if self.db_type != "chroma":
            return
        await asyncio.to_thread(
            _chroma_upsert,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    async def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        """Search for similar vectors. Returns list of { content, metadata }."""
        if self.db_type != "chroma":
            return []
        return await asyncio.to_thread(_chroma_search, query_vector, top_k)


vector_db = VectorDBService()
