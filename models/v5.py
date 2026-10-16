from __future__ import annotations

from pathlib import Path
import pandas as pd

from models.fundamental_ridge import FUNDAMENTALS, merge_fundamentals, walk_forward_ridge
from models.sector_guard import select_with_sector_cap
from models.walk_forward import Config, build_latest_signal_snapshot, load_source


def build_v5_signal(root: Path) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Return the V5 holdings, the full scored point-in-time universe, and prices.

    The universe is every member scored on the signal date. It is the same
    population the historical point-in-time equal-weight benchmark averages.
    """
    prices, intervals, _ = load_source(root)
    historical = pd.read_parquet(root / "data/pit/monthly_ml_dataset_v2.parquet")
    latest = build_latest_signal_snapshot(prices, intervals)
    combined = pd.concat([historical, latest], ignore_index=True).drop_duplicates(["date", "ticker"], keep="last")
    fundamentals = pd.read_parquet(root / "data/sec/annual_fundamentals.parquet")
    merged = merge_fundamentals(combined, fundamentals)
    predictions = walk_forward_ridge(merged, FUNDAMENTALS, Config(top_n=20, cost_bps=10))
    signal_date = latest["date"].max()
    current = predictions.loc[predictions["date"].eq(signal_date)].copy()
    universe = sorted(current["ticker"].astype(str).unique())
    sic = pd.read_parquet(root / "data/sec/current_sic_snapshot.parquet")
    current = current.merge(sic[["ticker", "company_name", "sic", "sic_major", "sic_description"]], on="ticker", how="left")
    selected = select_with_sector_cap(current, top_n=20, max_per_sector=4, max_per_division=6)
    if len(selected) != 20:
        raise ValueError(f"V5 selection produced {len(selected)} holdings instead of 20")
    return selected, universe, prices


def build_v5_selection(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected, _, prices = build_v5_signal(root)
    return selected, prices
