"""Seed `map_pins` from housing dataset cities using Open-Meteo geocoding.

Usage:
  uv --project backend run python -m backend.scripts.seed_map_pins --limit 500

Notes:
- Stores display labels as "City, ST".
- Caches coordinates in Postgres so dashboard heatmaps can join city metrics → lat/lon.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from loguru import logger
from psycopg2.extras import Json

from backend.app.services import live_apis
from backend.app.services.live_apis import open_meteo_geocode_city
from backend.database.connect import db_cursor


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


def _infer_state_abbr(state_name: str | None) -> str | None:
    if not state_name:
        return None
    cleaned = str(state_name).strip()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()

    fips = live_apis._STATE_FIPS.get(cleaned.title())
    if not fips:
        return None

    for abbr, abbr_fips in live_apis._STATE_ABBR_TO_FIPS.items():
        if abbr_fips == fips:
            return abbr
    return None


def _distinct_housing_cities(*, limit: int | None = None) -> list[tuple[str, str | None]]:
    sql = """
    SELECT DISTINCT region_name, state_name
    FROM housing_time_series
    WHERE region_name IS NOT NULL
      AND region_name <> ''
    ORDER BY region_name ASC
    """
    if limit is not None:
        sql += " LIMIT %s"

    with db_cursor() as cur:
        if limit is None:
            cur.execute(sql)
        else:
            cur.execute(sql, (int(limit),))
        rows = cur.fetchall() or []

    results: list[tuple[str, str | None]] = []
    for region_name, state_name in rows:
        results.append((str(region_name), str(state_name) if state_name else None))
    return results


def _normalize_city_label(region_name: str, state_abbr: str) -> str:
    cleaned_region = (region_name or "").strip()
    cleaned_abbr = (state_abbr or "").strip().upper()

    if not cleaned_region:
        return cleaned_abbr

    if "," not in cleaned_region:
        return f"{cleaned_region}, {cleaned_abbr}"

    before, after = cleaned_region.split(",", maxsplit=1)
    after_clean = after.strip()
    after_token = "".join(ch for ch in after_clean if ch.isalpha()).upper()

    # If the region already includes a state suffix ("City, PA" or "City, D.C."),
    # drop it so we don't end up with "City, PA, PA".
    if after_token == cleaned_abbr or after_clean.title() in live_apis._STATE_FIPS:
        cleaned_region = before.strip()

    return f"{cleaned_region}, {cleaned_abbr}"


def seed_map_pins(
    *,
    limit: int | None = None,
    delay_seconds: float = 0.15,
    dry_run: bool = False,
    truncate: bool = False,
) -> int:
    _ensure_map_pins_table()
    pin_kind = "city"

    if truncate and not dry_run:
        with db_cursor() as cur:
            cur.execute("TRUNCATE TABLE map_pins RESTART IDENTITY")

    cities = _distinct_housing_cities(limit=limit)
    logger.info("Seeding map_pins for {} housing regions", len(cities))

    written = 0
    for index, (region_name, state_name) in enumerate(cities, start=1):
        state_abbr = _infer_state_abbr(state_name)
        if not state_abbr:
            continue

        city_label = _normalize_city_label(region_name, state_abbr)
        location = open_meteo_geocode_city(city_label)
        if not location:
            continue

        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        data: dict[str, Any] = {
            "source": "open_meteo",
            "region_name": region_name,
            "state_name": state_name,
            "state_abbr": state_abbr,
            "geocode": {
                "name": location.get("name"),
                "admin1": location.get("admin1"),
                "country_code": location.get("country_code"),
            },
        }

        if dry_run:
            written += 1
        else:
            with db_cursor() as cur:
                cur.execute(
                    "DELETE FROM map_pins WHERE pin_kind = %s AND city = %s",
                    (pin_kind, city_label),
                )
                cur.execute(
                    """
                    INSERT INTO map_pins (pin_kind, city, latitude, longitude, data)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (pin_kind, city_label, latitude, longitude, Json(data)),
                )
            written += 1

        if delay_seconds > 0 and index < len(cities):
            time.sleep(delay_seconds)

    logger.info("Seeded {} map_pins rows", written)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.15)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--truncate", action="store_true")
    args = parser.parse_args()

    seed_map_pins(
        limit=args.limit,
        delay_seconds=args.delay_seconds,
        dry_run=args.dry_run,
        truncate=args.truncate,
    )


if __name__ == "__main__":
    main()
