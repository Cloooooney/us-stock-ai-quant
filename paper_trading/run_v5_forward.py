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

The tracker is model-agnostic: a ``TrackerSpec`` names the model, its freeze
date, its ledger and output folders. ``V5`` is the default; other frozen models
(see ``paper_trading.run_v6_forward``) reuse the same code with their own spec.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from paper_trading.ledger import append, read_events, validate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "paper_trading/v5_ledger.jsonl"
SIGNAL_DIR = ROOT / "paper_trading/signals"
REPORT_DIR = ROOT / "reports/v5_forward"
ETF_PRICES = ROOT / "data/pit/benchmark_etfs.parquet"
FROZEN_AT = pd.Timestamp("2026-10-05")
MODEL = "fundamental_ridge_v5_sector_guard"
TOP_N = 20
COST_BPS = 10
MIN_REVIEW_MONTHS = 6  # operational check only; not evidence of skill
MIN_CAPITAL_MONTHS = 24  # minimum forward record before any live allocation (docs/ROADMAP.md)
BENCHMARK = "SPY"
ETF_BENCHMARKS = ["RSP", "QUAL", "VLUE", "MTUM", "USMV"]  # supplementary; never block a PERIOD
EXIT_WINDOW_DAYS = 7  # same exit search window as models.walk_forward.build_monthly_dataset


@dataclass(frozen=True)
class TrackerSpec:
    key: str                          # short name used in event fields, e.g. "v5"
    model: str                        # model identifier written to every event
    frozen_at: pd.Timestamp           # only signals strictly after this date are recorded
    holding_fields: tuple[str, ...]   # extra descriptive columns copied into each holding
    ledger: Path
    signal_dir: Path
    report_dir: Path


V5 = TrackerSpec(key="v5", model=MODEL, frozen_at=FROZEN_AT, holding_fields=("sic", "sic_division"),
                 ledger=LEDGER, signal_dir=SIGNAL_DIR, report_dir=REPORT_DIR)


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

def signal_payload(selected: pd.DataFrame, universe: list[str], feature_names: list[str],
                   spec: TrackerSpec = V5) -> dict:
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
                "prediction": _round(row.prediction)}
        for field in spec.holding_fields:
            value = getattr(row, field)
            item[field] = None if pd.isna(value) else str(value)
        for feature in feature_names:
            value = getattr(row, feature)
            item[feature] = None if pd.isna(value) else _round(value)
        holdings.append(item)
    return {"event_type": "SIGNAL", "model": spec.model, "signal_date": _date(signal_dates.iloc[0]),
            "holdings": holdings, "universe": sorted(universe), "orders_enabled": False}


def entry_payload(signal: dict, prices: pd.DataFrame, spec: TrackerSpec = V5) -> dict | None:
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
    return {"event_type": "ENTRY", "model": spec.model, "signal_date": signal["signal_date"],
            "execution_date": _date(execution_date), "fills": fills, "unfilled_held_as_cash": unfilled,
            "benchmark_fill": {"ticker": BENCHMARK, "open": _round(bars.at[BENCHMARK, "open"]),
                               "adjusted_open_at_record": _round(bars.at[BENCHMARK, "adj_open"])},
            "cost_bps": COST_BPS}


def etf_period_returns(prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                       entry_session: pd.Timestamp, exit_session: pd.Timestamp) -> dict:
    """Open-to-open ETF returns over exactly the V5 holding period. An ETF whose
    bars do not cover both sessions is recorded as unavailable."""
    measured = holding_period_returns(prices, ETF_BENCHMARKS, start, end).set_index("ticker")
    out = {}
    for ticker in ETF_BENCHMARKS:
        r = measured.loc[ticker]
        if pd.isna(r["return"]):
            out[ticker] = {"return": None, "reason": "no prices for the period"}
        elif (pd.Timestamp(r["entry_date"]) != entry_session or r["exit_rule"] != "next_session_open"
              or pd.Timestamp(r["exit_date"]) != exit_session):
            out[ticker] = {"return": None, "reason": "prices do not cover the entry and exit sessions"}
        else:
            out[ticker] = {"return": _round(r["return"])}
    return out


