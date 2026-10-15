from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FEATURES = ["mom_21", "mom_63", "mom_126", "mom_252", "vol_21", "vol_63",
            "drawdown_252", "trend_200", "volume_change_63", "reversal_5"]


@dataclass(frozen=True)
class Config:
    first_prediction: str = "2018-01-01"
    train_years: int = 5
    top_n: int = 20
    cost_bps: float = 10.0
    seed: int = 42


def load_source(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    prices = pd.read_parquet(root / "data/pit/prices.parquet")
    intervals = pd.read_parquet(root / "data/pit/membership_intervals.parquet")
    recycled = set(pd.read_csv(root / "data/pit/recycled_tickers.csv")["ticker"])
    prices = prices.loc[(prices["date"] >= pd.Timestamp("2011-01-01")) & ~prices["ticker"].isin(recycled)].copy()
    return prices, intervals, recycled


def _features(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("date").copy()
    px, ret = g["adj_close"], g["adj_close"].pct_change()
    g["adj_open"] = g["open"] * g["adj_close"] / g["close"]
    for n in (21, 63, 126, 252):
        g[f"mom_{n}"] = px.pct_change(n)
    g["vol_21"] = ret.rolling(21).std() * np.sqrt(252)
    g["vol_63"] = ret.rolling(63).std() * np.sqrt(252)
    g["drawdown_252"] = px / px.rolling(252).max() - 1
    g["trend_200"] = px / px.rolling(200).mean() - 1
    g["volume_change_63"] = g["volume"].rolling(21).mean() / g["volume"].rolling(63).mean() - 1
    g["reversal_5"] = -px.pct_change(5)
    return g


def build_monthly_dataset(prices: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    enriched = pd.concat((_features(g) for _, g in prices.groupby("ticker", sort=False)), ignore_index=True)
    spy_dates = enriched.loc[enriched["ticker"].eq("SPY"), "date"]
    signal_dates = spy_dates.groupby(spy_dates.dt.to_period("M")).max().sort_values()
    # Exclude the last (possibly partial) calendar month from label creation.
    signal_dates = signal_dates.loc[signal_dates.dt.to_period("M") < enriched["date"].max().to_period("M")]
    next_signal = dict(zip(signal_dates.iloc[:-1], signal_dates.iloc[1:]))
    snap = enriched.loc[enriched["date"].isin(signal_dates)].copy().merge(intervals, on="ticker", how="left")
    snap = snap.loc[(snap["date"] >= snap["start"]) & (snap["end"].isna() | (snap["date"] < snap["end"]))]
    snap = snap.drop_duplicates(["date", "ticker"])
    daily = enriched[["date", "ticker", "adj_open", "adj_close"]].sort_values(["ticker", "date"])

    records: list[pd.DataFrame] = []
    for d, nd in next_signal.items():
        s = snap.loc[snap["date"].eq(d)].copy()
        if s.empty:
            continue
        window = daily.loc[(daily["date"] > d) & (daily["date"] <= nd)]
        entry = window.groupby("ticker", as_index=False).first()[["ticker", "date", "adj_open"]]
        entry.columns = ["ticker", "execution_date", "entry_price"]
        after_window = daily.loc[(daily["date"] > nd) & (daily["date"] <= nd + pd.Timedelta(days=7))]
        after = after_window.groupby("ticker", as_index=False).first()[["ticker", "date", "adj_open"]]
        after.columns = ["ticker", "exit_date", "exit_price"]
        fallback = window.groupby("ticker", as_index=False).last()[["ticker", "date", "adj_close"]]
        fallback.columns = ["ticker", "fallback_date", "fallback_price"]
        s = s.merge(entry, on="ticker", how="left").merge(after, on="ticker", how="left").merge(fallback, on="ticker", how="left")
        s["exit_price"] = s["exit_price"].fillna(s["fallback_price"])
        s["exit_date"] = s["exit_date"].fillna(s["fallback_date"])
        s["target_return"] = s["exit_price"] / s["entry_price"] - 1
        s["label_known_date"] = s["exit_date"]
        records.append(s)
    out = pd.concat(records, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    out = out.dropna(subset=FEATURES + ["target_return", "entry_price", "label_known_date"])
    keep = ["date", "ticker", "execution_date", "exit_date", "label_known_date", "target_return", *FEATURES]
    return out[keep]


def spy_monthly_returns(prices: pd.DataFrame, signal_dates: pd.Series) -> pd.DataFrame:
    spy = _features(prices.loc[prices["ticker"].eq("SPY")]).sort_values("date")
    dates = sorted(pd.to_datetime(signal_dates).unique())
    rows = []
    for d, nd in zip(dates[:-1], dates[1:]):
        start, end = spy.loc[spy["date"] > d].head(1), spy.loc[spy["date"] > nd].head(1)
        if not start.empty and not end.empty:
            rows.append({"date": d, "spy_return": end["adj_open"].iloc[0] / start["adj_open"].iloc[0] - 1})
    return pd.DataFrame(rows)


def build_latest_signal_snapshot(prices: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    """Build the latest completed-month feature rows without any future label."""
    enriched = pd.concat((_features(g) for _, g in prices.groupby("ticker", sort=False)), ignore_index=True)
    latest = enriched["date"].max()
    completed_period = latest.to_period("M") - 1
    spy = enriched.loc[(enriched["ticker"].eq("SPY")) &
                       (enriched["date"].dt.to_period("M").eq(completed_period))]
    signal_date = spy["date"].max()
    snap = enriched.loc[enriched["date"].eq(signal_date)].copy().merge(intervals, on="ticker", how="left")
    snap = snap.loc[(snap["date"] >= snap["start"]) & (snap["end"].isna() | (snap["date"] < snap["end"]))]
    next_dates = enriched.loc[enriched["date"] > signal_date].groupby("ticker")["date"].min()
    snap["execution_date"] = snap["ticker"].map(next_dates)
    snap["exit_date"] = pd.NaT; snap["label_known_date"] = pd.NaT; snap["target_return"] = np.nan
    keep = ["date", "ticker", "execution_date", "exit_date", "label_known_date", "target_return", *FEATURES]
    return snap.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)[keep].drop_duplicates(["date", "ticker"])


def fit_predict(dataset: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    predictions, model, last_fit = [], None, None
    dates = sorted(dataset.loc[dataset["date"] >= pd.Timestamp(cfg.first_prediction), "date"].unique())
    for raw_date in dates:
        d = pd.Timestamp(raw_date)
        train = dataset.loc[(dataset["date"] >= d - pd.DateOffset(years=cfg.train_years)) &
                            (dataset["date"] < d) & (dataset["label_known_date"] <= d)]
        test = dataset.loc[dataset["date"].eq(d)].copy()
        if len(train) < 5000 or test.empty:
            continue
        fit_period = (d.year, (d.month - 1) // 3)
        if model is None or fit_period != last_fit:
            model = LGBMRegressor(objective="regression_l1", n_estimators=250, learning_rate=.035,
                                  num_leaves=15, max_depth=5, min_child_samples=80,
                                  subsample=.8, colsample_bytree=.8, reg_alpha=.2, reg_lambda=1,
                                  random_state=cfg.seed, n_jobs=-1, verbosity=-1)
            model.fit(train[FEATURES], train["target_return"])
            last_fit = fit_period
        test["prediction"] = model.predict(test[FEATURES])
        test["train_rows"] = len(train)
        predictions.append(test)
    return pd.concat(predictions, ignore_index=True)


def portfolio_returns(pred: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, holdings, previous = [], [], set()
    for d, g in pred.groupby("date", sort=True):
        chosen = g.nlargest(cfg.top_n, "prediction").copy()
        current = set(chosen["ticker"])
        turnover = 1.0 if not previous else 1 - len(current & previous) / cfg.top_n
        gross = chosen["target_return"].mean()
        rows.append({"date": d, "execution_date": chosen["execution_date"].min(), "gross_return": gross,
                     "net_return": gross - turnover * cfg.cost_bps / 10_000, "turnover": turnover, "n": len(chosen)})
        chosen["rank"] = chosen["prediction"].rank(ascending=False, method="first").astype(int)
        holdings.append(chosen[["date", "execution_date", "ticker", "rank", "prediction", "target_return"]])
        previous = current
    return pd.DataFrame(rows), pd.concat(holdings, ignore_index=True)


def metrics(returns: pd.Series) -> dict[str, float]:
    r = returns.dropna(); wealth = (1 + r).cumprod(); years = len(r) / 12
    ann = wealth.iloc[-1] ** (1 / years) - 1
    vol = r.std(ddof=1) * np.sqrt(12)
    return {"annual_return": ann, "annual_volatility": vol, "sharpe_0rf": ann / vol if vol else np.nan,
            "max_drawdown": (wealth / wealth.cummax() - 1).min(), "total_return": wealth.iloc[-1] - 1, "months": len(r)}
