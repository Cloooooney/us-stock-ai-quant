from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from models.walk_forward import Config, FEATURES, portfolio_returns

FUNDAMENTALS = ["revenue_growth", "net_margin", "cash_quality", "roa",
                "liabilities_to_assets", "capex_to_revenue"]


def merge_fundamentals(dataset: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
    parts = []
    right_cols = ["available_date", "filed", "fiscal_end", *FUNDAMENTALS]
    for ticker, left in dataset.groupby("ticker", sort=False):
        right = fundamentals.loc[fundamentals["ticker"].eq(ticker), right_cols].sort_values("available_date")
        left = left.sort_values("date")
        if right.empty:
            joined = left.copy()
            for col in right_cols:
                joined[col] = pd.NaT if col in {"available_date", "filed", "fiscal_end"} else np.nan
        else:
            joined = pd.merge_asof(left, right, left_on="date", right_on="available_date", direction="backward")
        parts.append(joined)
    out = pd.concat(parts, ignore_index=True)
    known = out["available_date"].notna()
    assert (out.loc[known, "available_date"] <= out.loc[known, "date"]).all()
    out["fundamental_age_days"] = (out["date"] - out["filed"]).dt.days
    stale = out["fundamental_age_days"] > 550
    out.loc[stale, FUNDAMENTALS] = np.nan
    return out


def add_cross_sectional_ranks(data: pd.DataFrame) -> pd.DataFrame:
    d = data.copy()
    for col in [*FEATURES, *FUNDAMENTALS]:
        # Winsorization is implicit in ranks. Missing fundamentals receive the
        # cross-sectional neutral value and no missingness flag is exposed.
        d[f"rank_{col}"] = d.groupby("date")[col].rank(pct=True).fillna(.5)
    d["target_relative"] = d["target_return"] - d.groupby("date")["target_return"].transform("mean")
    return d


def walk_forward_ridge(data: pd.DataFrame, feature_names: list[str], cfg: Config) -> pd.DataFrame:
    ranked = add_cross_sectional_ranks(data)
    cols = [f"rank_{x}" for x in feature_names]
    outputs, model, last_fit = [], None, None
    dates = sorted(ranked.loc[ranked["date"] >= pd.Timestamp(cfg.first_prediction), "date"].unique())
    for raw_date in dates:
        date = pd.Timestamp(raw_date)
        train = ranked.loc[(ranked["date"] >= date - pd.DateOffset(years=cfg.train_years)) &
                           (ranked["date"] < date) & (ranked["label_known_date"] <= date)]
        test = ranked.loc[ranked["date"].eq(date)].copy()
        if len(train) < 5000 or test.empty:
            continue
        fit_period = (date.year, (date.month - 1) // 3)
        if model is None or fit_period != last_fit:
            model = Ridge(alpha=100.0)
            model.fit(train[cols], train["target_relative"])
            last_fit = fit_period
        test["prediction"] = model.predict(test[cols])
        outputs.append(test)
    return pd.concat(outputs, ignore_index=True)


def run_variant(data: pd.DataFrame, features: list[str], cfg: Config):
    pred = walk_forward_ridge(data, features, cfg)
    returns, holdings = portfolio_returns(pred, cfg)
    return pred, returns, holdings
