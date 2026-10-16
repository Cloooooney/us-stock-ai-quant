import numpy as np
import pandas as pd
import pytest

from app.analysis import (Finding, clean_ticker, concentration, findings, metrics, monthly_returns,
                          normalize_weights, portfolio_returns, run_checkup)
from app.i18n import TEXT, finding_text
from research.factor_attribution import FACTORS


def daily_prices(columns: dict[str, float], start="2018-01-01", end="2023-12-29", seed=0):
    """Business-day adjusted closes growing at a constant daily rate plus noise."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    data = {name: 100 * np.cumprod(1 + rate + rng.normal(0, 0.005, len(days))) for name, rate in columns.items()}
    return pd.DataFrame(data, index=days)


def test_clean_ticker_and_weights():
    assert clean_ticker(" brk.b ") == "BRK-B"
    weights, problems = normalize_weights(pd.DataFrame(
        {"ticker": ["aapl", "MSFT", "AAPL", "", "xyz"], "weight": [30, 50, 20, 10, -5]}))
    assert weights.to_dict() == pytest.approx({"AAPL": 0.5, "MSFT": 0.5})
    assert "duplicates_combined" in problems and "invalid_weight:XYZ" in problems
    with pytest.raises(ValueError):
        normalize_weights(pd.DataFrame({"ticker": ["A"], "weight": [0]}))


def test_monthly_returns_drop_unfinished_month():
    prices = daily_prices({"A": 0.0}, start="2026-01-01", end="2026-10-16")
    months = monthly_returns(prices)
    assert str(months.index.min()) == "2026-02" and str(months.index.max()) == "2026-09"
    finished = monthly_returns(daily_prices({"A": 0.0}, start="2026-01-01", end="2026-09-30"))
    assert str(finished.index.max()) == "2026-09"


def test_portfolio_is_monthly_rebalanced_over_common_history():
    returns = pd.DataFrame({"A": [0.10, 0.10, -0.10], "B": [np.nan, 0.00, 0.20]},
                           index=pd.period_range("2024-01", periods=3, freq="M"))
    series, info = portfolio_returns(returns, pd.Series({"A": 0.5, "B": 0.5}))
    assert series.tolist() == pytest.approx([0.05, 0.05])
    assert info["limited_by"] == "B" and info["first_month"] == "2024-02"
    with pytest.raises(ValueError, match="no price history"):
        portfolio_returns(returns, pd.Series({"C": 1.0}))


def test_metrics_and_concentration():
    stats = metrics(pd.Series([0.10, -0.50, 0.20]))
    assert stats["max_drawdown"] == pytest.approx(-0.50)
    assert stats["total_return"] == pytest.approx(1.1 * 0.5 * 1.2 - 1)
    conc = concentration(pd.Series({"A": 0.5, "B": 0.25, "C": 0.25}))
    assert conc["largest_ticker"] == "A" and conc["effective_holdings"] == pytest.approx(1 / 0.375)


def test_findings_flag_concentration_and_an_index_that_did_better():
    found = findings({"annual_return": 0.05, "sharpe_0rf": 0.3, "max_drawdown": -0.5, "months": 60},
                     {"largest_ticker": "TSLA", "largest_weight": 0.6, "effective_holdings": 2.0},
                     {"beta": 1.5}, {"annual_return": 0.10, "sharpe_0rf": 0.6, "months": 60}, None,
                     {"months": 60, "limited_by": None, "first_month": "2021-01"})
    keys = [f.key for f in found]
    for key in ["large_position", "few_holdings", "high_beta", "deep_drawdown", "index_was_better",
                "attribution_skipped", "past_not_future"]:
        assert key in keys


def test_every_finding_renders_in_both_languages():
    samples = [Finding("short_history", "warning", {"months": 12}),
               Finding("limited_by", "info", {"ticker": "X", "first": "2020-01"}),
               Finding("large_position", "warning", {"ticker": "X", "weight": 0.4}),
               Finding("few_holdings", "warning", {"n": 2.5}),
               Finding("high_beta", "warning", {"beta": 1.4}), Finding("low_beta", "info", {"beta": 0.6}),
               Finding("deep_drawdown", "warning", {"drawdown": -0.45}),
               Finding("index_was_better", "warning", {"gap": -0.03}),
               Finding("beat_index_history", "good", {"gap": 0.02}), Finding("mixed_vs_index", "info"),
               Finding("attribution_skipped", "info", {"months": 36}),
               Finding("alpha_significant", "good", {"alpha": 0.04, "t": 2.3}),
               Finding("no_alpha", "info", {"alpha": 0.01, "t": 0.4, "r2": 0.9}),
               Finding("factor_tilts", "info", {"tilts": [{"factor": "value", "beta": 0.4, "direction": "positive"},
                                                          {"factor": "momentum", "beta": -0.3, "direction": "negative"}]}),
               Finding("past_not_future", "info")]
    for finding in samples:
        for lang in ("zh", "en"):
            assert finding_text(finding, lang)
    assert all({"zh", "en"} <= set(entry) for entry in TEXT.values())
    assert "价值" in finding_text(samples[-2], "zh") and "momentum" in finding_text(samples[-2], "en")


def test_run_checkup_end_to_end_with_factors():
    prices = daily_prices({"AAA": 0.0006, "BBB": 0.0003, "SPY": 0.0004, "RSP": 0.0003})
    months = pd.period_range("2017-01", "2024-06", freq="M")
    rng = np.random.default_rng(5)
    factors = pd.DataFrame(rng.normal(0, 0.03, (len(months), len(FACTORS))), index=months, columns=FACTORS)
    factors["rf"] = 0.001
    result = run_checkup(pd.DataFrame({"ticker": ["AAA", "BBB"], "weight": [60, 40]}), prices, factors)
    assert result.info["months"] == len(result.portfolio) == 71  # Feb 2018 to Dec 2023
    assert set(result.benchmarks) == {"SPY", "RSP"}
    assert result.attribution is not None and result.attribution["months"] == 71
    assert result.concentration["largest_ticker"] == "AAA"
    keys = [f.key for f in result.findings]
    assert "large_position" in keys and keys[-1] == "past_not_future"
