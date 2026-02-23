"""Embedding helpers backed by LOCAL_EMBEDDING_URL."""
import logging
from typing import Any

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {"bypass-tunnel-reminder": "true"}


def _to_float_vector(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return []


def _extract_embeddings(payload: dict[str, Any], expected: int) -> list[list[float]]:
    data = payload.get("data")
    if isinstance(data, list):
        vectors: list[list[float]] = []
        for item in data:
            vector = _to_float_vector((item or {}).get("embedding"))
            if vector:
                vectors.append(vector)
        if len(vectors) == expected:
            return vectors

    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list):
        vectors = [_to_float_vector(v) for v in embeddings]
        vectors = [v for v in vectors if v]
        if len(vectors) == expected:
            return vectors

    vector = _to_float_vector(payload.get("embedding"))
    if vector and expected == 1:
        return [vector]

    return []


async def embed_texts(texts: list[str]) -> list[list[float]]:
    clean_texts = [text.strip() for text in texts if text and text.strip()]
    if not clean_texts or not settings.LOCAL_EMBEDDING_URL:
        return []

    body_candidates = (
        {"input": clean_texts},
        {"texts": clean_texts},
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        for body in body_candidates:
            try:
                response = await client.post(settings.LOCAL_EMBEDDING_URL, json=body, headers=_HEADERS)
                response.raise_for_status()
                vectors = _extract_embeddings(response.json(), expected=len(clean_texts))
                if vectors:
                    return vectors
            except (httpx.ConnectError, httpx.TimeoutException):
                logger.warning("Embedding endpoint unavailable: %s", settings.LOCAL_EMBEDDING_URL)
                return []
            except httpx.HTTPStatusError as exc:
                logger.warning("Embedding request failed (%s): %s", exc.response.status_code, exc.response.text)
            except Exception:
                logger.exception("Unexpected embedding response shape")

    return []


async def embed_single(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0] if vectors else []
