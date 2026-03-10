"""Housing & City Agent built on a Bedrock tool-use loop."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.agents.housing.prompts import SYSTEM_PROMPT
from backend.app.services import live_apis
from backend.app.services.live_apis import (
    get_census_city_data,
    get_city_season_context,
    get_city_weather,
    get_fred_macro_snapshot,
    get_hud_fmr_for_city,
)
from backend.database.connect import db_cursor

_HOUSING_FRED_SERIES = {
    "mortgage_rate": ("MORTGAGE30US", "30-Year Mortgage Rate"),
    "unemployment_rate": ("UNRATE", "Unemployment Rate"),
    "fed_funds_rate": ("FEDFUNDS", "Federal Funds Rate"),
    "inflation_cpi": ("CPIAUCSL", "Consumer Price Index"),
    "gdp": ("GDP", "Gross Domestic Product"),
}


class HousingAgent(BaseAgent):
    """Tool-use housing agent for city and real-estate questions."""

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "toolSpec": {
                    "name": "search_housing_inventory",
                    "description": (
                        "Query Zillow-style housing inventory history from the "
                        "housing_time_series table for a city."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "limit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 36,
                                },
                            },
                            "required": ["city"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_city_demographics",
                    "description": (
                        "Fetch Census ACS city-level demographics such as median "
                        "home value, median gross rent, and median household income."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                            },
                            "required": ["city"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_fair_market_rent",
                    "description": "Fetch HUD Fair Market Rent data for a city/metro area.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                            },
                            "required": ["city"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_city_weather",
                    "description": (
                        "Fetch current weather and a short daily forecast for a U.S. city."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "days": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 7,
                                },
                            },
                            "required": ["city"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_city_season",
                    "description": (
                        "Get the current local-date season context for a city. "
                        "Use this for questions asking what season it is."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                            },
                            "required": ["city"],
                        }
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "get_economic_indicators",
                    "description": (
                        "Fetch housing-relevant FRED indicators. Allowed values are: "
                        "mortgage_rate, unemployment_rate, fed_funds_rate, inflation_cpi, gdp."
                    ),
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "indicators": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": list(_HOUSING_FRED_SERIES),
                                    },
                                }
                            },
                            "required": ["indicators"],
                        }
                    },
                }
            },
        ]

    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "search_housing_inventory": self._tool_search_housing_inventory,
            "get_city_demographics": self._tool_get_city_demographics,
            "get_fair_market_rent": self._tool_get_fair_market_rent,
            "get_city_weather": self._tool_get_city_weather,
            "get_city_season": self._tool_get_city_season,
            "get_economic_indicators": self._tool_get_economic_indicators,
        }
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown housing tool: {name}")
        return handler(input_data)

    def _error_answer(self) -> str:
        return (
            "I'm sorry, I ran into an issue retrieving housing data. "
            "Please try rephrasing your question or check back later."
        )

    def _tool_search_housing_inventory(self, input_data: dict[str, Any]) -> dict[str, Any]:
        city, state = self._split_city_state(
            str(input_data.get("city", "")),
            self._optional_text(input_data.get("state")),
        )
        if not city:
            raise ValueError("city is required")

        limit = self._bounded_limit(input_data.get("limit"), default=12, maximum=36)
        where_clauses = [
            "metric = 'for_sale_inventory'",
            "(region_name ILIKE %s OR similarity(region_name, %s) > 0.45)",
        ]
        params: list[Any] = [f"%{city}%", city]
        if state:
            state_candidates = self._state_candidates(state)
            where_clauses.append(
                "(" + " OR ".join("LOWER(state_name) = LOWER(%s)" for _ in state_candidates) + ")"
            )
            params.extend(state_candidates)

        sql = f"""\
SELECT
  region_name AS city,
  date,
  value AS for_sale_inventory
