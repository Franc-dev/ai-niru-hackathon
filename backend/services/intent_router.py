"""Deterministic intent routing for the main chat flow."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from backend.services.chat_memory import build_memory_context
from backend.services.recommendations import recommendation_service


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "stress": ("stress", "stressed", "pressure", "burnout", "overwhelmed", "exam", "workload"),
    "anxiety": ("anxiety", "anxious", "panic", "worried", "worry", "fear", "nervous"),
    "depression": ("depression", "depressed", "sad", "hopeless", "empty", "low mood"),
    "loneliness": ("lonely", "alone", "isolated", "unseen"),
    "relationships": ("relationship", "partner", "marriage", "family", "breakup", "friend"),
    "grief": ("grief", "loss", "mourning", "bereavement", "heartbreak"),
    "trauma": ("trauma", "ptsd", "abuse", "violence", "flashback", "assault"),
    "sleep": ("sleep", "insomnia", "nightmare", "restless", "tired"),
    "self_esteem": ("confidence", "self worth", "worthless", "esteem", "confidence"),
    "addiction": ("addiction", "alcohol", "drugs", "substance", "drinking"),
}

CRISIS_TERMS = (
    "want to die",
    "kill myself",
    "end my life",
    "suicidal",
    "self harm",
    "hurt myself",
    "better off dead",
)

RESOURCE_TERMS = ("resource", "resources", "article", "articles", "video", "videos", "watch", "read")
COUNSELOR_TERMS = ("counselor", "counsellor", "therapist", "psychologist", "psychiatrist")


@dataclass
class IntentRoute:
    intent: str
    topic: str
    memory_context: str
    prompt_context: str
    recommendation: dict[str, Any] | None = None


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _infer_topic(message: str, history: list[dict[str, Any]]) -> str:
    turns = [
        _normalize(str(turn.get("content", "")))
        for turn in history[-6:]
        if turn.get("role") == "user"
    ]
    turns.append(_normalize(message))
    joined = " ".join(turns)

    best_topic = "general_support"
    best_score = 0
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in joined)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic


def route_message(
    *,
    message: str,
    history: list[dict[str, Any]],
    language: str = "en",
) -> IntentRoute:
    normalized = _normalize(message)
    topic = _infer_topic(message, history)
    memory_context = build_memory_context(message, history)
    recommendation = recommendation_service.maybe_build_response(
        message=message,
        history=history,
        language=language,
    )

    if _contains_any(normalized, CRISIS_TERMS):
        intent = "crisis"
    elif recommendation:
        kind = str((recommendation.get("metadata") or {}).get("recommendation_kind") or "")
        intent = "resource_request" if kind == "resources" else "counselor_request" if kind == "counselors" else "tool_handoff"
    elif _contains_any(normalized, COUNSELOR_TERMS):
        intent = "counselor_request"
    elif _contains_any(normalized, RESOURCE_TERMS):
        intent = "resource_request"
    else:
        intent = "emotional_support"

    NO_MATCH_EN = (
        "No specific resources/counselors match this topic in our database. "
        "Provide warm emotional support and practical coping steps. Do not suggest resources or counselors."
    )
    NO_MATCH_SW = (
        "Hakuna rasilimali au washauri maalum wanaolingana na mada hii kwenye hifadhidata yetu. "
        "Toa msaada wa kihemko wenye joto na hatua za vitendo. Usipendekezi rasilimali au washauri."
    )
    no_match_guidance = NO_MATCH_SW if language == "sw" else NO_MATCH_EN

    guidance_lines = [
        f"Intent: {intent}",
        f"Detected topic: {topic}",
        "Stay strictly within emotional and mental-health support.",
        "Do not diagnose, prescribe medication, or invent organizations, clinicians, or resources.",
        "Use a warm, grounded tone with 2-4 practical next steps.",
        "Ask at most one gentle follow-up question when it helps.",
    ]
    if memory_context:
        guidance_lines.append(memory_context)
    if not recommendation and intent in ("resource_request", "counselor_request"):
        guidance_lines.append(no_match_guidance)
    if recommendation:
        metadata = recommendation.get("metadata") or {}
        cards = metadata.get("cards") or []
        card_lines = ["Tool output already selected by the router:"]
        for card in cards[:3]:
            title = str(card.get("title", "")).strip()
            description = str(card.get("description", "")).strip()
            if title:
                card_lines.append(f"- {title}: {description}")
        guidance_lines.extend(card_lines)

    return IntentRoute(
        intent=intent,
        topic=topic,
        memory_context=memory_context,
        prompt_context="\n".join(guidance_lines),
        recommendation=recommendation,
    )
