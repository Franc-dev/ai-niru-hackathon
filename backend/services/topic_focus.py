"""Shared conversation-focus inference for chat routing and recommendations."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


def normalize_focus_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


@dataclass(frozen=True)
class FocusProfile:
    key: str
    label: str
    keywords: tuple[str, ...] = ()
    explicit_terms: tuple[str, ...] = ()
    evidence_terms: tuple[str, ...] = ()
    evidence_threshold: int = 0
    resource_categories: tuple[str, ...] = ()
    related_resource_categories: tuple[str, ...] = ()
    counselor_terms: tuple[str, ...] = ()
    related_counselor_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class FocusMatch:
    key: str
    label: str
    source: str
    used_default: bool
    resource_categories: tuple[str, ...]
    related_resource_categories: tuple[str, ...]
    counselor_terms: tuple[str, ...]
    related_counselor_terms: tuple[str, ...]


GENERAL_SUPPORT_FOCUS = FocusMatch(
    key="general_support",
    label="emotional support",
    source="default",
    used_default=True,
    resource_categories=(),
    related_resource_categories=(),
    counselor_terms=(),
    related_counselor_terms=(),
)


FOCUS_PROFILES: tuple[FocusProfile, ...] = (
    FocusProfile(
        key="depression",
        label="depression",
        explicit_terms=("depression", "depressed"),
        evidence_terms=(
            "hopeless",
            "empty",
            "emotionally numb",
            "feel numb",
            "worthless",
            "lost interest",
            "no motivation",
            "nothing matters",
            "for weeks",
            "for months",
        ),
        evidence_threshold=3,
        resource_categories=("depression",),
        related_resource_categories=("self_help", "mental_health_basics", "mindfulness"),
        counselor_terms=("depression", "psychiatry"),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="sadness",
        label="sadness",
        keywords=(
            "sad",
            "very sad",
            "feeling down",
            "down lately",
            "low mood",
            "unhappy",
            "heavy heart",
            "tearful",
            "crying",
            "huzuni",
        ),
        resource_categories=("self_help", "mental_health_basics", "mindfulness", "loneliness"),
        related_resource_categories=("grief", "depression"),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="stress",
        label="stress",
        keywords=(
            "stress",
            "stressed",
            "overwhelmed",
            "pressure",
            "burnout",
            "burned out",
            "work pressure",
            "exam stress",
            "msongo",
            "nimelemewa",
        ),
        resource_categories=("stress", "mindfulness", "meditation", "self_help"),
        related_resource_categories=("sleep", "mental_health_basics"),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="anxiety",
        label="anxiety",
        keywords=(
            "anxiety",
            "anxious",
            "panic",
            "panic attack",
            "worried",
            "worry",
            "fear",
            "nervous",
            "wasiwasi",
            "hofu",
        ),
        resource_categories=("stress", "mindfulness", "meditation", "self_help"),
        related_resource_categories=("sleep", "mental_health_basics"),
        counselor_terms=("anxiety", "psychiatry"),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="grief",
        label="grief",
        keywords=(
            "grief",
            "loss",
            "mourning",
            "bereavement",
            "heartbreak",
            "lost someone",
            "passed away",
            "died",
            "msiba",
            "kupoteza",
            "kuondokewa",
        ),
        resource_categories=("grief", "self_help", "mental_health_basics"),
        related_resource_categories=("loneliness", "mindfulness"),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="loneliness",
        label="loneliness",
        keywords=(
            "lonely",
            "alone",
            "isolated",
            "left out",
            "no one understands",
            "upweke",
            "peke yangu",
        ),
        resource_categories=("loneliness", "self_help", "mental_health_basics"),
        related_resource_categories=("mindfulness", "grief"),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="relationships",
        label="relationship stress",
        keywords=(
            "relationship",
            "relationships",
            "partner",
            "marriage",
            "family",
            "breakup",
            "uhusiano",
            "ndoa",
            "familia",
            "mwenzi",
        ),
        resource_categories=("relationships", "self_help", "mental_health_basics"),
        related_resource_categories=("mindfulness",),
        counselor_terms=("relationships", "couples therapy", "family therapy"),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="trauma",
        label="trauma",
        keywords=(
            "trauma",
            "ptsd",
            "abuse",
            "violence",
            "flashback",
            "assault",
            "kiwewe",
            "unyanyasaji",
        ),
        resource_categories=("trauma", "self_help", "mindfulness"),
        related_resource_categories=("stress", "mental_health_basics"),
        counselor_terms=("trauma", "trauma counseling", "psychiatry"),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="sleep",
        label="sleep trouble",
        keywords=(
            "sleep",
            "insomnia",
            "cant sleep",
            "cannot sleep",
            "nightmares",
            "usingizi",
            "silali",
            "kulala",
        ),
        resource_categories=("sleep", "meditation", "mindfulness", "stress"),
        related_resource_categories=("self_help",),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="self_esteem",
        label="self-esteem",
        keywords=(
            "self esteem",
            "confidence",
            "self worth",
            "esteem",
            "worthless",
            "kujiamini",
            "sina thamani",
        ),
        resource_categories=("self-esteem", "self_help", "mindfulness"),
        related_resource_categories=("mental_health_basics",),
        counselor_terms=(),
        related_counselor_terms=(),
    ),
    FocusProfile(
        key="addiction",
        label="addiction",
        keywords=(
            "addiction",
            "alcohol",
            "drugs",
            "substance",
            "drinking problem",
            "uraibu",
            "pombe",
            "madawa",
        ),
        resource_categories=("self_help", "mental_health_basics"),
        related_resource_categories=("mindfulness",),
        counselor_terms=("addiction", "addiction recovery", "psychiatry"),
        related_counselor_terms=(),
    ),
)

_PROFILE_BY_KEY = {profile.key: profile for profile in FOCUS_PROFILES}
_PRIORITY_ORDER = tuple(profile.key for profile in FOCUS_PROFILES)


def _score_profile(profile: FocusProfile, text: str) -> float:
    keyword_hits = sum(1 for keyword in profile.keywords if keyword in text)
    explicit_hits = sum(1 for keyword in profile.explicit_terms if keyword in text)
    evidence_hits = sum(1 for keyword in profile.evidence_terms if keyword in text)

    if profile.explicit_terms or profile.evidence_terms:
        if explicit_hits == 0 and evidence_hits < profile.evidence_threshold:
            return 0.0

    score = (keyword_hits * 1.8) + (explicit_hits * 3.2) + (evidence_hits * 1.25)
    return score


def _score_text(text: str) -> dict[str, float]:
    normalized = normalize_focus_text(text)
    if not normalized:
        return {}

    scores: dict[str, float] = {}
    for profile in FOCUS_PROFILES:
        score = _score_profile(profile, normalized)
        if score > 0:
            scores[profile.key] = score
    return scores


def _best_focus(scores: dict[str, float]) -> FocusProfile | None:
    if not scores:
        return None
    return max(
        (_PROFILE_BY_KEY[key] for key in scores.keys()),
        key=lambda profile: (scores.get(profile.key, 0.0), -_PRIORITY_ORDER.index(profile.key)),
    )


def _match_from_profile(profile: FocusProfile, source: str) -> FocusMatch:
    return FocusMatch(
        key=profile.key,
        label=profile.label,
        source=source,
        used_default=False,
        resource_categories=profile.resource_categories,
        related_resource_categories=profile.related_resource_categories,
        counselor_terms=profile.counselor_terms,
        related_counselor_terms=profile.related_counselor_terms,
    )


def recent_user_turns(history: list[dict[str, Any]], limit: int = 6) -> list[str]:
    turns = [
        str(turn.get("content", "")).strip()
        for turn in history
        if turn.get("role") == "user" and str(turn.get("content", "")).strip()
    ]
    return turns[-limit:]


def infer_focus(message: str, history: list[dict[str, Any]]) -> FocusMatch:
    current_scores = _score_text(message)
    current_profile = _best_focus(current_scores)
    if current_profile:
        return _match_from_profile(current_profile, "current_message")

    prior_turns = recent_user_turns(history, limit=6)
    normalized_message = normalize_focus_text(message)
    history_scores: dict[str, float] = {}

    for index, turn in enumerate(prior_turns):
        normalized_turn = normalize_focus_text(turn)
        if not normalized_turn or normalized_turn == normalized_message:
            continue
        weight = 1.0 + (index * 0.2)
        for key, score in _score_text(turn).items():
            history_scores[key] = history_scores.get(key, 0.0) + (score * weight)

    history_profile = _best_focus(history_scores)
    if history_profile:
        return _match_from_profile(history_profile, "history")

    return GENERAL_SUPPORT_FOCUS
