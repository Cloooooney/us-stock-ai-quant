from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


BENCHMARKS = {"SPY", "QQQ"}


@dataclass(frozen=True)
class BaselineConfig:
    top_n: int = 5
    transaction_cost_bps: float = 10.0
    min_history_days: int = 252


def load_market_data(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    required = {"date", "ticker", "open", "close", "adj_close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    if frame.duplicated(["date", "ticker"]).any():
        raise ValueError("Duplicate date/ticker rows found")
    if frame[["open", "close", "adj_close"]].isna().any().any():
        raise ValueError("Missing prices found")

    # Apply Yahoo's adjustment factor to the open so entry prices and signal
    # prices use the same split/dividend-adjusted scale.
    factor = frame["adj_close"] / frame["close"]
    frame["adj_open"] = frame["open"] * factor
    return frame


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("ticker", sort=False):
        group = group.copy().sort_values("date")
        price = group["adj_close"]
        returns = price.pct_change()
        group["mom_20"] = price.pct_change(20)
        group["mom_60"] = price.pct_change(60)
        group["mom_120"] = price.pct_change(120)
        group["trend_200"] = price / price.rolling(200).mean() - 1.0
        group["vol_20"] = returns.rolling(20).std() * np.sqrt(252)
        group["history_days"] = np.arange(1, len(group) + 1)
        parts.append(group)
    return pd.concat(parts, ignore_index=True).sort_values(["date", "ticker"])


def weekly_signal_dates(frame: pd.DataFrame) -> list[pd.Timestamp]:
    dates = pd.Series(sorted(frame["date"].unique()))
    return dates.groupby(dates.dt.to_period("W-FRI")).max().tolist()


def _rank_candidates(day: pd.DataFrame, config: BaselineConfig) -> pd.DataFrame:
    candidates = day[
        (~day["ticker"].isin(BENCHMARKS))
        & (day["history_days"] >= config.min_history_days)
        & (day["volume"] > 0)
    ].dropna(subset=["mom_20", "mom_60", "mom_120", "trend_200", "vol_20"])

    if len(candidates) < config.top_n:
        return candidates.assign(score=np.nan)

    candidates = candidates.copy()
    candidates["score"] = (
        0.15 * candidates["mom_20"].rank(pct=True)
        + 0.35 * candidates["mom_60"].rank(pct=True)
        + 0.25 * candidates["mom_120"].rank(pct=True)
        + 0.15 * candidates["trend_200"].rank(pct=True)
        + 0.10 * candidates["vol_20"].rank(pct=True, ascending=False)
    )
    return candidates.nlargest(config.top_n, "score")


def build_rebalance_table(
    featured: pd.DataFrame, config: BaselineConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_dates = pd.Index(sorted(featured["date"].unique()))
    records: list[dict] = []
    selections: list[dict] = []

    for signal_date in weekly_signal_dates(featured):
        pos = all_dates.searchsorted(signal_date, side="right")
        if pos >= len(all_dates):
            continue
        execution_date = pd.Timestamp(all_dates[pos])
        chosen = _rank_candidates(featured[featured["date"] == signal_date], config)
        if len(chosen) < config.top_n:
            continue
        weights = {ticker: 1.0 / config.top_n for ticker in chosen["ticker"]}
        records.append(
            {
                "signal_date": signal_date,
                "execution_date": execution_date,
                "weights": weights,
            }
        )
        for row in chosen.itertuples():
            selections.append(
                {
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "ticker": row.ticker,
                    "score": row.score,
                    "mom_20": row.mom_20,
                    "mom_60": row.mom_60,
                    "mom_120": row.mom_120,
                    "trend_200": row.trend_200,
                    "vol_20": row.vol_20,
                }
            )
    return pd.DataFrame(records), pd.DataFrame(selections)


def _turnover(previous: dict[str, float], current: dict[str, float]) -> float:
    names = set(previous) | set(current)
    return sum(abs(current.get(name, 0.0) - previous.get(name, 0.0)) for name in names)


def run_weekly_backtest(
    featured: pd.DataFrame,
    rebalances: pd.DataFrame,
    config: BaselineConfig,
) -> pd.DataFrame:
    open_prices = featured.pivot(index="date", columns="ticker", values="adj_open")
    rows: list[dict] = []
    previous_weights: dict[str, float] = {}

    for idx in range(len(rebalances) - 1):
        current = rebalances.iloc[idx]
        following = rebalances.iloc[idx + 1]
        start = current["execution_date"]
        end = following["execution_date"]
        weights = current["weights"]

        gross_return = 0.0
        valid = True
        for ticker, weight in weights.items():
            if ticker not in open_prices or pd.isna(open_prices.at[start, ticker]) or pd.isna(open_prices.at[end, ticker]):
                valid = False
                break
            gross_return += weight * (open_prices.at[end, ticker] / open_prices.at[start, ticker] - 1.0)
        if not valid:
            continue

        turnover = _turnover(previous_weights, weights)
        cost = turnover * config.transaction_cost_bps / 10_000.0
        spy_return = open_prices.at[end, "SPY"] / open_prices.at[start, "SPY"] - 1.0

        universe = [c for c in open_prices.columns if c not in BENCHMARKS]
        available = [c for c in universe if pd.notna(open_prices.at[start, c]) and pd.notna(open_prices.at[end, c])]
        equal_return = np.mean(
            [open_prices.at[end, c] / open_prices.at[start, c] - 1.0 for c in available]
        )

        rows.append(
            {
                "signal_date": current["signal_date"],
                "start": start,
                "end": end,
                "gross_return": gross_return,
                "turnover": turnover,
                "cost": cost,
                "strategy_return": gross_return - cost,
                "spy_return": spy_return,
                "equal_weight_return": equal_return,
            }
        )
        previous_weights = weights

    result = pd.DataFrame(rows)
    for column in ["strategy_return", "spy_return", "equal_weight_return"]:
        result[column.replace("_return", "_equity")] = (1.0 + result[column]).cumprod()
    return result


def performance_metrics(returns: pd.Series) -> dict[str, float]:
    returns = returns.dropna()
    if returns.empty:
        return {"annual_return": np.nan, "volatility": np.nan, "sharpe": np.nan, "max_drawdown": np.nan}
    periods = 52.0
    equity = (1.0 + returns).cumprod()
    years = len(returns) / periods
    annual_return = equity.iloc[-1] ** (1.0 / years) - 1.0
    volatility = returns.std(ddof=1) * np.sqrt(periods)
    sharpe = annual_return / volatility if volatility > 0 else np.nan
    max_drawdown = (equity / equity.cummax() - 1.0).min()
    return {
        "annual_return": annual_return,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "total_return": equity.iloc[-1] - 1.0,
    }
