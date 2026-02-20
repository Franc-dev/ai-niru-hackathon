"""
Agent Service: ReAct loop with RAG (search_knowledge) tool.
Uses our local model (trained on EM-NS mental health data). Returns final response as str.

System prompt: guardrails, language separation (EN/SW), crisis handling, off-topic redirection.
"""
import re
from typing import Any

import httpx

from backend.core.config import settings
from backend.services.agent_prompts import build_system_prompt
from backend.services.guardrails import check_guardrail
from backend.services.rag import retrieve

MAX_REACT_STEPS = 5


def _parse_action_or_final(text: str) -> tuple[str | None, str | None]:
    """Returns (action_type, argument) or (None, final_answer). action_type is 'search_knowledge', argument is the query."""
    text = text.strip()
    m = re.search(r"Final\s+Answer:\s*(.*)", text, re.I | re.DOTALL)
    if m:
        return None, m.group(1).strip()

    m = re.search(r"Action:\s*search_knowledge\s*\(\s*[\"']([^\"']*)[\"']\s*\)", text, re.I)
    if m:
        return "search_knowledge", m.group(1).strip()

    return None, None


async def _chat_completion(messages: list[dict[str, str]]) -> str:
    """Call our local model. POST to LOCAL_MODEL_URL with {"messages": [...]}. Expects {"content": "..."} or {"choices": [{"message": {"content": "..."}}]}."""
    if not settings.LOCAL_MODEL_URL:
        return ""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            r = await client.post(
                settings.LOCAL_MODEL_URL,
                json={"messages": messages},
                headers={"bypass-tunnel-reminder": "true"},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        raise
    if "content" in data:
        return (data["content"] or "").strip()
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message") or {}
        return (msg.get("content") or "").strip()
    return ""


class AgentService:
    """ReAct agent with RAG search tool. Uses our trained local model."""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def process_message(
        self,
        message: str,
        conversation_id: str,
        history: list[dict[str, Any]],
        language: str = "en",
    ) -> str:
        """
        Run ReAct loop. history is list of { role, content }.
        Returns final assistant response string.
        """
        lang = "sw" if language and str(language).lower().startswith("sw") else "en"

        # Guardrail: intercept off-topic requests (coding, math, etc.) before calling model
        should_redirect, redirect_msg = check_guardrail(message, lang)
        if should_redirect and redirect_msg:
            return redirect_msg

        system_content = build_system_prompt(language=lang, include_rag=True)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

        step = 0
        while step < MAX_REACT_STEPS:
            step += 1
            try:
                content = await _chat_completion(messages)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
                return (
                    "Elevana is temporarily unavailable. Please check that the model server is running and try again."
                    if lang == "en"
                    else "Elevana haupatikani kwa sasa. Tafadhali angalia kuwa seva ya modeli inaendesha na jaribu tena."
                )
            if not content:
                break

            action_type, value = _parse_action_or_final(content)
            if action_type == "search_knowledge" and value:
                chunks = await retrieve(value)
                observation = "\n\n".join(c.get("content", "") for c in chunks) if chunks else "No relevant results found."
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Observation:\n{observation}\n\nContinue with another Thought/Action or provide your Final Answer."})
                continue
            if value is not None and action_type is None:
                # Model used "Final Answer:" prefix — return the value
                return value or "I don't have a final answer for that."
            # Model gave a plain response without ReAct format.
            # Small models (e.g. 1.5B) often don't follow ReAct prompting
            # reliably, so treat any non-empty response as the final answer.
            if content:
                return content

        return "I couldn't complete a full answer. Please try asking again or rephrase your question."


agent_service = AgentService()
