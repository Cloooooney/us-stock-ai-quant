from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from data_pipeline.sec_fundamentals import ROOT

BASE_URL = "https://github.com/Johnbrick123/sp500-data/releases/download/data"
ASSETS = ["prices.parquet", "membership_intervals.parquet", "members.parquet",
          "recycled_tickers.csv", "verification_report.txt"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(session: requests.Session, name: str, target: Path) -> None:
    with session.get(f"{BASE_URL}/{name}", stream=True, timeout=120) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)


def validate(incoming: Path, current: Path) -> dict:
    prices = pd.read_parquet(incoming / "prices.parquet", columns=["date", "ticker", "close", "adj_close"])
    intervals = pd.read_parquet(incoming / "membership_intervals.parquet")
    members = pd.read_parquet(incoming / "members.parquet")
    required = {"date", "ticker", "close", "adj_close"}
    if not required.issubset(prices.columns) or prices.duplicated(["date", "ticker"]).any():
        raise ValueError("invalid price schema or duplicate rows")
    if (prices[["close", "adj_close"]].le(0).any(axis=1)).any():
        raise ValueError("non-positive prices found")
    if not {"ticker", "start", "end"}.issubset(intervals.columns) or len(intervals) < 1000:
        raise ValueError("invalid membership intervals")
    if not {"date", "ticker"}.issubset(members.columns) or len(members) < 1_000_000:
        raise ValueError("invalid daily membership table")
    report = (incoming / "verification_report.txt").read_text(encoding="utf-8", errors="replace")
    if "FAIL 0" not in report:
        raise ValueError("upstream verification report is not clean")
    existing = current / "prices.parquet"
    if existing.exists():
        old_max = pd.read_parquet(existing, columns=["date"])["date"].max()
        if prices["date"].max() < old_max:
            raise ValueError(f"incoming data regressed from {old_max} to {prices['date'].max()}")
    return {"rows": len(prices), "tickers": prices["ticker"].nunique(),
            "min_date": str(prices["date"].min().date()), "max_date": str(prices["date"].max().date())}


def update() -> dict:
    target = ROOT / "data/pit"; incoming = target / ".incoming"
    if incoming.exists(): shutil.rmtree(incoming)
    incoming.mkdir(parents=True)
    session = requests.Session(); session.headers.update({"User-Agent": "AIQuantResearch/1.0"})
    try:
        for name in ASSETS:
            print(f"downloading {name}", flush=True); download_file(session, name, incoming / name)
        stats = validate(incoming, target)
        hashes = {name: sha256_file(incoming / name) for name in ASSETS}
        for name in ASSETS:
            os.replace(incoming / name, target / ("source_verification_report.txt" if name == "verification_report.txt" else name))
        event = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "source": BASE_URL, **stats, "sha256": hashes}
        with (target / "update_log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event
    finally:
        if incoming.exists(): shutil.rmtree(incoming)


if __name__ == "__main__":
    print(json.dumps(update(), indent=2))
