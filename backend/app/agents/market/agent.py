"""Stock & Market Agent built on a Bedrock tool-use loop."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.agents.market.prompts import SYSTEM_PROMPT
from backend.app.services.live_apis import (
    finnhub_analyst_recommendations,
    finnhub_company_profile,
    finnhub_quote,
    finnhub_search_ticker,
    get_fred_macro_snapshot,
)
from backend.app.services.stock_sync import ensure_stock_data_table, normalize_recommendation
from backend.database.connect import db_cursor

_MARKET_FRED_SERIES = {
    "unemployment_rate": ("UNRATE", "Unemployment Rate"),
    "fed_funds_rate": ("FEDFUNDS", "Federal Funds Rate"),
    "inflation_cpi": ("CPIAUCSL", "Consumer Price Index"),
    "gdp": ("GDP", "Gross Domestic Product"),
    "mortgage_rate": ("MORTGAGE30US", "30-Year Mortgage Rate"),
}
_ANALYST_SIGNAL_FIELDS = {
    "strong_buy": "strong_buy_count",
    "buy": "buy_count",
    "hold": "hold_count",
    "sell": "sell_count",
    "strong_sell": "strong_sell_count",
}


class MarketAgent(BaseAgent):
    """Tool-use market agent for company, stock, and macro questions."""

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "toolSpec": {
                    "name": "search_ticker",
                    "description": (
                        "Resolve a company name to a ticker symbol. Use this first when "
                        "the user gives a company name instead of a ticker."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"company": {"type": "string"}},
                            "required": ["company"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_stock_quote",
                    "description": "Fetch a live stock quote for a ticker symbol from Finnhub.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"symbol": {"type": "string"}},
                            "required": ["symbol"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_company_profile",
                    "description": (
                        "Fetch company profile details for a ticker symbol from Finnhub."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"symbol": {"type": "string"}},
                            "required": ["symbol"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_analyst_recommendations",
                    "description": (
                        "Fetch the latest analyst recommendation counts for a ticker "
                        "symbol from Finnhub."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"symbol": {"type": "string"}},
                            "required": ["symbol"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_economic_indicators",
                    "description": (
                        "Fetch market-relevant FRED indicators. Allowed values are: "
                        "unemployment_rate, fed_funds_rate, inflation_cpi, gdp, mortgage_rate."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "indicators": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": list(_MARKET_FRED_SERIES),
                                    },
                                }
                            },
                            "required": ["indicators"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "screen_companies",
                    "description": (
                        "Screen the stock_data snapshot table for sector, analyst, or "
                        "ownership questions. Use analyst_signal for questions like "
                        "'strong buy ratings'. Use consensus_label for exact consensus "
                        "filters. Ownership thresholds are decimal fractions (0.10 = 10%)."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "sector": {"type": "string"},
                                "industry": {"type": "string"},
                                "analyst_signal": {
                                    "type": "string",
                                    "enum": list(_ANALYST_SIGNAL_FIELDS),
                                },
                                "consensus_label": {
                                    "type": "string",
                                    "enum": [
                                        "Strong Buy",
                                        "Buy",
                                        "Hold",
                                        "Sell",
                                        "Strong Sell",
                                    ],
                                },
                                "min_insider_ownership": {"type": "number"},
                                "min_institutional_ownership": {"type": "number"},
                                "limit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                        }
                    },
                }
            },
        ]

    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "search_ticker": self._tool_search_ticker,
            "get_stock_quote": self._tool_get_stock_quote,
            "get_company_profile": self._tool_get_company_profile,
            "get_analyst_recommendations": self._tool_get_analyst_recommendations,
            "get_economic_indicators": self._tool_get_economic_indicators,
            "screen_companies": self._tool_screen_companies,
        }
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown market tool: {name}")
        return handler(input_data)

    def _error_answer(self) -> str:
        return (
            "I'm sorry, I ran into an issue retrieving market data. "
            "Please try rephrasing your question or check back later.\n\n"
            "⚠️ This is informational only and not investment advice."
        )

    def _tool_search_ticker(self, input_data: dict[str, Any]) -> dict[str, Any]:
        company = str(input_data.get("company", "")).strip()
        if not company:
            raise ValueError("company is required")

        symbol = finnhub_search_ticker(company)
        return {
            "tool": "search_ticker",
            "company": company,
            "found": bool(symbol),
            "symbol": symbol or None,
        }

    def _tool_get_stock_quote(self, input_data: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required_symbol(input_data)
        quote = finnhub_quote(symbol)
        return {
            "tool": "get_stock_quote",
            "symbol": symbol,
            "source": "finnhub",
            "current_price": quote.get("c"),
            "change": quote.get("d"),
            "change_pct": quote.get("dp"),
            "day_high": quote.get("h"),
            "day_low": quote.get("l"),
            "open": quote.get("o"),
            "previous_close": quote.get("pc"),
            "quote_timestamp": quote.get("t"),
        }

    def _tool_get_company_profile(self, input_data: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required_symbol(input_data)
        profile = finnhub_company_profile(symbol)
        market_cap = profile.get("marketCapitalization")
        return {
            "tool": "get_company_profile",
            "symbol": symbol,
            "source": "finnhub",
            "name": profile.get("name"),
            "sector": profile.get("finnhubIndustry"),
            "industry": profile.get("finnhubIndustry"),
            "exchange": profile.get("exchange"),
            "country": profile.get("country"),
            "currency": profile.get("currency"),
            "ipo": profile.get("ipo"),
            "market_cap_B": round(market_cap / 1000, 2) if market_cap else None,
            "weburl": profile.get("weburl"),
        }

    def _tool_get_analyst_recommendations(self, input_data: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required_symbol(input_data)
        recs = finnhub_analyst_recommendations(symbol)
        latest = recs[0] if recs else {}
        return {
            "tool": "get_analyst_recommendations",
            "symbol": symbol,
            "source": "finnhub",
            "available": bool(recs),
            "consensus": normalize_recommendation(latest),
            "latest_period": latest.get("period"),
            "strong_buy": latest.get("strongBuy"),
            "buy": latest.get("buy"),
            "hold": latest.get("hold"),
            "sell": latest.get("sell"),
            "strong_sell": latest.get("strongSell"),
            "history": recs[:3],
        }

    def _tool_get_economic_indicators(self, input_data: dict[str, Any]) -> dict[str, Any]:
        requested = input_data.get("indicators") or []
        indicators = [str(item) for item in requested if str(item) in _MARKET_FRED_SERIES]
        if not indicators:
            raise ValueError("At least one valid indicator is required")

        series_ids = [_MARKET_FRED_SERIES[item][0] for item in indicators]
        snapshot = get_fred_macro_snapshot(series_ids)
        result: dict[str, Any] = {
            "tool": "get_economic_indicators",
            "source": "fred",
            "requested_indicators": indicators,
            "series": {},
        }
        for indicator in indicators:
            series_id, label = _MARKET_FRED_SERIES[indicator]
            if snapshot.get(series_id):
                result["series"][indicator] = {
                    "label": label,
                    "series_id": series_id,
                    **snapshot[series_id],
                }
        return result

    def _tool_screen_companies(self, input_data: dict[str, Any]) -> dict[str, Any]:
        ensure_stock_data_table()

        sector = self._optional_text(input_data.get("sector"))
        industry = self._optional_text(input_data.get("industry"))
        analyst_signal = self._optional_text(input_data.get("analyst_signal"))
        consensus_label = self._optional_text(input_data.get("consensus_label"))
        min_insider = self._normalize_ownership_threshold(input_data.get("min_insider_ownership"))
        min_institutional = self._normalize_ownership_threshold(
            input_data.get("min_institutional_ownership")
        )
        limit = self._bounded_limit(input_data.get("limit"), default=10, maximum=50)

        if not any(
            value is not None
            for value in (
                sector,
                industry,
                analyst_signal,
                consensus_label,
                min_insider,
                min_institutional,
            )
        ):
            raise ValueError("screen_companies needs at least one filter")

        where_clauses = [
            "COALESCE(metadata->>'ticker', '') <> ''",
            "COALESCE(metadata->>'name', '') <> ''",
        ]
        params: list[Any] = []

        if sector:
            where_clauses.append("metadata->>'sector' ILIKE %s")
            params.append(f"%{sector}%")
        if industry:
            where_clauses.append("metadata->>'industry' ILIKE %s")
            params.append(f"%{industry}%")
        if consensus_label:
            where_clauses.append("metadata->>'recommendation' = %s")
            params.append(consensus_label)
        if analyst_signal:
            field = _ANALYST_SIGNAL_FIELDS.get(analyst_signal)
            if field:
                where_clauses.append(f"COALESCE(NULLIF(metadata->>'{field}', ''), '0')::int > 0")
        if min_insider is not None:
            where_clauses.append(
                "COALESCE(NULLIF(metadata->>'insider_ownership', ''), '0')::float >= %s"
            )
            params.append(min_insider)
        if min_institutional is not None:
            where_clauses.append(
                "COALESCE(NULLIF(metadata->>'institutional_ownership', ''), '0')::float >= %s"
            )
            params.append(min_institutional)

        sql = f"""\
