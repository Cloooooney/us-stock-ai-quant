"""Download benchmark ETF prices used for forward and historical comparison.

RSP  equal-weight S&P 500, the natural benchmark for an equal-weight stock picker
QUAL quality factor     VLUE value factor     MTUM momentum factor     USMV minimum volatility

The file is separate from the point-in-time stock data so a benchmark failure
can never alter the stock universe. Prices are written atomically to
``data/pit/benchmark_etfs.parquet`` after validation.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data_pipeline.sec_fundamentals import ROOT

ETFS = ["RSP", "QUAL", "VLUE", "MTUM", "USMV"]
START = "2015-01-01"
TARGET = ROOT / "data/pit/benchmark_etfs.parquet"
LOG = ROOT / "data/pit/update_log.jsonl"


def download(tickers: list[str] = ETFS, start: str = START) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers, start=start, interval="1d", group_by="ticker", auto_adjust=False,
                      actions=False, threads=True, progress=False)
    frames = []
    for ticker in tickers:
        frame = raw[ticker].dropna(subset=["Open", "Close", "Adj Close"]).reset_index()
        frame = frame.rename(columns={"Date": "date", "Open": "open", "Close": "close",
                                      "Adj Close": "adj_close", "Volume": "volume"})
        frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None).dt.normalize()
        frame["ticker"] = ticker
        frames.append(frame[["ticker", "date", "open", "close", "adj_close", "volume"]])
    return pd.concat(frames, ignore_index=True)


def validate(prices: pd.DataFrame, existing: pd.DataFrame | None, tickers: list[str] = ETFS) -> dict:
    missing = sorted(set(tickers).difference(prices["ticker"]))
    if missing:
        raise ValueError(f"no rows for {', '.join(missing)}")
    if prices.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker-date rows")
    if (prices[["open", "close", "adj_close"]] <= 0).any().any() or prices[["open", "close", "adj_close"]].isna().any().any():
        raise ValueError("non-positive or missing prices")
    latest = prices.groupby("ticker")["date"].max()
    if (latest < latest.max() - pd.Timedelta(days=7)).any():
        raise ValueError(f"stale tickers: {', '.join(latest[latest < latest.max() - pd.Timedelta(days=7)].index)}")
    if existing is not None and not existing.empty and prices["date"].max() < existing["date"].max():
        raise ValueError(f"incoming data regressed from {existing['date'].max()} to {prices['date'].max()}")
    return {"rows": int(len(prices)), "tickers": sorted(prices["ticker"].unique()),
            "min_date": str(prices["date"].min().date()), "max_date": str(prices["date"].max().date())}


def update(target: Path = TARGET) -> dict:
    prices = download()
    existing = pd.read_parquet(target) if target.exists() else None
    stats = validate(prices, existing)
    incoming = target.with_suffix(".incoming.parquet")
    prices.to_parquet(incoming, index=False)
    os.replace(incoming, target)
    event = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "source": "yfinance",
             "dataset": "benchmark_etfs", **stats}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


if __name__ == "__main__":
    print(json.dumps(update(), indent=2))
