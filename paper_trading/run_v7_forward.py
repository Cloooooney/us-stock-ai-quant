"""Formal V7 forward paper tracker.

Inactive until backtests.run_v7_factor has recorded the pre-registered decision
and frozen V7 (reports/ai_v7_factor/frozen_config.json). From then on V7 is
tracked with the same rules as V5 and V6 in its own ledger; its first eligible
signal is the first completed month-end after the freeze date.
"""
from __future__ import annotations

import json

import pandas as pd

from paper_trading.run_v5_forward import ETF_PRICES, ROOT, TrackerSpec, track, write_reports

FROZEN = ROOT / "reports/ai_v7_factor/frozen_config.json"
FEATURES = ["momentum_score", "quality_score", "value_score", "improvement_score", "d_roa",
            "d_net_margin", "d_fcf_margin", "fundamental_age_days", "market_cap"]


def spec(frozen: dict) -> TrackerSpec:
    return TrackerSpec(key="v7", model=frozen["model"], frozen_at=pd.Timestamp(frozen["frozen_on"]),
                       holding_fields=("accession", "form", "cik"),
                       ledger=ROOT / "paper_trading/v7_ledger.jsonl", signal_dir=ROOT / "paper_trading/signals",
                       report_dir=ROOT / "reports/v7_forward")


def main() -> None:
    if not FROZEN.exists():
        print(json.dumps({"v7": "not frozen yet; run python -m backtests.run_v7_factor"}))
        return
    from models.v7_factor import build_v7_signal

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    tracker = spec(frozen)
    selected, universe, prices = build_v7_signal(ROOT, frozen["score"])
    etf_prices = pd.read_parquet(ETF_PRICES) if ETF_PRICES.exists() else None
    summary = track(tracker.ledger, selected, universe, prices, FEATURES, etf_prices, spec=tracker)
    write_reports(tracker.ledger, summary, spec=tracker)
    print(json.dumps({"ledger": str(tracker.ledger), **summary}, indent=2))


if __name__ == "__main__":
    main()
