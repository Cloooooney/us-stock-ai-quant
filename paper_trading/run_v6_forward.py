"""Formal V6 forward paper tracker.

V6 (equal-weight blend of momentum, quality, and value ranks) was frozen on
October 15, 2026; see docs/V6_RESULTS.md and reports/ai_v6_factor/frozen_config.json.
It is tracked with the same ledger, fill, and period rules as V5, in its own
ledger, so the two forward records stay independent. No parameters are refit.
"""
from __future__ import annotations

import json

import pandas as pd

from paper_trading.run_v5_forward import ETF_PRICES, ROOT, TrackerSpec, track, write_reports

V6 = TrackerSpec(
    key="v6",
    model="v6_equal_weight_momentum_quality_value",
    frozen_at=pd.Timestamp("2026-10-15"),
    holding_fields=("accession", "form"),
    ledger=ROOT / "paper_trading/v6_ledger.jsonl",
    signal_dir=ROOT / "paper_trading/signals",
    report_dir=ROOT / "reports/v6_forward",
)
FEATURES = ["momentum_score", "quality_score", "value_score", "mom_126", "mom_252",
            "fundamental_age_days", "market_cap"]


def main() -> None:
    from models.v6_factor import build_v6_signal

    selected, universe, prices = build_v6_signal(ROOT)
    etf_prices = pd.read_parquet(ETF_PRICES) if ETF_PRICES.exists() else None
    summary = track(V6.ledger, selected, universe, prices, FEATURES, etf_prices, spec=V6)
    if etf_prices is None:
        summary["notes"].append(f"{ETF_PRICES} not found; ETF benchmarks are recorded as unavailable")
    write_reports(V6.ledger, summary, spec=V6)
    print(json.dumps({"ledger": str(V6.ledger), **summary}, indent=2))


if __name__ == "__main__":
    main()
