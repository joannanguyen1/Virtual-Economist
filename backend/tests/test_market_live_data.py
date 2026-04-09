from __future__ import annotations

from typing import Any, Literal

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


def test_finnhub_search_ticker_handles_merged_market_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_finnhub_get(path: str, **params: str) -> dict:
        assert path == "/search"
        query = params["q"]
        calls.append(query)
        if query == "apple":
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
        return {"count": 0, "result": []}

    live_apis.finnhub_search_ticker.cache_clear()
    monkeypatch.setattr(live_apis, "_finnhub_get", fake_finnhub_get)

    assert live_apis.finnhub_search_ticker("appleshigh") == "AAPL"
    assert "apple" in calls


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
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def __enter__(self) -> Any:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


class _FakeOHLCVCursor:
    def __init__(self) -> None:
        self.description = [
            ("ticker", None, None, None, None, None, None),
            ("trade_date", None, None, None, None, None, None),
            ("open", None, None, None, None, None, None),
            ("high", None, None, None, None, None, None),
            ("low", None, None, None, None, None, None),
            ("close", None, None, None, None, None, None),
            ("volume", None, None, None, None, None, None),
            ("dividends", None, None, None, None, None, None),
            ("stock_splits", None, None, None, None, None, None),
        ]
        self.sql = ""
        self.params: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [
            ("AAPL", "2026-03-03", 100.0, 102.0, 99.0, 100.0, 1000000, 0.0, 1.0),
            ("AAPL", "2026-03-04", 101.0, 106.0, 100.0, 105.0, 1100000, 0.0, 1.0),
            ("AAPL", "2026-03-05", 105.0, 111.0, 104.0, 110.0, 1200000, 0.5, 1.0),
        ]


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


def test_market_agent_historical_ohlcv_tool_queries_stock_ohlcv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MarketAgent()
    cursor = _FakeOHLCVCursor()

    monkeypatch.setattr(
        agent,
        "_stock_ohlcv_columns",
        lambda: {
            "ticker": "ticker",
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "dividends": "dividends",
            "stock_splits": "stock_splits",
        },
    )
    monkeypatch.setattr(
        "backend.app.agents.market.agent.db_cursor",
        lambda: _FakeDBContext(cursor),
    )

    result = agent._execute_tool(
        "get_historical_ohlcv",
        {"symbol": "AAPL", "lookback_days": 3},
    )

    assert "FROM stock_ohlcv" in result["sql"]
    assert result["row_count"] == 3
    assert result["summary"]["latest_close"] == 110.0
    assert result["summary"]["period_return_pct"] == 10.0


def test_market_agent_performance_tool_calculates_risk_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MarketAgent()

    monkeypatch.setattr(
        agent,
        "_fetch_ohlcv_rows",
        lambda symbol, **kwargs: {
            "sql": "SELECT ... FROM stock_ohlcv",
            "rows": [
                {
                    "ticker": symbol,
                    "trade_date": "2026-03-01",
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 1000000,
                    "dividends": 0.0,
                    "stock_splits": 1.0,
                },
                {
                    "ticker": symbol,
                    "trade_date": "2026-03-02",
                    "open": 100.0,
                    "high": 106.0,
                    "low": 99.5,
                    "close": 105.0,
                    "volume": 1100000,
                    "dividends": 0.0,
                    "stock_splits": 1.0,
                },
                {
                    "ticker": symbol,
                    "trade_date": "2026-03-03",
                    "open": 105.0,
                    "high": 107.0,
                    "low": 101.0,
                    "close": 102.0,
                    "volume": 900000,
                    "dividends": 0.0,
                    "stock_splits": 1.0,
                },
                {
                    "ticker": symbol,
                    "trade_date": "2026-03-04",
                    "open": 102.0,
                    "high": 109.0,
                    "low": 101.5,
                    "close": 108.0,
                    "volume": 950000,
                    "dividends": 0.25,
                    "stock_splits": 1.0,
                },
            ],
        },
    )

    result = agent._execute_tool(
        "analyze_stock_performance",
        {"symbols": ["AAPL"], "lookback_days": 30, "risk_free_rate_pct": 4.0},
    )

    metrics = result["metrics"][0]
    assert metrics["found"] is True
    assert metrics["metrics_available"] is True
    assert metrics["sharpe_ratio"] is not None
    assert metrics["total_return_pct"] > 0
    assert metrics["max_drawdown_pct"] <= 0
