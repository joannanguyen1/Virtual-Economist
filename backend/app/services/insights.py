"""Structured, dashboard-friendly data helpers.

Unlike the chat agents (Bedrock tool-use), these helpers provide direct
read-only-ish endpoints designed for bulk visualization.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from loguru import logger
from psycopg2.extras import Json

from backend.app.services.live_apis import get_census_city_data, open_meteo_geocode_city
from backend.database.connect import db_cursor

_ALLOWED_HOUSING_METRICS: dict[str, list[str]] = {
    # Frontend-friendly keys (kept stable), mapped to the DB metric names.
    # Some environments may still have older/alternate metric strings, so we
    # accept both.
    "zhvi": ["home_values_zhvi", "zhvi"],
    "zori": ["rent_zori", "zori"],
    "inventory": ["for_sale_inventory", "inventory"],
    # Additional housing metrics present in our current housing_time_series.
    "price_cuts": ["price_cuts"],
    "new_listings": ["new_listings"],
    "mean_days_to_pending": ["mean_days_to_pending"],
    # Direct DB metric pass-through keys (useful for debugging / power users).
    "home_values_zhvi": ["home_values_zhvi"],
    "rent_zori": ["rent_zori"],
    "for_sale_inventory": ["for_sale_inventory"],
}

_ALLOWED_PIN_KINDS: set[str] = {"city", "zip", "neighborhood"}

_ALLOWED_HEATMAP_SOURCES: set[str] = {"zillow", "census"}

_ALLOWED_CENSUS_METRICS: set[str] = {
    "median_home_value",
    "median_gross_rent",
    "median_household_income",
    "population",
    "median_age",
    "poverty_rate",
}

_CENSUS_CACHE_KEY = "census_acs_1_year"
_CENSUS_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


@dataclass(frozen=True)
class CitySuggestion:
    city: str
    latitude: float
    longitude: float


def _normalize_city_state_label(label: str) -> str:
    cleaned = (label or "").strip()
    if not cleaned:
        return ""

    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}"
    return cleaned


def _ensure_map_pins_table() -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS map_pins (
                id         SERIAL            PRIMARY KEY,
                pin_kind   TEXT              NOT NULL DEFAULT 'city',
                city       VARCHAR(255)      NOT NULL,
                latitude   DOUBLE PRECISION  NOT NULL,
                longitude  DOUBLE PRECISION  NOT NULL,
                data       JSONB             NOT NULL DEFAULT '{}',
                created_at BIGINT            NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
            );
            """
        )

        # Backfill/migrate older schemas that created map_pins without pin_kind.
        # Safe to run on every request.
        cur.execute(
            "ALTER TABLE map_pins ADD COLUMN IF NOT EXISTS pin_kind TEXT NOT NULL DEFAULT 'city';"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_map_pins_city ON map_pins (city);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_map_pins_kind_city ON map_pins (pin_kind, city);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_map_pins_latlon ON map_pins (latitude, longitude);"
        )


