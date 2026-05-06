"""Import a Zillow Research CSV into `housing_time_series`.

Zillow "Research" datasets are typically monthly and published as CSV exports.
This repo stores them in an EAV/long format table (`housing_time_series`).

This script makes updates "live-ish" by letting you automate the ingestion
(e.g., via cron/systemd/GitHub Actions) whenever a fresh CSV is available.

Examples:
  uv --project backend run python -m backend.scripts.sync_zillow_data \
    --input ./data/zhvi_city.csv \
    --metric home_values_zhvi

  uv --project backend run python -m backend.scripts.sync_zillow_data \
    --url "https://example.com/ZHVI.csv" \
    --metric home_values_zhvi \
    --truncate-metric
"""

from __future__ import annotations

import argparse
import io
from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx
import pandas as pd
from loguru import logger
from psycopg2.extras import execute_values

from backend.database.connect import db_cursor

_META_CANDIDATES = [
    "RegionID",
    "RegionName",
    "RegionType",
    "StateName",
    "SizeRank",
]


def _download_csv(url: str) -> pd.DataFrame:
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content))


def _detect_date_columns(columns: Iterable[str]) -> list[str]:
    parsed = pd.to_datetime(list(columns), errors="coerce")
    return [col for col, parsed_dt in zip(columns, parsed, strict=False) if not pd.isna(parsed_dt)]


def _to_long(df: pd.DataFrame, *, metric: str) -> pd.DataFrame:
    if "RegionID" not in df.columns or "RegionName" not in df.columns:
        raise ValueError("CSV must include at least RegionID and RegionName columns")

    meta_cols = [col for col in _META_CANDIDATES if col in df.columns]
    date_cols = _detect_date_columns(df.columns)
    if not date_cols:
        raise ValueError(
            "No date columns detected. Expected wide format with date-like column names "
            "(e.g. '2024-01-31', '2015-06-30')."
        )

    df_long = df.melt(
        id_vars=meta_cols,
        value_vars=date_cols,
        var_name="date",
        value_name="value",
    )

    df_long["date"] = pd.to_datetime(df_long["date"], errors="coerce").dt.date
    df_long["metric"] = metric

    df_long = df_long.dropna(subset=["date", "value", "RegionID", "RegionName"])

    # Normalize dtypes
    df_long["RegionID"] = pd.to_numeric(df_long["RegionID"], errors="coerce").astype("Int64")
    df_long = df_long.dropna(subset=["RegionID"]).copy()

    # Keep only the columns we load into Postgres.
    for optional in ("RegionType", "StateName"):
        if optional not in df_long.columns:
            df_long[optional] = None

    return df_long[["RegionID", "RegionName", "RegionType", "StateName", "metric", "date", "value"]]


def _chunked(rows: list[tuple[Any, ...]], size: int) -> Iterable[list[tuple[Any, ...]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def sync_zillow_csv(
    *,
    df: pd.DataFrame,
    metric: str,
    truncate_metric: bool,
    dry_run: bool,
    batch_size: int,
) -> dict[str, int]:
    long_df = _to_long(df, metric=metric)

    rows: list[tuple[Any, ...]] = [
        (
            int(row.RegionID),
            str(row.RegionName),
            str(row.RegionType) if row.RegionType is not None else None,
            str(row.StateName) if row.StateName is not None else None,
            str(row.metric),
            row.date if isinstance(row.date, date) else None,
            float(row.value) if row.value is not None else None,
        )
        for row in long_df.itertuples(index=False)
    ]

    logger.info(
        "Prepared {} rows for metric={} (dry_run={}, truncate_metric={})",
        len(rows),
        metric,
        dry_run,
        truncate_metric,
    )

    if dry_run:
        return {"rows_prepared": len(rows), "rows_upserted": 0, "rows_deleted": 0}

    deleted = 0
    upserted = 0

    with db_cursor() as cur:
        if truncate_metric:
            cur.execute("DELETE FROM housing_time_series WHERE metric = %s", (metric,))
            deleted = int(cur.rowcount or 0)
            logger.info("Deleted {} existing rows for metric={}", deleted, metric)

        sql = """
            INSERT INTO housing_time_series
                ("RegionID", "RegionName", "RegionType", "StateName", metric, date, value)
            VALUES %s
            ON CONFLICT ("RegionID", metric, date)
            DO UPDATE SET
                value = EXCLUDED.value,
                "RegionName" = EXCLUDED."RegionName",
                "RegionType" = EXCLUDED."RegionType",
                "StateName" = EXCLUDED."StateName"
        """

        for batch in _chunked(rows, max(1, int(batch_size))):
            execute_values(cur, sql, batch, page_size=len(batch))
            upserted += len(batch)

    return {"rows_prepared": len(rows), "rows_upserted": upserted, "rows_deleted": deleted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync a Zillow Research CSV into Postgres")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Path to a local Zillow CSV")
    src.add_argument("--url", help="URL to a Zillow CSV")

    parser.add_argument(
        "--metric",
        required=True,
        help=(
            "Metric name to store in housing_time_series (e.g. home_values_zhvi, rent_zori, "
            "for_sale_inventory)."
        ),
    )
    parser.add_argument(
        "--truncate-metric",
        action="store_true",
        help="Delete existing rows for this metric before inserting",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse CSV but do not write")
    parser.add_argument("--batch-size", type=int, default=10_000)

    args = parser.parse_args()

    if args.url:
        df = _download_csv(args.url)
    else:
        df = pd.read_csv(args.input)

    result = sync_zillow_csv(
        df=df,
        metric=str(args.metric),
        truncate_metric=bool(args.truncate_metric),
        dry_run=bool(args.dry_run),
        batch_size=int(args.batch_size),
    )

    logger.info("Sync complete: {}", result)


if __name__ == "__main__":
    main()
