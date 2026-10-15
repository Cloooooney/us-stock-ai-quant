from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

from data_pipeline.download_sec_companyfacts import DEFAULT_UA, target_companies
from data_pipeline.sec_fundamentals import ROOT

OUT = ROOT / "data/sec/submissions"


def download(limit: int | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    companies = target_companies().drop_duplicates("cik")
    pending = [r for r in companies.itertuples() if not (OUT / f"CIK{r.cik:010d}.json").exists()]
    if limit is not None: pending = pending[:limit]
    session = requests.Session()
    session.headers.update({"User-Agent": os.environ.get("SEC_USER_AGENT", DEFAULT_UA), "Accept-Encoding": "gzip, deflate"})
    failures = []
    for i, row in enumerate(pending, 1):
        try:
            response = session.get(f"https://data.sec.gov/submissions/CIK{row.cik:010d}.json", timeout=45)
            response.raise_for_status(); payload = response.json()
            (OUT / f"CIK{row.cik:010d}.json").write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            failures.append({"cik": row.cik, "error": str(exc)})
        if i % 50 == 0: print(f"attempted {i}/{len(pending)}; failures={len(failures)}", flush=True)
        time.sleep(.18)
    pd.DataFrame(failures, columns=["cik", "error"]).to_csv(ROOT / "data/sec/submission_failures.csv", index=False)
    print(f"cached={len(list(OUT.glob('CIK*.json')))}, unique_ciks={len(companies)}, failures={len(failures)}")


def build_sic_snapshot() -> pd.DataFrame:
    mapping = target_companies()
    records = []
    for path in OUT.glob("CIK*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        cik = int(payload["cik"]); sic = str(payload.get("sic", "")).zfill(4)
        records.append({"cik": cik, "sic": sic, "sic_major": sic[:2] if sic.strip("0") else "unknown",
                        "sic_description": payload.get("sicDescription", ""), "entity_name": payload.get("name", "")})
    sectors = pd.DataFrame(records).merge(mapping, on="cik", how="right")
    sectors["sic_major"] = sectors["sic_major"].fillna("unknown")
    sectors.to_parquet(ROOT / "data/sec/current_sic_snapshot.parquet", index=False)
    return sectors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--limit", type=int)
    args = parser.parse_args(); download(args.limit)
    print(build_sic_snapshot().notna().mean().to_string())
