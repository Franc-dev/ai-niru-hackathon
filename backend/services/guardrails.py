"""
EM-NS Guardrails: Off-topic detection and canned redirects.

Intercepts clearly off-topic requests (coding, math, etc.) before the model
is called, returning a polite redirect to mental health topics.
"""
import re

from backend.services.topic_focus import normalize_focus_text

# Patterns that indicate off-topic (programming, coding, tech, math, etc.)
# Match if any of these appear as a significant part of the message
OFF_TOPIC_PATTERNS = (
    r"\bteach\s+me\s+(python|java|javascript|coding|programming|code)\b",
    r"\blearn\s+(python|java|javascript|coding|programming)\b",
    r"\bhow\s+to\s+(code|program|write\s+code)\b",
    r"\bpython\s+(tutorial|course|lesson|help)\b",
    r"\bwrite\s+(a\s+)?(function|code|program|script)\b",
    r"\bprogramming\s+(help|question|problem)\b",
    r"\bcoding\s+(help|question|problem)\b",
    r"\bdebug\s+(my\s+)?code\b",
    r"\bexplain\s+(this\s+)?code\b",
    r"\bmath\s+(problem|question|help|homework)\b",
    r"\bsolve\s+(this\s+)?(math|equation)\b",
    r"\bphysics\s+(problem|question|help)\b",
    r"\bhomework\s+help\b",
    r"\brecipe\s+for\b",
    r"\bhow\s+to\s+cook\b",
    r"\bweather\s+(today|tomorrow)\b",
    r"\bstock\s+(price|market)\b",
    r"\btranslate\s+(to|from)\b",
)

# Compiled for speed
_OFF_TOPIC_RE = re.compile(
    "|".join(f"(?:{p})" for p in OFF_TOPIC_PATTERNS),
    re.IGNORECASE,
)

_EXPLICIT_TECH_REQUEST_RE = re.compile(
    r"\b(?:help|teach|show|explain|write|debug|fix|solve|build|make|create|learn)\b"
    r"(?:\s+\w+){0,5}\s+\b(?:python|java|javascript|coding|code|codein|programming|program|script|function|algorithm)\b",
    re.IGNORECASE,
)

_IMPLEMENTATION_REQUEST_RE = re.compile(
    r"\b(?:code|codein|program|write|debug|fix|build|create)\b"
    r"(?:\s+\w+){0,4}\s+\b(?:python|java|javascript)\b",
    re.IGNORECASE,
)

_TECH_CONTEXT_REQUEST_RE = re.compile(
    r"\b(?:python|java|javascript|coding|code|codein|programming|program|script|function|algorithm)\b"
    r"(?:\s+\w+){0,4}\s+\b(?:help|tutorial|course|lesson|question|problem|debug|fix|explain)\b",
    re.IGNORECASE,
)

# Canned redirects per language
REDIRECT_EN = (
    "I'm here to support you with mental health and emotional well-being, "
    "not with programming, coding, or other topics. I'd be happy to help with "
    "stress, anxiety, mood, relationships, or how you're feeling. "
    "Is there something on your mind you'd like to talk about?"
)

REDIRECT_SW = (
    "Niko hapa kukusaidia na afya ya akili na msaada wa kihemko, "
    "si programu au mada nyingine. Ningependeza kusaidia na msongo, wasiwasi, "
    "hali ya moyo, uhusiano, au jinsi unavyohisi. "
    "Je, kuna kitu kwenye akili yako ungependa kuzungumzia?"
)


def is_off_topic(message: str) -> bool:
    """Return True if the message is clearly off-topic (coding, math, etc.)."""
    if not message or not message.strip():
        return False
    text = message.strip()
    # Must be substantial (avoid false positives on "hi" or "ok")
    if len(text) < 10:
        return False
    normalized = normalize_focus_text(text)
    return bool(
        _OFF_TOPIC_RE.search(text)
        or _EXPLICIT_TECH_REQUEST_RE.search(normalized)
        or _IMPLEMENTATION_REQUEST_RE.search(normalized)
        or _TECH_CONTEXT_REQUEST_RE.search(normalized)
    )


def get_off_topic_redirect(language: str = "en") -> str:
    """Return the canned redirect message for the given language."""
    return REDIRECT_SW if language and str(language).lower().startswith("sw") else REDIRECT_EN


def check_guardrail(message: str, language: str = "en") -> tuple[bool, str | None]:
    """
    Check if the message should be intercepted by the off-topic guardrail.
    Returns (should_redirect, redirect_message).
    If should_redirect is True, redirect_message is the canned response to return.
    """
    if is_off_topic(message):
        return True, get_off_topic_redirect(language)
    return False, None