def period_payload(signal: dict, entry: dict, next_signal: dict, prices: pd.DataFrame,
                   previous_signal: dict | None, observation: int, spec: TrackerSpec = V5) -> dict | None:
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

    etfs = etf_period_returns(prices, start, end, execution_date, exit_session)

    months = (end.to_period("M") - start.to_period("M")).n
    return {"event_type": "PERIOD", "model": spec.model, "observation": observation,
            "signal_date": signal["signal_date"], "next_signal_date": next_signal["signal_date"],
            "entry_execution_date": entry["execution_date"], "exit_execution_date": _date(exit_session),
            "calendar_months": int(months),
            spec.key: {"gross_return": _round(gross), "turnover": _round(turnover), "cost": _round(cost),
                   "net_return": _round(net), "held": len(filled), "unfilled_cash": TOP_N - len(filled)},
            "point_in_time_equal_weight": {"return": _round(equal_weight), "members": int(len(universe)),
                                           "members_scored": len(signal["universe"])},
            "spy": {"return": _round(spy_return)},
            "etf_benchmarks": etfs,
            "excess_vs_spy": _round(net - spy_return),
            "excess_vs_rsp": None if etfs["RSP"]["return"] is None else _round(net - etfs["RSP"]["return"]),
            "excess_vs_equal_weight": _round(net - equal_weight),
            "holdings": rows}


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def _events(path: Path, event_type: str) -> dict[str, dict]:
    return {e["signal_date"]: e for e in read_events(path) if e.get("event_type") == event_type}


def summarize(path: Path, spec: TrackerSpec = V5) -> dict:
    periods = sorted(_events(path, "PERIOD").values(), key=lambda e: e["signal_date"])
    signals, entries = _events(path, "SIGNAL"), _events(path, "ENTRY")
    monthly = [p for p in periods if p["calendar_months"] == 1]

    def growth(values: list[float]) -> float:
        total = 1.0
        for value in values:
            total *= 1 + value
        return total - 1

    etf_cumulative = {}
    for ticker in ETF_BENCHMARKS:
        values = [p.get("etf_benchmarks", {}).get(ticker, {}).get("return") for p in periods]
        known = [v for v in values if v is not None]
        etf_cumulative[ticker] = {"return": growth(known) if known else None,
                                  "periods_available": len(known)}

    return {"signals": len(signals), "entries": len(entries), "periods": len(periods),
            "complete_monthly_observations": len(monthly),
            "multi_month_periods": [p["signal_date"] for p in periods if p["calendar_months"] != 1],
            "review_gate_months": MIN_REVIEW_MONTHS,
            "review_gate_reached": len(monthly) >= MIN_REVIEW_MONTHS,
            "capital_gate_months": MIN_CAPITAL_MONTHS,
            "capital_gate_months_reached": len(monthly) >= MIN_CAPITAL_MONTHS,
            "pending_entries": sorted(set(signals).difference(entries)),
            "cumulative": {f"{spec.key}_net": growth([p[spec.key]["net_return"] for p in periods]),
                           "point_in_time_equal_weight": growth(
                               [p["point_in_time_equal_weight"]["return"] for p in periods]),
                           "spy": growth([p["spy"]["return"] for p in periods]),
                           "etf_benchmarks": etf_cumulative}}


