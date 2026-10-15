import numpy as np
import pandas as pd

from backtests.run_v6_factor import (
    align_benchmarks,
    apply_cost_scenario,
    drop_best_months,
    safe_metrics,
    spy_returns_for_horizons,
)


def _strategy_returns():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-02-29"]),
        "gross_return": [0.10, 0.20],
        "net_return": [0.099, 0.1995],
        "turnover": [1.0, 0.5],
    })


def test_benchmarks_are_aligned_to_identical_strategy_months():
    scored = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29"]),
        "target_return": [0.02, 0.04, -0.01, 0.03],
    })
    spy = pd.DataFrame({
        "date": pd.to_datetime(["2023-12-29", "2024-01-31", "2024-02-29"]),
        "spy_return": [0.50, 0.01, 0.02],
    })

    aligned = align_benchmarks(_strategy_returns(), scored, spy)

    assert aligned["date"].tolist() == pd.to_datetime(["2024-01-31", "2024-02-29"]).tolist()
    assert np.allclose(aligned["equal_weight_return"], [0.03, 0.01])
    assert np.allclose(aligned["spy_return"], [0.01, 0.02])


def test_cost_stress_is_recomputed_from_gross_return_and_turnover():
    stressed = apply_cost_scenario(_strategy_returns(), cost_bps=25)
    assert np.allclose(stressed, [0.0975, 0.19875])


def test_best_month_removal_drops_exactly_the_requested_strategy_months():
    reduced, removed = drop_best_months(_strategy_returns(), count=1, column="net_return")
    assert removed.tolist() == pd.to_datetime(["2024-02-29"]).tolist()
    assert reduced["date"].tolist() == pd.to_datetime(["2024-01-31"]).tolist()


def test_empty_period_metrics_are_explicit_instead_of_crashing():
    result = safe_metrics(pd.Series(dtype=float))
    assert result["months"] == 0
    assert np.isnan(result["annual_return"])
    assert np.isnan(result["max_drawdown"])


def test_spy_horizon_uses_the_dominant_calendar_not_an_early_delisting_fallback():
    scored = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31"] * 3),
        "execution_date": pd.to_datetime(["2024-02-01", "2024-02-01", "2024-02-01"]),
        "exit_date": pd.to_datetime(["2024-03-01", "2024-03-01", "2024-02-01"]),
    })
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2024-02-01", "2024-03-01"]),
        "ticker": ["SPY", "SPY"],
        "open": [100.0, 110.0],
        "close": [100.0, 110.0],
        "adj_close": [100.0, 110.0],
    })

    result = spy_returns_for_horizons(prices, scored)

    assert np.isclose(result.loc[0, "spy_return"], 0.10)
