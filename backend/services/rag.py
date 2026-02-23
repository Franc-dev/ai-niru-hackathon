"""Minimal retrieval and ingestion helpers for chat."""
from backend.core.config import settings
from backend.services.embeddings import embed_single, embed_texts
from backend.services.vector_db import vector_db

_CHUNK_SIZE = 700
_CHUNK_OVERLAP = 120


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    content = (text or "").strip()
    if not content:
        return []

    chunks: list[str] = []
    start = 0
    size = max(120, chunk_size)
    overlap_size = max(0, min(overlap, size - 1))

    while start < len(content):
        end = min(len(content), start + size)
        chunks.append(content[start:end])
        if end >= len(content):
            break
        start = end - overlap_size

    return chunks


async def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    if settings.VECTOR_DB_TYPE != "chroma":
        return []

    query_embedding = await embed_single(query)
    if not query_embedding:
        return []

    limit = top_k if isinstance(top_k, int) and top_k > 0 else settings.RAG_TOP_K
    return await vector_db.search(query_embedding, top_k=limit)


async def ingest_documents(documents: list[dict]) -> None:
    if settings.VECTOR_DB_TYPE != "chroma" or not documents:
        return

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for doc in documents:
        text = (doc or {}).get("text", "")
        doc_id = str((doc or {}).get("id", "")).strip()
        metadata = (doc or {}).get("metadata", {}) or {}
        if not text or not doc_id:
            continue

        for index, chunk in enumerate(chunk_text(text)):
            ids.append(f"{doc_id}:{index}")
            texts.append(chunk)
            metadatas.append({"chunk_index": index, **metadata})

    if not texts:
        return

    vectors = await embed_texts(texts)
    if len(vectors) != len(texts):
        return

    await vector_db.upsert_vectors(ids=ids, embeddings=vectors, metadatas=metadatas, documents=texts)
