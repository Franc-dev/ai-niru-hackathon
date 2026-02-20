"""RAG — disabled in production. Returns empty results."""


async def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    return []


async def ingest_documents(documents: list[dict]) -> None:
    return
