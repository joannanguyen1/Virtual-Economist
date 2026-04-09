from __future__ import annotations

import pytest
from backend.app.agents import router


def test_macro_market_questions_use_keyword_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious macro questions")
        ),
    )

    assert router.classify_question("What is the current unemployment rate?") == "market"


def test_housing_questions_use_keyword_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious housing questions")
        ),
    )

    assert router.classify_question("What is the median rent in Austin, Texas?") == "housing"


def test_city_alias_housing_questions_use_keyword_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious city alias housing questions")
        ),
    )

    assert router.classify_question("whats the median price in philly") == "housing"


def test_weather_questions_use_keyword_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious weather questions")
        ),
    )

    assert router.classify_question("What is the weather forecast in Austin, Texas?") == "housing"


def test_season_questions_use_keyword_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious season questions")
        ),
    )

    assert router.classify_question("What season is it in Philadelphia?") == "housing"


def test_unrelated_questions_fall_back_to_out_of_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called when fallback is enough")
        ),
    )

    assert router._keyword_fallback("Write me a haiku about pizza.") == "out_of_scope"


def test_market_screening_questions_use_keyword_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious market screening questions")
        ),
    )

    assert (
        router.classify_question("Which technology companies have strong buy ratings?") == "market"
    )


def test_quant_market_questions_use_keyword_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious quant market questions")
        ),
    )

    assert router.classify_question("What is Apple's Sharpe ratio over the last year?") == "market"


def test_merged_typo_market_questions_route_to_market(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        router,
        "invoke_claude",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Titan should not be called for obvious typo-tolerant market questions")
        ),
    )

    assert router.classify_question("what is appleshigh over the last 90 days") == "market"


def test_route_question_returns_scope_message_for_unrelated_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(router, "classify_question", lambda question: "out_of_scope")

    agent_type, result = router.route_question("Write me a haiku about pizza.")

    assert agent_type is None
    assert "U.S. housing/city questions and stock/market questions" in result.answer
