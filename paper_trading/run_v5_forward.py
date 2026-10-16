"""Formal V5 forward paper tracker.

Every month-end run appends at most three kinds of events to the hash-chained
ledger:

SIGNAL  The frozen V5 holdings and the scored point-in-time universe for one
        completed month-end. Written once and never recomputed.
ENTRY   Simulated next-session fills for the holdings of a ledgered SIGNAL.
        Built from the ledger, never from a fresh model run, and backfilled for
        any earlier SIGNAL that is still missing one.
PERIOD  One holding-period observation from one SIGNAL to the next, measured
        under the same conventions as the historical backtest: adjusted open to
        adjusted open, 10 bps times name turnover for V5, no costs for the
        point-in-time equal-weight universe or SPY.

Only the model rules are frozen. This module is bookkeeping: it does not change
scores, sector caps, the holding count, or the cost assumption.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from paper_trading.ledger import append, read_events, validate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "paper_trading/v5_ledger.jsonl"
SIGNAL_DIR = ROOT / "paper_trading/signals"
REPORT_DIR = ROOT / "reports/v5_forward"
FROZEN_AT = pd.Timestamp("2026-10-05")
MODEL = "fundamental_ridge_v5_sector_guard"
TOP_N = 20
COST_BPS = 10
MIN_REVIEW_MONTHS = 6
BENCHMARK = "SPY"
EXIT_WINDOW_DAYS = 7  # same exit search window as models.walk_forward.build_monthly_dataset


# ---------------------------------------------------------------------------
# Price helpers
# ---------------------------------------------------------------------------

def prepare_prices(prices: pd.DataFrame) -> pd.DataFrame:
    frame = prices.loc[:, ["ticker", "date", "open", "close", "adj_close"]].copy()
    frame["ticker"] = frame["ticker"].astype(str)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["adj_open"] = frame["open"] * frame["adj_close"] / frame["close"]
    return frame.sort_values(["ticker", "date"]).reset_index(drop=True)


def next_session(prices: pd.DataFrame, after: pd.Timestamp) -> pd.Timestamp | None:
    """First market session after ``after``, defined by the benchmark calendar."""
    dates = prices.loc[prices["ticker"].eq(BENCHMARK) & (prices["date"] > after), "date"]
    return None if dates.empty else pd.Timestamp(dates.min())


def _first_in_window(prices: pd.DataFrame, tickers: list[str], start: pd.Timestamp,
                     end: pd.Timestamp, column: str, last: bool = False) -> pd.DataFrame:
    """Per ticker, the first (or last) row with start < date <= end."""
    window = prices.loc[prices["ticker"].isin(tickers) & (prices["date"] > start) & (prices["date"] <= end)]
    grouped = window.groupby("ticker", as_index=False)
    picked = grouped.last() if last else grouped.first()
    return picked[["ticker", "date", column]]


def holding_period_returns(prices: pd.DataFrame, tickers: list[str], signal_date: pd.Timestamp,
                           next_signal_date: pd.Timestamp) -> pd.DataFrame:
    """Backtest-identical label: first adjusted open after the signal, to the
    first adjusted open after the next signal (within seven days), falling back
    to the last adjusted close before the next signal for names that stopped
    trading."""
    entry = _first_in_window(prices, tickers, signal_date, next_signal_date, "adj_open")
    entry.columns = ["ticker", "entry_date", "entry_price"]
    exit_ = _first_in_window(prices, tickers, next_signal_date,
                             next_signal_date + pd.Timedelta(days=EXIT_WINDOW_DAYS), "adj_open")
    exit_.columns = ["ticker", "exit_date", "exit_price"]
    fallback = _first_in_window(prices, tickers, signal_date, next_signal_date, "adj_close", last=True)
    fallback.columns = ["ticker", "fallback_date", "fallback_price"]
    out = pd.DataFrame({"ticker": tickers}).merge(entry, on="ticker", how="left")
    out = out.merge(exit_, on="ticker", how="left").merge(fallback, on="ticker", how="left")
    used_fallback = out["exit_price"].isna() & out["fallback_price"].notna()
    out["exit_price"] = out["exit_price"].fillna(out["fallback_price"])
    out["exit_date"] = out["exit_date"].fillna(out["fallback_date"])
    out["exit_rule"] = "next_session_open"
    out.loc[used_fallback, "exit_rule"] = "last_close_before_next_signal"
    out["return"] = out["exit_price"] / out["entry_price"] - 1
    return out.drop(columns=["fallback_date", "fallback_price"])


def _date(value) -> str:
    return str(pd.Timestamp(value).date())


def _round(value: float) -> float:
    return round(float(value), 10)


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------

def signal_payload(selected: pd.DataFrame, universe: list[str], feature_names: list[str]) -> dict:
    signal_dates = pd.to_datetime(selected["date"]).dt.normalize().drop_duplicates()
    if len(signal_dates) != 1:
        raise ValueError("V5 selection must contain exactly one signal date")
    if len(selected) != TOP_N or selected["ticker"].duplicated().any():
        raise ValueError(f"V5 selection must contain {TOP_N} unique tickers")
    if BENCHMARK in set(selected["ticker"].astype(str)):
        raise ValueError(f"{BENCHMARK} must remain a benchmark and cannot be a V5 holding")
    missing = sorted(set(selected["ticker"].astype(str)).difference(universe))
    if missing:
        raise ValueError(f"holdings are not in the scored universe: {', '.join(missing)}")
    holdings = []
    for row in selected.sort_values("portfolio_rank").itertuples():
        item = {"ticker": str(row.ticker), "rank": int(row.portfolio_rank), "weight": 1 / TOP_N,
                "prediction": _round(row.prediction), "sic": str(row.sic), "sic_division": row.sic_division}
        for feature in feature_names:
            value = getattr(row, feature)
            item[feature] = None if pd.isna(value) else _round(value)
        holdings.append(item)
    return {"event_type": "SIGNAL", "model": MODEL, "signal_date": _date(signal_dates.iloc[0]),
            "holdings": holdings, "universe": sorted(universe), "orders_enabled": False}


def entry_payload(signal: dict, prices: pd.DataFrame) -> dict | None:
    """Fills for a ledgered SIGNAL at the next market session, or None if that
    session is not in the data yet. A holding with no bar on the execution date
    (halted, delisted, data gap) is recorded as unfilled and held as cash."""
    signal_date = pd.Timestamp(signal["signal_date"])
    execution_date = next_session(prices, signal_date)
    if execution_date is None:
        return None
    tickers = [h["ticker"] for h in signal["holdings"]]
    bars = prices.loc[prices["date"].eq(execution_date) & prices["ticker"].isin(tickers + [BENCHMARK])]
    bars = bars.set_index("ticker")
    fills = [{"ticker": t, "open": _round(bars.at[t, "open"]),
              "adjusted_open_at_record": _round(bars.at[t, "adj_open"])}
             for t in tickers if t in bars.index]
    unfilled = [t for t in tickers if t not in bars.index]
    return {"event_type": "ENTRY", "model": MODEL, "signal_date": signal["signal_date"],
            "execution_date": _date(execution_date), "fills": fills, "unfilled_held_as_cash": unfilled,
            "benchmark_fill": {"ticker": BENCHMARK, "open": _round(bars.at[BENCHMARK, "open"]),
                               "adjusted_open_at_record": _round(bars.at[BENCHMARK, "adj_open"])},
            "cost_bps": COST_BPS}


def period_payload(signal: dict, entry: dict, next_signal: dict, prices: pd.DataFrame,
                   previous_signal: dict | None, observation: int) -> dict | None:
    """One holding-period observation from ``signal`` to ``next_signal``, or
    None until the session after ``next_signal`` is in the data."""
    start, end = pd.Timestamp(signal["signal_date"]), pd.Timestamp(next_signal["signal_date"])
    exit_session = next_session(prices, end)
    if exit_session is None:
        return None
    execution_date = pd.Timestamp(entry["execution_date"])

    # V5: the ledgered fills, held to the next rebalance; unfilled names earn 0.
    tickers = [h["ticker"] for h in signal["holdings"]]
    filled = [f["ticker"] for f in entry["fills"]]
    measured = holding_period_returns(prices, filled, start, end).set_index("ticker")
    rows = []
    for ticker in tickers:
        if ticker not in measured.index:
            rows.append({"ticker": ticker, "return": 0.0, "status": "unfilled_cash"})
            continue
        r = measured.loc[ticker]
        if pd.isna(r["return"]) or pd.Timestamp(r["entry_date"]) != execution_date:
            raise ValueError(f"{ticker}: entry bar on {entry['execution_date']} is missing from current prices")
        rows.append({"ticker": ticker, "entry_price": _round(r["entry_price"]),
                     "exit_date": _date(r["exit_date"]), "exit_price": _round(r["exit_price"]),
                     "exit_rule": r["exit_rule"], "return": _round(r["return"]), "status": "held"})
    gross = sum(row["return"] for row in rows) / TOP_N
    if previous_signal is None:
        turnover = 1.0  # initial build from cash, as in the backtest
    else:
        overlap = set(tickers) & {h["ticker"] for h in previous_signal["holdings"]}
        turnover = 1 - len(overlap) / TOP_N
    cost = turnover * COST_BPS / 10_000
    net = gross - cost

    # Point-in-time equal weight: every scored member, same label rule, no costs.
    universe = holding_period_returns(prices, signal["universe"], start, end).dropna(subset=["return"])
    equal_weight = float(universe["return"].mean())

    spy = holding_period_returns(prices, [BENCHMARK], start, end).iloc[0]
    if pd.isna(spy["return"]):
        raise ValueError(f"{BENCHMARK} return is unavailable for {signal['signal_date']}")
    spy_return = float(spy["return"])

    months = (end.to_period("M") - start.to_period("M")).n
    return {"event_type": "PERIOD", "model": MODEL, "observation": observation,
            "signal_date": signal["signal_date"], "next_signal_date": next_signal["signal_date"],
            "entry_execution_date": entry["execution_date"], "exit_execution_date": _date(exit_session),
            "calendar_months": int(months),
            "v5": {"gross_return": _round(gross), "turnover": _round(turnover), "cost": _round(cost),
                   "net_return": _round(net), "held": len(filled), "unfilled_cash": TOP_N - len(filled)},
            "point_in_time_equal_weight": {"return": _round(equal_weight), "members": int(len(universe)),
                                           "members_scored": len(signal["universe"])},
            "spy": {"return": _round(spy_return)},
            "excess_vs_spy": _round(net - spy_return),
            "excess_vs_equal_weight": _round(net - equal_weight),
            "holdings": rows}


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def _events(path: Path, event_type: str) -> dict[str, dict]:
    return {e["signal_date"]: e for e in read_events(path) if e.get("event_type") == event_type}


def summarize(path: Path) -> dict:
    periods = sorted(_events(path, "PERIOD").values(), key=lambda e: e["signal_date"])
    signals, entries = _events(path, "SIGNAL"), _events(path, "ENTRY")
    monthly = [p for p in periods if p["calendar_months"] == 1]

    def growth(values: list[float]) -> float:
        total = 1.0
        for value in values:
            total *= 1 + value
        return total - 1

    return {"signals": len(signals), "entries": len(entries), "periods": len(periods),
            "complete_monthly_observations": len(monthly),
            "multi_month_periods": [p["signal_date"] for p in periods if p["calendar_months"] != 1],
            "review_gate_months": MIN_REVIEW_MONTHS,
            "review_gate_reached": len(monthly) >= MIN_REVIEW_MONTHS,
            "pending_entries": sorted(set(signals).difference(entries)),
            "cumulative": {"v5_net": growth([p["v5"]["net_return"] for p in periods]),
                           "point_in_time_equal_weight": growth(
                               [p["point_in_time_equal_weight"]["return"] for p in periods]),
                           "spy": growth([p["spy"]["return"] for p in periods])}}


def track(ledger: Path, selected: pd.DataFrame, universe: list[str], prices: pd.DataFrame,
          feature_names: list[str]) -> dict:
    """Append any due SIGNAL, ENTRY and PERIOD events. Idempotent."""
    valid, detail = validate(ledger)
    if not valid:
        raise RuntimeError(f"ledger validation failed: {detail}")
    prices = prepare_prices(prices)
    notes: list[str] = []

    payload = signal_payload(selected, universe, feature_names)
    signal_date = pd.Timestamp(payload["signal_date"])
    signals = _events(ledger, "SIGNAL")
    if signal_date <= FROZEN_AT:
        notes.append(f"latest completed-month signal {payload['signal_date']} is not after the "
                     f"{FROZEN_AT.date()} freeze; nothing recorded")
    elif payload["signal_date"] not in signals:
        latest = max(signals) if signals else None
        if latest is not None and payload["signal_date"] < latest:
            raise RuntimeError(f"signal {payload['signal_date']} precedes ledgered signal {latest}; "
                               "market data look stale")
        if latest is not None:
            gap = (signal_date.to_period("M") - pd.Timestamp(latest).to_period("M")).n
            if gap > 1:
                notes.append(f"{gap - 1} month-end signal(s) after {latest} were never recorded; the "
                             f"{latest} portfolio is treated as held until {payload['signal_date']}")
        append(ledger, payload)
    else:
        recorded = {h["ticker"] for h in signals[payload["signal_date"]]["holdings"]}
        if recorded != {h["ticker"] for h in payload["holdings"]}:
            notes.append(f"a fresh run would now pick different {payload['signal_date']} holdings; "
                         "the ledgered SIGNAL is kept and used")

    signals = _events(ledger, "SIGNAL")
    entries = _events(ledger, "ENTRY")
    for date in sorted(signals):
        if date not in entries:
            entry = entry_payload(signals[date], prices)
            if entry is None:
                notes.append(f"ENTRY for {date} waits for the next session's opening prices")
            else:
                append(ledger, entry)
                if entry["unfilled_held_as_cash"]:
                    notes.append(f"{date}: no execution bar for {', '.join(entry['unfilled_held_as_cash'])}; "
                                 "held as cash")

    entries = _events(ledger, "ENTRY")
    periods = _events(ledger, "PERIOD")
    ordered = sorted(signals)
    for i, date in enumerate(ordered[:-1]):
        if date in periods or date not in entries:
            continue
        previous = signals[ordered[i - 1]] if i > 0 else None
        period = period_payload(signals[date], entries[date], signals[ordered[i + 1]], prices,
                                previous, observation=len(periods) + 1)
        if period is None:
            notes.append(f"PERIOD for {date} waits for the session after {ordered[i + 1]}")
            continue
        append(ledger, period)
        periods = _events(ledger, "PERIOD")

    valid, tail = validate(ledger)
    return {**summarize(ledger), "ledger_valid": valid, "ledger_tail_hash": tail, "notes": notes}


def write_reports(ledger: Path, summary: dict, report_dir: Path = REPORT_DIR,
                  signal_dir: Path = SIGNAL_DIR) -> None:
    signal_dir.mkdir(parents=True, exist_ok=True)
    for date, signal in _events(ledger, "SIGNAL").items():
        snapshot = signal_dir / f"v5_{date}.json"
        if not snapshot.exists():
            snapshot.write_text(json.dumps({"signal_date": date, "holdings": signal["holdings"]}, indent=2),
                                encoding="utf-8")
    periods = sorted(_events(ledger, "PERIOD").values(), key=lambda e: e["signal_date"])
    if not periods:
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"observation": p["observation"], "signal_date": p["signal_date"],
             "next_signal_date": p["next_signal_date"], "calendar_months": p["calendar_months"],
             "v5_net_return": p["v5"]["net_return"], "v5_turnover": p["v5"]["turnover"],
             "point_in_time_equal_weight_return": p["point_in_time_equal_weight"]["return"],
             "spy_return": p["spy"]["return"], "excess_vs_spy": p["excess_vs_spy"]} for p in periods]
    pd.DataFrame(rows).to_csv(report_dir / "period_returns.csv", index=False)
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    from models.fundamental_ridge import FUNDAMENTALS
    from models.v5 import build_v5_signal

    selected, universe, prices = build_v5_signal(ROOT)
    summary = track(LEDGER, selected, universe, prices, FUNDAMENTALS)
    write_reports(LEDGER, summary)
    print(json.dumps({"ledger": str(LEDGER), **summary}, indent=2))


if __name__ == "__main__":
    main()
