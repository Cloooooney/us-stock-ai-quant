import json

import pandas as pd

from paper_trading.run_rehearsal import run


def test_run_writes_isolated_non_official_reports(tmp_path):
    preview_dir = tmp_path / "reports/v5_sector_guard"
    data_dir = tmp_path / "data/pit"
    preview_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": ["2026-09-30", "2026-09-30"],
            "portfolio_rank": [1, 2],
        }
    ).to_csv(preview_dir / "latest_preview_not_forward_result.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2026-10-01", "open": 10.0, "close": 10.0, "adj_close": 10.0},
            {"ticker": "AAA", "date": "2026-10-02", "open": 11.0, "close": 11.0, "adj_close": 11.0},
            {"ticker": "BBB", "date": "2026-10-01", "open": 20.0, "close": 20.0, "adj_close": 20.0},
            {"ticker": "BBB", "date": "2026-10-02", "open": 19.0, "close": 19.0, "adj_close": 19.0},
            {"ticker": "SPY", "date": "2026-10-01", "open": 100.0, "close": 100.0, "adj_close": 100.0},
            {"ticker": "SPY", "date": "2026-10-02", "open": 101.0, "close": 101.0, "adj_close": 101.0},
        ]
    ).assign(date=lambda frame: pd.to_datetime(frame["date"])).to_parquet(data_dir / "prices.parquet", index=False)

    result = run(tmp_path, initial_cash=1_000.0, cost_bps=10)

    assert result["rehearsal_only"] is True
    assert result["official_forward_result"] is False
    assert result["model"] == "fundamental_ridge_v5_sector_guard"
    assert result["portfolio"]["signal_date"] == "2026-09-30"
    assert result["portfolio"]["execution_date"] == result["spy"]["execution_date"]
    assert result["portfolio"]["valuation_date"] == result["spy"]["valuation_date"]
    assert result["excess_return_vs_spy"] == (
        result["portfolio"]["net_return_if_liquidated"]
        - result["spy"]["net_return_if_liquidated"]
    )
    output = tmp_path / "reports/paper_rehearsal"
    assert (output / "positions.csv").exists()
    assert json.loads((output / "summary.json").read_text(encoding="utf-8")) == result
    assert not (tmp_path / "paper_trading/v5_ledger.jsonl").exists()