FROM housing_time_series
WHERE {" AND ".join(where_clauses)}
ORDER BY date DESC
LIMIT %s"""
        params.append(limit)

        with db_cursor() as cur:
            rows, columns = self._safe_execute(sql, cur, tuple(params))

        return {
            "tool": "search_housing_inventory",
            "city": self._city_label(city, state),
            "metric": "for_sale_inventory",
            "sql": sql,
            "row_count": len(rows),
            "columns": columns,
            "rows": [dict(zip(columns, row, strict=False)) for row in rows],
        }

    def _tool_get_city_demographics(self, input_data: dict[str, Any]) -> dict[str, Any]:
        city, state = self._split_city_state(
            str(input_data.get("city", "")),
            self._optional_text(input_data.get("state")),
        )
        if not city:
            raise ValueError("city is required")

        query = self._city_label(city, state)
        data = get_census_city_data(query)
        if not data:
            return {
                "tool": "get_city_demographics",
                "city": query,
                "source": "census_acs_1_year",
                "found": False,
            }

        return {
            "tool": "get_city_demographics",
            "city": query,
            "source": "census_acs_1_year",
            "found": True,
            **data,
        }

    def _tool_get_fair_market_rent(self, input_data: dict[str, Any]) -> dict[str, Any]:
        city, state = self._split_city_state(
            str(input_data.get("city", "")),
            self._optional_text(input_data.get("state")),
        )
        if not city:
            raise ValueError("city is required")

        query = self._city_label(city, state)
        data = get_hud_fmr_for_city(query)
        if not data:
            return {
                "tool": "get_fair_market_rent",
                "city": query,
                "source": "hud_fmr",
                "found": False,
            }

        return {
            "tool": "get_fair_market_rent",
            "city": query,
            "source": "hud_fmr",
            "found": True,
            **data,
        }

    def _tool_get_city_weather(self, input_data: dict[str, Any]) -> dict[str, Any]:
        city, state = self._split_city_state(
            str(input_data.get("city", "")),
            self._optional_text(input_data.get("state")),
        )
        if not city:
            raise ValueError("city is required")

        days = self._bounded_limit(input_data.get("days"), default=5, maximum=7)
        query = self._city_label(city, state)
        data = get_city_weather(query, days=days)
        if not data:
            return {
                "tool": "get_city_weather",
                "city": query,
                "days": days,
                "source": "open_meteo",
                "found": False,
            }

        return {
            "tool": "get_city_weather",
            "city": query,
            "days": days,
            "source": "open_meteo",
            "found": True,
            **data,
        }

    def _tool_get_city_season(self, input_data: dict[str, Any]) -> dict[str, Any]:
        city, state = self._split_city_state(
            str(input_data.get("city", "")),
            self._optional_text(input_data.get("state")),
        )
        if not city:
            raise ValueError("city is required")

        query = self._city_label(city, state)
        data = get_city_season_context(query)
        if not data:
            return {
                "tool": "get_city_season",
                "city": query,
                "source": "calendar_and_geocoding",
                "found": False,
            }

        return {
            "tool": "get_city_season",
            "city": query,
            "source": "calendar_and_geocoding",
            "found": True,
            **data,
        }

    def _tool_get_economic_indicators(self, input_data: dict[str, Any]) -> dict[str, Any]:
        requested = input_data.get("indicators") or []
        indicators = [str(item) for item in requested if str(item) in _HOUSING_FRED_SERIES]
        if not indicators:
            raise ValueError("At least one valid indicator is required")

        series_ids = [_HOUSING_FRED_SERIES[item][0] for item in indicators]
        snapshot = get_fred_macro_snapshot(series_ids)
        result: dict[str, Any] = {
            "tool": "get_economic_indicators",
            "source": "fred",
            "requested_indicators": indicators,
            "series": {},
        }
        for indicator in indicators:
            series_id, label = _HOUSING_FRED_SERIES[indicator]
            if snapshot.get(series_id):
                result["series"][indicator] = {
                    "label": label,
                    "series_id": series_id,
                    **snapshot[series_id],
                }
        return result

    def _split_city_state(self, city: str, state: str | None) -> tuple[str, str | None]:
        city = city.strip()
        state = state.strip() if state else None
        if city and "," in city and not state:
            city_part, state_part = city.split(",", maxsplit=1)
            return live_apis.normalize_city_alias(city_part.strip()), state_part.strip()
        return live_apis.normalize_city_alias(city), state

    def _city_label(self, city: str, state: str | None) -> str:
        return f"{city}, {state}" if state else city

    def _state_candidates(self, state: str) -> list[str]:
        candidates = [state.strip()]
        state_key = state.strip().title()
        fips = live_apis._STATE_FIPS.get(state_key) or live_apis._STATE_ABBR_TO_FIPS.get(
            state.strip().upper()
        )
        if fips:
            for abbr, abbr_fips in live_apis._STATE_ABBR_TO_FIPS.items():
                if abbr_fips == fips and abbr not in candidates:
                    candidates.append(abbr)
                    break
        return candidates

    def _optional_text(self, value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    def _bounded_limit(self, value: Any, *, default: int, maximum: int) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(limit, maximum))
