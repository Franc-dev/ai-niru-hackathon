"""
Voice-optimised agent for real-time spoken conversation.

Uses Anthropic Claude (Haiku) directly — no local model, no ReAct loop, no markdown.
Responses are kept short (≤ 3 sentences) so ElevenLabs TTS sounds natural.

Two system prompts:
  VOICE_SYSTEM_EN — English spoken conversation
  VOICE_SYSTEM_SW — Swahili spoken conversation
"""
import logging
from typing import Any

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
VOICE_MODEL = "claude-haiku-4-5-20251001"
VOICE_MAX_TOKENS = 180  # ~2–3 spoken sentences

# ---------------------------------------------------------------------------
# System prompts — optimised for TEXT-TO-SPEECH output
# Rules: no markdown, no lists, short sentences, warm conversational tone
# ---------------------------------------------------------------------------

VOICE_SYSTEM_EN = """\
You are Elevana, a warm and caring mental health companion having a real-time voice conversation.

SPEAK NATURALLY. Keep every reply to one to three short sentences — your words will be read aloud by a voice engine. Never use bullet points, numbered lists, asterisks, hashtags, bold text, or any markdown formatting. Write plain spoken sentences only.

Be empathetic, gentle, and present. Your focus is mental health, emotional wellbeing, stress, anxiety, mood, relationships, and coping. If someone raises an unrelated topic, kindly say you are here for emotional support and invite them to share how they are feeling.

If someone expresses thoughts of self-harm or a crisis, respond with compassion, encourage them to call a helpline or emergency services, and stay supportive throughout.

Always respond in English only. Never mix languages.\
"""

VOICE_SYSTEM_SW = """\
Wewe ni Elevana, mshauri wa afya ya akili mwenye upole na huruma, unayeongea katika mazungumzo ya sauti ya wakati halisi.

ONGEA KWA KAWAIDA. Weka kila jibu katika sentensi moja hadi tatu fupi — maneno yako yatasomwa kwa sauti na injini ya sauti. Usitumie orodha, nambari, nyota, alama za gridi, maandishi mazito, au muundo wowote wa markdown. Andika sentensi za kawaida za mazungumzo tu.

Kuwa na huruma, upole, na uwepo. Zingatia afya ya akili, ustawi wa kihemko, msongo wa mawazo, wasiwasi, hisia, mahusiano, na kukabiliana. Kama mtu akiuliza kuhusu mada nyingine, sema kwa upole kwamba uko hapa kwa msaada wa kihemko na umwomba ashiriki hisia zake.

Kama mtu anaonyesha mawazo ya kujidhuru au hali ya dharura, jibu kwa huruma, mhimize kupiga simu ya dharura au msaada wa kiakili, na endelea kumsaidia.

Jibu kwa Kiswahili peke yake daima. Usichanganye lugha.\
"""


def _system_prompt(language: str) -> str:
    return VOICE_SYSTEM_SW if language == "sw" else VOICE_SYSTEM_EN


async def voice_respond(
    message: str,
    history: list[dict[str, Any]],
    language: str = "en",
) -> str:
    """
    Call Claude Haiku with the voice system prompt and return a short spoken response.
    history: list of {"role": "user"|"assistant", "content": "..."}
    """
    if not settings.ANTHROPIC_API_KEY:
        # Graceful fallback if key not yet configured
        return (
            "Voice responses are not configured yet. Please add your Anthropic API key."
            if language != "sw"
            else "Majibu ya sauti hayajasanidiwa bado. Tafadhali ongeza ufunguo wako wa Anthropic API."
        )

    # Build messages list (last 10 turns for context, skip system messages)
    messages: list[dict[str, str]] = []
    for turn in history[-10:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Ensure current user message is last
    if not messages or messages[-1]["content"] != message:
        messages.append({"role": "user", "content": message})

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": VOICE_MODEL,
        "max_tokens": VOICE_MAX_TOKENS,
        "system": _system_prompt(language),
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(ANTHROPIC_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"].strip()
    except httpx.HTTPStatusError as exc:
        logger.error("Anthropic API error %s: %s", exc.response.status_code, exc.response.text)
        raise
    except Exception as exc:
        logger.exception("Voice agent error: %s", exc)
        raise
