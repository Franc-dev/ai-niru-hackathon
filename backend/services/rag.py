"""
RAG: retrieval and optional ingestion helpers.
"""
from backend.core.config import settings
from backend.services.embeddings import embed_single
from backend.services.vector_db import vector_db


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if overlap < chunk_size else end
    return chunks


async def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """Embed query, search vector DB, return list of { content, metadata }."""
    k = top_k if top_k is not None else settings.RAG_TOP_K
    query_embedding = await embed_single(query)
    return await vector_db.search(query_embedding, top_k=k)


async def ingest_documents(documents: list[dict]) -> None:
    """
    Ingest documents: each dict has 'id', 'text', optional 'metadata'.
    Chunks text, embeds, upserts to vector DB.
    """
    from backend.services.embeddings import embed_texts

    all_ids = []
    all_embeddings = []
    all_metadatas = []
    all_documents = []

    for doc in documents:
        doc_id = doc.get("id", "")
        text = doc.get("text", "")
        meta = doc.get("metadata") or {}
        chunks = chunk_text(text)
        if not chunks:
            continue
        embeddings = await embed_texts(chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_{i}" if doc_id else f"chunk_{i}"
            all_ids.append(chunk_id)
            all_embeddings.append(emb)
            all_metadatas.append({**meta, "chunk_index": i})
            all_documents.append(chunk)

    if all_ids:
        await vector_db.upsert_vectors(
            ids=all_ids,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
            documents=all_documents,
        )
