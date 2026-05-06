"""Insights (dashboard) routes.

These endpoints are meant for structured visualizations (heatmaps, summaries)
and are separate from the Bedrock tool-use chat flow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import (
    CitySuggestionResponse,
    HousingHeatmapResponse,
)
from backend.app.services import insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/cities", response_model=list[CitySuggestionResponse])
def cities(q: str, limit: int = 10, kind: str = "city") -> list[CitySuggestionResponse]:
    try:
        results = insights.suggest_cities(q, limit=limit, kind=kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [
        CitySuggestionResponse(city=item.city, latitude=item.latitude, longitude=item.longitude)
        for item in results
    ]


@router.get("/housing-heatmap", response_model=HousingHeatmapResponse)
def housing_heatmap(
    metric: str,
    south: float,
    north: float,
    west: float,
    east: float,
    limit: int = 2500,
    kind: str = "city",
    source: str = "zillow",
) -> HousingHeatmapResponse:
    try:
        payload = insights.get_housing_heatmap_points(
            metric,
            source=source,
            kind=kind,
            south=south,
            north=north,
            west=west,
            east=east,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HousingHeatmapResponse(**payload)
