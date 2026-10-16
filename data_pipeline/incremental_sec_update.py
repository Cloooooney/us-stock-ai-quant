from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from data_pipeline.download_sec_companyfacts import DEFAULT_UA, target_companies
from data_pipeline.download_sec_submissions import build_sic_snapshot
from data_pipeline.sec_fundamentals import ROOT

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
QUARTERLY_FORMS = {"10-Q", "10-Q/A"}
# V6 uses quarterly facts, so a new 10-Q must refresh Company Facts as well.
REFRESH_FORMS = ANNUAL_FORMS | QUARTERLY_FORMS


def recent_filing_date(payload: dict, forms: set[str] = REFRESH_FORMS) -> pd.Timestamp | None:
    recent = payload.get("filings", {}).get("recent", {})
    dates = [pd.Timestamp(d) for form, d in zip(recent.get("form", []), recent.get("filingDate", []))
             if form in forms]
    return max(dates) if dates else None


def recent_annual_date(payload: dict) -> pd.Timestamp | None:
    return recent_filing_date(payload, ANNUAL_FORMS)


def known_filing_dates(root: Path = ROOT) -> dict[int, pd.Timestamp]:
    """Latest filing date already parsed per CIK, across annual and quarterly features."""
    frames = [pd.read_parquet(root / "data/sec/annual_fundamentals.parquet", columns=["cik", "filed"])]
    quarterly = root / "data/sec/quarterly_fundamentals.parquet"
    if quarterly.exists():
        frames.append(pd.read_parquet(quarterly, columns=["cik", "filed"]))
    known = pd.concat(frames, ignore_index=True)
    known["filed"] = pd.to_datetime(known["filed"])
    return known.groupby("cik")["filed"].max().to_dict()


def needs_refresh(payload: dict, cached: bool, known: pd.Timestamp | None) -> bool:
    latest = recent_filing_date(payload)
    if not cached:
        return True
    return latest is not None and latest > (known if known is not None else pd.Timestamp.min)


def update() -> dict:
    companies = target_companies().drop_duplicates("cik")
    current_members = pd.read_parquet(ROOT / "data/pit/members.parquet")
    latest_price = pd.read_parquet(ROOT / "data/pit/prices.parquet", columns=["date"])["date"].max()
    latest = current_members.loc[current_members["date"] <= latest_price, "date"].max()
    current_tickers = set(current_members.loc[current_members["date"].eq(latest), "ticker"])
    companies = companies.loc[companies["ticker"].isin(current_tickers)].drop_duplicates("cik")
    known = known_filing_dates()
    sub_dir = ROOT / "data/sec/submissions"; fact_dir = ROOT / "data/sec/companyfacts"
    sub_dir.mkdir(parents=True, exist_ok=True); fact_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session(); session.headers.update({"User-Agent": os.environ.get("SEC_USER_AGENT", DEFAULT_UA),
                                                           "Accept-Encoding": "gzip, deflate"})
    refreshed_facts, failures = [], []
    for i, row in enumerate(companies.itertuples(), 1):
        try:
            sub = session.get(f"https://data.sec.gov/submissions/CIK{row.cik:010d}.json", timeout=45)
            sub.raise_for_status(); payload = sub.json()
            (sub_dir / f"CIK{row.cik:010d}.json").write_text(json.dumps(payload), encoding="utf-8")
            cached_file = fact_dir / f"CIK{row.cik:010d}.json"
            if needs_refresh(payload, cached_file.exists(), known.get(row.cik)):
                facts = session.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{row.cik:010d}.json", timeout=90)
                facts.raise_for_status(); fact_payload = facts.json()
                cached_file.write_text(json.dumps(fact_payload), encoding="utf-8")
                refreshed_facts.append(int(row.cik))
        except Exception as exc:
            failures.append({"cik": int(row.cik), "ticker": row.ticker, "error": str(exc)})
        if i % 50 == 0: print(f"SEC {i}/{len(companies)} refreshed_facts={len(refreshed_facts)} failures={len(failures)}", flush=True)
        time.sleep(.18)
    pd.DataFrame(failures, columns=["cik", "ticker", "error"]).to_csv(ROOT / "data/sec/incremental_failures.csv", index=False)
    build_sic_snapshot()
    event = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "current_membership_date": str(latest.date()),
             "companies_checked": len(companies), "companyfacts_refreshed": refreshed_facts, "failures": len(failures)}
    with (ROOT / "data/sec/update_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


if __name__ == "__main__":
    print(json.dumps(update(), indent=2))
