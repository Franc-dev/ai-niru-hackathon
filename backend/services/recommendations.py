"""
Intent-aware recommendation engine for counselors, resources, and crisis support.

This stays local-first:
- Uses current message + recent user history to infer recommendation intent.
- Carries forward the conversation focus without over-stating clinical labels.
- Returns structured cards for the frontend to render.
- Does not require web search or agentic tool execution.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend.services.crisis_detection import is_crisis_text
from backend.services.topic_focus import FocusMatch, infer_focus, normalize_focus_text, recent_user_turns


def _normalize(text: str) -> str:
    return normalize_focus_text(text)


RESOURCE_TERMS = (
    "resource", "resources", "video", "videos", "article", "articles", "read", "watch",
    "recommend some", "show me", "helpful things", "something to watch", "nyenzo",
    "video za", "makala", "onyesha", "recommend", "some few resources",
)

COUNSELOR_TERMS = (
    "counselor", "counsellor", "therapist", "psychologist", "psychiatrist", "doctor",
    "professional help", "someone to talk to", "find a counselor", "mshauri", "mtaalamu",
    "daktari", "wanasaikolojia", "book a counselor", "book counselor",
)

def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _youtube_thumbnail(url: str) -> str | None:
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/") or None
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    return None


@lru_cache(maxsize=1)
def _load_dataset(filename: str) -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class RecommendationService:
    RESOURCE_FALLBACK_CATEGORIES = frozenset({"mental_health_basics", "self_help", "mindfulness"})
    RESOURCE_MIN_SCORE = 1.0
    COUNSELOR_MIN_SCORE = 1.4

    def __init__(self) -> None:
        self.resources = _load_dataset("resources.json")
        self.counselors = _load_dataset("counselors.json")
        self.crisis_hotlines = _load_dataset("crisis.json")

    def _detect_recommendation_kind(self, current_text: str, all_text: str) -> str | None:
        if is_crisis_text(current_text) or is_crisis_text(all_text):
            return "crisis"
        if _contains_any(current_text, COUNSELOR_TERMS):
            return "counselors"
        if _contains_any(current_text, RESOURCE_TERMS):
            return "resources"
        return None

    def is_self_harm_crisis(self, message: str) -> bool:
        return is_crisis_text(message)

    def maybe_build_response(
        self,
        message: str,
        history: list[dict[str, Any]],
        language: str = "en",
    ) -> dict[str, Any] | None:
        normalized_message = _normalize(message)
        history_text = " ".join(recent_user_turns(history, limit=5))
        normalized_history = _normalize(history_text)
        kind = self._detect_recommendation_kind(
            normalized_message,
            f"{normalized_history} {normalized_message}".strip(),
        )
        if not kind:
            return None

        focus = infer_focus(message, history)
        if kind == "crisis":
            return self._build_crisis_response(language, focus)
        if focus.used_default:
            return None
        if kind == "counselors":
            candidates, used_fallback = self._counselor_candidates(focus, language)
            if not candidates:
                return None
            return self._build_counselor_response(language, focus, candidates, used_fallback)
        if kind == "resources":
            candidates, used_fallback = self._resource_candidates(focus)
            if not candidates:
                return None
            return self._build_resource_response(language, focus, candidates, used_fallback)
        return None

    def _resource_candidates(self, focus: FocusMatch) -> tuple[list[dict[str, Any]], bool]:
        primary_categories = set(focus.resource_categories)
        secondary_categories = set(focus.related_resource_categories)
        ranked: list[tuple[float, dict[str, Any]]] = []

        for item in self.resources:
            category = str(item.get("category", "")).strip().lower()
            score = 0.0
            if category in primary_categories:
                score += 4.0
            elif category in secondary_categories:
                score += 2.4

            text = _normalize(
                " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("description", "")),
                        str(item.get("category", "")),
                    ]
                )
            )
            for term in primary_categories:
                if term and term in text:
                    score += 0.4
            for term in secondary_categories:
                if term and term in text:
                    score += 0.2
            if item.get("type") == "video":
                score += 0.2
            if score > 0:
                ranked.append((score, item))

        ranked.sort(key=lambda item: (-item[0], item[1].get("title", "")))
        focused = [item for score, item in ranked if score >= self.RESOURCE_MIN_SCORE]
        if focused:
            return (focused[:4], False)

        fallback = [
            item
            for item in self.resources
            if str(item.get("category", "")).strip().lower() in self.RESOURCE_FALLBACK_CATEGORIES
        ]
        return (fallback[:4], True)

    def _counselor_candidates(self, focus: FocusMatch, language: str) -> tuple[list[dict[str, Any]], bool]:
        lang_label = "swahili" if language == "sw" else "english"
        primary_terms = tuple(_normalize(term) for term in focus.counselor_terms)
        secondary_terms = tuple(_normalize(term) for term in focus.related_counselor_terms)
        if not primary_terms:
            return ([], False)
        ranked: list[tuple[float, dict[str, Any]]] = []

        for item in self.counselors:
            specialization = _normalize(str(item.get("specialization", "")))
            title = _normalize(str(item.get("title", "")))
            clinic = _normalize(str(item.get("clinic", "")))
            languages = [_normalize(lang) for lang in item.get("languages", [])]
            location = _normalize(str(item.get("location", "")))

            score = 0.0
            combined_text = " ".join(part for part in (specialization, title, clinic) if part)
            if any(term in combined_text for term in primary_terms):
                score += 4.5
            if any(term in combined_text for term in secondary_terms):
                score += 2.0
            if lang_label in languages:
                score += 0.6
            if "nationwide" in location:
                score += 0.4
            rating = float(item.get("rating", 0.0) or 0.0)
            score += min(rating / 10.0, 0.6)
            if score > 0:
                ranked.append((score, item))

        ranked.sort(
            key=lambda item: (-item[0], -float(item[1].get("rating", 0) or 0), item[1].get("name", "")),
        )
        focused = [item for score, item in ranked if score >= self.COUNSELOR_MIN_SCORE]
        if focused:
            return (focused[:4], False)
        return ([], False)

    def _build_resource_response(
        self,
        language: str,
        focus: FocusMatch,
        candidates: list[dict[str, Any]],
        used_fallback: bool,
    ) -> dict[str, Any]:
        cards = []
        for item in candidates:
            action = "Watch" if item.get("type") == "video" else "Read"
            if language == "sw":
                action = "Tazama" if item.get("type") == "video" else "Soma"
            cards.append(
                {
                    "id": _normalize(f"{item.get('title', '')}-{item.get('url', '')}"),
                    "kind": "resource",
                    "title": item.get("title"),
                    "subtitle": item.get("source"),
                    "description": item.get("description"),
                    "badges": [
                        str(item.get("category", "")).replace("_", " ").title(),
                        str(item.get("duration", "")),
                        str(item.get("language", "")),
                    ],
                    "cta_label": action,
                    "cta_href": item.get("url"),
                    "cta_kind": "external",
                    "media_image": _youtube_thumbnail(str(item.get("url", ""))),
                }
            )

        if language == "sw":
            if focus.source == "history":
                text = (
                    "Kutokana na yale umekuwa ukishiriki, nimekusanya rasilimali chache zinazoweza kusaidia."
                    if not used_fallback
                    else "Kutokana na yale umekuwa ukishiriki, hizi ni rasilimali za jumla zinazoweza kusaidia."
                )
            else:
                text = (
                    f"Nimekusanya rasilimali chache zinazoweza kusaidia kuhusu {focus.label}."
                    if not used_fallback
                    else "Nimekusanya rasilimali za jumla zinazoweza kusaidia."
                )
        else:
            if focus.source == "history":
                text = (
                    "Based on what you've been sharing, I pulled together a few resources that may help."
                    if not used_fallback
                    else "Based on what you've been sharing, here are a few general resources that may help."
                )
            else:
                text = (
                    f"I pulled together a few resources that may help with {focus.label}."
                    if not used_fallback
                    else "I pulled together a few general resources that may help."
                )

        return {
            "text": text,
            "metadata": {
                "ui_type": "recommendations",
                "recommendation_kind": "resources",
                "recommendation_topic": focus.key,
                "recommendation_focus_label": focus.label,
                "recommendation_reason": focus.source,
                "cards": cards,
            },
        }

    def _build_counselor_response(
        self,
        language: str,
        focus: FocusMatch,
        candidates: list[dict[str, Any]],
        used_fallback: bool,
    ) -> dict[str, Any]:
        cards = []
        for item in candidates:
            languages = ", ".join(item.get("languages", []))
            cards.append(
                {
                    "id": _normalize(f"{item.get('name', '')}-{item.get('phone', '')}"),
                    "kind": "counselor",
                    "title": item.get("name"),
                    "subtitle": f"{item.get('title')} - {item.get('clinic')}",
                    "description": item.get("specialization"),
                    "badges": [
                        str(item.get("location", "")),
                        f"Rating {item.get('rating')}",
                        f"{item.get('years_experience')} yrs",
                        languages,
                    ],
                    "cta_label": "Call" if language == "en" else "Piga simu",
                    "cta_href": f"tel:{item.get('phone')}",
                    "cta_kind": "phone",
                    "secondary_cta_label": "Email" if language == "en" else "Barua pepe",
                    "secondary_cta_href": f"mailto:{item.get('email')}",
                    "secondary_cta_kind": "email",
                }
            )

        if language == "sw":
            if focus.source == "history":
                text = (
                    "Kutokana na yale umekuwa ukishiriki, hawa ni wataalamu ambao wanaweza kusaidia."
                    if not used_fallback
                    else "Kutokana na yale umekuwa ukishiriki, hawa ni wataalamu wa jumla ambao wanaweza kusaidia."
                )
            else:
                text = (
                    f"Hawa ni wataalamu ambao wanaweza kusaidia kuhusu {focus.label}."
                    if not used_fallback
                    else "Hawa ni wataalamu wa jumla ambao wanaweza kusaidia."
                )
        else:
            if focus.source == "history":
                text = (
                    "Based on what you've been sharing, these counselors may be a good fit."
                    if not used_fallback
                    else "Based on what you've been sharing, here are a few general counselors who may help."
                )
            else:
                text = (
                    f"These counselors may be a good fit for support around {focus.label}."
                    if not used_fallback
                    else "Here are a few general counselors who may help."
                )

        return {
            "text": text,
            "metadata": {
                "ui_type": "recommendations",
                "recommendation_kind": "counselors",
                "recommendation_topic": focus.key,
                "recommendation_focus_label": focus.label,
                "recommendation_reason": focus.source,
                "cards": cards,
            },
        }

    def _crisis_candidates(self) -> list[dict[str, Any]]:
        kenya = [h for h in self.crisis_hotlines if str(h.get("country", "")).strip() == "Kenya"]
        others = [h for h in self.crisis_hotlines if str(h.get("country", "")).strip() != "Kenya"]
        type_order = (
            "crisis_hotline",
            "suicide_prevention_hotline",
            "youth_crisis_hotline",
            "hospital_crisis_line",
            "health_support_hotline",
            "text_crisis_support",
            "global_directory",
        )

        def sort_key(item: dict[str, Any]) -> int:
            kind = str(item.get("type", "")).strip().lower()
            return type_order.index(kind) if kind in type_order else 99

        kenya.sort(key=sort_key)
        others.sort(key=sort_key)
        return kenya[:5] + others[:3]

    def _build_crisis_response(self, language: str, focus: FocusMatch) -> dict[str, Any]:
        cards = []
        for item in self._crisis_candidates():
            org = str(item.get("organization", "")).strip()
            langs = ", ".join(item.get("languages", []))
            cta_label = "Call now" if language == "en" else "Piga simu sasa"
            phone = item.get("phone")
            website = item.get("website")
            if website:
                cta_href = website
                cta_kind = "external"
                cta_label = "Visit" if language == "en" else "Tembelea"
            elif phone:
                cta_href = f"tel:{phone.replace(' ', '')}"
                cta_kind = "phone"
            else:
                continue
            cards.append(
                {
                    "id": _normalize(f"crisis-{item.get('name', '')}-{item.get('phone', website or '')}"),
                    "kind": "crisis",
                    "title": item.get("name"),
                    "subtitle": org,
                    "description": item.get("description"),
                    "badges": [str(item.get("country", "")), str(item.get("availability", "")), langs],
                    "cta_label": cta_label,
                    "cta_href": cta_href,
                    "cta_kind": cta_kind,
                }
            )

        text = (
            "If this feels urgent or unsafe, please reach out to a crisis support line right now and contact someone you trust nearby."
            if language == "en"
            else "Ikiwa hali hii ni ya dharura au si salama, tafadhali wasiliana na huduma ya msaada wa dharura sasa hivi na mjulishe mtu unayemwamini aliye karibu."
        )

        return {
            "text": text,
            "metadata": {
                "ui_type": "recommendations",
                "recommendation_kind": "crisis",
                "recommendation_topic": focus.key,
                "recommendation_focus_label": focus.label,
                "recommendation_reason": "current_message",
                "cards": cards,
            },
        }


recommendation_service = RecommendationService()
