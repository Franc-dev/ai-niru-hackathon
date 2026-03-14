"""
Intent-aware recommendation engine for counselors, resources, and crisis support.

This stays local-first:
- Uses current message + recent user history to infer recommendation intent.
- Scores topics deterministically from a mental-health taxonomy.
- Returns structured cards for the frontend to render.
- Does not require web search or agentic tool execution.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "stress": (
        "stress", "stressed", "burnout", "overwhelmed", "pressure", "work pressure",
        "academic stress", "workload", "msongo", "nimelemewa", "nimechoka", "burn out",
    ),
    "anxiety": (
        "anxiety", "anxious", "panic", "worried", "worry", "fear", "nervous",
        "wasiwasi", "hofu", "panic attack",
    ),
    "depression": (
        "depression", "depressed", "sad", "empty", "hopeless", "low mood",
        "huzuni", "kukata tamaa", "sina furaha",
    ),
    "loneliness": (
        "lonely", "alone", "isolated", "upweke", "peke yangu", "no one understands",
    ),
    "relationships": (
        "relationship", "relationships", "partner", "marriage", "family", "breakup",
        "uhusiano", "ndoa", "familia", "mwenzi",
    ),
    "grief": (
        "grief", "loss", "mourning", "bereavement", "heartbreak", "lost someone",
        "msiba", "kupoteza", "kuondokewa",
    ),
    "trauma": (
        "trauma", "ptsd", "abuse", "violence", "flashback", "assault",
        "kiwewe", "unyanyasaji",
    ),
    "sleep": (
        "sleep", "insomnia", "cant sleep", "cannot sleep", "nightmares",
        "usingizi", "silali", "kulala",
    ),
    "self-esteem": (
        "self esteem", "confidence", "self worth", "worthless", "esteem",
        "kujiamini", "sina thamani",
    ),
    "addiction": (
        "addiction", "alcohol", "drugs", "substance", "drinking problem",
        "uraibu", "pombe", "madawa",
    ),
    "mental_health_basics": (
        "mental health", "mental wellness", "wellbeing", "emotional help",
        "afya ya akili", "ustawi wa akili",
    ),
    "mindfulness": (
        "mindfulness", "mindful", "present", "awareness",
        "ufahamu", "uwepo",
    ),
    "meditation": (
        "meditation", "meditate", "breathing", "calm",
        "fomoyo", "kupumua", "utulivu",
    ),
    "self_help": (
        "self help", "self-help", "coping", "strategies", "tips",
        "kujisaidia", "mbinu", "njia",
    ),
}

RELATED_TOPICS: dict[str, tuple[str, ...]] = {
    "stress": ("burnout", "anxiety", "mindfulness", "self_help"),
    "anxiety": ("stress", "mindfulness", "meditation", "self_help"),
    "depression": ("self_help", "mental_health_basics"),
    "relationships": ("self-esteem",),
    "grief": ("depression", "self_help"),
    "sleep": ("stress", "anxiety", "meditation"),
    "self-esteem": ("self_help", "mindfulness"),
    "trauma": ("anxiety",),
    "addiction": ("self_help", "mental_health_basics"),
    "mindfulness": ("meditation", "self_help", "stress"),
    "meditation": ("mindfulness", "sleep", "self_help"),
    "self_help": ("mental_health_basics", "mindfulness"),
}

RESOURCE_TERMS = (
    "resource", "resources", "video", "videos", "article", "articles", "read", "watch",
    "recommend some", "show me", "helpful things", "something to watch", "nyenzo",
    "video za", "makala", "onyesha", "recommend", "some few resources",
)

COUNSELOR_TERMS = (
    "counselor", "counsellor", "therapist", "psychologist", "psychiatrist", "doctor",
    "professional help", "someone to talk to", "find a counselor", "mshauri", "mtaalamu",
    "daktari", "wanasaikolojia",
)

CRISIS_TERMS = (
    "crisis", "emergency", "suicide", "suicidal", "self harm", "kill myself", "hurt myself",
    "dont want to live", "i want to die", "i need crisis help", "nataka kufa",
    "kujidhuru", "msaada wa dharura",
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


def _history_user_turns(history: list[dict[str, Any]]) -> list[str]:
    return [
        str(turn.get("content", "")).strip()
        for turn in history
        if turn.get("role") == "user" and str(turn.get("content", "")).strip()
    ]


@lru_cache(maxsize=1)
def _load_dataset(filename: str) -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class RecommendationService:
    def __init__(self) -> None:
        self.resources = _load_dataset("resources.json")
        self.counselors = _load_dataset("counselors.json")
        self.crisis_hotlines = _load_dataset("crisis.json")

    def _detect_recommendation_kind(self, current_text: str, all_text: str) -> str | None:
        if _contains_any(current_text, CRISIS_TERMS) or _contains_any(all_text, CRISIS_TERMS):
            return "crisis"
        if _contains_any(current_text, COUNSELOR_TERMS):
            return "counselors"
        if _contains_any(current_text, RESOURCE_TERMS):
            return "resources"
        return None

    def _topic_scores(self, texts: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        total = len(texts)
        for index, raw_text in enumerate(texts):
            text = _normalize(raw_text)
            if not text:
                continue
            weight = 2.8 if index == total - 1 else max(0.6, 1.7 - ((total - index - 2) * 0.22))
            for topic, keywords in TOPIC_KEYWORDS.items():
                matches = sum(1 for keyword in keywords if keyword in text)
                if matches:
                    scores[topic] = scores.get(topic, 0.0) + (matches * weight)
        return scores

    def _infer_topic(self, message: str, history: list[dict[str, Any]]) -> tuple[str, bool, bool]:
        """Return (topic, inferred_from_history, used_default). used_default=True when no keywords matched."""
        user_turns = _history_user_turns(history)
        combined_turns = user_turns[-5:]
        if not combined_turns or combined_turns[-1] != message:
            combined_turns.append(message)

        scores = self._topic_scores(combined_turns)
        if scores:
            topic = max(scores.items(), key=lambda item: item[1])[0]
            current_only_scores = self._topic_scores([message])
            inferred_from_history = topic not in current_only_scores
            return topic, inferred_from_history, False

        return "mental_health_basics", False, True

    def is_self_harm_crisis(self, message: str) -> bool:
        return _contains_any(_normalize(message), CRISIS_TERMS)

    def maybe_build_response(
        self,
        message: str,
        history: list[dict[str, Any]],
        language: str = "en",
    ) -> dict[str, Any] | None:
        normalized_message = _normalize(message)
        history_text = " ".join(_history_user_turns(history)[-5:])
        normalized_history = _normalize(history_text)
        kind = self._detect_recommendation_kind(normalized_message, f"{normalized_history} {normalized_message}".strip())
        if not kind:
            return None

        topic, used_history, used_default_topic = self._infer_topic(message, history)
        if kind == "crisis":
            return self._build_crisis_response(language, topic)
        if kind == "counselors":
            has_match, candidates = self._has_counselor_match(topic, language, used_default_topic)
            if not has_match:
                return None
            return self._build_counselor_response(language, topic, used_history, candidates)
        if kind == "resources":
            has_match, candidates = self._has_resource_match(topic, used_default_topic)
            if not has_match:
                return None
            return self._build_resource_response(language, topic, used_history, candidates)
        return None

    RESOURCE_FALLBACK_CATEGORIES = frozenset({"mental_health_basics", "self_help", "mindfulness"})
    RESOURCE_MIN_SCORE = 1.0
    COUNSELOR_MIN_SCORE = 2.0

    def _resource_candidates(self, topic: str) -> tuple[list[dict[str, Any]], bool]:
        """Return (candidates, used_fallback). used_fallback=True when only generic fallback matched."""
        related = {topic, *RELATED_TOPICS.get(topic, ())}
        ranked: list[tuple[float, dict[str, Any]]] = []

        for item in self.resources:
            category = str(item.get("category", "")).strip().lower()
            score = 0.0
            if category == topic:
                score += 4.0
            if category in related:
                score += 2.2
            text = _normalize(
                " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("description", "")),
                        str(item.get("category", "")),
                    ]
                )
            )
            for keyword in TOPIC_KEYWORDS.get(topic, ()):
                if keyword in text:
                    score += 0.45
            if item.get("type") == "video":
                score += 0.2
            if score > 0:
                ranked.append((score, item))

        ranked.sort(key=lambda item: (-item[0], item[1].get("title", "")))
        topic_matched = [item for s, item in ranked[:4] if s >= self.RESOURCE_MIN_SCORE]
        if topic_matched:
            return (topic_matched[:4], False)

        fallback = [
            item for item in self.resources
            if str(item.get("category", "")).strip().lower() in self.RESOURCE_FALLBACK_CATEGORIES
        ]
        return (fallback[:4], True)

    def _has_resource_match(
        self, topic: str, used_default_topic: bool = False
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Return (has_match, candidates). No match when only fallback and topic not in fallback set.
        When used_default_topic=True (e.g. user said 'OCD'), never return - we didn't understand the request."""
        if used_default_topic:
            return (False, [])
        candidates, used_fallback = self._resource_candidates(topic)
        if not candidates:
            return (False, [])
        if not used_fallback:
            return (True, candidates)
        if topic in self.RESOURCE_FALLBACK_CATEGORIES:
            return (True, candidates)
        return (False, [])

    def _counselor_candidates(self, topic: str, language: str) -> tuple[list[dict[str, Any]], bool]:
        """Return (candidates, used_fallback). used_fallback=True when only generic counselors matched."""
        lang_label = "swahili" if language == "sw" else "english"
        ranked: list[tuple[float, dict[str, Any]]] = []

        for item in self.counselors:
            specialization = _normalize(str(item.get("specialization", "")))
            title = _normalize(str(item.get("title", "")))
            languages = [_normalize(lang) for lang in item.get("languages", [])]
            location = _normalize(str(item.get("location", "")))

            score = 0.0
            if any(keyword in specialization for keyword in TOPIC_KEYWORDS.get(topic, ())):
                score += 4.5
            if topic in specialization:
                score += 2.5
            if topic in title:
                score += 1.5
            if lang_label in languages:
                score += 0.6
            if "nationwide" in location:
                score += 0.4
            if "crisis" in specialization and topic == "crisis":
                score += 4.0
            rating = float(item.get("rating", 0.0) or 0.0)
            score += min(rating / 10.0, 0.6)
            if score > 0:
                ranked.append((score, item))

        ranked.sort(key=lambda item: (-item[0], -float(item[1].get("rating", 0) or 0), item[1].get("name", "")))
        topic_matched = [item for s, item in ranked[:4] if s >= self.COUNSELOR_MIN_SCORE]
        if topic_matched:
            return (topic_matched[:4], False)

        fallback = [
            item for item in self.counselors
            if "crisis" not in _normalize(str(item.get("specialization", "")))
        ]
        fallback.sort(key=lambda item: (-float(item.get("rating", 0) or 0), item.get("name", "")))
        return (fallback[:4], True)

    def _has_counselor_match(
        self, topic: str, language: str, used_default_topic: bool = False
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Return (has_match, candidates). No match when only generic fallback with no topic overlap.
        When used_default_topic=True, never return - we didn't understand the request."""
        if used_default_topic:
            return (False, [])
        candidates, used_fallback = self._counselor_candidates(topic, language)
        if not candidates:
            return (False, [])
        if not used_fallback:
            return (True, candidates)
        return (False, [])

    def _build_resource_response(
        self, language: str, topic: str, used_history: bool, candidates: list[dict[str, Any]]
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
            text = (
                f"Nimekusanya rasilimali chache zinazolenga {topic.replace('_', ' ')}."
                if not used_history
                else f"Umetaja {topic.replace('_', ' ')} kwenye mazungumzo yetu, kwa hiyo nimechagua rasilimali zinazolingana na hilo."
            )
        else:
            text = (
                f"I pulled together a few resources focused on {topic.replace('_', ' ')}."
                if not used_history
                else f"You were talking about {topic.replace('_', ' ')} earlier, so I picked resources that match that context."
            )

        return {
            "text": text,
            "metadata": {
                "ui_type": "recommendations",
                "recommendation_kind": "resources",
                "recommendation_topic": topic,
                "recommendation_reason": "history" if used_history else "current_message",
                "cards": cards,
            },
        }

    def _build_counselor_response(
        self, language: str, topic: str, used_history: bool, candidates: list[dict[str, Any]]
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
                        f"⭐ {item.get('rating')}",
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
            text = (
                f"Hawa ni washauri na wataalamu wanaoweza kusaidia zaidi kwenye {topic.replace('_', ' ')}."
                if not used_history
                else f"Kwa kuwa ulikuwa ukizungumzia {topic.replace('_', ' ')}, nimepanga wataalamu wanaofaa zaidi kwa hali hiyo."
            )
        else:
            text = (
                f"These counselors look like the best fit for support around {topic.replace('_', ' ')}."
                if not used_history
                else f"Since you were discussing {topic.replace('_', ' ')} earlier, I prioritized counselors whose specialties align with that."
            )

        return {
            "text": text,
            "metadata": {
                "ui_type": "recommendations",
                "recommendation_kind": "counselors",
                "recommendation_topic": topic,
                "recommendation_reason": "history" if used_history else "current_message",
                "cards": cards,
            },
        }

    def _crisis_candidates(self) -> list[dict[str, Any]]:
        """Return crisis hotlines from crisis.json: Kenya first, then global."""
        kenya = [h for h in self.crisis_hotlines if str(h.get("country", "")).strip() == "Kenya"]
        others = [h for h in self.crisis_hotlines if str(h.get("country", "")).strip() != "Kenya"]
        # Kenya: general crisis first, then suicide, then youth, then others
        type_order = ("crisis_hotline", "suicide_prevention_hotline", "youth_crisis_hotline", "hospital_crisis_line", "health_support_hotline", "text_crisis_support", "global_directory")
        def sort_key(h):
            t = str(h.get("type", "")).strip().lower()
            try:
                return type_order.index(t) if t in type_order else 99
            except ValueError:
                return 99
        kenya.sort(key=sort_key)
        others.sort(key=sort_key)
        return kenya[:5] + others[:3]  # Up to 5 Kenya + 3 global

    def _build_crisis_response(self, language: str, topic: str) -> dict[str, Any]:
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
                "recommendation_topic": topic,
                "recommendation_reason": "current_message",
                "cards": cards,
            },
        }


recommendation_service = RecommendationService()
