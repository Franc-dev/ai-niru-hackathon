"""
Chat Endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.repositories.conversation_repo import (
    get_or_create_conversation,
    add_message,
    get_conversation_messages,
    conversation_exists,
)
from backend.services.safety import check_safety_rules
from backend.services.agent import agent_service

router = APIRouter()

REFUSAL_MESSAGE = "I can't help with that. How else can I assist you?"


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint: get/create conversation, safety check, agent (ReAct + RAG), persist and return.
    """
    try:
        conversation_id = await get_or_create_conversation(request.conversation_id)
        await add_message(conversation_id, "user", request.message)

        safety = check_safety_rules(request.message)
        if not safety.get("safe", True):
            await add_message(conversation_id, "assistant", REFUSAL_MESSAGE)
            return ChatResponse(
                response=REFUSAL_MESSAGE,
                conversation_id=conversation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        history = await get_conversation_messages(conversation_id)
        history_for_agent = [{"role": m["role"], "content": m["content"]} for m in history]

        response_text = await agent_service.process_message(
            request.message,
            conversation_id,
            history_for_agent,
        )
        await add_message(conversation_id, "assistant", response_text)

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while processing your message.")


@router.get("/history/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Get chat history for a conversation. Returns 404 if not found."""
    if not await conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_conversation_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}
