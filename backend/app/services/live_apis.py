"""Live external API clients for the Virtual Economist agents.

Provides thin wrappers around:
  - Finnhub       (real-time stock data, analyst ratings)
  - FRED          (Federal Reserve economic data)
  - Alpha Vantage (macro indicators: GDP, CPI, unemployment)
  - Census Bureau (ACS 1-year: home value, rent, income by city)
  - HUD           (Fair Market Rents by metro area)
  - Open-Meteo    (city weather + forecast)
"""

from __future__ import annotations

import difflib
import json
import os
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import tenacity
from dotenv import load_dotenv
from loguru import logger

# Load backend/.env even when this module is imported outside FastAPI startup.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)
logger.info(
    "Live API env loaded | FINNHUB={} | FRED={} | CENSUS={} | HUD={}",
    bool(os.getenv("FINNHUB_API_KEY")),
    bool(os.getenv("FRED_API_KEY")),
    bool(os.getenv("CENSUS_API_KEY")),
    bool(os.getenv("HUD_API_TOKEN")),
)

# ---------------------------------------------------------------------------
# Shared HTTP client (connection pooling, reasonable timeouts)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _http_client() -> httpx.Client:
    return httpx.Client(timeout=12.0, follow_redirects=True)


# Retry decorator — retry on transient network errors only (not 4xx)
_http_retry = tenacity.retry(
    retry=tenacity.retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=0.5, max=4),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Finnhub — real-time stock quotes, company profiles, analyst ratings
# ---------------------------------------------------------------------------

_CORPORATE_SUFFIX_RE = re.compile(
    r"\b("
    r"inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|holdings?|group|"
    r"sa|ag|nv|spa|se|lp|class a|class b"
    r")\b\.?",
    re.IGNORECASE,
)
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")
_MARKET_CONTEXT_TERMS = (
    "stock",
    "stocks",
    "price",
    "prices",
    "graph",
    "chart",
    "plot",
    "change",
    "quote",
    "quotes",
    "high",
    "low",
    "open",
    "close",
    "return",
    "returns",
    "volatility",
    "sharpe",
    "ratio",
    "history",
    "historical",
    "trend",
    "trends",
    "drawdown",
    "ohlcv",
)
_MARKET_CONTEXT_PATTERN = "|".join(
    sorted((re.escape(term) for term in _MARKET_CONTEXT_TERMS), key=len, reverse=True)
)
_MERGED_MARKET_TERM_RE = re.compile(
    rf"\b([A-Za-z]{{3,}}?)({_MARKET_CONTEXT_PATTERN})\b",
    re.IGNORECASE,
)
_TRAILING_MARKET_TERM_RE = re.compile(
    rf"\b([A-Za-z]{{3,}}?)(?:s)? ((?:{_MARKET_CONTEXT_PATTERN})(?: .*)?)\b",
    re.IGNORECASE,
)
_REPEATED_LETTER_RE = re.compile(r"([A-Za-z])\1{2,}")
_SEARCH_TOKEN_RE = re.compile(r"\b[A-Za-z]{4,}\b")
_COMMON_COMPANY_HINTS = {
    "apple",
    "microsoft",
    "nvidia",
    "tesla",
    "amazon",
    "alphabet",
    "google",
    "meta",
    "broadcom",
    "adobe",
    "amd",
    "netflix",
    "oracle",
    "salesforce",
    "jpmorgan",
    "walmart",
    "exxon",
}
_SEARCH_CORRECTION_WORDS = {
    word
    for phrase in (
        set(_MARKET_CONTEXT_TERMS)
        | _COMMON_COMPANY_HINTS
        | {"current", "change", "graph", "chart", "plot"}
    )
    for word in re.findall(r"[a-z]+", phrase.lower())
    if len(word) >= 4
}


def _normalize_company_name(value: str) -> str:
    """Lowercase and normalize punctuation/spacing for fuzzy company matching."""
    value = _REPEATED_LETTER_RE.sub(lambda match: match.group(1) * 2, value)
    cleaned = _NON_ALNUM_RE.sub(" ", value).strip().lower()
    return " ".join(cleaned.split())


def _strip_corporate_suffixes(value: str) -> str:
    """Remove common legal suffixes so API search works on simple company names."""
    stripped = _CORPORATE_SUFFIX_RE.sub(" ", value)
    return " ".join(stripped.split()).strip(" .,-")


