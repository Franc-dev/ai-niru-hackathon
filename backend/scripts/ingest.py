"""
RAG ingestion script: read .txt/.md from a directory, chunk, embed via our local model, upsert to Chroma.
Usage: python -m backend.scripts.ingest --path data/documents
Run from project root. Requires LOCAL_EMBEDDING_URL and VECTOR_DB_TYPE=chroma.
"""
import argparse
import asyncio
from pathlib import Path

# Load env before importing app modules
from dotenv import load_dotenv
load_dotenv()

from backend.services.rag import ingest_documents, chunk_text
from backend.services.embeddings import embed_texts
from backend.services.vector_db import vector_db
from backend.core.config import settings


def load_documents_from_path(path: str) -> list[dict]:
    """Load .txt and .md files from path. Returns list of { id, text, metadata }."""
    root = Path(path)
    if not root.is_dir():
        return []
    documents = []
    for ext in ("*.txt", "*.md"):
        for f in root.glob(ext):
            text = f.read_text(encoding="utf-8", errors="replace")
            documents.append({
                "id": f.stem,
                "text": text,
                "metadata": {"source": str(f.name)},
            })
    return documents


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG vector store")
    parser.add_argument("--path", default="data/documents", help="Directory containing .txt/.md files")
    args = parser.parse_args()

    if settings.VECTOR_DB_TYPE != "chroma":
        print("Set VECTOR_DB_TYPE=chroma and CHROMA_PERSIST_DIR in .env")
        return

    docs = load_documents_from_path(args.path)
    if not docs:
        print(f"No .txt or .md files found in {args.path}")
        return

    print(f"Ingesting {len(docs)} document(s) from {args.path}")
    await vector_db.initialize()
    await ingest_documents(docs)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
