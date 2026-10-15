import numpy as np
import pandas as pd

from models.v6_factor import (
    attach_valuation_features,
    merge_quarterly_fundamentals,
    run_v6_variant,
    score_factors,
)
from models.walk_forward import Config


def test_point_in_time_merge_blocks_future_filings_and_expires_stale_values():
    dataset = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-03-31", "2024-12-31"]),
        "ticker": ["TEST", "TEST", "TEST"],
    })
    fundamentals = pd.DataFrame({
        "ticker": ["TEST"],
        "accession": ["filing-1"],
        "form": ["10-K"],
        "filed": pd.to_datetime(["2024-02-01"]),
        "available_date": pd.to_datetime(["2024-02-02"]),
        "fiscal_end": pd.to_datetime(["2023-12-31"]),
        "ttm_revenue": [1_000.0],
        "ttm_net_income": [100.0],
        "ttm_operating_cash_flow": [120.0],
        "ttm_capex": [20.0],
        "revenue_growth": [0.10],
        "net_margin": [0.10],
        "cash_quality": [1.20],
        "roa": [0.20],
        "liabilities_to_assets": [0.40],
        "capex_to_revenue": [0.02],
        "free_cash_flow_margin": [0.10],
        "accruals_to_assets": [-0.04],
        "shares_outstanding": [10.0],
    })

    merged = merge_quarterly_fundamentals(dataset, fundamentals, max_age_days=200)

    assert np.isnan(merged.loc[merged["date"].eq("2024-01-31"), "ttm_revenue"]).all()
    march = merged.loc[merged["date"].eq("2024-03-31")].iloc[0]
    assert march["ttm_revenue"] == 1_000
    assert march["available_date"] <= march["date"]
    assert np.isnan(merged.loc[merged["date"].eq("2024-12-31"), "ttm_revenue"]).all()


def test_valuation_uses_diluted_shares_and_rejects_invalid_market_cap():
    data = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
        "ticker": ["GOOD", "BAD"],
        "shares_outstanding": [10.0, 0.0],
        "weighted_average_shares": [12.0, 0.0],
        "ttm_revenue": [1_000.0, 1_000.0],
        "ttm_net_income": [100.0, 100.0],
        "ttm_operating_cash_flow": [150.0, 150.0],
        "ttm_capex": [50.0, 50.0],
    })
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
        "ticker": ["GOOD", "BAD"],
        "close": [20.0, 20.0],
        "adj_close": [2.0, 2.0],
    })

    valued = attach_valuation_features(data, prices).set_index("ticker")

    assert valued.loc["GOOD", "market_cap"] == 240
    assert np.isclose(valued.loc["GOOD", "sales_yield"], 1_000 / 240)
    assert np.isclose(valued.loc["GOOD", "earnings_yield"], 100 / 240)
    assert np.isclose(valued.loc["GOOD", "fcf_yield"], 100 / 240)
    assert np.isnan(valued.loc["BAD", "market_cap"])


def test_valuation_restates_historical_shares_for_later_stock_splits():
    data = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-31"]),
        "ticker": ["SPLIT"],
        "filed": pd.to_datetime(["2019-12-31"]),
        "shares_outstanding": [20.0],
        "weighted_average_shares": [20.0],
        "ttm_revenue": [1_000.0],
        "ttm_net_income": [100.0],
        "ttm_operating_cash_flow": [150.0],
        "ttm_capex": [50.0],
    })
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-31", "2024-06-26"]),
        "ticker": ["SPLIT", "SPLIT"],
        "close": [10.0, 20.0],
        "adj_close": [10.0, 20.0],
        "stock_splits": [0.0, 50.0],
    })

    valued = attach_valuation_features(data, prices).iloc[0]

    assert valued["share_split_factor"] == 50
    assert valued["split_adjusted_shares"] == 1_000
    assert valued["market_cap"] == 10_000


def test_valuation_reconciles_million_share_units_in_either_sec_field():
    data = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
        "ticker": ["DILUTED_IN_MILLIONS", "ENTITY_IN_THOUSANDS"],
        "shares_outstanding": [714_000_000.0, 146_000.0],
        "weighted_average_shares": [717.0, 147_000_000.0],
        "ttm_revenue": [1.0, 1.0],
        "ttm_net_income": [1.0, 1.0],
        "ttm_operating_cash_flow": [1.0, 1.0],
        "ttm_capex": [0.0, 0.0],
    })
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
        "ticker": ["DILUTED_IN_MILLIONS", "ENTITY_IN_THOUSANDS"],
        "close": [1.0, 1.0],
    })

    valued = attach_valuation_features(data, prices).set_index("ticker")

    assert valued.loc["DILUTED_IN_MILLIONS", "valuation_shares"] == 714_000_000
    assert valued.loc["ENTITY_IN_THOUSANDS", "valuation_shares"] == 147_000_000


def _factor_frame():
    rows = []
    for ticker, sign in [("HIGH", 1.0), ("LOW", -1.0), ("MISSING", np.nan)]:
        rows.append({
            "date": pd.Timestamp("2024-01-31"),
            "ticker": ticker,
            "mom_126": sign,
            "mom_252": sign,
            "revenue_growth": sign,
            "net_margin": sign,
            "roa": sign,
            "cash_quality": sign,
            "free_cash_flow_margin": sign,
            "accruals_to_assets": -sign if pd.notna(sign) else np.nan,
            "liabilities_to_assets": -sign if pd.notna(sign) else np.nan,
            "sales_yield": sign,
            "earnings_yield": sign,
            "fcf_yield": sign,
        })
    return pd.DataFrame(rows)


def test_factor_directions_missing_neutrality_and_equal_sleeve_weights():
    scored = score_factors(_factor_frame()).set_index("ticker")

    assert scored.loc["HIGH", "v6_score"] > scored.loc["LOW", "v6_score"]
    assert scored.loc["MISSING", "momentum_score"] == 0.5
    assert scored.loc["MISSING", "quality_score"] == 0.5
    assert scored.loc["MISSING", "value_score"] == 0.5
    expected = scored[["momentum_score", "quality_score", "value_score"]].mean(axis=1)
    assert np.allclose(scored["v6_score"], expected)
    assert np.allclose(scored["prediction"], scored["v6_score"])


def test_portfolio_selection_is_deterministic_and_keeps_next_open_execution():
    frame = pd.concat([_factor_frame().assign(
        execution_date=pd.Timestamp("2024-02-01"), target_return=[0.03, -0.01, 0.00]
    )] * 2, ignore_index=True).drop_duplicates(["date", "ticker"])
    cfg = Config(top_n=2, cost_bps=10)

    _, returns_a, holdings_a = run_v6_variant(frame.sample(frac=1, random_state=1), cfg)
    _, returns_b, holdings_b = run_v6_variant(frame.sample(frac=1, random_state=2), cfg)

    assert holdings_a["ticker"].tolist() == holdings_b["ticker"].tolist()
    assert (holdings_a["execution_date"] > holdings_a["date"]).all()
    assert returns_a.loc[0, "net_return"] == returns_b.loc[0, "net_return"]
