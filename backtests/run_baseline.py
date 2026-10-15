from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.baseline import (  # noqa: E402
    BaselineConfig,
    add_features,
    build_rebalance_table,
    load_market_data,
    performance_metrics,
    run_weekly_backtest,
)


DATA_FILE = ROOT / "data" / "us_daily_completed_through_2026-10-02.parquet"
REPORT_DIR = ROOT / "reports" / "baseline"


def summarize_period(backtest: pd.DataFrame, name: str, start: str, end: str | None) -> list[dict]:
    subset = backtest[backtest["start"] >= pd.Timestamp(start)]
    if end:
        subset = subset[subset["start"] <= pd.Timestamp(end)]
    rows = []
    for label, column in [
        ("strategy", "strategy_return"),
        ("SPY", "spy_return"),
        ("equal_weight", "equal_weight_return"),
    ]:
        rows.append({"period": name, "portfolio": label, **performance_metrics(subset[column])})
    return rows


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    config = BaselineConfig(top_n=5, transaction_cost_bps=10.0)
    market = load_market_data(DATA_FILE)
    featured = add_features(market)
    rebalances, selections = build_rebalance_table(featured, config)
    backtest = run_weekly_backtest(featured, rebalances, config)

    summaries = []
    summaries += summarize_period(backtest, "train_2012_2019", "2012-01-01", "2019-12-31")
    summaries += summarize_period(backtest, "validation_2020_2022", "2020-01-01", "2022-12-31")
    summaries += summarize_period(backtest, "test_2023_2026", "2023-01-01", None)
    summaries += summarize_period(backtest, "full", "2012-01-01", None)
    summary = pd.DataFrame(summaries)

    backtest.to_csv(REPORT_DIR / "weekly_returns.csv", index=False, encoding="utf-8-sig")
    selections.to_csv(REPORT_DIR / "weekly_selections.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(REPORT_DIR / "performance_summary.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(backtest["end"], backtest["strategy_equity"], label="Baseline Top 5", linewidth=1.6)
    ax.plot(backtest["end"], backtest["spy_equity"], label="SPY", linewidth=1.3)
    ax.plot(backtest["end"], backtest["equal_weight_equity"], label="Equal Weight", linewidth=1.3)
    ax.set_yscale("log")
    ax.set_title("Weekly Baseline: Momentum + Trend + Low Volatility")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "equity_curve.png", dpi=160)
    plt.close(fig)

    display = summary.copy()
    for col in ["annual_return", "volatility", "max_drawdown", "total_return"]:
        display[col] = display[col].map(lambda x: f"{x:.2%}")
    display["sharpe"] = display["sharpe"].map(lambda x: f"{x:.3f}")
    print(display.to_string(index=False))
    print(f"\nReports written to: {REPORT_DIR}")


if __name__ == "__main__":
    main()
