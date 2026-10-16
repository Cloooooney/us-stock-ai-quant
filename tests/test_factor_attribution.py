import numpy as np
import pandas as pd
import pytest

from research.factor_attribution import (FACTORS, attribute, describe, load_strategy_returns,
                                         ols_newey_west, parse_french_csv, run_attribution)

FIVE = """This file was created using the 202608 CRSP database.
The 1-month TBill rate data until 202405 are from Ibbotson Associates.

,Mkt-RF,SMB,HML,RMW,CMA,RF
202606,   1.10,  -0.20,   0.30,   0.40,  -0.10,   0.35
202607,  -2.00,   0.50, -99.99,   0.10,   0.20,   0.36

  Annual Factors: January-December
,Mkt-RF,SMB,HML,RMW,CMA,RF
2025,  18.00,   1.00,   2.00,   3.00,   4.00,   4.10
"""


def test_parse_french_csv_reads_monthly_table_only():
    frame = parse_french_csv(FIVE)
    assert list(frame.columns) == ["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]
    assert [str(p) for p in frame.index] == ["2026-06", "2026-07"]
    assert frame.loc[pd.Period("2026-06", "M"), "mkt_rf"] == pytest.approx(0.011)
    assert np.isnan(frame.loc[pd.Period("2026-07", "M"), "hml"])  # -99.99 is a missing value


def synthetic_factors(n=240, seed=0, start="2006-01"):
    rng = np.random.default_rng(seed)
    index = pd.period_range(start, periods=n, freq="M")
    data = rng.normal(0, 0.04, size=(n, len(FACTORS)))
    frame = pd.DataFrame(data, index=index, columns=FACTORS)
    frame["rf"] = 0.002
    return frame


def test_ols_recovers_coefficients_and_lag_zero_matches_white_errors():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(500, 2))
    y = 0.01 + x @ np.array([0.8, -0.3]) + rng.normal(0, 0.05, 500)
    fit = ols_newey_west(y, x, lags=0)
    assert fit["beta"] == pytest.approx([0.01, 0.8, -0.3], abs=0.01)
    design = np.column_stack([np.ones(500), x])
    resid = y - design @ fit["beta"]
    bread = np.linalg.inv(design.T @ design)
    white = bread @ (design.T * resid**2) @ design @ bread * 500 / 497
    assert fit["se"] == pytest.approx(np.sqrt(np.diag(white)))


def test_attribute_separates_alpha_from_factor_exposure():
    factors = synthetic_factors()
    rng = np.random.default_rng(2)
    excess = 0.004 + 1.0 * factors["mkt_rf"] + 0.5 * factors["hml"] + rng.normal(0, 0.01, len(factors))
    result = attribute(excess + factors["rf"], factors, factors["rf"])
    assert result["alpha_annual"] == pytest.approx(0.048, abs=0.02)
    assert result["beta_mkt_rf"] == pytest.approx(1.0, abs=0.05)
    assert result["beta_hml"] == pytest.approx(0.5, abs=0.05)
    assert result["alpha_t"] > 2
    assert abs(result["t_smb"]) < 3


def test_repository_returns_align_to_execution_month():
    returns = load_strategy_returns()
    assert {"v4_fundamental_ridge", "point_in_time_equal_weight", "spy"}.issubset(returns.columns)
    assert returns.index.is_unique and returns.index.is_monotonic_increasing
    # The first signal is 2018-01-31; it executes and earns in February 2018.
    assert returns.index.min() == pd.Period("2018-02", "M")


def test_run_attribution_end_to_end():
    factors = synthetic_factors(n=110, start="2017-01")
    index = factors.index
    rng = np.random.default_rng(3)
    ew = factors["rf"] + factors["mkt_rf"] + rng.normal(0, 0.01, len(index))
    returns = pd.DataFrame({"model": ew + 0.3 * factors["rmw"], "point_in_time_equal_weight": ew,
                            "spy": factors["rf"] + factors["mkt_rf"]}, index=index)
    returns = returns.loc[returns.index >= pd.Period("2018-01", "M")]
    table = run_attribution(returns, factors)
    active = table.query("strategy == 'model' and regression == 'active_vs_equal_weight' and split == 'full_oos'")
    assert active["beta_rmw"].iloc[0] == pytest.approx(0.3, abs=0.1)
    assert "Factor Attribution" in describe(table)


