"""Favorites service.

CRUD layer for per-user favorite cities.

We intentionally keep schema management lightweight ("ensure" on-demand),
similar to `backend.app.services.history`, because this repo doesn't use a
formal migration tool in all environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from loguru import logger

from backend.database.connect import db_cursor


@lru_cache(maxsize=1)
def ensure_favorites_schema() -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_cities (
                id         SERIAL            PRIMARY KEY,
                user_id    INT               NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                city       VARCHAR(255)      NOT NULL,
                latitude   DOUBLE PRECISION  NOT NULL,
                longitude  DOUBLE PRECISION  NOT NULL,
                created_at BIGINT            NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,

                UNIQUE (user_id, city)
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorite_cities_user " "ON favorite_cities (user_id);"
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_favorite_cities_user_city
            ON favorite_cities (user_id, city);
            """
        )

    logger.debug("favorites | ensured schema compatibility")


@dataclass(frozen=True)
class FavoriteCity:
    city: str
    latitude: float
    longitude: float


def list_favorite_cities(user_id: int) -> list[FavoriteCity]:
    ensure_favorites_schema()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT city, latitude, longitude
            FROM favorite_cities
            WHERE user_id = %s
            ORDER BY city ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []

    return [
        FavoriteCity(
            city=str(row[0]),
            latitude=float(row[1]),
            longitude=float(row[2]),
        )
        for row in rows
    ]


def upsert_favorite_city(
    user_id: int,
    city: str,
    latitude: float,
    longitude: float,
) -> FavoriteCity:
    ensure_favorites_schema()

    city_clean = (city or "").strip()
    if not city_clean:
        raise ValueError("city is required")

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO favorite_cities (user_id, city, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, city)
            DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
            RETURNING city, latitude, longitude
            """,
            (user_id, city_clean, float(latitude), float(longitude)),
        )
        row = cur.fetchone()

    return FavoriteCity(
        city=str(row[0]),
        latitude=float(row[1]),
        longitude=float(row[2]),
    )


def delete_favorite_city(user_id: int, city: str) -> bool:
    ensure_favorites_schema()

    city_clean = (city or "").strip()
    if not city_clean:
        raise ValueError("city is required")

    with db_cursor() as cur:
        cur.execute(
            """
            DELETE FROM favorite_cities
            WHERE user_id = %s AND city = %s
            """,
            (user_id, city_clean),
        )
        deleted = cur.rowcount

    return bool(deleted)
