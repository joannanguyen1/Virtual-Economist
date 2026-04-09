from __future__ import annotations

import json
from typing import Literal

import pytest
from backend.app.agents.housing.agent import HousingAgent
from backend.app.services import live_apis


class _FakeResponse:
    def __init__(
        self,
        *,
        payload: list[list[str]] | dict | None = None,
        text: str = "",
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[list[str]] | dict:
        if self._payload is None:
            raise json.JSONDecodeError("Expecting value", self.text, 0)
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict[str, str]] = []

    def get(self, url: str, params: dict[str, str]) -> _FakeResponse:
        assert "acs/acs1" in url
        self.calls.append(params)
        return self._responses.pop(0)


class _FakeWeatherClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict[str, str | int | float]) -> _FakeResponse:
        self.calls.append((url, params))
        if "geocoding-api.open-meteo.com" in url:
            return _FakeResponse(
                payload={
                    "results": [
                        {
                            "name": "Austin",
                            "admin1": "Texas",
                            "country_code": "US",
                            "timezone": "America/Chicago",
                            "latitude": 30.2672,
                            "longitude": -97.7431,
                            "feature_code": "PPLA2",
                        }
                    ]
                }
            )
        if "api.open-meteo.com" in url:
            return _FakeResponse(
                payload={
                    "timezone": "America/Chicago",
                    "current": {
                        "time": "2026-03-10T14:00",
                        "temperature_2m": 72.5,
                        "apparent_temperature": 74.0,
                        "relative_humidity_2m": 58,
                        "precipitation": 0.0,
                        "weather_code": 1,
                        "wind_speed_10m": 9.1,
                    },
                    "daily": {
                        "time": ["2026-03-10", "2026-03-11", "2026-03-12"],
                        "weather_code": [1, 2, 61],
                        "temperature_2m_max": [79.0, 81.0, 68.0],
                        "temperature_2m_min": [59.0, 61.0, 52.0],
                        "precipitation_sum": [0.0, 0.0, 0.35],
                        "precipitation_probability_max": [5, 10, 70],
                    },
                }
            )
        raise AssertionError(f"unexpected weather URL: {url}")


def test_parse_city_state_uses_db_inference_for_city_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(live_apis, "_infer_state_fips_from_housing_db", lambda city: "42")

    assert live_apis._parse_city_state("Philadelphia") == ("Philadelphia", "42")


def test_parse_city_state_falls_back_to_weather_geocode_for_ambiguous_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(live_apis, "_infer_state_fips_from_housing_db", lambda city: "")
    monkeypatch.setattr(
        live_apis,
        "_infer_state_fips_from_weather_geocode",
        lambda city: "48",
    )

    assert live_apis._parse_city_state("Austin") == ("Austin", "48")


def test_census_city_snapshot_retries_without_invalid_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeClient(
        [
            _FakeResponse(text="<html>Invalid Key</html>"),
            _FakeResponse(
                payload=[
                    ["NAME", "B25077_001E", "B25064_001E", "B19013_001E", "state", "place"],
                    ["Philadelphia city, Pennsylvania", "231400", "1285", "60302", "42", "60000"],
                ]
            ),
        ]
    )

    monkeypatch.setenv("CENSUS_API_KEY", "bad-key")
    monkeypatch.setattr(live_apis, "_http_client", lambda: fake_client)
    monkeypatch.setattr(
        live_apis,
        "_parse_city_state",
        lambda city: ("Philadelphia", "42"),
    )

    snapshot = live_apis.census_city_snapshot("Philadelphia, Pennsylvania")

    assert snapshot == {
        "place_name": "Philadelphia city, Pennsylvania",
        "median_home_value": "231400",
        "median_gross_rent": "1285",
        "median_household_income": "60302",
    }
    assert fake_client.calls[0]["key"] == "bad-key"
    assert "key" not in fake_client.calls[1]