def _split_embedded_market_terms(value: str) -> str:
    """Insert spaces into merged phrases like 'appleshigh' -> 'apples high'."""
    return _MERGED_MARKET_TERM_RE.sub(r"\1 \2", value)


def _correct_search_typos(value: str) -> str:
    """Correct obvious company/market typos before Finnhub search."""

    def is_confident_typo(word: str, replacement: str) -> bool:
        if abs(len(replacement) - len(word)) > 1:
            return False
        if "".join(sorted(word)) == "".join(sorted(replacement)):
            return True
        return word[0] == replacement[0] and word[-1] == replacement[-1]

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        lower = word.lower()
        if lower in _SEARCH_CORRECTION_WORDS:
            return word

        suggestions = difflib.get_close_matches(
            lower,
            sorted(_SEARCH_CORRECTION_WORDS),
            n=1,
            cutoff=0.6,
        )
        if not suggestions:
            return word

        replacement = suggestions[0]
        if not is_confident_typo(lower, replacement):
            return word
        if word.isupper():
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    return _SEARCH_TOKEN_RE.sub(replace, value)


def _strip_market_context_terms(value: str) -> str:
    """Reduce company strings that accidentally include finance terms."""
    split_value = _split_embedded_market_terms(value.strip())
    stripped = _TRAILING_MARKET_TERM_RE.sub(r"\1", split_value)
    words = stripped.split()
    if words and len(words[-1]) > 4 and words[-1].endswith("s"):
        words[-1] = words[-1][:-1]
    return " ".join(words).strip(" .,-")


def _company_search_candidates(company: str) -> list[str]:
    """Generate progressively simpler queries for Finnhub symbol search."""
    raw = company.strip()
    if not raw:
        return []

    raw = _REPEATED_LETTER_RE.sub(lambda match: match.group(1) * 2, raw)
    raw = _correct_search_typos(_split_embedded_market_terms(raw))

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        normalized = candidate.strip(" .,'\"")
        key = normalized.lower()
        if normalized and key not in seen:
            candidates.append(normalized)
            seen.add(key)

    add(raw)
    add(raw.replace(".", ""))
    add(_split_embedded_market_terms(raw.replace(".", "")))

    finance_trimmed = _strip_market_context_terms(raw.replace(".", ""))
    add(finance_trimmed)

    simplified = _strip_corporate_suffixes(finance_trimmed or raw.replace(".", ""))
    add(simplified)

    parts = simplified.split()
    if len(parts) > 1:
        add(" ".join(parts[:2]))
        add(parts[0])

    return candidates


def _score_finnhub_result(company: str, result: dict) -> int:
    """Heuristic scoring for the best Finnhub search match."""
    corrected_company = _correct_search_typos(
        _split_embedded_market_terms(
            _REPEATED_LETTER_RE.sub(lambda match: match.group(1) * 2, company)
        )
    )
    stripped_company = _strip_market_context_terms(corrected_company) or corrected_company
    target = _normalize_company_name(stripped_company)
    raw_upper = company.strip().upper()
    symbol = str(result.get("symbol", ""))
    display_symbol = str(result.get("displaySymbol", ""))
    description = str(result.get("description", ""))
    security_type = str(result.get("type", ""))

    desc_norm = _normalize_company_name(description)
    score = 0

    if raw_upper and raw_upper in {symbol.upper(), display_symbol.upper()}:
        score += 200
    if target and desc_norm == target:
        score += 140
    if target and desc_norm.startswith(target):
        score += 100
    if target and target in desc_norm:
        score += 80
    if security_type == "Common Stock":
        score += 40
    elif "Stock" in security_type:
        score += 20

    return score


def _finnhub_get(path: str, **params) -> dict | list:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        logger.error("FINNHUB_API_KEY is not set in environment!")
        raise RuntimeError("FINNHUB_API_KEY not set")
    url = f"https://finnhub.io/api/v1{path}"
    logger.debug("Finnhub GET {} params={}", path, dict(params))
    resp = _http_client().get(url, params={"token": key, **params})
    logger.debug(
        "Finnhub response status={} body_preview={}",
        resp.status_code,
        str(resp.text)[:200],
    )
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=256)
@_http_retry
def finnhub_search_ticker(company: str) -> str:
    """Return best-match ticker symbol for a company name."""
    best_symbol = ""
    best_score = -1

    for query in _company_search_candidates(company):
        data = _finnhub_get("/search", q=query)
        results = data.get("result", []) if isinstance(data, dict) else []
        if not results:
            continue

        ranked = sorted(
            ((result, _score_finnhub_result(company, result)) for result in results),
            key=lambda item: item[1],
            reverse=True,
        )
        symbol, score = str(ranked[0][0].get("symbol", "")), ranked[0][1]
        if symbol and score > best_score:
            best_symbol = symbol
            best_score = score
        if best_symbol and best_score >= 140:
            break

    return best_symbol


