"""
Agent Service: ReAct loop with RAG (search_knowledge) tool.
Uses our local model (trained on synthetic data). Returns final response as str.
"""
import re
from typing import Any

import httpx

from backend.core.config import settings
from backend.services.rag import retrieve

MAX_REACT_STEPS = 5

SYSTEM_PROMPT = """You are a helpful assistant with access to a knowledge base. When you need to look up information, use the tool search_knowledge.

Format your response as follows:
- To search: write exactly "Action: search_knowledge(\"your search query here\")" on its own line.
- To answer the user: write "Final Answer: " followed by your reply.

You may use search_knowledge zero or more times, then provide a Final Answer. Base your answer on the observations from search when relevant. If the knowledge base has no relevant information, say so and answer from general knowledge."""


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
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(settings.LOCAL_MODEL_URL, json={"messages": messages})
        r.raise_for_status()
        data = r.json()
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
    ) -> str:
        """
        Run ReAct loop. history is list of { role, content }.
        Returns final assistant response string.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

        step = 0
        while step < MAX_REACT_STEPS:
            step += 1
            content = await _chat_completion(messages)
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
                return value or "I don't have a final answer for that."
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "Please provide either Action: search_knowledge(\"query\") or Final Answer: your response."})

        return "I couldn't complete a full answer. Please try asking again or rephrase your question."


agent_service = AgentService()
