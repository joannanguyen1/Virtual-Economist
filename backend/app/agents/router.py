"""Question Router — Amazon Titan Text Lite classifier.

Uses Amazon Titan Text Lite to classify user questions into one of three
domains before dispatching to the appropriate specialist agent:

  HOUSING → HousingAgent  (real estate, cities, rent, home values, mortgages)
  MARKET  → MarketAgent   (stocks, companies, economy, GDP, unemployment)
  OUT_OF_SCOPE → unsupported for this product
"""

from __future__ import annotations

import re

from loguru import logger

from backend.app.agents.base import AgentResult
from backend.app.agents.housing.agent import HousingAgent
from backend.app.agents.market.agent import MarketAgent
from backend.app.services.bedrock import TITAN_TEXT_LITE, invoke_claude

# ---------------------------------------------------------------------------
# Singleton agents
# ---------------------------------------------------------------------------
_housing_agent = HousingAgent()
_market_agent = MarketAgent()

# ---------------------------------------------------------------------------
# Titan classifier prompt
# ---------------------------------------------------------------------------
_CLASSIFY_SYSTEM = """\
You are a question classifier for an economics platform.
Classify the user's question into exactly ONE category.

HOUSING — questions about: real estate, home values, home prices, rent, \
apartments, cities, neighborhoods, housing inventory, Zillow, mortgages, \
property, fair market rent, median income by city, weather, climate, \
temperature, rain, snow, precipitation, forecast.

MARKET — questions about: stocks, stock price, companies, investing, \
economy, GDP, unemployment, inflation, CPI, interest rates, federal reserve, \
analyst recommendations, sectors, earnings, financial markets.

OUT_OF_SCOPE — anything unrelated to those domains, such as coding help, \
general trivia, creative writing, personal advice, recipes, homework outside \
housing/markets, or casual chat not about these topics.

Reply with ONLY one word: HOUSING, MARKET, or OUT_OF_SCOPE
Do not include any explanation.\
"""

_OUT_OF_SCOPE_ANSWER = (
    "I'm built for U.S. housing/city questions and stock/market questions. "
    "I can help with home values, rent, income, weather, housing inventory, "
    "stock prices, analyst recommendations, sectors, and macro indicators.\n\n"
    "If you want, ask a question in one of those areas."
)

_MARKET_CONTEXT_TERMS = (
    "stock",
    "stocks",
    "price",
    "prices",
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
    rf"\b([a-z]{{3,}}?)({_MARKET_CONTEXT_PATTERN})\b",
    re.IGNORECASE,
)
_TRAILING_PLURAL_MARKET_RE = re.compile(
    rf"\b([a-z]{{4,}})s ((?:{_MARKET_CONTEXT_PATTERN})\b)",
    re.IGNORECASE,
)
_TIME_WINDOW_RE = re.compile(
    r"\b(?:last|past)\s+(?:\d+\s+)?(?:day|days|week|weeks|month|months|year|years)\b",
    re.IGNORECASE,
)

_MARKET_OVERRIDE_KW = {
    "stock",
    "stocks",
    "stock price",
    "share price",
    "company",
    "companies",
    "ticker",
    "market cap",
    "analyst",
    "recommendation",
    "recommendations",
    "rating",
    "ratings",
    "strong buy",
    "buy rating",
    "buy ratings",
    "earnings",
    "sector",
    "industry",
    "portfolio",
    "dividend",
    "dividends",
    "ipo",
    "trading",
    "price history",
    "historical price",
    "historical prices",
    "ohlcv",
    "return",
    "returns",
    "volatility",
    "sharpe",
    "drawdown",
    "max drawdown",
    "risk-adjusted",
    "risk adjusted",
    "unemployment",
    "inflation",
    "cpi",
    "gdp",
    "economy",
    "federal reserve",
    "fed funds",
    "interest rate",
    "interest rates",
    "treasury",
}
_HOUSING_OVERRIDE_KW = {
    "housing",
    "home value",
    "home values",
    "home price",
    "home prices",
    "median price",
    "median home",
    "rent",
    "rental",
    "apartment",
    "real estate",
    "housing inventory",
    "inventory",
    "listing",
    "zillow",
    "property",
    "fair market rent",
    "hud",
    "city",
    "neighborhood",
    "philly",
    "mortgage",
    "weather",
    "forecast",
    "temperature",
    "climate",
    "season",
    "rain",
    "snow",
    "precipitation",
}


def _contains_keyword(text: str, keyword: str) -> bool:
    """Match whole words/phrases so short keywords don't hit unrelated words."""
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _normalize_question_text(question: str) -> str:
    """Normalize obvious merged words and possessives so routing is typo-tolerant."""
    normalized = question.strip()
    normalized = re.sub(r"(?i)\b([a-z]{3,})'s\b", r"\1", normalized)
    normalized = _MERGED_MARKET_TERM_RE.sub(r"\1 \2", normalized)
    normalized = _TRAILING_PLURAL_MARKET_RE.sub(r"\1 \2", normalized)
    return " ".join(normalized.split())