@_http_retry
def finnhub_quote(symbol: str) -> dict:
    data = _finnhub_get("/quote", symbol=symbol)
    return data if isinstance(data, dict) else {}


@_http_retry
def finnhub_company_profile(symbol: str) -> dict:
    data = _finnhub_get("/stock/profile2", symbol=symbol)
    return data if isinstance(data, dict) else {}


@_http_retry
def finnhub_analyst_recommendations(symbol: str) -> list[dict]:
    data = _finnhub_get("/stock/recommendation", symbol=symbol)
    return data[:3] if isinstance(data, list) else []


def get_finnhub_company_data(company: str, *, include_analyst_data: bool = False) -> dict:
    """Return merged dict with quote, profile, and analyst data for a company."""
    try:
        symbol = finnhub_search_ticker(company)
        if not symbol:
            logger.warning("Finnhub: no ticker found for company={!r}", company)
            return {}
        quote = finnhub_quote(symbol)
        profile = finnhub_company_profile(symbol)
        recs = finnhub_analyst_recommendations(symbol) if include_analyst_data else []
        market_cap = profile.get("marketCapitalization")
        return {
            "symbol": symbol,
            "current_price": quote.get("c"),
            "change": quote.get("d"),
            "change_pct": quote.get("dp"),
            "high_52w": quote.get("h"),
            "low_52w": quote.get("l"),
            "open": quote.get("o"),
            "prev_close": quote.get("pc"),
            "name": profile.get("name"),
            "sector": profile.get("finnhubIndustry"),
            "country": profile.get("country"),
            "exchange": profile.get("exchange"),
            "market_cap_B": round(market_cap / 1000, 2) if market_cap else None,
            "ipo": profile.get("ipo"),
            "analyst_recommendations": recs,
        }
    except Exception as exc:
        logger.exception("Finnhub data fetch FAILED for company={!r}: {}", company, exc)
        return {}


# ---------------------------------------------------------------------------
# FRED — Federal Reserve economic data
# ---------------------------------------------------------------------------


@_http_retry
def fred_series(series_id: str, limit: int = 5) -> list[dict]:
    """Fetch the most recent observations for a FRED series."""
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        raise RuntimeError("FRED_API_KEY not set")
    resp = _http_client().get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "limit": limit,
            "sort_order": "desc",
        },
    )
    resp.raise_for_status()
    observations = resp.json().get("observations", [])
    return [{"date": o["date"], "value": o["value"]} for o in observations]


def get_fred_macro_snapshot(series_keys: list[str] | None = None) -> dict:
    """Return the latest observation for each FRED series ID."""
    if series_keys is None:
        series_keys = ["MORTGAGE30US", "UNRATE", "CPIAUCSL", "FEDFUNDS", "GDP"]
    result: dict[str, dict] = {}
    for sid in series_keys:
        try:
            obs = fred_series(sid, limit=1)
            if obs:
                result[sid] = obs[0]
        except Exception:
            logger.warning("FRED series fetch failed: {}", sid)
    return result


# ---------------------------------------------------------------------------
# Alpha Vantage — macro indicators (25 req/day — use sparingly)
# ---------------------------------------------------------------------------


@_http_retry
def alpha_vantage_indicator(indicator: str, interval: str = "annual") -> list[dict]:
    """Fetch a macro indicator. indicator = 'REAL_GDP', 'CPI', 'UNEMPLOYMENT', etc."""
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if not key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY not set")
    resp = _http_client().get(
        "https://www.alphavantage.co/query",
        params={"function": indicator, "interval": interval, "apikey": key},
    )
    resp.raise_for_status()
    data = resp.json()
    records = data.get("data", [])
    return records[:5]


# ---------------------------------------------------------------------------
# Census Bureau — ACS 1-year place-level estimates
# ---------------------------------------------------------------------------

