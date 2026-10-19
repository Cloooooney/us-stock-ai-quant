import math

import numpy as np
import pandas as pd
import pytest

from research.factor_lab import (add_net_issuance, bonferroni_t, monthly_panel, registry, seasonal_signal,
                                 summarize)
from research.factor_attribution import FACTORS
from research.presample_check import reading


def snap(fiscal_end, filed, shares, accession, ticker="AAA"):
    filed = pd.Timestamp(filed)
    return {"ticker": ticker, "accession": accession, "fiscal_end": pd.Timestamp(fiscal_end), "filed": filed,
            "available_date": filed + pd.Timedelta(days=1), "weighted_average_shares": shares,
            "shares_outstanding": np.nan}


def test_bonferroni_threshold_for_four_candidates():
    assert bonferroni_t(4) == pytest.approx(2.2414, abs=1e-3)
    assert bonferroni_t(1) == pytest.approx(1.6449, abs=1e-3)


def test_net_issuance_adjusts_for_splits_between_filings_only():
    fundamentals = pd.DataFrame([
        snap("2023-03-31", "2023-05-01", 100.0, "a"),
        snap("2024-03-31", "2024-05-01", 210.0, "b"),            # 2-for-1 split in between, then 5% issuance
        snap("2025-03-31", "2025-05-01", 189.0, "c"),            # 10% buyback, no split in between
        snap("2025-06-30", "2025-08-01", 189.0, "d"),            # no snapshot one year earlier
    ])
    splits = pd.DataFrame({"ticker": ["AAA", "AAA"], "date": pd.to_datetime(["2023-09-01", "2026-01-01"]),
                           "stock_splits": [2.0, 3.0]})
    out = add_net_issuance(fundamentals, splits).set_index("accession")
    assert out.loc["b", "net_issuance"] == pytest.approx(math.log(1.05))
    assert out.loc["c", "net_issuance"] == pytest.approx(math.log(0.9))   # the 2026 split is in the future
    assert np.isnan(out.loc["a", "net_issuance"]) and np.isnan(out.loc["d", "net_issuance"])


def test_net_issuance_rejects_unit_errors_and_later_filed_prior_snapshots():
    fundamentals = pd.DataFrame([
        snap("2023-03-31", "2023-05-01", 100.0, "a"),
        snap("2024-03-31", "2024-05-01", 100_000.0, "b"),         # thousands-vs-units error
        snap("2024-06-30", "2024-08-01", 100.0, "c"),
        snap("2023-06-30", "2024-09-01", 50.0, "late"),           # prior-year period filed after "c"
    ])
    out = add_net_issuance(fundamentals, pd.DataFrame(columns=["ticker", "date", "stock_splits"]))
    out = out.set_index("accession")
    assert np.isnan(out.loc["b", "net_issuance"])
    assert np.isnan(out.loc["c", "net_issuance"])                 # only "late" matches, and it was not yet filed


def test_seasonality_uses_only_completed_prior_years():
    days = pd.bdate_range("2018-01-01", "2024-12-31")
    month = days.month
    # March is +10% every year; other months are flat. One huge move in March 2024 must not leak into 2024.
    daily_growth = np.where(month == 3, 1.10 ** (1 / 22), 1.0)
    price = 100 * np.cumprod(daily_growth)
    price[(days >= "2024-03-01") & (days <= "2024-03-31")] *= 5
    prices = pd.DataFrame({"ticker": "AAA", "date": days, "adj_close": price})
    signal = seasonal_signal(prices).set_index("holding_month")["seasonality"]
    march_2023 = signal.loc[pd.Period("2023-03", "M")]
    assert march_2023 == pytest.approx(0.10, abs=0.02)            # mean of March 2018-2022
    assert signal.loc[pd.Period("2024-04", "M")] == pytest.approx(0.0, abs=1e-9)
    assert pd.Period("2020-03", "M") not in signal.index           # only two prior Marches


