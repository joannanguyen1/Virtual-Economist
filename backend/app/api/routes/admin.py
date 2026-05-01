"""Admin routes — manage user roles.

GET    /api/admin/users                — list all users with their role
PATCH  /api/admin/users/{user_id}/role — change a user's role

All endpoints require the admin role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.middleware.auth import ALLOWED_ROLES, CurrentUser, require_role
from backend.database.connect import db_cursor

router = APIRouter(prefix="/admin", tags=["admin"])


class UserRow(BaseModel):
    id: int
    username: str
    email: str
    role: str
    email_verified: bool
    created_at: str


class RoleUpdate(BaseModel):
    role: str = Field(..., description="One of: admin, housing, market")


@router.get("/users", response_model=list[UserRow])
def list_users(_: CurrentUser = Depends(require_role("admin"))) -> list[UserRow]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, username, email, role, email_verified, created_at
            FROM users
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()

    return [
        UserRow(
            id=r[0],
            username=r[1],
            email=r[2],
            role=r[3],
            email_verified=bool(r[4]),
            created_at=r[5].isoformat() if r[5] else "",
        )
        for r in rows
    ]


@router.patch("/users/{user_id}/role", response_model=UserRow)
def update_role(
    user_id: int,
    body: RoleUpdate,
    actor: CurrentUser = Depends(require_role("admin")),
) -> UserRow:
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {list(ALLOWED_ROLES)}",
        )

    if actor.id == user_id and body.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="You cannot demote your own admin account.",
        )

    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE users SET role = %s
            WHERE id = %s
            RETURNING id, username, email, role, email_verified, created_at
            """,
            (body.role, user_id),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("admin {} set user {} role -> {}", actor.id, user_id, body.role)

    return UserRow(
        id=row[0],
        username=row[1],
        email=row[2],
        role=row[3],
        email_verified=bool(row[4]),
        created_at=row[5].isoformat() if row[5] else "",
    )
