"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Returns 200 OK. Used by load balancers and monitoring."""
    return {"status": "ok"}