def test_etf_returns_use_backtest_execution_windows_and_compare():
    from research.factor_attribution import compare_to_etfs, etf_holding_returns

    days = pd.bdate_range("2017-12-01", "2021-03-31")
    etf = pd.DataFrame({"ticker": "RSP", "date": days, "close": 100.0,
                        "adj_close": [100.0 * 1.0004 ** i for i in range(len(days))]})
    etf["open"] = etf["close"]
    execution = pd.Series([d for d in days if d == days[days.to_period("M") == d.to_period("M")][0]])
    etf_returns = etf_holding_returns(etf, execution)
    first, second = execution.iloc[0], execution.iloc[1]
    expected = etf.set_index("date").loc[second, "adj_close"] / etf.set_index("date").loc[first, "adj_close"] - 1
    assert etf_returns.loc[first.to_period("M"), "RSP"] == pytest.approx(expected)

    strategy = pd.DataFrame({"model": etf_returns["RSP"] + 0.001}, index=etf_returns.index)
    strategy = strategy.loc[strategy.index >= pd.Period("2018-01", "M")]
    table = compare_to_etfs(strategy, etf_returns)
    row = table.query("split == 'full_oos'").iloc[0]
    assert row["excess_annual"] == pytest.approx(0.012)
    assert row["hit_rate"] == 1.0


def test_benchmark_etf_validation_rejects_bad_data():
    from data_pipeline.update_benchmark_etfs import validate

    days = pd.bdate_range("2026-01-01", "2026-02-27")
    good = pd.concat([pd.DataFrame({"ticker": t, "date": days, "open": 10.0, "close": 10.0,
                                    "adj_close": 10.0, "volume": 1}) for t in ["RSP", "QUAL"]])
    assert validate(good, None, ["RSP", "QUAL"])["tickers"] == ["QUAL", "RSP"]
    with pytest.raises(ValueError, match="no rows"):
        validate(good, None, ["RSP", "QUAL", "MTUM"])
    with pytest.raises(ValueError, match="stale"):
        validate(good.loc[~(good["ticker"].eq("QUAL") & (good["date"] > "2026-02-10"))], None, ["RSP", "QUAL"])
    with pytest.raises(ValueError, match="regressed"):
        validate(good, good.assign(date=good["date"] + pd.Timedelta(days=30)), ["RSP", "QUAL"])
    bad = good.copy(); bad.iloc[0, bad.columns.get_loc("close")] = 0.0
    with pytest.raises(ValueError, match="non-positive"):
        validate(bad, None, ["RSP", "QUAL"])


def test_active_regression_uses_the_models_own_universe():
    factors = synthetic_factors(n=110, start="2017-01")
    rng = np.random.default_rng(4)
    shared = factors["rf"] + factors["mkt_rf"] + rng.normal(0, 0.01, len(factors))
    own = shared + 0.5 * factors["smb"]
    returns = pd.DataFrame({"model": own + 0.2 * factors["hml"], "model::equal_weight": own,
                            "point_in_time_equal_weight": shared, "spy": factors["rf"] + factors["mkt_rf"]},
                           index=factors.index)
    returns = returns.loc[returns.index >= pd.Period("2018-01", "M")]
    table = run_attribution(returns, factors)
    active = table.query("strategy == 'model' and regression == 'active_vs_equal_weight' and split == 'full_oos'")
    assert active["beta_smb"].iloc[0] == pytest.approx(0.0, abs=0.05)
    assert active["beta_hml"].iloc[0] == pytest.approx(0.2, abs=0.05)
    assert "model::equal_weight" not in set(table["strategy"])


def test_repository_includes_v6_with_its_own_universe():
    returns = load_strategy_returns()
    assert {"v6_factor_blend", "v6_factor_blend::equal_weight"}.issubset(returns.columns)
