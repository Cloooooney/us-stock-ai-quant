from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.baseline import (  # noqa: E402
    BaselineConfig,
    add_features,
    build_rebalance_table,
    load_market_data,
)


DATA_FILE = ROOT / "data" / "us_daily_completed_through_2026-10-02.parquet"


def test_market_data_is_clean():
    data = load_market_data(DATA_FILE)
    assert data["ticker"].nunique() == 31
    assert not data.duplicated(["date", "ticker"]).any()
    assert data["date"].max() == pd.Timestamp("2026-10-02")
    assert (data[["open", "close", "adj_close", "adj_open"]] > 0).all().all()


def test_signals_execute_after_they_are_observed():
    data = add_features(load_market_data(DATA_FILE))
    rebalances, selections = build_rebalance_table(data, BaselineConfig())
    assert len(rebalances) > 500
    assert (rebalances["execution_date"] > rebalances["signal_date"]).all()
    assert (selections["execution_date"] > selections["signal_date"]).all()
    assert selections.groupby("signal_date")["ticker"].size().eq(5).all()
