"""Chat routes — unified endpoint + per-agent endpoints.

POST /api/chat           →  Titan classifier auto-routes to the right agent (admin only)
POST /api/chat/housing   →  HousingAgent (admin or housing role)
POST /api/chat/market    →  MarketAgent (admin or market role)

All endpoints:
 - Require an authenticated user with the appropriate role
 - Run the agent pipeline
 - Persist the turn to stored_chats / stored_messages
 - Return a ChatResponse (includes conversation_id so the frontend can continue the thread)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from loguru import logger

from backend.app.agents.housing.agent import HousingAgent
from backend.app.agents.market.agent import MarketAgent
from backend.app.agents.router import route_question
from backend.app.api.schemas import ChatRequest, ChatResponse
from backend.app.middleware.auth import CurrentUser, require_role
from backend.app.services import history as hist
from backend.app.services.history import SENDER_AGENT, SENDER_USER

router = APIRouter(prefix="/chat", tags=["chat"])

# One shared instance per process — agents hold no mutable state
_housing_agent = HousingAgent()
_market_agent = MarketAgent()


_ADMIN_ONLY = require_role("admin")
_ADMIN_ONLY_DEP = Depends(_ADMIN_ONLY)

_ADMIN_OR_HOUSING = require_role("admin", "housing")
_ADMIN_OR_HOUSING_DEP = Depends(_ADMIN_OR_HOUSING)

_ADMIN_OR_MARKET = require_role("admin", "market")
_ADMIN_OR_MARKET_DEP = Depends(_ADMIN_OR_MARKET)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _persist_turn(
    user_id: int,
    agent_type: str | None,
    question: str,
    chat_request_conv_id: int | None,
    answer: str,
    sql_used: str | None,
    rows_found: int,
    error: str | None,
    tool_trace: list[dict] | None,
    chart_data: dict | None,
) -> int:
    """Save a user + agent message pair and return the chat_id."""
    if chat_request_conv_id is not None:
        chat_id = chat_request_conv_id
    else:
        title = question[:60] + ("…" if len(question) > 60 else "")
        chat_id = hist.create_chat(user_id, agent_type, title=title)

    hist.save_message(chat_id, SENDER_USER, question)
    hist.save_message(
        chat_id,
        SENDER_AGENT,
        answer,
        metadata={
            "sql_used": sql_used,
            "rows_found": rows_found,
            "error": error,
            "tool_trace": tool_trace,
            "chart_data": chart_data,
        },
    )
    return chat_id


# ---------------------------------------------------------------------------
# Unified endpoint — Titan Text Lite auto-classifies and routes (admin only)
# ---------------------------------------------------------------------------


@router.post("", response_model=ChatResponse)
def unified_chat(
    body: ChatRequest,
    user: CurrentUser = _ADMIN_ONLY_DEP,
) -> ChatResponse:
    """Send any question to the Virtual Economist (admin-only auto-routing)."""
    logger.info("POST /chat (unified) | user={} question={!r}", user.id, body.question)
    agent_type, result = route_question(body.question)

    chat_id: int | None = None
    try:
        chat_id = _persist_turn(
            user_id=user.id,
            agent_type=agent_type,
            question=body.question,
            chat_request_conv_id=body.conversation_id,
            answer=result.answer,
            sql_used=result.sql_used,
            rows_found=result.rows_found,
            error=result.error,
            tool_trace=result.tool_trace,
            chart_data=result.chart_data,
        )
    except Exception as exc:
        logger.warning("history save failed (unified/{}): {}", agent_type, exc)

    return ChatResponse(
        answer=result.answer,
        agent_type=agent_type,
        conversation_id=chat_id,
        rows_found=result.rows_found,
        sql_used=result.sql_used,
        error=result.error,
        tool_trace=result.tool_trace,
        chart_data=result.chart_data,
    )


# ---------------------------------------------------------------------------
# Housing endpoint — admin or housing role
# ---------------------------------------------------------------------------


@router.post("/housing", response_model=ChatResponse)
def housing_chat(
    body: ChatRequest,
    user: CurrentUser = _ADMIN_OR_HOUSING_DEP,
) -> ChatResponse:
    """Send a message directly to the Housing & City Agent."""
    logger.info("POST /chat/housing | user={} question={!r}", user.id, body.question)
    result = _housing_agent.run(body.question)

    chat_id: int | None = None
    try:
        chat_id = _persist_turn(
            user_id=user.id,
            agent_type="housing",
            question=body.question,
            chat_request_conv_id=body.conversation_id,
            answer=result.answer,
            sql_used=result.sql_used,
            rows_found=result.rows_found,
            error=result.error,
            tool_trace=result.tool_trace,
            chart_data=result.chart_data,
        )
    except Exception as exc:
        logger.warning("history save failed (housing): {}", exc)

    return ChatResponse(
        answer=result.answer,
        agent_type="housing",
        conversation_id=chat_id,
        rows_found=result.rows_found,
        sql_used=result.sql_used,
        error=result.error,
        tool_trace=result.tool_trace,
        chart_data=result.chart_data,
    )


# ---------------------------------------------------------------------------
# Market endpoint — admin or market role
# ---------------------------------------------------------------------------


@router.post("/market", response_model=ChatResponse)
def market_chat(
    body: ChatRequest,
    user: CurrentUser = _ADMIN_OR_MARKET_DEP,
) -> ChatResponse:
    """Send a message directly to the Stock & Market Agent."""
    logger.info("POST /chat/market | user={} question={!r}", user.id, body.question)
    result = _market_agent.run(body.question)

    chat_id: int | None = None
    try:
        chat_id = _persist_turn(
            user_id=user.id,
            agent_type="market",
            question=body.question,
            chat_request_conv_id=body.conversation_id,
            answer=result.answer,
            sql_used=result.sql_used,
            rows_found=result.rows_found,
            error=result.error,
            tool_trace=result.tool_trace,
            chart_data=result.chart_data,
        )
    except Exception as exc:
        logger.warning("history save failed (market): {}", exc)

    return ChatResponse(
        answer=result.answer,
        agent_type="market",
        conversation_id=chat_id,
        rows_found=result.rows_found,
        sql_used=result.sql_used,
        error=result.error,
        tool_trace=result.tool_trace,
        chart_data=result.chart_data,
    )
