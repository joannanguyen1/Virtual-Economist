"""JWT authentication middleware for FastAPI.

Verifies tokens issued by the Node.js auth backend (jsonwebtoken / HS256).
Provides two FastAPI dependency functions:

  get_current_user_id  — returns user_id or None (for optional auth endpoints)
  require_user_id      — returns user_id or raises 401 (for protected endpoints)

The JWT payload from Node.js looks like:
  { "id": 42, "email": "user@example.com", "iat": ..., "exp": ... }
"""

from __future__ import annotations

import os

import jwt
from fastapi import Depends, Header, HTTPException
from loguru import logger


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        logger.warning("JWT_SECRET is not set — all token verifications will fail")
    return secret


def _decode_token(token: str) -> dict | None:
    """Decode and verify a JWT.  Returns the payload dict, or None on failure."""
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.debug("auth | expired token")
        return None
    except jwt.InvalidTokenError as exc:
        logger.debug("auth | invalid token: {}", exc)
        return None


# ---------------------------------------------------------------------------
# FastAPI dependency: optional auth
# ---------------------------------------------------------------------------


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> int | None:
    """Extract user_id from the Authorization header if present and valid.

    Returns None (not 401) so agents can be used without auth during dev
    — chat history simply won't be persisted when user_id is None.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("id")
    return int(user_id) if user_id is not None else None


# ---------------------------------------------------------------------------
# FastAPI dependency: required auth
# ---------------------------------------------------------------------------


async def require_user_id(
    user_id: int | None = Depends(get_current_user_id),
) -> int:
    """Like get_current_user_id but raises 401 if no valid token is provided.

    Use this for history endpoints that must belong to a specific user.
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
