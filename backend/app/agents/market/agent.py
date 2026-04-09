"""Stock & Market Agent built on a Bedrock tool-use loop."""

from __future__ import annotations

import math
import re
from itertools import pairwise
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
_TRADING_DAYS_PER_YEAR = 252
_MAX_OHLCV_ROWS = 2520


def _normalize_db_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class MarketAgent(BaseAgent):
    """Tool-use market agent for company, stock, and macro questions."""

    def __init__(self) -> None:
        super().__init__()
        self._ohlcv_columns_cache: dict[str, str] | None = None

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
            {
                "toolSpec": {
                    "name": "get_historical_ohlcv",
                    "description": (
                        "Fetch historical daily OHLCV data from the local stock_ohlcv table. "
                        "Useful for price-history, trend, high/low range, dividend, and "
                        "volume questions."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                                "lookback_days": {
                                    "type": "integer",
                                    "minimum": 2,
                                    "maximum": _MAX_OHLCV_ROWS,
                                },
                                "start_date": {"type": "string"},
                                "end_date": {"type": "string"},
                            },
                            "required": ["symbol"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_stock_performance",
                    "description": (
                        "Analyze historical stock performance from the stock_ohlcv table. "
                        "Computes return, annualized volatility, Sharpe ratio, max drawdown, "
                        "and related metrics for one or more ticker symbols."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "symbols": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                    "maxItems": 5,
                                },
                                "lookback_days": {
                                    "type": "integer",
                                    "minimum": 20,
                                    "maximum": _MAX_OHLCV_ROWS,
                                },
                                "risk_free_rate_pct": {"type": "number"},
                            },
                            "required": ["symbols"],
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
            "get_historical_ohlcv": self._tool_get_historical_ohlcv,
            "analyze_stock_performance": self._tool_analyze_stock_performance,
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

    def _tool_get_historical_ohlcv(self, input_data: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required_symbol(input_data)
        lookback_days = self._bounded_limit(
            input_data.get("lookback_days"),
            default=90,
            maximum=_MAX_OHLCV_ROWS,
        )
        rows_payload = self._fetch_ohlcv_rows(
            symbol,
            lookback_days=lookback_days,
            start_date=self._optional_text(input_data.get("start_date")),
            end_date=self._optional_text(input_data.get("end_date")),
        )
        rows = rows_payload["rows"]
        summary = self._summarize_ohlcv_rows(rows)

        return {
            "tool": "get_historical_ohlcv",
            "symbol": symbol,
            "source": "stock_ohlcv",
            "sql": rows_payload["sql"],
            "row_count": len(rows),
            "rows": rows[-min(len(rows), 120) :],
            "summary": summary,
        }

    def _tool_analyze_stock_performance(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raw_symbols = input_data.get("symbols") or []
        symbols = [str(symbol).strip().upper() for symbol in raw_symbols if str(symbol).strip()]
        deduped_symbols = list(dict.fromkeys(symbols))[:5]
        if not deduped_symbols:
            raise ValueError("symbols is required")

        lookback_days = self._bounded_limit(
            input_data.get("lookback_days"),
            default=252,
            maximum=_MAX_OHLCV_ROWS,
        )
        risk_free_rate_pct = self._to_float(input_data.get("risk_free_rate_pct"), default=4.0)

        metrics: list[dict[str, Any]] = []
        for symbol in deduped_symbols:
            payload = self._fetch_ohlcv_rows(symbol, lookback_days=lookback_days)
            metrics.append(
                {
                    "symbol": symbol,
                    "source": "stock_ohlcv",
                    "assumption": (
                        "Metrics are computed from local daily close series with "
                        "dividends added and stock split factors applied when present."
                    ),
                    **self._compute_performance_metrics(
                        payload["rows"],
                        risk_free_rate_pct=risk_free_rate_pct,
                    ),
                }
            )

        return {
            "tool": "analyze_stock_performance",
            "source": "stock_ohlcv",
            "lookback_days": lookback_days,
            "risk_free_rate_pct": risk_free_rate_pct,
            "metrics": metrics,
        }

    def _stock_ohlcv_columns(self) -> dict[str, str]:
        if self._ohlcv_columns_cache is not None:
            return self._ohlcv_columns_cache

        with db_cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'stock_ohlcv'
                ORDER BY ordinal_position
                """
            )
            rows = cur.fetchall()

        columns = {
            _normalize_db_column_name(str(row[0])): str(row[0]) for row in rows if row and row[0]
        }
        self._ohlcv_columns_cache = columns
        return columns

    def _fetch_ohlcv_rows(
        self,
        symbol: str,
        *,
        lookback_days: int = 90,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        columns = self._stock_ohlcv_columns()
        required = {"ticker", "date", "open", "high", "low", "close", "volume"}
        missing = sorted(column for column in required if column not in columns)
        if missing:
            raise ValueError(f"stock_ohlcv is missing required columns: {', '.join(missing)}")

        ticker_col = _quote_ident(columns["ticker"])
        date_col = _quote_ident(columns["date"])
        open_col = _quote_ident(columns["open"])
        high_col = _quote_ident(columns["high"])
        low_col = _quote_ident(columns["low"])
        close_col = _quote_ident(columns["close"])
        volume_col = _quote_ident(columns["volume"])
        dividends_expr = (
            f"{_quote_ident(columns['dividends'])} AS dividends"
            if "dividends" in columns
            else "0::numeric AS dividends"
        )
        splits_expr = (
            f"{_quote_ident(columns['stock_splits'])} AS stock_splits"
            if "stock_splits" in columns
            else "1::numeric AS stock_splits"
        )

        select_list = f"""\
{ticker_col} AS ticker,
{date_col} AS trade_date,
{open_col} AS open,
{high_col} AS high,
{low_col} AS low,
{close_col} AS close,
{volume_col} AS volume,
{dividends_expr},
{splits_expr}"""

        if start_date or end_date:
            where_clauses = [f"{ticker_col} = %s"]
            params: list[Any] = [symbol]
            if start_date:
                where_clauses.append(f"{date_col} >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append(f"{date_col} <= %s")
                params.append(end_date)
            params.append(min(lookback_days, _MAX_OHLCV_ROWS))
            sql = f"""\
SELECT *
FROM (
  SELECT
    {select_list}
  FROM stock_ohlcv
  WHERE {" AND ".join(where_clauses)}
  ORDER BY {date_col} DESC
  LIMIT %s
) recent
ORDER BY trade_date ASC"""
        else:
            limit = min(max(lookback_days, 2), _MAX_OHLCV_ROWS)
            sql = f"""\
SELECT *
FROM (
  SELECT
    {select_list}
  FROM stock_ohlcv
  WHERE {ticker_col} = %s
  ORDER BY {date_col} DESC
  LIMIT %s
) recent
ORDER BY trade_date ASC"""
            params = [symbol, limit]

        with db_cursor() as cur:
            rows, columns_out = self._safe_execute(sql, cur, tuple(params))

        return {
            "sql": sql,
            "rows": [dict(zip(columns_out, row, strict=False)) for row in rows],
        }

    def _summarize_ohlcv_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"found": False}

        closes = [self._to_float(row.get("close")) for row in rows if row.get("close") is not None]
        highs = [self._to_float(row.get("high")) for row in rows if row.get("high") is not None]
        lows = [self._to_float(row.get("low")) for row in rows if row.get("low") is not None]
        volumes = [
            self._to_float(row.get("volume")) for row in rows if row.get("volume") is not None
        ]
        total_dividends = sum(self._to_float(row.get("dividends")) for row in rows)

        first_close = closes[0] if closes else None
        last_close = closes[-1] if closes else None
        period_return_pct = None
        if first_close is not None and first_close != 0.0 and last_close is not None:
            period_return_pct = round(((last_close / first_close) - 1.0) * 100.0, 2)

        return {
            "found": True,
            "start_date": rows[0].get("trade_date"),
            "end_date": rows[-1].get("trade_date"),
            "latest_close": round(last_close, 4) if last_close is not None else None,
            "period_return_pct": period_return_pct,
            "highest_high": round(max(highs), 4) if highs else None,
            "lowest_low": round(min(lows), 4) if lows else None,
            "average_volume": round(sum(volumes) / len(volumes), 2) if volumes else None,
            "total_dividends": round(total_dividends, 4),
        }

    def _compute_performance_metrics(
        self,
        rows: list[dict[str, Any]],
        *,
        risk_free_rate_pct: float,
    ) -> dict[str, Any]:
        if len(rows) < 2:
            return {
                "found": bool(rows),
                "metrics_available": False,
                "reason": "Not enough OHLCV rows to calculate returns.",
            }

        returns: list[float] = []
        total_dividends = 0.0
        split_events = 0

        for previous, current in pairwise(rows):
            previous_close = self._to_float(previous.get("close"))
            current_close = self._to_float(current.get("close"))
            dividend = self._to_float(current.get("dividends"))
            split_factor = self._to_float(current.get("stock_splits"), default=1.0)

            if previous_close <= 0 or current_close <= 0:
                continue

            if split_factor not in (0.0, 1.0):
                split_events += 1

            total_dividends += dividend
            adjusted_previous_close = (
                previous_close / split_factor if split_factor not in (0.0, 1.0) else previous_close
            )
            if adjusted_previous_close <= 0:
                continue
            returns.append(((current_close + dividend) / adjusted_previous_close) - 1.0)

        if not returns:
            return {
                "found": True,
                "metrics_available": False,
                "reason": "No valid close-to-close return observations were available.",
            }

        mean_daily_return = sum(returns) / len(returns)
        variance = (
            sum((value - mean_daily_return) ** 2 for value in returns) / (len(returns) - 1)
            if len(returns) > 1
            else 0.0
        )
        daily_volatility = math.sqrt(max(variance, 0.0))
        rf_daily = (risk_free_rate_pct / 100.0) / _TRADING_DAYS_PER_YEAR
        sharpe_ratio = None
        if daily_volatility > 0:
            sharpe_ratio = ((mean_daily_return - rf_daily) / daily_volatility) * math.sqrt(
                _TRADING_DAYS_PER_YEAR
            )

        cumulative_growth = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for daily_return in returns:
            cumulative_growth *= 1.0 + daily_return
            peak = max(peak, cumulative_growth)
            max_drawdown = min(max_drawdown, (cumulative_growth / peak) - 1.0)

        annualized_return = None
        if cumulative_growth > 0:
            annualized_return = cumulative_growth ** (_TRADING_DAYS_PER_YEAR / len(returns)) - 1.0

        highs = [self._to_float(row.get("high")) for row in rows if row.get("high") is not None]
        lows = [self._to_float(row.get("low")) for row in rows if row.get("low") is not None]
        volumes = [
            self._to_float(row.get("volume")) for row in rows if row.get("volume") is not None
        ]
        latest_close = self._to_float(rows[-1].get("close"))

        return {
            "found": True,
            "metrics_available": True,
            "start_date": rows[0].get("trade_date"),
            "end_date": rows[-1].get("trade_date"),
            "observations": len(rows),
            "return_observations": len(returns),
            "latest_close": round(latest_close, 4),
            "total_return_pct": round((cumulative_growth - 1.0) * 100.0, 2),
            "annualized_return_pct": (
                round(annualized_return * 100.0, 2) if annualized_return is not None else None
            ),
            "annualized_volatility_pct": round(
                daily_volatility * math.sqrt(_TRADING_DAYS_PER_YEAR) * 100.0,
                2,
            ),
            "sharpe_ratio": round(sharpe_ratio, 3) if sharpe_ratio is not None else None,
            "max_drawdown_pct": round(max_drawdown * 100.0, 2),
            "average_daily_return_pct": round(mean_daily_return * 100.0, 3),
            "positive_days_pct": round(
                (sum(value > 0 for value in returns) / len(returns)) * 100.0,
                2,
            ),
            "highest_high": round(max(highs), 4) if highs else None,
            "lowest_low": round(min(lows), 4) if lows else None,
            "average_volume": round(sum(volumes) / len(volumes), 2) if volumes else None,
            "total_dividends": round(total_dividends, 4),
            "stock_split_events": split_events,
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

    def _to_float(self, value: Any, *, default: float = 0.0) -> float:
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
