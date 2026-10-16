"""Data access for the analysis app: market prices and the local forward ledgers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def download_adjusted_close(tickers: list[str], start: str) -> tuple[pd.DataFrame, list[str]]:
    """Daily adjusted closes from Yahoo Finance, plus tickers that returned nothing."""
    import yfinance as yf

    raw = yf.download(sorted(set(tickers)), start=start, auto_adjust=False, actions=False,
                      progress=False, group_by="ticker", threads=True)
    columns, failed = {}, []
    for ticker in sorted(set(tickers)):
        try:
            series = raw[ticker]["Adj Close"].dropna()
        except (KeyError, TypeError):
            series = pd.Series(dtype=float)
        if series.empty:
            failed.append(ticker)
        else:
            columns[ticker] = series
    prices = pd.DataFrame(columns)
    if not prices.empty:
        prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    return prices, failed


def forward_ledgers() -> dict[str, Path]:
    from automation.status import LEDGERS

    return LEDGERS


def read_csv(relative: str) -> pd.DataFrame | None:
    path = ROOT / relative
    return pd.read_csv(path) if path.exists() else None