def track(ledger: Path, selected: pd.DataFrame, universe: list[str], prices: pd.DataFrame,
          feature_names: list[str], etf_prices: pd.DataFrame | None = None, spec: TrackerSpec = V5) -> dict:
    """Append any due SIGNAL, ENTRY and PERIOD events. Idempotent."""
    valid, detail = validate(ledger)
    if not valid:
        raise RuntimeError(f"ledger validation failed: {detail}")
    notes: list[str] = []
    if etf_prices is not None:
        etf_prices = etf_prices.loc[etf_prices["ticker"].isin(ETF_BENCHMARKS)]
        overlap = sorted(set(etf_prices["ticker"]).intersection(prices["ticker"]))
        scored = sorted(set(overlap).intersection(universe))
        if scored:
            # A scored stock sharing an ETF ticker would make the benchmark ambiguous.
            raise ValueError(f"benchmark ETF tickers collide with scored stocks: {', '.join(scored)}")
        if overlap:
            # The stock price file also carries these ETFs; use the validated ETF file for benchmarks.
            prices = prices.loc[~prices["ticker"].isin(overlap)]
            notes.append(f"stock prices also contain {', '.join(overlap)}; benchmark returns use the ETF file")
        prices = pd.concat([prices, etf_prices], ignore_index=True)
    prices = prepare_prices(prices)

    payload = signal_payload(selected, universe, feature_names, spec)
    signal_date = pd.Timestamp(payload["signal_date"])
    signals = _events(ledger, "SIGNAL")
    if signal_date <= spec.frozen_at:
        notes.append(f"latest completed-month signal {payload['signal_date']} is not after the "
                     f"{spec.frozen_at.date()} freeze; nothing recorded")
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
            entry = entry_payload(signals[date], prices, spec)
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
                                previous, observation=len(periods) + 1, spec=spec)
        if period is None:
            notes.append(f"PERIOD for {date} waits for the session after {ordered[i + 1]}")
            continue
        append(ledger, period)
        periods = _events(ledger, "PERIOD")

    valid, tail = validate(ledger)
    return {**summarize(ledger, spec), "ledger_valid": valid, "ledger_tail_hash": tail, "notes": notes}


def write_reports(ledger: Path, summary: dict, report_dir: Path | None = None,
                  signal_dir: Path | None = None, spec: TrackerSpec = V5) -> None:
    report_dir = spec.report_dir if report_dir is None else report_dir
    signal_dir = spec.signal_dir if signal_dir is None else signal_dir
    signal_dir.mkdir(parents=True, exist_ok=True)
    for date, signal in _events(ledger, "SIGNAL").items():
        snapshot = signal_dir / f"{spec.key}_{date}.json"
        if not snapshot.exists():
            snapshot.write_text(json.dumps({"signal_date": date, "holdings": signal["holdings"]}, indent=2),
                                encoding="utf-8")
    periods = sorted(_events(ledger, "PERIOD").values(), key=lambda e: e["signal_date"])
    if not periods:
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"observation": p["observation"], "signal_date": p["signal_date"],
             "next_signal_date": p["next_signal_date"], "calendar_months": p["calendar_months"],
             f"{spec.key}_net_return": p[spec.key]["net_return"], f"{spec.key}_turnover": p[spec.key]["turnover"],
             "point_in_time_equal_weight_return": p["point_in_time_equal_weight"]["return"],
             "spy_return": p["spy"]["return"], "excess_vs_spy": p["excess_vs_spy"],
             "excess_vs_rsp": p.get("excess_vs_rsp"),
             **{f"{t.lower()}_return": p.get("etf_benchmarks", {}).get(t, {}).get("return")
                for t in ETF_BENCHMARKS}} for p in periods]
    pd.DataFrame(rows).to_csv(report_dir / "period_returns.csv", index=False)
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    from models.fundamental_ridge import FUNDAMENTALS
    from models.v5 import build_v5_signal

    selected, universe, prices = build_v5_signal(ROOT)
    etf_prices = pd.read_parquet(ETF_PRICES) if ETF_PRICES.exists() else None
    summary = track(LEDGER, selected, universe, prices, FUNDAMENTALS, etf_prices)
    if etf_prices is None:
        summary["notes"].append(f"{ETF_PRICES} not found; ETF benchmarks are recorded as unavailable")
    write_reports(LEDGER, summary)
    print(json.dumps({"ledger": str(LEDGER), **summary}, indent=2))


if __name__ == "__main__":
    main()