_STATE_FIPS: dict[str, str] = {
    "Alabama": "01",
    "Alaska": "02",
    "Arizona": "04",
    "Arkansas": "05",
    "California": "06",
    "Colorado": "08",
    "Connecticut": "09",
    "Delaware": "10",
    "Florida": "12",
    "Georgia": "13",
    "Hawaii": "15",
    "Idaho": "16",
    "Illinois": "17",
    "Indiana": "18",
    "Iowa": "19",
    "Kansas": "20",
    "Kentucky": "21",
    "Louisiana": "22",
    "Maine": "23",
    "Maryland": "24",
    "Massachusetts": "25",
    "Michigan": "26",
    "Minnesota": "27",
    "Mississippi": "28",
    "Missouri": "29",
    "Montana": "30",
    "Nebraska": "31",
    "Nevada": "32",
    "New Hampshire": "33",
    "New Jersey": "34",
    "New Mexico": "35",
    "New York": "36",
    "North Carolina": "37",
    "North Dakota": "38",
    "Ohio": "39",
    "Oklahoma": "40",
    "Oregon": "41",
    "Pennsylvania": "42",
    "Rhode Island": "44",
    "South Carolina": "45",
    "South Dakota": "46",
    "Tennessee": "47",
    "Texas": "48",
    "Utah": "49",
    "Vermont": "50",
    "Virginia": "51",
    "Washington": "53",
    "West Virginia": "54",
    "Wisconsin": "55",
    "Wyoming": "56",
    "District of Columbia": "11",
}

_STATE_ABBR_TO_FIPS: dict[str, str] = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
    "DC": "11",
}
_STATE_FIPS_TO_NAME: dict[str, str] = {fips: name for name, fips in _STATE_FIPS.items()}
_STATE_FIPS_TO_ABBR: dict[str, str] = {fips: abbr for abbr, fips in _STATE_ABBR_TO_FIPS.items()}

_CITY_ALIASES: dict[str, str] = {
    "philly": "Philadelphia",
    "nyc": "New York",
    "la": "Los Angeles",
    "dc": "Washington",
}


def normalize_city_alias(city: str) -> str:
    cleaned = city.strip()
    return _CITY_ALIASES.get(cleaned.lower(), cleaned)


def _parse_city_state(city: str) -> tuple[str, str]:
    """Split 'Austin, Texas' → ('Austin', '48').  Returns (city, '') on failure."""
    parts = [p.strip() for p in city.split(",")]
    if len(parts) < 2:
        city_name = normalize_city_alias(city.strip())
        state_fips = _infer_state_fips_from_housing_db(city_name)
        if not state_fips:
            state_fips = _infer_state_fips_from_weather_geocode(city_name)
        return city_name, state_fips
    city_name = normalize_city_alias(parts[0])
    state_raw = parts[1].strip()
    fips = _STATE_FIPS.get(state_raw) or _STATE_ABBR_TO_FIPS.get(state_raw.upper(), "")
    return city_name, fips


