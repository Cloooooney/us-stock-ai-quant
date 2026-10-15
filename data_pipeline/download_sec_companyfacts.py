from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

from data_pipeline.sec_fundamentals import ROOT, load_ticker_cik

OUT = ROOT / "data/sec/companyfacts"
DEFAULT_UA = "AIQuantResearch/1.0 (personal educational research)"


def target_companies() -> pd.DataFrame:
    members = pd.read_parquet(ROOT / "data/pit/members.parquet")
    historical = set(members.loc[members["date"] >= "2017-01-01", "ticker"])
    mapping = load_ticker_cik()
    return mapping.loc[mapping["ticker"].isin(historical)].sort_values("cik").reset_index(drop=True)


def download(limit: int | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    companies = target_companies()
    pending = [row for row in companies.itertuples() if not (OUT / f"CIK{row.cik:010d}.json").exists()]
    if limit is not None:
        pending = pending[:limit]
    user_agent = os.environ.get("SEC_USER_AGENT", DEFAULT_UA)
    session = requests.Session(); session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    failures = []
    for i, row in enumerate(pending, 1):
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{row.cik:010d}.json"
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
            # Parse before saving so interrupted/error HTML never becomes cache.
            payload = response.json()
            (OUT / f"CIK{row.cik:010d}.json").write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            failures.append({"ticker": row.ticker, "cik": row.cik, "error": str(exc)})
        if i % 25 == 0:
            print(f"downloaded/attempted {i}/{len(pending)}; failures={len(failures)}", flush=True)
        time.sleep(0.18)  # comfortably below SEC's 10 requests/second ceiling
    pd.DataFrame(failures, columns=["ticker", "cik", "error"]).to_csv(ROOT / "data/sec/download_failures.csv", index=False)
    cached = len(list(OUT.glob("CIK*.json")))
    print(f"cached={cached}, universe={len(companies)}, remaining={len(companies)-cached}, failures={len(failures)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--limit", type=int)
    download(parser.parse_args().limit)
