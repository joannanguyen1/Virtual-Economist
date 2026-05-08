"""JWT authentication + role-based access control for FastAPI.

Verifies tokens issued by the Node.js auth backend (jsonwebtoken / HS256).
Provides FastAPI dependency functions:

  get_current_user_id  — returns user_id or None (optional auth)
  require_user_id      — returns user_id or raises 401
  get_current_user     — returns {id, role} dict or raises 401 (looks up role from DB)
  require_role(*roles) — dependency factory that allows only the listed roles

The JWT payload from Node.js looks like:
  { "id": 42, "iat": ..., "exp": ... }

Role is fetched from the users table on each request so admin role changes
take effect immediately (no waiting for token expiry).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from loguru import logger

from backend.database.connect import db_cursor

ALLOWED_ROLES = ("admin", "housing", "market")


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: str


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


def _lookup_role(user_id: int) -> str | None:
    with db_cursor() as cur:
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> int | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("id")
    return int(user_id) if user_id is not None else None


async def require_user_id(
    user_id: int | None = Depends(get_current_user_id),
) -> int:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


async def get_current_user(
    user_id: int = Depends(require_user_id),
) -> CurrentUser:
    """Return {id, role} for the authenticated user, fetching role from DB."""
    role = _lookup_role(user_id)
    if role is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if role not in ALLOWED_ROLES:
        logger.warning("auth | user {} has invalid role {!r}", user_id, role)
        raise HTTPException(status_code=403, detail="Invalid role on user account")
    return CurrentUser(id=user_id, role=role)


_CURRENT_USER_DEP = Depends(get_current_user)


def require_role(*allowed: str):
    """Dependency factory: 403 unless the user's role is in `allowed`."""
    allowed_set = set(allowed)

    async def _dep(user: CurrentUser = _CURRENT_USER_DEP) -> CurrentUser:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of the following roles: {sorted(allowed_set)}",
            )
        return user

    return _dep