@lru_cache(maxsize=256)
def _infer_state_fips_from_housing_db(city_name: str) -> str:
    """Use the housing table to resolve a city-only query when it maps to one state."""
    from backend.database.connect import db_cursor

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT state_name
                FROM housing_time_series
                WHERE LOWER(SPLIT_PART(region_name, ',', 1)) = LOWER(%s)
                ORDER BY state_name
                """,
                (city_name,),
            )
            states = [str(row[0]).upper() for row in cur.fetchall() if row and row[0]]
    except Exception:
        logger.warning("Housing DB city-state inference failed for city={!r}", city_name)
        return ""

    unique_states = sorted(set(states))
    if len(unique_states) == 1:
        return _STATE_ABBR_TO_FIPS.get(unique_states[0], "")

    if len(unique_states) > 1:
        logger.info(
            "City-state inference ambiguous for city={!r}: states={}",
            city_name,
            unique_states,
        )
    return ""


@lru_cache(maxsize=256)
def _infer_state_fips_from_weather_geocode(city_name: str) -> str:
    """Use Open-Meteo geocoding as a fallback when DB-based city-state inference fails."""
    try:
        location = _open_meteo_geocode_city_result(city_name, "")
    except Exception:
        logger.warning("Weather geocode state inference failed for city={!r}", city_name)
        return ""

    if not location:
        return ""

    state_name = str(location.get("admin1", "")).strip()
    return _STATE_FIPS.get(state_name) or _STATE_ABBR_TO_FIPS.get(state_name.upper(), "")


def _census_rows(state_fips: str, key: str = "") -> list[list[str]]:
    """Fetch ACS rows, retrying without an API key if the configured key is invalid."""
    url = "https://api.census.gov/data/2022/acs/acs1"
    base_params = {
        "get": "NAME,B25077_001E,B25064_001E,B19013_001E",
        "for": "place:*",
        "in": f"state:{state_fips}",
    }
    attempts = [{**base_params, "key": key}] if key else []
    attempts.append(base_params)

    last_error: Exception | None = None
    for params in attempts:
        resp = _http_client().get(url, params=params)
        resp.raise_for_status()
        try:
            payload = resp.json()
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Census returned non-JSON response; retrying without API key if possible"
            )
            continue

        if isinstance(payload, dict) and payload.get("error"):
            last_error = RuntimeError(str(payload["error"]))
            logger.warning("Census API error: {}", payload["error"])
            continue

        if isinstance(payload, list):
            return payload

        last_error = RuntimeError("Unexpected Census response format")

    if last_error is not None:
        raise last_error
    return []


@_http_retry
def census_city_snapshot(city: str) -> dict | None:
    """Return ACS 1-year median home value, rent, and income for a city/place."""
    key = os.getenv("CENSUS_API_KEY", "")
    city_name, state_fips = _parse_city_state(city)
    if not state_fips:
        logger.warning("Census: could not determine state FIPS for city={!r}", city)
        return None

    rows = _census_rows(state_fips, key=key)
    if len(rows) < 2:
        return None
    headers = rows[0]
    city_lower = city_name.lower()
    name_idx = headers.index("NAME") if "NAME" in headers else 0
    for row in rows[1:]:
        if city_lower in row[name_idx].lower():
            result = dict(zip(headers, row, strict=False))
            return {
                "place_name": row[name_idx],
                "median_home_value": result.get("B25077_001E"),
                "median_gross_rent": result.get("B25064_001E"),
                "median_household_income": result.get("B19013_001E"),
            }
    return None


def get_census_city_data(city: str) -> dict:
    try:
        data = census_city_snapshot(city)
        return data or {}
    except Exception:
        logger.warning("Census data fetch failed for city={!r}", city)
        return {}


# ---------------------------------------------------------------------------
# HUD — Fair Market Rents by metro area
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _hud_metro_list() -> list[dict]:
    token = os.getenv("HUD_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = _http_client().get(
        "https://www.huduser.gov/hudapi/public/fmr/listMetroAreas",
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@_http_retry
def hud_fmr_data(entity_id: str, year: int = 2024) -> dict:
    token = os.getenv("HUD_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = _http_client().get(
        f"https://www.huduser.gov/hudapi/public/fmr/data/{entity_id}",
        headers=headers,
        params={"year": year},
    )
    resp.raise_for_status()
    return resp.json()


def get_hud_fmr_for_city(city: str) -> dict | None:
    """Fuzzy-match a city name to a HUD metro area and return its FMR data."""
    try:
        metros = _hud_metro_list()
        city_lower = city.split(",")[0].lower().strip()
        best = None
        for m in metros:
            name = m.get("metro_name", m.get("area_name", "")).lower()
            if city_lower in name:
                best = m
                break
        if not best:
            return None
        entity_id = best.get("cbsa_code") or best.get("entity_id") or best.get("code")
        if not entity_id:
            return None
        fmr = hud_fmr_data(str(entity_id))
        data = fmr.get("data", {})
        basic = data.get("basicdata", [{}])
        row = basic[0] if isinstance(basic, list) and basic else (basic or {})
        return {
            "metro_name": best.get("metro_name", ""),
            "year": fmr.get("year"),
            "fmr_0br": row.get("Efficiency"),
            "fmr_1br": row.get("One-Bedroom"),
            "fmr_2br": row.get("Two-Bedroom"),
            "fmr_3br": row.get("Three-Bedroom"),
            "fmr_4br": row.get("Four-Bedroom"),
        }
    except Exception:
        logger.warning("HUD FMR fetch failed for city={!r}", city)
        return None


# ---------------------------------------------------------------------------
# Open-Meteo — geocoding + weather forecast
# ---------------------------------------------------------------------------

_WEATHER_CODE_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _normalize_place_text(value: str) -> str:
    cleaned = _NON_ALNUM_RE.sub(" ", value).strip().lower()
    return " ".join(cleaned.split())


def _score_weather_geocode_result(city_name: str, state_name: str, result: dict) -> int:
    city_target = _normalize_place_text(city_name)
    state_target = _normalize_place_text(state_name)
    name = _normalize_place_text(str(result.get("name", "")))
    admin1 = _normalize_place_text(str(result.get("admin1", "")))

    score = 0
    if city_target and name == city_target:
        score += 120
    elif city_target and name.startswith(city_target):
        score += 90
    elif city_target and city_target in name:
        score += 70

    if state_target and admin1 == state_target:
        score += 120

    if str(result.get("country_code", "")).upper() == "US":
        score += 20
    if str(result.get("feature_code", "")).upper().startswith("PPL"):
        score += 10
    return score


@_http_retry
def _open_meteo_geocode_city_result(query_city: str, state_name: str) -> dict | None:
    """Resolve a U.S. city string to one Open-Meteo geocoding result."""
    resp = _http_client().get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": query_city,
            "count": 10,
            "language": "en",
            "format": "json",
            "countryCode": "US",
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return None

    ranked = sorted(
        results,
        key=lambda item: _score_weather_geocode_result(query_city, state_name, item),
        reverse=True,
    )
    return ranked[0] if ranked else None


@_http_retry
def open_meteo_geocode_city(city: str) -> dict | None:
    """Resolve a U.S. city string to one Open-Meteo geocoding result."""
    query_city, state_fips = _parse_city_state(city)
    state_name = _STATE_FIPS_TO_NAME.get(state_fips, "")
    return _open_meteo_geocode_city_result(query_city, state_name)


@_http_retry
def open_meteo_weather_forecast(
    latitude: float,
    longitude: float,
    *,
    timezone: str = "auto",
    days: int = 5,
) -> dict:
    """Fetch current weather plus a short daily forecast from Open-Meteo."""
    forecast_days = max(1, min(days, 7))
    resp = _http_client().get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max"
            ),
            "forecast_days": forecast_days,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": timezone or "auto",
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_city_weather(city: str, *, days: int = 5) -> dict | None:
    """Return current weather + daily forecast for a U.S. city."""
    try:
        location = open_meteo_geocode_city(city)
        if not location:
            return None

        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        timezone = str(location.get("timezone") or "auto")
        forecast = open_meteo_weather_forecast(
            latitude,
            longitude,
            timezone=timezone,
            days=days,
        )

        current = forecast.get("current", {}) if isinstance(forecast, dict) else {}
        daily = forecast.get("daily", {}) if isinstance(forecast, dict) else {}
        dates = list(daily.get("time", []) or [])
        weather_codes = list(daily.get("weather_code", []) or [])
        highs = list(daily.get("temperature_2m_max", []) or [])
        lows = list(daily.get("temperature_2m_min", []) or [])
        precipitation = list(daily.get("precipitation_sum", []) or [])
        precip_prob = list(daily.get("precipitation_probability_max", []) or [])

        forecast_days: list[dict] = []
        for index, date_value in enumerate(dates):
            code = weather_codes[index] if index < len(weather_codes) else None
            forecast_days.append(
                {
                    "date": date_value,
                    "weather_code": code,
                    "weather": _WEATHER_CODE_LABELS.get(int(code), "Unknown")
                    if code is not None
                    else "Unknown",
                    "temperature_max_f": highs[index] if index < len(highs) else None,
                    "temperature_min_f": lows[index] if index < len(lows) else None,
                    "precipitation_sum_in": (
                        precipitation[index] if index < len(precipitation) else None
                    ),
                    "precipitation_probability_max_pct": (
                        precip_prob[index] if index < len(precip_prob) else None
                    ),
                }
            )

        current_code = current.get("weather_code")
        return {
            "query_city": city,
            "resolved_city": location.get("name"),
            "resolved_state": location.get("admin1"),
            "country_code": location.get("country_code"),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": forecast.get("timezone") or timezone,
            "current": {
                "observed_at": current.get("time"),
                "temperature_f": current.get("temperature_2m"),
                "apparent_temperature_f": current.get("apparent_temperature"),
                "relative_humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_in": current.get("precipitation"),
                "wind_speed_mph": current.get("wind_speed_10m"),
                "weather_code": current_code,
                "weather": _WEATHER_CODE_LABELS.get(int(current_code), "Unknown")
                if current_code is not None
                else "Unknown",
            },
            "forecast_days": forecast_days,
        }
    except Exception:
        logger.warning("Weather fetch failed for city={!r}", city)
        return None


def _flip_season(season: str) -> str:
    opposites = {
        "Winter": "Summer",
        "Spring": "Fall",
        "Summer": "Winter",
        "Fall": "Spring",
    }
    return opposites.get(season, season)


def _meteorological_season(local_date: date, *, northern_hemisphere: bool) -> str:
    if local_date.month in {12, 1, 2}:
        season = "Winter"
    elif local_date.month in {3, 4, 5}:
        season = "Spring"
    elif local_date.month in {6, 7, 8}:
        season = "Summer"
    else:
        season = "Fall"
    return season if northern_hemisphere else _flip_season(season)


def _astronomical_season_info(
    local_date: date,
    *,
    northern_hemisphere: bool,
) -> tuple[str, date, str]:
    year = local_date.year
    spring_equinox = date(year, 3, 20)
    summer_solstice = date(year, 6, 21)
    autumn_equinox = date(year, 9, 22)
    winter_solstice = date(year, 12, 21)

    if local_date < spring_equinox:
        season = "Winter"
        next_transition = spring_equinox
        next_season = "Spring"
    elif local_date < summer_solstice:
        season = "Spring"
        next_transition = summer_solstice
        next_season = "Summer"
    elif local_date < autumn_equinox:
        season = "Summer"
        next_transition = autumn_equinox
        next_season = "Fall"
    elif local_date < winter_solstice:
        season = "Fall"
        next_transition = winter_solstice
        next_season = "Winter"
    else:
        season = "Winter"
        next_transition = date(year + 1, 3, 20)
        next_season = "Spring"

    if northern_hemisphere:
        return season, next_transition, next_season
    return _flip_season(season), next_transition, _flip_season(next_season)


def get_city_season_context(city: str) -> dict | None:
    """Return local-date season context for a city."""
    try:
        location = open_meteo_geocode_city(city)
        if not location:
            return None

        latitude = float(location["latitude"])
        timezone_name = str(location.get("timezone") or "UTC")
        try:
            local_date = datetime.now(ZoneInfo(timezone_name)).date()
        except Exception:
            local_date = datetime.utcnow().date()

        northern_hemisphere = latitude >= 0
        meteorological = _meteorological_season(
            local_date,
            northern_hemisphere=northern_hemisphere,
        )
        astronomical, next_transition, next_astronomical = _astronomical_season_info(
            local_date,
            northern_hemisphere=northern_hemisphere,
        )

        return {
            "query_city": city,
            "resolved_city": location.get("name"),
            "resolved_state": location.get("admin1"),
            "timezone": timezone_name,
            "latitude": latitude,
            "local_date": local_date.isoformat(),
            "hemisphere": "Northern" if northern_hemisphere else "Southern",
            "meteorological_season": meteorological,
            "astronomical_season": astronomical,
            "next_astronomical_season": next_astronomical,
            "next_astronomical_transition_date": next_transition.isoformat(),
        }
    except Exception:
        logger.warning("Season context fetch failed for city={!r}", city)
        return None


# ---------------------------------------------------------------------------
# Question classification helpers
# ---------------------------------------------------------------------------

_RENT_KW = {"rent", "apartment", "rental", "fair market", "fmr", "lease", "renter"}
_MACRO_KW = {
    "mortgage",
    "interest rate",
    "unemployment",
    "inflation",
    "federal reserve",
    "fed rate",
    "treasury",
    "cpi",
    "consumer price",
    "economy",
}
_AV_KW = {"gdp", "gross domestic product", "consumer price index"}


def classify_housing_question(question: str) -> set[str]:
    """Return set of API tags needed to answer this housing question."""
    q = question.lower()
    tags: set[str] = {"census"}  # census is always useful for city questions
    if any(kw in q for kw in _RENT_KW):
        tags.add("hud")
    if any(kw in q for kw in _MACRO_KW):
        tags.add("fred")
    return tags


def classify_market_question(question: str) -> set[str]:
    """Return set of API tags needed to answer this market question."""
    q = question.lower()
    tags: set[str] = {"finnhub"}  # always call for market questions
    if any(kw in q for kw in _MACRO_KW):
        tags.add("fred")
    if any(kw in q for kw in _AV_KW):
        tags.add("alpha_vantage")
    return tags


# ---------------------------------------------------------------------------
# Format live data for synthesis prompts
# ---------------------------------------------------------------------------

_FRED_LABELS: dict[str, str] = {
    "MORTGAGE30US": "30-Year Mortgage Rate (%)",
    "UNRATE": "Unemployment Rate (%)",
    "CPIAUCSL": "CPI (index, 1982-84=100)",
    "FEDFUNDS": "Federal Funds Rate (%)",
    "GDP": "GDP (billions USD)",
}


def format_live_data_for_synthesis(live_data: dict) -> str:
    """Convert a live_data dict into a readable block for the synthesis prompt."""
    if not live_data:
        return ""
    lines: list[str] = []

    if live_data.get("finnhub"):
        d = live_data["finnhub"]
        lines.append("=== Finnhub Real-Time Stock Data ===")
        if d.get("name"):
            lines.append(f"Company: {d['name']} ({d.get('symbol', '')})")
        if d.get("sector"):
            lines.append(f"Sector/Industry: {d['sector']}")
        if d.get("exchange"):
            lines.append(f"Exchange: {d['exchange']}")
        if d.get("current_price") is not None:
            lines.append(f"Current Price: ${d['current_price']}")
        if d.get("change_pct") is not None:
            lines.append(f"Day Change: {d['change_pct']:+.2f}%")
        if d.get("high_52w") is not None:
            lines.append(f"52-Week High: ${d['high_52w']}")
        if d.get("low_52w") is not None:
            lines.append(f"52-Week Low: ${d['low_52w']}")
        if d.get("market_cap_B") is not None:
            lines.append(f"Market Cap: ${d['market_cap_B']}B")
        if d.get("ipo"):
            lines.append(f"IPO Date: {d['ipo']}")
        recs = d.get("analyst_recommendations", [])
        if recs:
            r = recs[0]
            lines.append(
                f"Analyst Consensus (most recent period): "
                f"strongBuy={r.get('strongBuy', 0)}, buy={r.get('buy', 0)}, "
                f"hold={r.get('hold', 0)}, sell={r.get('sell', 0)}, "
                f"strongSell={r.get('strongSell', 0)}"
            )

    if live_data.get("fred"):
        lines.append("=== FRED Macro Economic Data ===")
        for sid, obs in live_data["fred"].items():
            label = _FRED_LABELS.get(sid, sid)
            lines.append(f"{label}: {obs.get('value')} (as of {obs.get('date')})")

    if live_data.get("census"):
        d = live_data["census"]
        lines.append("=== Census Bureau ACS 1-Year Data ===")
        if d.get("place_name"):
            lines.append(f"Place: {d['place_name']}")
        val = d.get("median_home_value")
        if val and val != "-666666666":
            lines.append(f"Median Home Value: ${int(val):,}")
        val = d.get("median_gross_rent")
        if val and val != "-666666666":
            lines.append(f"Median Gross Rent: ${int(val):,}/mo")
        val = d.get("median_household_income")
        if val and val != "-666666666":
            lines.append(f"Median Household Income: ${int(val):,}")

    if live_data.get("census_compare"):
        lines.append("=== Census Bureau ACS 1-Year City Comparison ===")
        for item in live_data["census_compare"]:
            label = item.get("place_name") or item.get("query_city", "Unknown city")
            lines.append(f"City: {label}")
            val = item.get("median_home_value")
            if val and val != "-666666666":
                lines.append(f"Median Home Value: ${int(val):,}")
            val = item.get("median_gross_rent")
            if val and val != "-666666666":
                lines.append(f"Median Gross Rent: ${int(val):,}/mo")
            val = item.get("median_household_income")
            if val and val != "-666666666":
                lines.append(f"Median Household Income: ${int(val):,}")

    if live_data.get("hud"):
        d = live_data["hud"]
        lines.append("=== HUD Fair Market Rents ===")
        if d.get("metro_name"):
            lines.append(f"Metro Area: {d['metro_name']} ({d.get('year', '')})")
        for key, label in [
            ("fmr_0br", "Studio"),
            ("fmr_1br", "1BR"),
            ("fmr_2br", "2BR"),
            ("fmr_3br", "3BR"),
            ("fmr_4br", "4BR"),
        ]:
            if d.get(key):
                lines.append(f"  {label}: ${d[key]}/mo")

    if live_data.get("alpha_vantage"):
        lines.append("=== Alpha Vantage Macro Indicators ===")
        for indicator, records in live_data["alpha_vantage"].items():
            if records:
                latest = records[0]
                lines.append(f"{indicator}: {latest.get('value')} ({latest.get('date')})")

    return "\n".join(lines)
