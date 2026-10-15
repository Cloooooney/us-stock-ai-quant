from __future__ import annotations

import os
from pathlib import Path
import pandas as pd

from data_pipeline.sec_fundamentals import ROOT
from models.walk_forward import FEATURES, build_monthly_dataset, load_source


def rebuild() -> dict:
    target = ROOT / "data/pit/monthly_ml_dataset_v2.parquet"
    temp = target.with_suffix(".incoming.parquet")
    prices, intervals, _ = load_source(ROOT)
    dataset = build_monthly_dataset(prices, intervals)
    if dataset.empty or dataset.duplicated(["date", "ticker"]).any():
        raise ValueError("rebuilt monthly dataset is empty or duplicated")
    if not (dataset["execution_date"] > dataset["date"]).all():
        raise ValueError("execution look-ahead check failed")
    if not (dataset["label_known_date"] > dataset["date"]).all():
        raise ValueError("label timing check failed")
    if dataset[FEATURES + ["target_return"]].isna().any().any():
        raise ValueError("rebuilt monthly dataset contains missing model values")
    dataset.to_parquet(temp, index=False); os.replace(temp, target)
    return {"rows": len(dataset), "tickers": dataset["ticker"].nunique(),
            "first_signal": str(dataset["date"].min().date()), "last_signal": str(dataset["date"].max().date())}


if __name__ == "__main__": print(rebuild())
