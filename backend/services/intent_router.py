"""Deterministic intent routing for the main chat flow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.chat_memory import build_memory_context
from backend.services.crisis_detection import is_crisis_text
from backend.services.recommendations import recommendation_service
from backend.services.topic_focus import infer_focus, normalize_focus_text


def _normalize(text: str) -> str:
    return normalize_focus_text(text)


RESOURCE_TERMS = (
    "resource",
    "resources",
    "article",
    "articles",
    "video",
    "videos",
    "watch",
    "read",
)
COUNSELOR_TERMS = (
    "counselor",
    "counsellor",
    "therapist",
    "psychologist",
    "psychiatrist",
    "doctor",
    "professional help",
    "someone to talk to",
    "find a counselor",
    "book a counselor",
    "book counselor",
)


@dataclass
class IntentRoute:
    intent: str
    topic: str
    memory_context: str
    prompt_context: str
    recommendation: dict[str, Any] | None = None
    fallback_reply: dict[str, Any] | None = None


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _build_unavailable_reply(intent: str, language: str, focus_label: str, has_specific_focus: bool) -> dict[str, Any]:
    if intent == "counselor_request":
        if language == "sw":
            text = (
                f"Kwa sasa hatuna pendekezo la mshauri linalolingana na {focus_label} kwenye hifadhidata yetu."
                if has_specific_focus
                else "Kwa sasa siwezi kupendekeza mshauri mahususi kutoka kwenye hifadhidata yetu bila maelezo zaidi."
            )
            if not has_specific_focus:
                text += " Unaweza kuniambia kama ni kuhusu depression, anxiety, stress, sleep, grief, trauma, au relationships."
        else:
            text = (
                f"I don't have a counselor recommendation available for {focus_label} in our dataset right now."
                if has_specific_focus
                else "I can't recommend a specific counselor from our dataset yet because I don't have enough detail."
            )
            if not has_specific_focus:
                text += " You can tell me if this is about depression, anxiety, stress, sleep, grief, trauma, or relationships."
    else:
        if language == "sw":
            text = (
                f"Kwa sasa hatuna rasilimali zinazolingana na {focus_label} kwenye hifadhidata yetu."
                if has_specific_focus
                else "Kwa sasa siwezi kupata rasilimali mahususi kutoka kwenye hifadhidata yetu bila maelezo zaidi."
            )
        else:
            text = (
                f"I don't have resources available for {focus_label} in our dataset right now."
                if has_specific_focus
                else "I can't find specific resources from our dataset yet because I don't have enough detail."
            )

    return {
        "text": text,
        "metadata": {
            "ui_type": "unavailable",
            "request_kind": "counselor" if intent == "counselor_request" else "resource",
            "recommendation_focus_label": focus_label if has_specific_focus else None,
            "request_unavailable": True,
        },
    }


def route_message(
    *,
    message: str,
    history: list[dict[str, Any]],
    language: str = "en",
) -> IntentRoute:
    normalized = _normalize(message)
    focus = infer_focus(message, history)
    memory_context = build_memory_context(message, history)
    recommendation = recommendation_service.maybe_build_response(
        message=message,
        history=history,
        language=language,
    )
    fallback_reply: dict[str, Any] | None = None

    if is_crisis_text(message):
        intent = "crisis"
    elif recommendation:
        kind = str((recommendation.get("metadata") or {}).get("recommendation_kind") or "")
        intent = (
            "crisis"
            if kind == "crisis"
            else
            "resource_request"
            if kind == "resources"
            else "counselor_request"
            if kind == "counselors"
            else "tool_handoff"
        )
    elif _contains_any(normalized, COUNSELOR_TERMS):
        intent = "counselor_request"
    elif _contains_any(normalized, RESOURCE_TERMS):
        intent = "resource_request"
    else:
        intent = "emotional_support"

    NO_MATCH_RESOURCE_EN = (
        "No specific resources match this focus in our database. "
        "Provide warm emotional support and practical coping steps. Do not suggest resources."
    )
    NO_MATCH_RESOURCE_SW = (
        "Hakuna rasilimali maalum zinazolingana na jambo hili kwenye hifadhidata yetu. "
        "Toa msaada wa kihemko wenye joto na hatua za vitendo. Usipendekezi rasilimali."
    )
    NO_MATCH_COUNSELOR_EN = (
        "The user asked for a counselor. We have no matching counselors for this focus. "
        "Provide warm emotional support only. Do NOT suggest resources, videos, or articles as alternatives. "
        "Do not say you 'picked' or 'chose' anything. Do not recommend anything, just emotional support."
    )
    NO_MATCH_COUNSELOR_SW = (
        "Mtumiaji aliuliza mshauri. Hatuna washauri wanaolingana na jambo hili. "
        "Toa msaada wa kihemko tu. Usipendekezi rasilimali, video, au makala. Usiseme 'nilichagua' chochote."
    )
    if language == "sw":
        no_match_guidance = NO_MATCH_COUNSELOR_SW if intent == "counselor_request" else NO_MATCH_RESOURCE_SW
    else:
        no_match_guidance = NO_MATCH_COUNSELOR_EN if intent == "counselor_request" else NO_MATCH_RESOURCE_EN

    has_specific_focus = not focus.used_default
    if not recommendation and intent in ("resource_request", "counselor_request"):
        fallback_reply = _build_unavailable_reply(intent, language, focus.label, has_specific_focus)

    guidance_lines = [
        f"Intent: {intent}",
        f"Detected focus: {focus.label}",
        "Stay strictly within emotional and mental-health support.",
        "Do not diagnose, prescribe medication, or invent organizations, clinicians, or resources.",
        "Use a warm, grounded tone with 2-4 practical next steps.",
        "Ask at most one gentle follow-up question when it helps.",
    ]
    if focus.source == "history":
        guidance_lines.append("The current request appears to refer back to the user's earlier conversation context.")
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
        topic=focus.key,
        memory_context=memory_context,
        prompt_context="\n".join(guidance_lines),
        recommendation=recommendation,
        fallback_reply=fallback_reply,
    )