def _looks_like_market_time_series(question: str) -> bool:
    """Catch messy time-series market questions like 'appleshigh over 90 days'."""
    metric_terms = {
        "price",
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
        "drawdown",
        "quote",
    }
    return _TIME_WINDOW_RE.search(question) is not None and any(
        _contains_keyword(question, term) for term in metric_terms
    )


def _keyword_override(question: str) -> str | None:
    """Deterministically route obvious questions before calling Titan."""
    q = _normalize_question_text(question).lower()
    market_hits = sum(_contains_keyword(q, keyword) for keyword in _MARKET_OVERRIDE_KW)
    housing_hits = sum(_contains_keyword(q, keyword) for keyword in _HOUSING_OVERRIDE_KW)

    if market_hits and not housing_hits:
        return "market"
    if housing_hits and not market_hits:
        return "housing"
    if not housing_hits and _looks_like_market_time_series(q):
        return "market"
    return None


def classify_question(question: str) -> str:
    """Classify a question as 'housing', 'market', or 'out_of_scope'.

    Returns:
        'housing', 'market', or 'out_of_scope' (lowercase).
    """
    normalized_question = _normalize_question_text(question)
    override = _keyword_override(normalized_question)
    if override is not None:
        logger.debug(
            "Router | keyword override={!r} | question={!r} | normalized={!r}",
            override,
            question,
            normalized_question,
        )
        return override

    try:
        response = invoke_claude(
            prompt=normalized_question,
            system=_CLASSIFY_SYSTEM,
            model_id=TITAN_TEXT_LITE,
            max_tokens=8,
            temperature=0.0,
        )
        label = response.strip().upper()
        if "HOUSING" in label:
            return "housing"
        if "MARKET" in label:
            return "market"
        if "OUT_OF_SCOPE" in label:
            return "out_of_scope"
        # Fallback heuristic if Titan gives an unexpected answer
        logger.warning("Titan classifier returned unexpected label: {!r}, using heuristic", label)
        return _keyword_fallback(normalized_question)
    except Exception as exc:
        logger.warning("Titan classifier failed ({}), using keyword fallback", exc)
        return _keyword_fallback(normalized_question)


def _keyword_fallback(question: str) -> str:
    """Simple keyword heuristic when Titan is unavailable."""
    q = question.lower()
    housing_kw = {
        "housing",
        "home value",
        "home values",
        "home price",
        "home prices",
        "median price",
        "median home",
        "rent",
        "rental",
        "apartment",
        "real estate",
        "housing inventory",
        "inventory",
        "listing",
        "zillow",
        "property",
        "fair market rent",
        "hud",
        "city",
        "neighborhood",
        "philly",
        "mortgage",
        "weather",
        "forecast",
        "temperature",
        "climate",
        "season",
        "rain",
        "snow",
        "precipitation",
    }
    market_kw = {
        "stock",
        "company",
        "companies",
        "invest",
        "gdp",
        "earnings",
        "share price",
        "analyst",
        "recommendation",
        "recommendations",
        "rating",
        "ratings",
        "strong buy",
        "buy rating",
        "buy ratings",
        "sector",
        "s&p",
        "nasdaq",
        "dow",
        "portfolio",
        "dividend",
        "dividends",
        "market cap",
        "ipo",
        "trading",
        "price history",
        "historical price",
        "historical prices",
        "ohlcv",
        "return",
        "returns",
        "volatility",
        "sharpe",
        "drawdown",
        "max drawdown",
        "risk-adjusted",
        "risk adjusted",
        "unemployment",
        "inflation",
        "cpi",
        "interest rate",
        "interest rates",
    }
    if any(_contains_keyword(q, kw) for kw in housing_kw):
        return "housing"
    if any(_contains_keyword(q, kw) for kw in market_kw):
        return "market"
    return "out_of_scope"


def route_question(question: str) -> tuple[str | None, AgentResult]:
    """Classify a question and run the appropriate agent.

    Returns:
        Tuple of (agent_type, AgentResult).
    """
    normalized_question = _normalize_question_text(question)
    effective_question = (
        question
        if normalized_question == question.strip()
        else (
            f"{question}\n\n"
            f"Interpret obvious misspellings or merged words as: {normalized_question}"
        )
    )
    agent_type = classify_question(question)
    logger.info("Router | classified={!r} | question={!r}", agent_type, question)

    if agent_type == "market":
        result = _market_agent.run(effective_question)
        return agent_type, result
    if agent_type == "housing":
        result = _housing_agent.run(effective_question)
        return agent_type, result

    return None, AgentResult(answer=_OUT_OF_SCOPE_ANSWER)