SELECT
  metadata->>'ticker' AS ticker,
  metadata->>'name' AS name,
  metadata->>'sector' AS sector,
  metadata->>'industry' AS industry,
  metadata->>'recommendation' AS recommendation,
  COALESCE(NULLIF(metadata->>'strong_buy_count', ''), '0')::int AS strong_buy_count,
  COALESCE(NULLIF(metadata->>'buy_count', ''), '0')::int AS buy_count,
  COALESCE(NULLIF(metadata->>'hold_count', ''), '0')::int AS hold_count,
  COALESCE(NULLIF(metadata->>'sell_count', ''), '0')::int AS sell_count,
  COALESCE(NULLIF(metadata->>'strong_sell_count', ''), '0')::int AS strong_sell_count,
  ROUND(COALESCE(NULLIF(metadata->>'insider_ownership', ''), '0')::numeric * 100, 2)
    AS insider_pct,
  ROUND(COALESCE(NULLIF(metadata->>'institutional_ownership', ''), '0')::numeric * 100, 2)
    AS institutional_pct
FROM stock_data
WHERE {" AND ".join(where_clauses)}
ORDER BY strong_buy_count DESC, buy_count DESC, name ASC
LIMIT %s"""
        params.append(limit)

        with db_cursor() as cur:
            rows, columns = self._safe_execute(sql, cur, tuple(params))

        return {
            "tool": "screen_companies",
            "sql": sql,
            "row_count": len(rows),
            "columns": columns,
            "rows": [dict(zip(columns, row, strict=False)) for row in rows],
        }

    def _required_symbol(self, input_data: dict[str, Any]) -> str:
        symbol = str(input_data.get("symbol", "")).strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        return symbol

    def _optional_text(self, value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    def _bounded_limit(self, value: Any, *, default: int, maximum: int) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(limit, maximum))

    def _normalize_ownership_threshold(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric > 1:
            numeric /= 100.0
        return max(0.0, numeric)
