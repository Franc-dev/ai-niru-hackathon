"""
Agent service — calls LOCAL_MODEL_URL when configured, otherwise returns
a prompt to use voice mode (ElevenLabs Conversational AI).
"""
import httpx

from backend.core.config import settings
from backend.services.agent_prompts import build_system_prompt
from backend.services.guardrails import check_guardrail

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


async def _chat_completion(messages: list[dict]) -> str | None:
    """Call the local model. Returns None if unavailable."""
    if not settings.LOCAL_MODEL_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                settings.LOCAL_MODEL_URL,
                json={"messages": messages},
                headers={"bypass-tunnel-reminder": "true"},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return None

    if "content" in data:
        return (data["content"] or "").strip() or None
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message") or {}
        return (msg.get("content") or "").strip() or None
    return None


class AgentService:
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def process_message(
        self,
        message: str,
        conversation_id: str,
        history: list,
        language: str = "en",
    ) -> str:
        lang = "sw" if str(language).lower().startswith("sw") else "en"

        should_redirect, redirect_msg = check_guardrail(message, lang)
        if should_redirect and redirect_msg:
            return redirect_msg

        system = build_system_prompt(language=lang, include_rag=False)
        messages = [{"role": "system", "content": system}]
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        response = await _chat_completion(messages)
        return response if response else _UNAVAILABLE[lang]


agent_service = AgentService()
