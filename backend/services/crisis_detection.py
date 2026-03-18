"""Shared crisis-language detection for routing and dataset-backed responses."""
from __future__ import annotations

import re

from backend.services.topic_focus import normalize_focus_text


CRISIS_TERMS = (
    "crisis",
    "crisis help",
    "emergency",
    "want to die",
    "kill myself",
    "end my life",
    "suicide",
    "suicidal",
    "self harm",
    "hurt myself",
    "better off dead",
    "dont want to live",
    "i want to die",
    "i need crisis help",
    "nataka kufa",
    "nataka kujiua",
    "kujiua",
    "kujidhuru",
    "msaada wa dharura",
)

_CRISIS_PATTERNS = (
    re.compile(r"\bi want to kill\b$"),
    re.compile(r"\bwant to kill\b$"),
)


def is_crisis_text(text: str) -> bool:
    normalized = normalize_focus_text(text)
    if not normalized:
        return False
    if any(term in normalized for term in CRISIS_TERMS):
        return True
    return any(pattern.search(normalized) for pattern in _CRISIS_PATTERNS)
