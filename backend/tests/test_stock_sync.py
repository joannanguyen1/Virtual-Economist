from __future__ import annotations

from backend.app.services import stock_sync


def test_normalize_recommendation_prefers_highest_bucket() -> None:
    latest = {
        "strongBuy": 9,
        "buy": 6,
        "hold": 2,
        "sell": 0,
        "strongSell": 0,
    }

    assert stock_sync.normalize_recommendation(latest) == "Strong Buy"


def test_normalize_recommendation_returns_none_for_empty_counts() -> None:
    assert stock_sync.normalize_recommendation({}) is None
    assert stock_sync.normalize_recommendation(None) is None


def test_build_snapshot_shapes_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        stock_sync,
        "finnhub_company_profile",
        lambda symbol: {
            "name": "Apple Inc",
            "finnhubIndustry": "Technology",
            "exchange": "NASDAQ",
            "country": "US",
            "marketCapitalization": 3821353.67,
        },
    )
    monkeypatch.setattr(
        stock_sync,
        "finnhub_analyst_recommendations",
        lambda symbol: [
            {
                "period": "2026-03-01",
                "strongBuy": 14,
                "buy": 22,
                "hold": 16,
                "sell": 2,
                "strongSell": 0,
            }
        ],
    )

    snapshot = stock_sync.build_snapshot("AAPL")

    assert snapshot is not None
    assert snapshot.ticker == "AAPL"
    assert snapshot.metadata["name"] == "Apple Inc"
    assert snapshot.metadata["sector"] == "Technology"
    assert snapshot.metadata["industry"] == "Technology"
    assert snapshot.metadata["recommendation"] == "Buy"
    assert snapshot.metadata["ownership_data_status"] == "unavailable_on_current_finnhub_plan"
