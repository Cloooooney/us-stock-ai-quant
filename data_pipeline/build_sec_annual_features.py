from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.sec_fundamentals import ROOT
from data_pipeline.download_sec_companyfacts import target_companies

CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
}
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}


def usd_facts(payload: dict, tags: list[str]) -> list[dict]:
    gaap = payload.get("facts", {}).get("us-gaap", {})
    combined = []
    for priority, tag in enumerate(tags):  # retain old and new taxonomy aliases
        units = gaap.get(tag, {}).get("units", {})
        for fact in units.get("USD", []):
            item = dict(fact); item["_priority"] = priority
            combined.append(item)
    return combined


def extract_company(path: Path, tickers: list[str]) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_accession: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for logical, tags in CONCEPTS.items():
        for fact in usd_facts(payload, tags):
            if fact.get("form") in ANNUAL_FORMS and fact.get("filed") and fact.get("accn"):
                by_accession[fact["accn"]][logical].append(fact)

    output = []
    for accn, concepts in by_accession.items():
        filed = pd.Timestamp(next(iter(concepts.values()))[0]["filed"])
        revenue = []
        for f in concepts.get("revenue", []):
            if not f.get("start") or not f.get("end"):
                continue
            start, end = pd.Timestamp(f["start"]), pd.Timestamp(f["end"])
            if 300 <= (end - start).days <= 430 and end <= filed and (filed - end).days <= 200:
                revenue.append((end, int(f.get("_priority", 99)), float(f["val"])))
        # Comparative annual facts in the same filing make growth point-in-time safe.
        revenue = sorted(revenue, key=lambda x: (-x[0].value, x[1]))
        if not revenue:
            continue
        dedup_revenue = []
        for d, priority, value in revenue:
            if not dedup_revenue or d != dedup_revenue[-1][0]:
                dedup_revenue.append((d, value))
        current_end, current_revenue = dedup_revenue[0]
        previous_revenue = next((v for d, v in dedup_revenue[1:] if 300 <= (current_end - d).days <= 430), np.nan)

        def duration_value(name: str) -> float:
            values = []
            for f in concepts.get(name, []):
                if not f.get("start") or not f.get("end"):
                    continue
                start, end = pd.Timestamp(f["start"]), pd.Timestamp(f["end"])
                if 300 <= (end - start).days <= 430 and abs((end - current_end).days) <= 7:
                    values.append((int(f.get("_priority", 99)), float(f["val"])))
            return sorted(values)[0][1] if values else np.nan

        def instant_value(name: str) -> float:
            values = [(pd.Timestamp(f["end"]), int(f.get("_priority", 99)), float(f["val"])) for f in concepts.get(name, []) if f.get("end")]
            aligned = [(priority, value) for d, priority, value in values if abs((d - current_end).days) <= 7]
            return sorted(aligned)[0][1] if aligned else np.nan

        ni, cfo, capex = duration_value("net_income"), duration_value("operating_cash_flow"), duration_value("capex")
        assets, liabilities = instant_value("assets"), instant_value("liabilities")
        for ticker in tickers:
            output.append({"ticker": ticker, "cik": int(payload["cik"]), "accession": accn,
                           "filed": filed, "available_date": filed + pd.Timedelta(days=1), "fiscal_end": current_end,
                           "revenue": current_revenue,
                           "revenue_growth": current_revenue / previous_revenue - 1 if previous_revenue > 0 else np.nan,
                           "net_margin": ni / current_revenue if current_revenue else np.nan,
                           "cash_quality": cfo / abs(ni) if ni and abs(ni) > 1 else np.nan,
                           "roa": ni / assets if assets else np.nan,
                           "liabilities_to_assets": liabilities / assets if assets else np.nan,
                           "capex_to_revenue": capex / current_revenue if current_revenue else np.nan})
    return output


def main() -> None:
    mapping = target_companies(); cik_tickers = mapping.groupby("cik")["ticker"].apply(list).to_dict()
    rows, failures = [], []
    files = sorted((ROOT / "data/sec/companyfacts").glob("CIK*.json"))
    for i, path in enumerate(files, 1):
        cik = int(path.stem[3:])
        try:
            rows.extend(extract_company(path, cik_tickers.get(cik, [])))
        except Exception as exc:
            failures.append({"file": path.name, "error": str(exc)})
        if i % 50 == 0:
            print(f"parsed {i}/{len(files)}; annual records={len(rows)}; failures={len(failures)}", flush=True)
    out = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    out = out.sort_values(["ticker", "available_date", "fiscal_end"]).drop_duplicates(["ticker", "accession"], keep="last")
    # Company Facts usually assigns comparative values to their original filing,
    # not the later accession. Reconstruct YoY growth only from values that had
    # already been disclosed before each new filing; amendments update the cache.
    rebuilt = []
    for ticker, group in out.groupby("ticker", sort=False):
        known: dict[pd.Timestamp, float] = {}
        for idx, row in group.sort_values(["available_date", "fiscal_end"]).iterrows():
            prior_ends = [d for d in known if 300 <= (row["fiscal_end"] - d).days <= 430]
            prior = known[max(prior_ends)] if prior_ends else np.nan
            out.at[idx, "revenue_growth"] = row["revenue"] / prior - 1 if prior and prior > 0 else np.nan
            known[row["fiscal_end"]] = row["revenue"]
    target = ROOT / "data/sec/annual_fundamentals.parquet"; target.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(target, index=False)
    pd.DataFrame(failures, columns=["file", "error"]).to_csv(ROOT / "data/sec/parse_failures.csv", index=False)
    print(f"saved {len(out):,} rows, {out.ticker.nunique()} tickers, {out.filed.min()} -> {out.filed.max()}")
    print(out.notna().mean().to_string())


if __name__ == "__main__": main()
