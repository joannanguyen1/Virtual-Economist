"""Pydantic request/response schemas for the chat and history APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Chat (agent) schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Body sent by the frontend when a user submits a message."""

    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: int | None = Field(
        default=None,
        description=(
            "ID of an existing stored_chats row to continue. "
            "If omitted (and the user is authenticated), a new chat is created automatically."
        ),
    )


class ChatResponse(BaseModel):
    """Response from POST /api/chat, /api/chat/housing, or /api/chat/market."""

    answer: str
    agent_type: str | None = None  # 'housing' | 'market' (set by unified endpoint)
    conversation_id: int | None = None  # echoes back the stored_chats.id
    rows_found: int = 0
    sql_used: str | None = None  # debug only; omit in production if desired
    error: str | None = None
    tool_trace: list[dict] | None = None
    chart_data: dict | None = None


# ---------------------------------------------------------------------------
# Chat history schemas
# ---------------------------------------------------------------------------


class ChatSummaryResponse(BaseModel):
    """One stored_chats row (returned in the sidebar / chat-list view)."""

    id: int
    agent_type: str | None = None  # 'housing' | 'market' | null
    title: str | None = None
    created_at: datetime


class MessageResponse(BaseModel):
    """One stored_messages row.

    `sender` is normalised to a string for the frontend:
      0 (SENDER_USER)  → 'user'
      1 (SENDER_AGENT) → 'agent'
    """

    id: int
    sender: str  # 'user' | 'agent'
    message: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Full thread returned by GET /api/history/chats/{chat_id}/messages."""

    chat_id: int
    agent_type: str | None = None
    title: str | None = None
    messages: list[MessageResponse]


class UpdateChatTitleRequest(BaseModel):
    """Body for PATCH /api/history/chats/{chat_id}/title."""

    title: str = Field(..., min_length=1, max_length=200)
