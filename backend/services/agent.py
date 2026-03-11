"""
Agent service calls LOCAL_MODEL_URL when configured, otherwise returns
a prompt to use voice mode (ElevenLabs Conversational AI).
"""
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from backend.core.config import settings
from backend.services.agent_prompts import build_system_prompt
from backend.services.guardrails import check_guardrail
from backend.services.rag import retrieve
from backend.services.recommendations import recommendation_service
from backend.services.swahili_quality import normalize_swahili_response, remove_english_words

logger = logging.getLogger(__name__)

_UNAVAILABLE = {
    "en": (
        "Hi! I'm Elevana. For the best real-time experience, please tap the "
        "microphone button to talk with me via voice."
    ),
    "sw": (
        "Habari! Mimi ni Elevana. Kwa uzoefu bora, tafadhali bonyeza kitufe cha "
        "kipaza sauti ili kuzungumza nami kwa wakati halisi."
    ),
}


@dataclass
class AgentReply:
    text: str
    metadata: dict[str, Any] | None = None


async def _chat_completion(messages: list[dict]) -> str | None:
    """Call the local model. Returns None if unavailable."""
    if not settings.LOCAL_MODEL_URL:
        return None
    payload = {
        "messages": messages,
        "max_new_tokens": 180,
        "temperature": 0,
        "top_p": 1.0,
        "repetition_penalty": 1.08,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                settings.LOCAL_MODEL_URL,
                json=payload,
                headers={"bypass-tunnel-reminder": "true"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
        logger.warning("Local model request failed: %s", exc)
        return None

    if "content" in data:
        return (data["content"] or "").strip() or None
    if "choices" in data and data["choices"]:
        message = data["choices"][0].get("message") or {}
        return (message.get("content") or "").strip() or None
    return None


def _build_messages(
    system_prompt: str,
    history: list[dict[str, Any]],
    message: str,
    context_prompt: str = "",
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    if context_prompt:
        messages.append({"role": "system", "content": context_prompt})

    for turn in history[-12:]:
        role = turn.get("role", "user")
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})
    return messages


def _build_swahili_context_prompt(matches: list[dict]) -> str:
    lines: list[str] = []
    for match in matches[: settings.RAG_TOP_K]:
        snippet = str(match.get("document", "")).strip()
        if snippet:
            lines.append(f"- {snippet[:280]}")

    if not lines:
        return ""

    return (
        "Tumia muktadha huu kuboresha usahihi wa jibu kwa Kiswahili. "
        "Usibadilishe maana ya swali la mtumiaji.\n" + "\n".join(lines)
    )


async def _load_swahili_context(message: str) -> str:
    if settings.VECTOR_DB_TYPE != "chroma":
        return ""

    matches = await retrieve(message, top_k=settings.RAG_TOP_K)
    if not matches:
        logger.warning("Swahili chat running without retrieval context.")
        return ""

    return _build_swahili_context_prompt(matches)


class AgentService:
    def __init__(self) -> None:
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    async def process_message(
        self,
        message: str,
        conversation_id: str,
        history: list,
        language: str = "en",
    ) -> AgentReply:
        lang = "sw" if str(language).lower().startswith("sw") else "en"
        conversation_history = history or []

        should_redirect, redirect_msg = check_guardrail(message, lang)
        if should_redirect and redirect_msg:
            return AgentReply(text=redirect_msg)

        recommendation = recommendation_service.maybe_build_response(
            message=message,
            history=conversation_history,
            language=lang,
        )
        if recommendation:
            return AgentReply(
                text=str(recommendation.get("text", "")).strip(),
                metadata=recommendation.get("metadata"),
            )

        if lang == "sw":
            return await self._process_swahili_message(message, conversation_history)

        system = build_system_prompt(language=lang, include_rag=False)
        messages = _build_messages(system, conversation_history, message)

        response = await _chat_completion(messages)
        return AgentReply(text=response if response else _UNAVAILABLE[lang])

    async def _process_swahili_message(self, message: str, history: list[dict[str, Any]]) -> AgentReply:
        system = build_system_prompt(language="sw", include_rag=False)
        context_prompt = await _load_swahili_context(message)
        messages = _build_messages(system, history, message, context_prompt=context_prompt)

        draft = await _chat_completion(messages)
        if not draft:
            return AgentReply(text=_UNAVAILABLE["sw"])

        normalized = normalize_swahili_response(draft)
        return AgentReply(text=remove_english_words(normalized) or normalized)


agent_service = AgentService()
