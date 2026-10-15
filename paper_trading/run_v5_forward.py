from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from models.fundamental_ridge import FUNDAMENTALS
from models.v5 import build_v5_selection
from paper_trading.ledger import append, contains, validate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "paper_trading/v5_ledger.jsonl"
FROZEN_AT = pd.Timestamp("2026-10-05")


def adjusted_open_fills(prices: pd.DataFrame, tickers: list[str], signal_date: pd.Timestamp) -> list[dict]:
    frame = prices.loc[(prices["ticker"].isin(tickers)) & (prices["date"] > signal_date)].copy()
    frame["adjusted_open"] = frame["open"] * frame["adj_close"] / frame["close"]
    first = frame.sort_values("date").groupby("ticker", as_index=False).first()
    return [{"ticker": row.ticker, "execution_date": str(row.date.date()), "adjusted_open": round(float(row.adjusted_open), 8)}
            for row in first.itertuples()]


def main() -> None:
    valid, detail = validate(LEDGER)
    if not valid: raise RuntimeError(f"ledger validation failed: {detail}")
    selected, prices = build_v5_selection(ROOT)
    signal = pd.Timestamp(selected["date"].max()); signal_text = str(signal.date())
    if signal <= FROZEN_AT:
        print(json.dumps({"status": "not_yet_eligible", "latest_completed_month_signal": signal_text,
                          "must_be_after": str(FROZEN_AT.date()), "ledger_valid": True}, indent=2))
        return
    holdings = []
    for row in selected.sort_values("portfolio_rank").itertuples():
        item = {"ticker": row.ticker, "rank": int(row.portfolio_rank), "weight": .05,
                "prediction": round(float(row.prediction), 10), "sic": str(row.sic),
                "sic_division": row.sic_division}
        for feature in FUNDAMENTALS:
            value = getattr(row, feature); item[feature] = None if pd.isna(value) else round(float(value), 10)
        holdings.append(item)
    if not contains(LEDGER, "SIGNAL", signal_text):
        append(LEDGER, {"event_type": "SIGNAL", "model": "fundamental_ridge_v5_sector_guard",
                        "signal_date": signal_text, "holdings": holdings, "orders_enabled": False})
    fills = adjusted_open_fills(prices, [x["ticker"] for x in holdings], signal)
    if len(fills) == 20 and not contains(LEDGER, "ENTRY", signal_text):
        append(LEDGER, {"event_type": "ENTRY", "model": "fundamental_ridge_v5_sector_guard",
                        "signal_date": signal_text, "fills": fills, "cost_bps": 10})
    snapshot = ROOT / f"paper_trading/signals/v5_{signal_text}.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists(): snapshot.write_text(json.dumps({"signal_date": signal_text, "holdings": holdings}, indent=2), encoding="utf-8")
    print(json.dumps({"status": "recorded", "signal_date": signal_text, "holdings": len(holdings),
                      "fills": len(fills), "ledger": str(LEDGER), "ledger_tail_hash": validate(LEDGER)[1]}, indent=2))


if __name__ == "__main__": main()
