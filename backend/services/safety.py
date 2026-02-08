"""
Minimal safety rule checking (blocklist + severity).
Per docs/SAFETY_RULES.md: returns safe, reason, escalate, severity.
"""
import re
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]

# MVP: blocklist of regex patterns (case-insensitive) with severity
_BLOCKLIST: list[tuple[str, Severity]] = [
    (r"\bhow to (build|make|create) (a )?bomb\b", "critical"),
    (r"\bkill (myself|yourself)\b", "critical"),
    (r"\bcommit suicide\b", "critical"),
    (r"\bhack into\b", "medium"),
    (r"\bsteal (passwords|credentials)\b", "medium"),
]

_COMPILED: list[tuple[re.Pattern, Severity]] = [
    (re.compile(p, re.I), s) for p, s in _BLOCKLIST
]


def check_safety_rules(message: str) -> dict:
    """
    Check message against safety rules.
    Returns: { "safe": bool, "reason": str, "escalate": bool, "severity": str }
    """
    if not message or not message.strip():
        return {"safe": True, "reason": "", "escalate": False, "severity": "low"}

    text = message.strip()
    for pattern, severity in _COMPILED:
        if pattern.search(text):
            return {
                "safe": False,
                "reason": "Content violates safety policy.",
                "escalate": severity in ("high", "critical"),
                "severity": severity,
            }

    return {"safe": True, "reason": "", "escalate": False, "severity": "low"}
