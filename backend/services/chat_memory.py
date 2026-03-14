"""Conversation-memory helpers for prompt grounding."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from backend.core.config import settings

_TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "we",
    "you",
    "your",
}


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if len(token) > 2 and token not in _STOP_WORDS
    ]


def _trim(text: str, limit: int = 220) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"


def _score_turn(
    *,
    turn: dict[str, Any],
    index: int,
    total: int,
    query_counts: Counter[str],
) -> float:
    content = str(turn.get("content", "")).strip()
    if not content:
        return 0.0

    turn_counts = Counter(_tokenize(content))
    overlap = sum(min(count, turn_counts[token]) for token, count in query_counts.items())
    recency = max(0.15, 1.0 - ((total - index - 1) * 0.12))
    role_bonus = 0.18 if turn.get("role") == "user" else 0.0
    return float(overlap) * 1.6 + recency + role_bonus


def select_relevant_turns(
    message: str,
    history: list[dict[str, Any]],
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return the most relevant past turns for the current message."""
    if not history:
        return []

    limit = top_k if isinstance(top_k, int) and top_k > 0 else settings.CHAT_MEMORY_TOP_K
    query_counts = Counter(_tokenize(message))
    scored: list[tuple[float, int, dict[str, Any]]] = []

    for index, turn in enumerate(history[-16:]):
        score = _score_turn(
            turn=turn,
            index=index,
            total=min(len(history), 16),
            query_counts=query_counts,
        )
        if score > 0.4:
            scored.append((score, index, turn))

    if not scored:
        return history[-min(limit, len(history)) :]

    scored.sort(key=lambda item: (-item[0], -item[1]))
    selected = [turn for _, _, turn in scored[:limit]]

    # Preserve chronology in the returned prompt context.
    history_lookup = {id(turn): pos for pos, turn in enumerate(history)}
    selected.sort(key=lambda turn: history_lookup.get(id(turn), 0))
    return selected


def build_memory_context(message: str, history: list[dict[str, Any]]) -> str:
    """Build a compact system-message memory block from prior turns."""
    selected = select_relevant_turns(message, history)
    if not selected:
        return ""

    lines = ["Conversation memory to preserve continuity:"]
    for turn in selected:
        role = "User" if turn.get("role") == "user" else "Assistant"
        lines.append(f"- {role}: {_trim(str(turn.get('content', '')))}")

    context = "\n".join(lines)
    max_chars = max(240, settings.CHAT_MEMORY_MAX_CHARS)
    if len(context) <= max_chars:
        return context
    return f"{context[: max_chars - 1].rstrip()}…"
