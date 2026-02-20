"""
Voice endpoints:
  GET  /voice/convai/token     — return ElevenLabs signed WebSocket URL (keeps API key server-side)
  POST /voice/tts/stream       — ElevenLabs streaming TTS chunks
  POST /voice/tts              — ElevenLabs blocking TTS (full MP3 blob)
  POST /voice/stt              — ElevenLabs Scribe STT (server-side fallback)
"""
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.services.voice import stream_speech, synthesize_speech, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
LanguageCode = Literal["en", "sw"]

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


# ─── /voice/convai/token ────────────────────────────────────────────────────

@router.get("/convai/token")
async def get_convai_token(
    lang: str = "en",
    current_user: dict = Depends(get_current_user),
):
    """
    Exchange a JWT for an ElevenLabs Conversational AI signed WebSocket URL.
    The API key never reaches the browser — only the short-lived signed URL does.
    """
    agent_id = (
        settings.ELEVENLABS_AGENT_ID_SW
        if lang == "sw"
        else settings.ELEVENLABS_AGENT_ID_EN
    )
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ElevenLabs agent not configured for language '{lang}'. "
                "Set ELEVENLABS_AGENT_ID_EN / ELEVENLABS_AGENT_ID_SW in .env and "
                "create the agents at elevenlabs.io/app/conversational-ai."
            ),
        )
    if not settings.ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ELEVENLABS_API_KEY not configured.")

    url = f"{_ELEVENLABS_BASE}/convai/conversation/get_signed_url?agent_id={agent_id}"
    headers = {"xi-api-key": settings.ELEVENLABS_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return {"signed_url": data["signed_url"], "agent_id": agent_id}
    except httpx.HTTPStatusError as exc:
        logger.error("ElevenLabs signed URL error: %s %s", exc.response.status_code, exc.response.text)
        raise HTTPException(status_code=502, detail="Could not get ElevenLabs signed URL") from exc
    except Exception as exc:
        logger.exception("Signed URL unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Signed URL fetch failed") from exc


# ─── Pydantic models ─────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class STTResponse(BaseModel):
    transcript: str
    language: str


# ─── /voice/tts/stream ──────────────────────────────────────────────────────

@router.post("/tts/stream")
async def tts_stream(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """Forward ElevenLabs streaming TTS chunks — audio starts within ~150 ms."""
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    async def generate():
        try:
            async for chunk in stream_speech(request.text, request.language):
                yield chunk
        except httpx.HTTPStatusError as exc:
            logger.error("ElevenLabs stream TTS error: %s", exc.response.status_code)
        except Exception as exc:
            logger.exception("TTS stream error: %s", exc)

    return StreamingResponse(generate(), media_type="audio/mpeg", headers={"Cache-Control": "no-cache"})


# ─── /voice/tts ─────────────────────────────────────────────────────────────

@router.post("/tts", response_class=Response)
async def tts(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """Full MP3 blob — reliable fallback."""
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    try:
        mp3_bytes = await synthesize_speech(request.text, request.language)
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    except httpx.HTTPStatusError as exc:
        logger.error("ElevenLabs TTS error: %s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Voice synthesis failed") from exc
    except Exception as exc:
        logger.exception("TTS unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Voice synthesis failed") from exc


# ─── /voice/stt ─────────────────────────────────────────────────────────────

@router.post("/stt", response_model=STTResponse)
async def stt(
    file: UploadFile,
    language: str = Form("en"),
    current_user: dict = Depends(get_current_user),
):
    """Server-side STT fallback via ElevenLabs Scribe."""
    audio_bytes = await file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB)")
    try:
        transcript = await transcribe_audio(audio_bytes, filename=file.filename or "audio.webm", language=language)
        return STTResponse(transcript=transcript, language=language)
    except httpx.HTTPStatusError as exc:
        logger.error("ElevenLabs STT error: %s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Speech transcription failed") from exc
    except Exception as exc:
        logger.exception("STT unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Speech transcription failed") from exc
