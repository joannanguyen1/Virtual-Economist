"""Chat history routes.

All endpoints require authentication (Bearer JWT).

GET  /api/history/chats                     — list the user's chat sessions
GET  /api/history/chats/{chat_id}/messages  — get all messages in a chat
PATCH /api/history/chats/{chat_id}/title    — rename a chat
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas import (
    ChatHistoryResponse,
    ChatSummaryResponse,
    MessageResponse,
    UpdateChatTitleRequest,
)
from backend.app.middleware.auth import require_user_id
from backend.app.services import history as hist

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/chats", response_model=list[ChatSummaryResponse])
def list_chats(
    limit: int = 20,
    user_id: int = Depends(require_user_id),
) -> list[ChatSummaryResponse]:
    """Return the authenticated user's chat sessions, newest first.

    Query params:
        limit — max sessions to return (default 20, max 100)
    """
    limit = min(limit, 100)
    chats = hist.get_user_chats(user_id, limit=limit)
    return [
        ChatSummaryResponse(
            id=c.id,
            agent_type=c.agent_type,
            title=c.title,
            created_at=c.created_at,
        )
        for c in chats
    ]


@router.get("/chats/{chat_id}/messages", response_model=ChatHistoryResponse)
def get_chat_messages(
    chat_id: int,
    user_id: int = Depends(require_user_id),
) -> ChatHistoryResponse:
    """Return all messages in a specific chat session.

    Returns 404 if the chat doesn't exist or belongs to a different user.
    """
    chat = hist.get_chat_by_id(chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = hist.get_chat_messages(chat_id)
    return ChatHistoryResponse(
        chat_id=chat.id,
        agent_type=chat.agent_type,
        title=chat.title,
        messages=[
            MessageResponse(
                id=m.id,
                sender=m.sender_label,  # int 0/1 → 'user'/'agent' string for API
                message=m.message,
                metadata=m.metadata,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.patch("/chats/{chat_id}/title", response_model=dict)
def rename_chat(
    chat_id: int,
    body: UpdateChatTitleRequest,
    user_id: int = Depends(require_user_id),
) -> dict:
    """Update the display title for a chat session.

    Returns 404 if the chat doesn't exist or belongs to a different user.
    """
    updated = hist.update_chat_title(chat_id, user_id, body.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True, "title": body.title}
