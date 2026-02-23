"""Swahili quality checks and normalization for chat responses."""
import re

_TOKEN_RE = re.compile(r"[A-Za-z']+")
_CONSECUTIVE_VOWELS = re.compile(r"[aeiou]{3,}", re.I)

SWAHILI_VOCAB = frozenset({
    "na", "kwa", "hii", "hiyo", "kama", "sana", "pole", "tafadhali", "weza",
    "wasiwasi", "hisia", "akili", "msaada", "mawazo", "msongo", "uhusiano",
    "niko", "hapa", "kuhisi", "kiasi", "usiku", "kipimo", "ni", "ya", "wa",
    "za", "la", "cha", "au", "katika", "hata", "bado", "lakini", "pia", "hivi",
    "kabisa", "kidogo", "sasa", "leo", "kesho", "jana", "kila", "kutoka",
    "mpaka", "bila", "kuhusu", "jinsi", "tangu", "kabla", "baada", "wakati",
    "kufanya", "kusaidia", "kusikiliza", "kujua", "kuwa", "kulikuwa", "kupata",
    "kuja", "kwenda", "kulala", "kula", "kunywa", "kupumzika", "kufikiri",
    "uchovu", "usingizi", "huzuni", "furaha", "huruma", "upole", "usalama",
    "afya", "mwili", "roho", "mtu", "watu", "jambo", "mambo", "neno", "maneno",
    "sababu", "hatua", "njia", "mbinu", "usaidizi", "maelezo", "swali", "jibu",
    "unavyohisi", "upweke", "niambie", "hayo", "peke", "ujumbe", "kifedha",
    "gani", "kushindwa", "tumbo", "ghali",
    "maumivu", "kuvunja", "mpenzi", "mahusiano", "kupoteza", "kumwamini",
    "naweza", "eleza", "zaidi", "kuhusu", "unachopitia", "tukatafute",
    "vitendo", "ueleze", "kusikiliza", "ndogo",
})

ENGLISH_LEAK_WORDS = frozenset({
    "the", "and", "is", "are", "to", "of", "for", "with", "your", "you",
    "this", "that", "can", "help", "please", "java", "python", "code",
    "if", "else", "how", "what", "when", "where", "why",
})

SWAHILI_MARKERS = SWAHILI_VOCAB

TERM_REPLACEMENTS = {
    "stress": "msongo wa mawazo",
    "anxiety": "wasiwasi",
    "depression": "huzuni ya muda mrefu",
    "panic attack": "shambulio la hofu",
    "therapy": "ushauri wa kisaikolojia",
    "mental health": "afya ya akili",
    "emotional wellbeing": "ustawi wa kihisia",
}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "")]


def normalize_swahili_response(text: str) -> str:
    content = (text or "").strip()
    if not content:
        return ""

    normalized = content
    for source, target in TERM_REPLACEMENTS.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def remove_english_words(text: str) -> str:
    """Remove English words from Swahili text. Returns cleaned string."""
    if not text:
        return ""
    tokens = _TOKEN_RE.findall(text)
    kept = [t for t in tokens if t.lower() not in ENGLISH_LEAK_WORDS]
    result = " ".join(kept)
    return re.sub(r"\s+", " ", result).strip()


def _looks_garbled(text: str) -> bool:
    """Reject only obvious gibberish: 3+ vowels, heavy English, or code words."""
    if not text:
        return True
    lower = text.lower()
    if _CONSECUTIVE_VOWELS.search(lower):
        return True
    tokens = _tokens(text)
    if not tokens:
        return True
    english = sum(1 for t in tokens if t in ENGLISH_LEAK_WORDS)
    if english / len(tokens) > 0.12:
        return True
    return False


def swahili_quality_report(text: str) -> dict:
    tokens = _tokens(text)
    if not tokens:
        return {"passed": False, "sw_ratio": 0.0, "en_ratio": 1.0}

    if _looks_garbled(text):
        return {"passed": False, "sw_ratio": 0.0, "en_ratio": 1.0}

    sw_hits = sum(1 for token in tokens if token in SWAHILI_MARKERS)
    en_hits = sum(1 for token in tokens if token in ENGLISH_LEAK_WORDS)
    total = len(tokens)
    sw_ratio = sw_hits / total
    en_ratio = en_hits / total

    passed = sw_ratio >= 0.08 and en_ratio <= 0.15
    return {"passed": passed, "sw_ratio": sw_ratio, "en_ratio": en_ratio}


def passes_swahili_quality(text: str) -> bool:
    return bool(swahili_quality_report(text)["passed"])
