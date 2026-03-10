"""Helpers for populating the stock_data snapshot table from live APIs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from loguru import logger
from psycopg2.extras import Json

from backend.app.services.bedrock import embed_text
from backend.app.services.live_apis import (
    finnhub_analyst_recommendations,
    finnhub_company_profile,
)
from backend.database.connect import db_cursor

DEFAULT_STARTER_TICKERS: list[str] = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "AVGO",
    "CRM",
    "ADBE",
    "NOW",
    "QCOM",
    "PANW",
    "PLTR",
    "JPM",
    "WMT",
    "XOM",
    "LLY",
    "UNH",
]

_RECOMMENDATION_ORDER = [
    ("strongBuy", "Strong Buy"),
    ("buy", "Buy"),
    ("hold", "Hold"),
    ("sell", "Sell"),
    ("strongSell", "Strong Sell"),
]


@dataclass
class StockSnapshot:
    ticker: str
    metadata: dict
    embedding: list[float] | None = None


def normalize_recommendation(latest: dict | None) -> str | None:
    """Convert Finnhub recommendation counts into one consensus label."""
    if not latest:
        return None

    best_count = -1
    best_label: str | None = None
    for key, label in _RECOMMENDATION_ORDER:
        count = int(latest.get(key, 0) or 0)
        if count > best_count:
            best_count = count
            best_label = label

    return best_label if best_count > 0 else None


def snapshot_text(metadata: dict) -> str:
    """Stable text representation for optional embeddings."""
    lines = [
        f"Ticker: {metadata.get('ticker', '')}",
        f"Name: {metadata.get('name', '')}",
        f"Sector: {metadata.get('sector', '')}",
        f"Industry: {metadata.get('industry', '')}",
        f"Recommendation: {metadata.get('recommendation', '')}",
        f"Recommendation Period: {metadata.get('recommendation_period', '')}",
        f"Strong Buy Count: {metadata.get('strong_buy_count', '')}",
        f"Buy Count: {metadata.get('buy_count', '')}",
        f"Hold Count: {metadata.get('hold_count', '')}",
        f"Sell Count: {metadata.get('sell_count', '')}",
        f"Strong Sell Count: {metadata.get('strong_sell_count', '')}",
        f"Exchange: {metadata.get('exchange', '')}",
        f"Country: {metadata.get('country', '')}",
        f"Market Cap (B): {metadata.get('market_cap_B', '')}",
    ]
    return "\n".join(lines)


def build_snapshot(symbol: str, *, with_embeddings: bool = False) -> StockSnapshot | None:
    """Fetch live profile + recommendation data and shape one stock snapshot row."""
    profile = finnhub_company_profile(symbol)
    if not profile or not profile.get("name"):
        logger.warning("Skipping ticker={} because profile data is missing", symbol)
        return None

    recs = finnhub_analyst_recommendations(symbol)
    latest = recs[0] if recs else {}
    market_cap = profile.get("marketCapitalization")
    industry = profile.get("finnhubIndustry")

    metadata = {
        "ticker": symbol,
        "name": profile.get("name"),
        "sector": industry,
        "industry": industry,
        "recommendation": normalize_recommendation(latest),
        "recommendation_period": latest.get("period"),
        "strong_buy_count": latest.get("strongBuy"),
        "buy_count": latest.get("buy"),
        "hold_count": latest.get("hold"),
        "sell_count": latest.get("sell"),
        "strong_sell_count": latest.get("strongSell"),
        "exchange": profile.get("exchange"),
        "country": profile.get("country"),
        "market_cap_B": round(market_cap / 1000, 2) if market_cap else None,
        # Finnhub ownership endpoints are not available on the current plan.
        "insider_ownership": None,
        "institutional_ownership": None,
        "ownership_data_status": "unavailable_on_current_finnhub_plan",
        "source": "finnhub",
    }

    embedding = embed_text(snapshot_text(metadata)) if with_embeddings else None
    return StockSnapshot(ticker=symbol, metadata=metadata, embedding=embedding)


def ensure_stock_data_table() -> None:
    """Normalize stock_data so sync inserts work with the current app schema."""
    with db_cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_data (
                id SERIAL PRIMARY KEY,
                embedding vector(1536),
                metadata JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                stored_messages_id INT REFERENCES stored_messages(id) ON DELETE SET NULL
            );
            """
        )
        cur.execute("ALTER TABLE stock_data ADD COLUMN IF NOT EXISTS embedding vector(1536);")
        cur.execute(
            "ALTER TABLE stock_data ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';"
        )
        cur.execute(
            "ALTER TABLE stock_data "
            "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;"
        )
        cur.execute(
            "ALTER TABLE stock_data "
            "ADD COLUMN IF NOT EXISTS stored_messages_id INT "
            "REFERENCES stored_messages(id) ON DELETE SET NULL;"
        )
        cur.execute("CREATE SEQUENCE IF NOT EXISTS stock_data_id_seq;")
        cur.execute(
            """
            SELECT setval(
                'stock_data_id_seq',
                COALESCE((SELECT MAX(id) FROM stock_data), 0) + 1,
                false
            );
            """
        )
        cur.execute("ALTER SEQUENCE stock_data_id_seq OWNED BY stock_data.id;")
        cur.execute(
            "ALTER TABLE stock_data ALTER COLUMN id SET DEFAULT nextval('stock_data_id_seq');"
        )
        cur.execute("ALTER TABLE stock_data ALTER COLUMN embedding DROP NOT NULL;")
        cur.execute("ALTER TABLE stock_data ALTER COLUMN metadata SET DEFAULT '{}';")
        cur.execute("ALTER TABLE stock_data ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;")
        cur.execute("ALTER TABLE stock_data ALTER COLUMN stored_messages_id DROP NOT NULL;")
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stock_data_name_trgm
            ON stock_data USING gin ((metadata->>'name') gin_trgm_ops);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stock_data_sector
            ON stock_data ((metadata->>'sector'));
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stock_data_recommendation
            ON stock_data ((metadata->>'recommendation'));
            """
        )


def persist_snapshots(snapshots: list[StockSnapshot], *, truncate: bool = False) -> int:
    """Write snapshots into stock_data."""
    if not snapshots:
        return 0

    ensure_stock_data_table()
    with db_cursor() as cur:
        if truncate:
            cur.execute("TRUNCATE TABLE stock_data RESTART IDENTITY;")
        for snapshot in snapshots:
            cur.execute(
                "DELETE FROM stock_data WHERE metadata->>'ticker' = %s;",
                (snapshot.ticker,),
            )
            cur.execute(
                """
                INSERT INTO stock_data (embedding, metadata, stored_messages_id)
                VALUES (%s, %s, NULL)
                """,
                (
                    json.dumps(snapshot.embedding) if snapshot.embedding is not None else None,
                    Json(snapshot.metadata),
                ),
            )
    return len(snapshots)


def sync_stock_data(
    tickers: list[str],
    *,
    with_embeddings: bool = False,
    truncate: bool = False,
    delay_seconds: float = 1.0,
) -> int:
    """Fetch and persist stock snapshots for the provided ticker list."""
    snapshots: list[StockSnapshot] = []
    unique_tickers = [ticker.strip().upper() for ticker in tickers if ticker.strip()]
    unique_tickers = [
        ticker for i, ticker in enumerate(unique_tickers) if ticker not in unique_tickers[:i]
    ]

    for index, ticker in enumerate(unique_tickers):
        try:
            snapshot = build_snapshot(ticker, with_embeddings=with_embeddings)
            if snapshot is not None:
                snapshots.append(snapshot)
                logger.info("Prepared stock snapshot for {}", ticker)
        except Exception as exc:
            logger.warning("Stock snapshot fetch failed for {}: {}", ticker, exc)

        if delay_seconds > 0 and index < len(unique_tickers) - 1:
            time.sleep(delay_seconds)

    written = persist_snapshots(snapshots, truncate=truncate)
    logger.info("Persisted {} stock snapshots", written)
    return written