def panel_data(predictive: bool, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in pd.date_range("2012-01-31", "2024-06-30", freq="ME"):
        x = rng.normal(size=200)
        rows.append(pd.DataFrame({"date": d, "ticker": [f"T{i}" for i in range(200)],
                                  "execution_date": d + pd.Timedelta(days=1), "candidate": x,
                                  "v6_score": rng.uniform(size=200),
                                  "target_return": (0.01 * x if predictive else 0) + rng.normal(0, 0.06, 200)}))
    months = pd.period_range("2011-01", "2025-01", freq="M")
    factors = pd.DataFrame(rng.normal(0, 0.03, (len(months), len(FACTORS))), index=months, columns=FACTORS)
    factors["rf"] = 0.001
    return pd.concat(rows, ignore_index=True), factors


def test_evaluation_passes_a_real_signal_and_rejects_noise():
    data, factors = panel_data(True)
    good = summarize(monthly_panel(data, "candidate", 1), factors, bonferroni_t(4))
    assert good["passes"] and good["eligible_for_v8"] and good["months"] == 132
    bad = summarize(monthly_panel(data, "candidate", -1), factors, bonferroni_t(4))
    assert not bad["passes"]
    data, factors = panel_data(False, seed=3)
    noise = summarize(monthly_panel(data, "candidate", 1), factors, bonferroni_t(4))
    assert not noise["passes"]


def test_turnover_and_missing_values():
    data, _ = panel_data(False, seed=1)
    data.loc[data["ticker"].isin([f"T{i}" for i in range(150)]), "candidate"] = np.nan
    panel = monthly_panel(data, "candidate", 1)
    assert panel["coverage"].iloc[0] == pytest.approx(0.25)
    assert panel["turnover"].iloc[0] == 1.0 and 0 <= panel["turnover"].iloc[1:].mean() <= 1


def test_registry_records_every_candidate():
    table = registry({"a": {"passes": False}, "b": {"passes": True}}, 2.24)
    assert {"a", "b"} <= set(table["candidate"])


def test_presample_reading_rule():
    assert reading(0.002, 1.8) == "consistent_with_edge"
    assert reading(-0.001, 2.5) == "inconsistent_with_edge"
    assert reading(0.002, 1.0) == "inconclusive"


def test_build_candidates_end_to_end():
    from research.factor_lab import build_candidates

    days = pd.bdate_range("2016-01-01", "2020-12-31")
    prices = pd.concat([pd.DataFrame({"ticker": t, "date": days, "close": 10.0 + i,
                                      "adj_close": (10.0 + i) * np.linspace(1, 2, len(days)),
                                      "stock_splits": 0.0}) for i, t in enumerate(["AAA", "BBB"])])
    dataset = pd.DataFrame({"date": pd.to_datetime(["2020-06-30", "2020-06-30"]), "ticker": ["AAA", "BBB"],
                            "execution_date": pd.to_datetime(["2020-07-01"] * 2), "target_return": [0.01, 0.02],
                            "drawdown_252": [-0.1, -0.2], "mom_21": [0.03, -0.02],
                            "mom_126": [0.1, 0.2], "mom_252": [0.2, 0.1]})
    fundamentals = pd.DataFrame([{**snap("2019-03-31", "2019-05-01", 100.0, "a1"), "form": "10-Q"},
                                 {**snap("2020-03-31", "2020-05-01", 95.0, "a2"), "form": "10-Q"}])
    out = build_candidates(dataset, fundamentals, prices).set_index("ticker")
    assert out.loc["AAA", "net_issuance"] == pytest.approx(math.log(0.95))
    assert np.isnan(out.loc["BBB", "net_issuance"])
    assert out.loc["AAA", "short_reversal"] == pytest.approx(-0.03)
    assert out.loc["BBB", "high_52w"] == pytest.approx(-0.2)
    assert out["seasonality"].notna().all()                      # July 2017-2019 are available
    assert "v6_score" in out


def test_presample_excess_stats():
    from research.presample_check import excess_stats

    execution = pd.Series(pd.date_range("2012-02-01", periods=72, freq="MS"))
    rng = np.random.default_rng(7)
    benchmark = pd.Series(rng.normal(0.01, 0.04, 72))
    strategy = benchmark + 0.004 + rng.normal(0, 0.005, 72)
    months = pd.period_range("2011-01", "2018-12", freq="M")
    factors = pd.DataFrame(rng.normal(0, 0.03, (len(months), len(FACTORS))), index=months, columns=FACTORS)
    stats = excess_stats(strategy, benchmark, execution, factors)
    assert stats["months"] == 72 and stats["reading"] == "consistent_with_edge"
    assert stats["annual_excess"] == pytest.approx(0.048, abs=0.01) and "factor_alpha_t" in stats