def test_get_city_weather_returns_current_and_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeWeatherClient()

    monkeypatch.setattr(live_apis, "_http_client", lambda: fake_client)
    monkeypatch.setattr(
        live_apis,
        "_parse_city_state",
        lambda city: ("Austin", "48"),
    )

    weather = live_apis.get_city_weather("Austin, Texas", days=3)

    assert weather is not None
    assert weather["resolved_city"] == "Austin"
    assert weather["resolved_state"] == "Texas"
    assert weather["current"]["temperature_f"] == 72.5
    assert weather["current"]["weather"] == "Mainly clear"
    assert len(weather["forecast_days"]) == 3
    assert weather["forecast_days"][2]["weather"] == "Slight rain"


class _FakeCursor:
    def __init__(self) -> None:
        self.description = [
            ("city", None, None, None, None, None, None),
            ("date", None, None, None, None, None, None),
            ("for_sale_inventory", None, None, None, None, None, None),
        ]
        self.sql = ""
        self.params: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [
            ("Austin, Texas", "2026-01-31", 11227),
            ("Austin, Texas", "2025-12-31", 12373),
        ]


class _FakeDBContext:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeCursor:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


def test_housing_agent_inventory_tool_queries_time_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HousingAgent()
    cursor = _FakeCursor()

    monkeypatch.setattr(
        "backend.app.agents.housing.agent.db_cursor",
        lambda: _FakeDBContext(cursor),
    )

    result = agent._execute_tool(
        "search_housing_inventory",
        {"city": "Austin", "state": "Texas", "limit": 6},
    )

    assert "FROM housing_time_series" in result["sql"]
    assert "metric = 'for_sale_inventory'" in cursor.sql
    assert result["row_count"] == 2
    assert result["rows"][0]["city"] == "Austin, Texas"


def test_housing_agent_demographics_tool_uses_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HousingAgent()

    monkeypatch.setattr(
        "backend.app.agents.housing.agent.get_census_city_data",
        lambda city: {
            "place_name": "Philadelphia city, Pennsylvania",
            "median_home_value": "237900",
            "median_gross_rent": "1365",
            "median_household_income": "60302",
        },
    )

    result = agent._execute_tool("get_city_demographics", {"city": "Philadelphia"})

    assert result["found"] is True
    assert result["source"] == "census_acs_1_year"
    assert result["place_name"] == "Philadelphia city, Pennsylvania"


def test_housing_agent_weather_tool_uses_open_meteo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HousingAgent()

    monkeypatch.setattr(
        "backend.app.agents.housing.agent.get_city_weather",
        lambda city, days=5: {
            "resolved_city": "Austin",
            "resolved_state": "Texas",
            "timezone": "America/Chicago",
            "current": {
                "observed_at": "2026-03-10T14:00",
                "temperature_f": 72.5,
                "weather": "Mainly clear",
            },
            "forecast_days": [
                {"date": "2026-03-10", "weather": "Mainly clear", "temperature_max_f": 79.0}
            ],
        },
    )

    result = agent._execute_tool("get_city_weather", {"city": "Austin", "days": 3})

    assert result["found"] is True
    assert result["source"] == "open_meteo"
    assert result["days"] == 3
    assert result["current"]["temperature_f"] == 72.5


def test_housing_agent_season_tool_returns_calendar_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HousingAgent()

    monkeypatch.setattr(
        "backend.app.agents.housing.agent.get_city_season_context",
        lambda city: {
            "resolved_city": "Philadelphia",
            "resolved_state": "Pennsylvania",
            "local_date": "2026-03-10",
            "hemisphere": "Northern",
            "meteorological_season": "Spring",
            "astronomical_season": "Winter",
            "next_astronomical_season": "Spring",
            "next_astronomical_transition_date": "2026-03-20",
        },
    )

    result = agent._execute_tool("get_city_season", {"city": "Philadelphia"})

    assert result["found"] is True
    assert result["meteorological_season"] == "Spring"
    assert result["astronomical_season"] == "Winter"
