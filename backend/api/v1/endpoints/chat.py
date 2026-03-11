"""
Chat Endpoints
"""
import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field

from backend.api.deps import get_current_user
from backend.repositories.conversation_repo import (
    add_message,
    archive_conversation,
    conversation_exists,
    delete_conversation,
    delete_message,
    get_conversation,
    get_conversation_messages,
    get_or_create_conversation,
    list_conversations,
    pin_conversation,
    set_conversation_title_if_empty,
    update_conversation_language,
    update_conversation_title,
    update_message_content,
)
from backend.repositories.user_repo import update_user_preferred_language
from backend.services.agent import agent_service
from backend.services.recommendations import recommendation_service
from backend.services.safety import check_safety_rules

router = APIRouter()

LanguageCode = Literal["en", "sw"]

REFUSAL_MESSAGES: dict[LanguageCode, str] = {
    "en": "I can't help with that. How else can I assist you?",
    "sw": "Siwezi kusaidia kwa hilo. Naweza kukusaidia vipi vinginevyo?",
}


def normalize_language(language: str | None) -> LanguageCode:
    """Map unknown language input to supported values."""
    return "sw" if language == "sw" else "en"


def generate_title_from_response(response_text: str, max_length: int = 72) -> str:
    """Build a one-line title from the first response paragraph."""
    if not response_text:
        return ""
    first_paragraph = response_text.strip().split("\n\n")[0].strip()
    normalized = " ".join(first_paragraph.replace("#", "").replace("*", "").split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length - 1].rstrip()}…"


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    message_id: Optional[str] = None
    metadata: dict | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None
    language: Optional[LanguageCode] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    conversation_title: str | None = None
    language: LanguageCode = "en"
    timestamp: str
    message_metadata: dict | None = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    title: str | None = None
    language: LanguageCode = "en"
    messages: list[ChatMessage]


class ConversationListItem(BaseModel):
    conversation_id: str
    title: str | None = None
    language: LanguageCode = "en"
    created_at: str | None = None
    updated_at: str | None = None
    preview: str = ""
    pinned: bool = False
    archived: bool = False


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Chat endpoint: user-scoped conversation, safety check, agent (ReAct + RAG), persist and return.
    """
    try:
        user_id = current_user["id"]
        selected_language = normalize_language(request.language or current_user.get("preferred_language"))

        conversation_id = await get_or_create_conversation(
            user_id=user_id,
            conversation_id=request.conversation_id,
            language=selected_language,
        )

        if request.language:
            await update_conversation_language(conversation_id, user_id, request.language)
            await update_user_preferred_language(user_id, request.language)

        await add_message(
            conversation_id,
            "user",
            request.message,
            metadata={"language": selected_language},
        )

        safety = check_safety_rules(request.message)
        if not safety.get("safe", True):
            if recommendation_service.is_self_harm_crisis(request.message):
                crisis_reply = recommendation_service.maybe_build_response(
                    message=request.message,
                    history=[{"role": "user", "content": request.message}],
                    language=selected_language,
                )
                crisis_text = str((crisis_reply or {}).get("text", "")).strip() or REFUSAL_MESSAGES[selected_language]
                crisis_metadata = {"language": selected_language, **((crisis_reply or {}).get("metadata") or {})}
                await add_message(
                    conversation_id,
                    "assistant",
                    crisis_text,
                    metadata=crisis_metadata,
                )
                conversation = await get_conversation(conversation_id, user_id)
                return ChatResponse(
                    response=crisis_text,
                    conversation_id=conversation_id,
                    conversation_title=conversation.get("title") if conversation else None,
                    language=selected_language,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    message_metadata=crisis_metadata,
                )

            refusal = REFUSAL_MESSAGES[selected_language]
            await add_message(
                conversation_id,
                "assistant",
                refusal,
                metadata={"language": selected_language, "safety_refusal": True},
            )
            conversation = await get_conversation(conversation_id, user_id)
            return ChatResponse(
                response=refusal,
                conversation_id=conversation_id,
                conversation_title=conversation.get("title") if conversation else None,
                language=selected_language,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        history = await get_conversation_messages(conversation_id)
        history_for_agent = [{"role": m["role"], "content": m["content"]} for m in history]

        agent_reply = await agent_service.process_message(
            request.message,
            conversation_id,
            history_for_agent,
            language=selected_language,
        )
        response_metadata = {"language": selected_language, **(agent_reply.metadata or {})}
        await add_message(
            conversation_id,
            "assistant",
            agent_reply.text,
            metadata=response_metadata,
        )

        title = generate_title_from_response(agent_reply.text)
        if title:
            await set_conversation_title_if_empty(conversation_id, user_id, title)

        conversation = await get_conversation(conversation_id, user_id)
        return ChatResponse(
            response=agent_reply.text,
            conversation_id=conversation_id,
            conversation_title=conversation.get("title") if conversation else None,
            language=normalize_language(conversation.get("language") if conversation else selected_language),
            timestamp=datetime.now(timezone.utc).isoformat(),
            message_metadata=response_metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat error: %s", e)
        raise HTTPException(status_code=500, detail="An error occurred while processing your message.")


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_chat_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get user-scoped chat history for a conversation. Returns 404 if not found."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_conversation_messages(conversation_id)
    conversation = await get_conversation(conversation_id, current_user["id"])
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        title=(conversation.get("title") if conversation else None),
        language=normalize_language(conversation.get("language") if conversation else "en"),
        messages=[ChatMessage(**message) for message in messages],
    )


@router.get("/conversations", response_model=list[ConversationListItem])
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    include_archived: bool = False,
):
    """List authenticated user's conversations."""
    items = await list_conversations(
        current_user["id"], limit=min(max(limit, 1), 200), include_archived=include_archived
    )
    return [ConversationListItem(**item) for item in items]


class UpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class PinRequest(BaseModel):
    pinned: bool


class ArchiveRequest(BaseModel):
    archived: bool


class UpdateMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    if not await delete_conversation(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.patch("/conversations/{conversation_id}")
async def edit_conversation_title(
    conversation_id: str,
    body: UpdateTitleRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit conversation title."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    await update_conversation_title(conversation_id, current_user["id"], body.title)
    return {"ok": True}


@router.patch("/conversations/{conversation_id}/pin")
async def pin_conversation_endpoint(
    conversation_id: str,
    body: PinRequest,
    current_user: dict = Depends(get_current_user),
):
    """Toggle pin on a conversation."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    await pin_conversation(conversation_id, current_user["id"], body.pinned)
    return {"ok": True}


@router.patch("/conversations/{conversation_id}/archive")
async def archive_conversation_endpoint(
    conversation_id: str,
    body: ArchiveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Toggle archive on a conversation."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    await archive_conversation(conversation_id, current_user["id"], body.archived)
    return {"ok": True}


@router.delete("/conversations/{conversation_id}/messages/{message_id}")
async def delete_message_endpoint(
    conversation_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a single message."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not await delete_message(message_id, conversation_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True}


@router.patch("/conversations/{conversation_id}/messages/{message_id}")
async def edit_message_endpoint(
    conversation_id: str,
    message_id: str,
    body: UpdateMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit a message's content."""
    if not await conversation_exists(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not await update_message_content(message_id, conversation_id, body.content):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True}
