"""FastAPI application entry point for Virtual Economist.

Start the server:
    uv run uvicorn backend.app.main:app --reload --port 8000

Endpoints:
    GET   /health                                    — health check
    POST  /api/chat                                  — Unified agent (auto-routes)
    POST  /api/chat/housing                          — Housing & City Agent
    POST  /api/chat/market                           — Stock & Market Agent
    GET   /api/history/chats                         — list user's chat sessions
    GET   /api/history/chats/{id}/messages           — full message thread
    PATCH /api/history/chats/{id}/title              — rename a chat

Interactive docs (dev only):
    http://localhost:8000/docs
    http://localhost:8000/redoc
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env BEFORE anything else reads os.getenv()
_env_path = Path(__file__).resolve().parents[1] / ".env"  # backend/.env
load_dotenv(_env_path)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from loguru import logger  # noqa: E402

from backend.app.api.routes import chat, health, history  # noqa: E402

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Virtual Economist API",
    description=(
        "AI-powered economic analysis agents for U.S. housing markets and "
        "stock/company insights. Powered by AWS Bedrock (Amazon Nova + Titan), "
        "enriched with live data from Finnhub, FRED, Census, and HUD. "
        "Includes per-user chat history stored in AWS RDS PostgreSQL."
    ),
    version="0.3.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the React dev server and any deployed frontend origin
# ---------------------------------------------------------------------------
_allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:800",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")


# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Virtual Economist API v{} starting up...", app.version)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Virtual Economist API shutting down.")
