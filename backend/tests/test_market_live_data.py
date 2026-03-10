from __future__ import annotations

from typing import Literal

import pytest
from backend.app.agents.market.agent import MarketAgent
from backend.app.services import live_apis


def test_finnhub_search_ticker_normalizes_company_name(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_finnhub_get(path: str, **params: str) -> dict:
        assert path == "/search"
        query = params["q"]
        calls.append(query)
        if query == "Apple Inc":
            return {
                "count": 1,
                "result": [
                    {
                        "description": "Apple Inc",
                        "displaySymbol": "AAPL",
                        "symbol": "AAPL",
                        "type": "Common Stock",
                    }
                ],
            }
        raise AssertionError(f"unexpected Finnhub search query: {query}")

    live_apis.finnhub_search_ticker.cache_clear()
    monkeypatch.setattr(live_apis, "_finnhub_get", fake_finnhub_get)

    assert live_apis.finnhub_search_ticker("Apple Inc.") == "AAPL"
    assert calls == ["Apple Inc"]


def test_get_finnhub_company_data_skips_analyst_call_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"analyst": 0}

    monkeypatch.setattr(live_apis, "finnhub_search_ticker", lambda company: "AAPL")
    monkeypatch.setattr(
        live_apis,
        "finnhub_quote",
        lambda symbol: {"c": 200.0, "d": 1.5, "dp": 0.75},
    )
    monkeypatch.setattr(
        live_apis,
        "finnhub_company_profile",
        lambda symbol: {
            "name": "Apple Inc",
            "finnhubIndustry": "Technology",
            "exchange": "NASDAQ",
            "marketCapitalization": 3000.0,
        },
    )

    def fake_analyst(symbol: str) -> list[dict]:
        calls["analyst"] += 1
        return [{"strongBuy": 10, "buy": 5, "hold": 2, "sell": 0, "strongSell": 0}]

    monkeypatch.setattr(live_apis, "finnhub_analyst_recommendations", fake_analyst)

    data = live_apis.get_finnhub_company_data("Apple")

    assert data["symbol"] == "AAPL"
    assert data["current_price"] == 200.0
    assert data["analyst_recommendations"] == []
    assert calls["analyst"] == 0


class _FakeCursor:
    def __init__(self) -> None:
        self.description = [
            ("ticker", None, None, None, None, None, None),
            ("name", None, None, None, None, None, None),
            ("sector", None, None, None, None, None, None),
            ("industry", None, None, None, None, None, None),
            ("recommendation", None, None, None, None, None, None),
            ("strong_buy_count", None, None, None, None, None, None),
            ("buy_count", None, None, None, None, None, None),
            ("hold_count", None, None, None, None, None, None),
            ("sell_count", None, None, None, None, None, None),
            ("strong_sell_count", None, None, None, None, None, None),
            ("insider_pct", None, None, None, None, None, None),
            ("institutional_pct", None, None, None, None, None, None),
        ]
        self.sql = ""
        self.params: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [
            (
                "MSFT",
                "Microsoft Corp",
                "Technology",
                "Technology",
                "Buy",
                24,
                36,
                4,
                0,
                0,
                0.0,
                0.0,
            )
        ]


class _FakeDBContext:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeCursor:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


def test_market_agent_screen_companies_builds_structured_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MarketAgent()
    cursor = _FakeCursor()

    monkeypatch.setattr(
        "backend.app.agents.market.agent.ensure_stock_data_table",
        lambda: None,
    )
    monkeypatch.setattr(
        "backend.app.agents.market.agent.db_cursor",
        lambda: _FakeDBContext(cursor),
    )

    result = agent._execute_tool(
        "screen_companies",
        {"sector": "Technology", "analyst_signal": "strong_buy", "limit": 5},
    )

    assert "FROM stock_data" in result["sql"]
    assert "metadata->>'sector' ILIKE %s" in cursor.sql
    assert "strong_buy_count" in cursor.sql
    assert result["row_count"] == 1
    assert result["rows"][0]["ticker"] == "MSFT"


def test_market_agent_analyst_tool_returns_consensus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MarketAgent()

    monkeypatch.setattr(
        "backend.app.agents.market.agent.finnhub_analyst_recommendations",
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

    result = agent._execute_tool("get_analyst_recommendations", {"symbol": "AAPL"})

    assert result["symbol"] == "AAPL"
    assert result["consensus"] == "Buy"
    assert result["available"] is True