def suggest_cities(query: str, *, limit: int = 10, kind: str = "city") -> list[CitySuggestion]:
    """Return city suggestions for a typeahead.

    Uses map_pins as the cache. If no DB matches and query looks like
    "City, ST", it will attempt to geocode via Open-Meteo and cache the result.
    """

    query = (query or "").strip()
    if not query:
        return []

    kind = (kind or "city").strip().lower()
    if kind not in _ALLOWED_PIN_KINDS:
        raise ValueError(f"Unsupported pin kind: {kind}")

    limit = max(1, min(int(limit), 20))
    _ensure_map_pins_table()

    like = f"%{query}%"
    with db_cursor() as cur:
        try:
            cur.execute(
                """
                SELECT city, latitude, longitude
                FROM map_pins
                                WHERE pin_kind = %s
                                    AND city ILIKE %s
                ORDER BY similarity(city, %s) DESC, city ASC
                LIMIT %s
                """,
                (kind, like, query, limit),
            )
        except Exception:
            # pg_trgm might not be enabled in some environments.
            cur.execute(
                """
                SELECT city, latitude, longitude
                FROM map_pins
                                WHERE pin_kind = %s
                                    AND city ILIKE %s
                ORDER BY city ASC
                LIMIT %s
                """,
                (kind, like, limit),
            )

        rows = cur.fetchall() or []

    suggestions = [
        CitySuggestion(
            city=_normalize_city_state_label(str(row[0])),
            latitude=float(row[1]),
            longitude=float(row[2]),
        )
        for row in rows
    ]

    if suggestions:
        return suggestions

    if kind == "city" and "," not in query:
        return []

    # On-demand geocode+cache for a single user-entered place.
    location = open_meteo_geocode_city(query)
    if not location:
        return []

    city_label = query
    region_name = query.split(",", maxsplit=1)[0].strip()
    state_name = query.split(",", maxsplit=1)[1].strip() if "," in query else ""
    latitude = float(location["latitude"])
    longitude = float(location["longitude"])

    try:
        with db_cursor() as cur:
            cur.execute(
                "DELETE FROM map_pins WHERE pin_kind = %s AND city = %s",
                (kind, city_label),
            )
            cur.execute(
                """
                INSERT INTO map_pins (pin_kind, city, latitude, longitude, data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    kind,
                    city_label,
                    latitude,
                    longitude,
                    Json(
                        {
                            "source": "open_meteo",
                            "pin_kind": kind,
                            "region_name": region_name,
                            "state_name": state_name,
                            "geocode": {
                                "name": location.get("name"),
                                "admin1": location.get("admin1"),
                                "country_code": location.get("country_code"),
                            },
                        }
                    ),
                ),
            )
    except Exception as exc:
        logger.warning("Failed to cache map_pins geocode for {}: {}", city_label, exc)

    return [CitySuggestion(city=city_label, latitude=latitude, longitude=longitude)]


def get_housing_heatmap_points(
    metric: str,
    *,
    source: str = "zillow",
    kind: str = "city",
    south: float,
    north: float,
    west: float,
    east: float,
    limit: int = 2500,
) -> dict[str, Any]:
    """Return a list of heatmap points within a bounding box."""

    source_key = (source or "zillow").strip().lower()
    if source_key not in _ALLOWED_HEATMAP_SOURCES:
        raise ValueError(f"Unsupported source: {source}")

    metric_key = (metric or "").strip().lower()
    limit = max(1, min(int(limit), 5000))

    kind = (kind or "city").strip().lower()
    if kind not in _ALLOWED_PIN_KINDS:
        raise ValueError(f"Unsupported pin kind: {kind}")

    _ensure_map_pins_table()

    if source_key == "census":
        if metric_key not in _ALLOWED_CENSUS_METRICS:
            raise ValueError(f"Unsupported metric for census: {metric}")

        # Live API calls are expensive; keep the cap smaller.
        limit = max(1, min(limit, 250))
        now = int(time.time())

        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, city, latitude, longitude, data
                FROM map_pins
                WHERE pin_kind = %s
                  AND latitude BETWEEN %s AND %s
                  AND longitude BETWEEN %s AND %s
                ORDER BY city ASC
                LIMIT %s
                """,
                (kind, float(south), float(north), float(west), float(east), limit),
            )
            pin_rows = cur.fetchall() or []

        points: list[dict[str, Any]] = []
        updates: list[tuple[int, dict[str, Any]]] = []
        failed_fetches = 0
        cache_hits = 0

        for pin_id, city, latitude, longitude, data in pin_rows:
            data_obj: dict[str, Any]
            if isinstance(data, dict):
                data_obj = data
            elif isinstance(data, str) and data:
                try:
                    data_obj = json.loads(data)
                except Exception:
                    data_obj = {}
            else:
                data_obj = {}

            city_label = _normalize_city_state_label(str(city))

            cached = data_obj.get(_CENSUS_CACHE_KEY)
            cached_value = None
            if isinstance(cached, dict):
                fetched_at = cached.get("fetched_at")
                if isinstance(fetched_at, int) and now - fetched_at <= _CENSUS_CACHE_TTL_SECONDS:
                    cached_value = cached.get(metric_key)
                    cache_hits += 1

            value_obj = cached_value
            if value_obj in (None, ""):
                fresh = get_census_city_data(city_label) or {}
                if not fresh:
                    failed_fetches += 1
                    continue
                fetched = {
                    "fetched_at": now,
                    "place_name": fresh.get("place_name"),
                    "median_home_value": fresh.get("median_home_value"),
                    "median_gross_rent": fresh.get("median_gross_rent"),
                    "median_household_income": fresh.get("median_household_income"),
                    "population": fresh.get("population"),
                    "median_age": fresh.get("median_age"),
                    "pct_bachelors_or_higher": fresh.get("pct_bachelors_or_higher"),
                    "poverty_rate": fresh.get("poverty_rate"),
                }
                value_obj = fetched.get(metric_key)
                updates.append((int(pin_id), {_CENSUS_CACHE_KEY: fetched}))

            if value_obj is None or value_obj == "":
                continue

            try:
                value = float(value_obj)
            except Exception:
                continue

            points.append(
                {
                    "city": city_label,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "value": value,
                    "as_of": None,
                }
            )

        if updates:
            try:
                with db_cursor() as cur:
                    for pin_id, patch in updates:
                        cur.execute(
                            """
                            UPDATE map_pins
                            SET data = COALESCE(data, '{}'::jsonb) || %s::jsonb
                            WHERE id = %s
                            """,
                            (Json(patch), pin_id),
                        )
            except Exception as exc:
                logger.warning("Failed to cache census ACS data into map_pins: {}", exc)

        if not points and failed_fetches > 0 and cache_hits == 0:
            raise ValueError("Census ACS appears unavailable (non-JSON/failed responses). ")

        return {
            "metric": metric_key,
            "as_of": None,
            "point_count": len(points),
            "points": points,
            "sql": (
                "census_acs_1_year (live API; cached in map_pins.data) "
                f"| cache_hits={cache_hits} | failed_fetches={failed_fetches}"
            ),
        }

    if metric_key not in _ALLOWED_HOUSING_METRICS:
        raise ValueError(f"Unsupported metric: {metric}")

    metrics = _ALLOWED_HOUSING_METRICS[metric_key]

    sql = """
        WITH pins AS (
            SELECT
                city,
                latitude,
                longitude,
                btrim(COALESCE(data->>'region_name', split_part(city, ',', 1))) AS region_name,
                btrim(COALESCE(data->>'state_name', split_part(city, ',', 2))) AS state_name
            FROM map_pins
            WHERE pin_kind = %s
                AND latitude BETWEEN %s AND %s
                AND longitude BETWEEN %s AND %s
            ORDER BY city ASC
            LIMIT %s
        ), latest AS (
            SELECT DISTINCT ON (lower(t.region_name), lower(t.state_name))
                lower(t.region_name) AS region_key,
                lower(t.state_name) AS state_key,
                t.value,
                t.date
            FROM housing_time_series t
            JOIN pins p
                ON lower(t.region_name) = lower(p.region_name)
             AND lower(t.state_name) = lower(p.state_name)
            WHERE t.metric = ANY(%s)
            ORDER BY lower(t.region_name), lower(t.state_name), t.date DESC
        )
        SELECT
            p.city,
            p.latitude,
            p.longitude,
            l.value,
            l.date AS as_of
        FROM pins p
        LEFT JOIN latest l
            ON l.region_key = lower(p.region_name)
         AND l.state_key = lower(p.state_name)
        """

    with db_cursor() as cur:
        cur.execute(
            sql,
            (kind, float(south), float(north), float(west), float(east), limit, metrics),
        )
        rows = cur.fetchall() or []

    points = []
    latest: str | None = None
    for city, latitude, longitude, value, as_of in rows:
        if value is None:
            continue
        as_of_text = None
        if isinstance(as_of, date):
            as_of_text = as_of.isoformat()
        elif as_of is not None:
            as_of_text = str(as_of)
        if as_of_text and (latest is None or as_of_text > latest):
            latest = as_of_text

        points.append(
            {
                "city": str(city),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "value": float(value),
                "as_of": as_of_text,
            }
        )

    return {
        "metric": metric_key,
        "as_of": latest,
        "point_count": len(points),
        "points": points,
        "sql": sql.strip(),
    }
