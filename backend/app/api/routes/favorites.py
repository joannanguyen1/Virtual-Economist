"""Favorites routes.

Per-user favorite cities used by the Housing heatmap page.
All endpoints require authentication (Bearer JWT).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas import FavoriteCityCreateRequest, FavoriteCityResponse
from backend.app.middleware.auth import require_user_id
from backend.app.services import favorites

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/cities", response_model=list[FavoriteCityResponse])
def list_favorite_cities(
    user_id: int = Depends(require_user_id),
) -> list[FavoriteCityResponse]:
    cities = favorites.list_favorite_cities(user_id)
    return [
        FavoriteCityResponse(city=c.city, latitude=c.latitude, longitude=c.longitude)
        for c in cities
    ]


@router.post("/cities", response_model=FavoriteCityResponse)
def add_favorite_city(
    body: FavoriteCityCreateRequest,
    user_id: int = Depends(require_user_id),
) -> FavoriteCityResponse:
    try:
        saved = favorites.upsert_favorite_city(
            user_id,
            body.city,
            body.latitude,
            body.longitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FavoriteCityResponse(city=saved.city, latitude=saved.latitude, longitude=saved.longitude)


@router.delete("/cities", response_model=dict)
def remove_favorite_city(
    city: str,
    user_id: int = Depends(require_user_id),
) -> dict:
    try:
        ok = favorites.delete_favorite_city(user_id, city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": ok}
