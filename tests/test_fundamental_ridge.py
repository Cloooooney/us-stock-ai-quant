import pandas as pd
from models.fundamental_ridge import merge_fundamentals


def test_asof_merge_never_uses_future_filing():
    market = pd.DataFrame({"ticker": ["A", "A"], "date": pd.to_datetime(["2020-01-31", "2020-02-29"])})
    fund = pd.DataFrame({"ticker": ["A"], "available_date": pd.to_datetime(["2020-02-01"]),
                         "filed": pd.to_datetime(["2020-01-31"]), "fiscal_end": pd.to_datetime(["2019-12-31"]),
                         "revenue_growth": [.1], "net_margin": [.1], "cash_quality": [1.], "roa": [.1],
                         "liabilities_to_assets": [.5], "capex_to_revenue": [.05]})
    out = merge_fundamentals(market, fund)
    assert pd.isna(out.loc[out.date.eq("2020-01-31"), "revenue_growth"]).all()
    assert out.loc[out.date.eq("2020-02-29"), "revenue_growth"].iloc[0] == .1


def test_stale_fundamentals_expire():
    market = pd.DataFrame({"ticker": ["A"], "date": pd.to_datetime(["2022-01-01"])})
    fund = pd.DataFrame({"ticker": ["A"], "available_date": pd.to_datetime(["2020-01-02"]),
                         "filed": pd.to_datetime(["2020-01-01"]), "fiscal_end": pd.to_datetime(["2019-12-31"]),
                         "revenue_growth": [.1], "net_margin": [.1], "cash_quality": [1.], "roa": [.1],
                         "liabilities_to_assets": [.5], "capex_to_revenue": [.05]})
    out = merge_fundamentals(market, fund)
    assert out["fundamental_age_days"].iloc[0] > 550
    assert pd.isna(out["revenue_growth"].iloc[0])
