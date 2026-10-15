from __future__ import annotations

import math

import numpy as np
import pandas as pd


PRICE_COLUMNS = {"ticker", "date", "open", "close", "adj_close"}
HOLDING_COLUMNS = {"ticker", "date"}


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(missing)}")


def _require_positive_finite(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    invalid = ~np.isfinite(values.to_numpy()) | (values.to_numpy() <= 0)
    if invalid.any():
        raise ValueError(f"{label} contains invalid prices")


def simulate_equal_weight_portfolio(
    holdings: pd.DataFrame,
    prices: pd.DataFrame,
    initial_cash: float,
    cost_bps: int,
    valuation_date: pd.Timestamp | str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Simulate whole-share equal-weight buys and mark them to one common date."""
    if not math.isfinite(float(initial_cash)) or initial_cash <= 0:
        raise ValueError("initial_cash must be positive and finite")
    if not math.isfinite(float(cost_bps)) or cost_bps < 0:
        raise ValueError("cost_bps must be non-negative and finite")
    _require_columns(holdings, HOLDING_COLUMNS, "holdings")
    _require_columns(prices, PRICE_COLUMNS, "prices")
    if holdings.empty:
        raise ValueError("holdings must not be empty")

    selected = holdings.loc[:, ["ticker", "date"]].copy()
    selected["ticker"] = selected["ticker"].astype(str)
    selected["date"] = pd.to_datetime(selected["date"], errors="raise").dt.normalize()
    if selected["ticker"].duplicated().any():
        duplicates = sorted(selected.loc[selected["ticker"].duplicated(False), "ticker"].unique())
        raise ValueError(f"duplicate holdings: {', '.join(duplicates)}")
    signal_dates = selected["date"].drop_duplicates()
    if len(signal_dates) != 1:
        raise ValueError("holdings must share one signal date")
    signal_date = pd.Timestamp(signal_dates.iloc[0])

    wanted = selected["ticker"].tolist()
    market = prices.loc[prices["ticker"].astype(str).isin(wanted), list(PRICE_COLUMNS)].copy()
    market["ticker"] = market["ticker"].astype(str)
    market["date"] = pd.to_datetime(market["date"], errors="raise").dt.normalize()
    if market.duplicated(["ticker", "date"]).any():
        raise ValueError("prices contain duplicate ticker-date rows")

    post_signal = market.loc[market["date"] > signal_date]
    if post_signal.empty:
        raise ValueError("no prices exist after the signal date")
    execution_date = pd.Timestamp(post_signal["date"].min())
    fills = post_signal.loc[post_signal["date"].eq(execution_date)].copy()
    missing_fills = sorted(set(wanted).difference(fills["ticker"]))
    if missing_fills:
        raise ValueError(f"missing common execution price for: {', '.join(missing_fills)}")
    _require_positive_finite(fills, ["open", "close", "adj_close"], "execution data")
    fills["fill_price"] = fills["open"] * fills["adj_close"] / fills["close"]

    if valuation_date is None:
        mark_date = pd.Timestamp(market["date"].max())
    else:
        mark_date = pd.Timestamp(valuation_date).normalize()
    if mark_date < execution_date:
        raise ValueError("valuation_date cannot precede execution_date")
    marks = market.loc[market["date"].eq(mark_date), ["ticker", "adj_close"]].copy()
    missing_marks = sorted(set(wanted).difference(marks["ticker"]))
    if missing_marks:
        raise ValueError(f"missing common valuation price for: {', '.join(missing_marks)}")
    _require_positive_finite(marks, ["adj_close"], "valuation data")
    marks = marks.rename(columns={"adj_close": "mark_price"})

    positions = selected[["ticker"]].merge(
        fills[["ticker", "fill_price"]], on="ticker", how="left", validate="one_to_one"
    ).merge(marks, on="ticker", how="left", validate="one_to_one")
    rate = float(cost_bps) / 10_000.0
    target_value = float(initial_cash) / len(positions)
    positions["target_value"] = target_value
    positions["shares"] = np.floor(target_value / (positions["fill_price"] * (1.0 + rate))).astype(int)
    if (positions["shares"] <= 0).any():
        tickers = ", ".join(positions.loc[positions["shares"] <= 0, "ticker"])
        raise ValueError(f"initial_cash is too small to buy one share of: {tickers}")
    positions["entry_notional"] = positions["shares"] * positions["fill_price"]
    positions["entry_cost"] = positions["entry_notional"] * rate
    positions["market_value"] = positions["shares"] * positions["mark_price"]
    positions["estimated_exit_cost"] = positions["market_value"] * rate
    positions["unrealized_pnl_after_costs"] = (
        positions["market_value"]
        - positions["entry_notional"]
        - positions["entry_cost"]
        - positions["estimated_exit_cost"]
    )
    positions.insert(1, "signal_date", str(signal_date.date()))
    positions.insert(2, "execution_date", str(execution_date.date()))
    positions.insert(3, "valuation_date", str(mark_date.date()))

    entry_notional = float(positions["entry_notional"].sum())
    entry_cost = float(positions["entry_cost"].sum())
    cash = float(initial_cash) - entry_notional - entry_cost
    if cash < -1e-8:
        raise RuntimeError("simulated orders overspent the account")
    market_value = float(positions["market_value"].sum())
    account_equity = cash + market_value
    estimated_exit_cost = float(positions["estimated_exit_cost"].sum())
    net_liquidation_value = account_equity - estimated_exit_cost
    summary = {
        "signal_date": str(signal_date.date()),
        "execution_date": str(execution_date.date()),
        "valuation_date": str(mark_date.date()),
        "holdings": int(len(positions)),
        "initial_cash": float(initial_cash),
        "cost_bps_each_side": float(cost_bps),
        "entry_notional": entry_notional,
        "entry_cost": entry_cost,
        "cash": cash,
        "market_value": market_value,
        "account_equity": account_equity,
        "estimated_exit_cost": estimated_exit_cost,
        "net_liquidation_value": net_liquidation_value,
        "net_return_if_liquidated": net_liquidation_value / float(initial_cash) - 1.0,
    }
    return positions.sort_values("ticker").reset_index(drop=True), summary
