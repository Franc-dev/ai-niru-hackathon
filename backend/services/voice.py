"""
ElevenLabs voice service — TTS (streaming + blob) and STT via REST API.
No SDK dependency; uses httpx which is already in requirements.
"""
import logging
from typing import AsyncIterator

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}


def _voice_id(language: str) -> str:
    return settings.ELEVENLABS_VOICE_ID_SW if language == "sw" else settings.ELEVENLABS_VOICE_ID_EN


def _tts_payload(text: str) -> dict:
    return {
        "text": text,
        "model_id": settings.ELEVENLABS_TTS_MODEL,
        "voice_settings": _VOICE_SETTINGS,
    }


async def synthesize_speech(text: str, language: str = "en") -> bytes:
    """Return full MP3 bytes (single request, no streaming)."""
    voice_id = _voice_id(language)
    url = f"{_ELEVENLABS_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=_tts_payload(text), headers=headers)
        response.raise_for_status()
        return response.content


async def stream_speech(text: str, language: str = "en") -> AsyncIterator[bytes]:
    """
    Yield MP3 chunks as ElevenLabs generates them.
    Callers can start piping audio to the browser before generation finishes,
    giving perceptibly lower latency (first byte in ~100–200 ms).
    """
    voice_id = _voice_id(language)
    url = f"{_ELEVENLABS_BASE}/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=_tts_payload(text), headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                if chunk:
                    yield chunk


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm", language: str = "en") -> str:
    """Call ElevenLabs Scribe STT. Kept as fallback; primary STT is the browser Web Speech API."""
    url = f"{_ELEVENLABS_BASE}/speech-to-text"
    headers = {"xi-api-key": settings.ELEVENLABS_API_KEY}
    language_code = "sw" if language == "sw" else "en"
    files = {
        "file": (filename, audio_bytes, "audio/webm"),
        "model_id": (None, settings.ELEVENLABS_STT_MODEL),
        "language_code": (None, language_code),
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        return data.get("text", "")
