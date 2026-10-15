from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from paper_trading.simulator import simulate_equal_weight_portfolio


ROOT = Path(__file__).resolve().parents[1]
MODEL = "fundamental_ridge_v5_sector_guard"


def _latest_common_date(prices: pd.DataFrame, tickers: list[str], signal_date: pd.Timestamp) -> pd.Timestamp:
    eligible = prices.loc[(prices["ticker"].isin(tickers)) & (prices["date"] > signal_date), ["ticker", "date"]]
    counts = eligible.drop_duplicates().groupby("date")["ticker"].nunique()
    common = counts.loc[counts.eq(len(tickers))]
    if common.empty:
        raise ValueError("no common valuation date exists for the portfolio and SPY")
    return pd.Timestamp(common.index.max())


def run(root: Path, initial_cash: float = 100_000.0, cost_bps: int = 10) -> dict:
    root = Path(root)
    preview_path = root / "reports/v5_sector_guard/latest_preview_not_forward_result.csv"
    price_path = root / "data/pit/prices.parquet"
    preview = pd.read_csv(preview_path, parse_dates=["date"])
    if not {"ticker", "date"}.issubset(preview.columns):
        raise ValueError("V5 preview must contain ticker and date")
    holdings = preview.loc[:, ["ticker", "date"]].copy()
    if holdings.empty:
        raise ValueError("V5 preview is empty")
    signal_dates = holdings["date"].dt.normalize().drop_duplicates()
    if len(signal_dates) != 1:
        raise ValueError("V5 preview must contain one signal date")
    signal_date = pd.Timestamp(signal_dates.iloc[0])

    tickers = holdings["ticker"].astype(str).tolist()
    if "SPY" in tickers:
        raise ValueError("SPY must remain a benchmark and cannot be a V5 holding")
    market_tickers = tickers + ["SPY"]
    prices = pd.read_parquet(
        price_path,
        columns=["ticker", "date", "open", "close", "adj_close"],
        filters=[("ticker", "in", market_tickers)],
    )
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    valuation_date = _latest_common_date(prices, market_tickers, signal_date)

    positions, portfolio = simulate_equal_weight_portfolio(
        holdings, prices, initial_cash=initial_cash, cost_bps=cost_bps, valuation_date=valuation_date
    )
    spy_holding = pd.DataFrame({"ticker": ["SPY"], "date": [signal_date]})
    _, spy = simulate_equal_weight_portfolio(
        spy_holding, prices, initial_cash=initial_cash, cost_bps=cost_bps, valuation_date=valuation_date
    )
    if portfolio["execution_date"] != spy["execution_date"]:
        raise ValueError("portfolio and SPY do not share a common execution date")

    result = {
        "rehearsal_only": True,
        "official_forward_result": False,
        "model": MODEL,
        "source_preview": str(preview_path),
        "portfolio": portfolio,
        "spy": spy,
        "excess_return_vs_spy": portfolio["net_return_if_liquidated"] - spy["net_return_if_liquidated"],
        "interpretation": "Pipeline rehearsal only; the signal predates the frozen model and is not forward evidence.",
    }
    output = root / "reports/paper_rehearsal"
    output.mkdir(parents=True, exist_ok=True)
    positions.to_csv(output / "positions.csv", index=False)
    (output / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an offline, non-official V5 paper-trading rehearsal.")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--cost-bps", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run(ROOT, args.initial_cash, args.cost_bps), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
