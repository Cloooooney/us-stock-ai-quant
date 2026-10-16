from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.download_sec_companyfacts import target_companies
from data_pipeline.sec_fundamentals import ROOT


FLOW_CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
}
INSTANT_CONCEPTS = {
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}
SHARE_FLOW_CONCEPTS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
]
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
QUARTERLY_FORMS = {"10-Q", "10-Q/A"}
SUPPORTED_FORMS = ANNUAL_FORMS | QUARTERLY_FORMS
TTM_FLOWS = ("revenue", "net_income", "operating_cash_flow", "capex")


def _concept_facts(payload: dict, namespace: str, tags: list[str], unit: str) -> list[dict]:
    taxonomy = payload.get("facts", {}).get(namespace, {})
    combined: list[dict] = []
    for priority, tag in enumerate(tags):
        for fact in taxonomy.get(tag, {}).get("units", {}).get(unit, []):
            if fact.get("form") not in SUPPORTED_FORMS or not fact.get("accn") or not fact.get("filed"):
                continue
            item = dict(fact)
            item["_priority"] = priority
            combined.append(item)
    return combined


def _duration_days(fact: dict) -> int | None:
    if not fact.get("start") or not fact.get("end"):
        return None
    return (pd.Timestamp(fact["end"]) - pd.Timestamp(fact["start"])).days


def _safe_divide(numerator: float, denominator: float, absolute_denominator: bool = False) -> float:
    if pd.isna(numerator) or pd.isna(denominator):
        return np.nan
    value = abs(float(denominator)) if absolute_denominator else float(denominator)
    if abs(value) <= 1e-12:
        return np.nan
    result = float(numerator) / value
    return result if np.isfinite(result) else np.nan


def _select_period(revenue_facts: list[dict], accession: str, form: str, filed: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp, int] | None:
    candidates = []
    for fact in revenue_facts:
        if fact["accn"] != accession:
            continue
        days = _duration_days(fact)
        if days is None:
            continue
        start, end = pd.Timestamp(fact["start"]), pd.Timestamp(fact["end"])
        if end > filed or not 0 <= (filed - end).days <= 250:
            continue
        valid = 300 <= days <= 430 if form in ANNUAL_FORMS else 70 <= days <= 300
        if valid:
            candidates.append((end, days, -int(fact.get("_priority", 99)), start))
    if not candidates:
        return None
    current_end = max(x[0] for x in candidates)
    at_current_end = [x for x in candidates if abs((x[0] - current_end).days) <= 7]
    if form in ANNUAL_FORMS:
        _, days, _, start = min(at_current_end, key=lambda x: (abs(x[1] - 365), -x[2]))
    else:
        _, days, _, start = max(at_current_end, key=lambda x: (x[1], x[2]))
    return start, current_end, days


def _duration_value(facts: list[dict], accession: str, end: pd.Timestamp, target_days: int) -> float:
    candidates = []
    for fact in facts:
        if fact["accn"] != accession:
            continue
        days = _duration_days(fact)
        if days is None or abs((pd.Timestamp(fact["end"]) - end).days) > 7:
            continue
        candidates.append((abs(days - target_days), int(fact.get("_priority", 99)), float(fact["val"])))
    return min(candidates)[2] if candidates else np.nan


def _prior_duration_value(facts: list[dict], accession: str, end: pd.Timestamp, target_days: int) -> float:
    candidates = []
    for fact in facts:
        if fact["accn"] != accession:
            continue
        days = _duration_days(fact)
        if days is None:
            continue
        prior_end = pd.Timestamp(fact["end"])
        year_gap = (end - prior_end).days
        if 330 <= year_gap <= 400:
            candidates.append((abs(days - target_days), abs(year_gap - 365), int(fact.get("_priority", 99)), float(fact["val"])))
    return min(candidates)[3] if candidates else np.nan


def _instant_value(facts: list[dict], accession: str, fiscal_end: pd.Timestamp) -> float:
    candidates = []
    for fact in facts:
        if fact["accn"] != accession or not fact.get("end"):
            continue
        end = pd.Timestamp(fact["end"])
        if abs((end - fiscal_end).days) <= 10:
            candidates.append((abs((end - fiscal_end).days), int(fact.get("_priority", 99)), float(fact["val"])))
    return min(candidates)[2] if candidates else np.nan


def _shares_value(facts: list[dict], accession: str, filed: pd.Timestamp) -> float:
    candidates = []
    for fact in facts:
        if fact["accn"] != accession or not fact.get("end"):
            continue
        end = pd.Timestamp(fact["end"])
        if end <= filed:
            candidates.append((end, -int(fact.get("_priority", 99)), float(fact["val"])))
    return max(candidates)[2] if candidates else np.nan


def _raw_snapshots(payload: dict, tickers: list[str]) -> list[dict]:
    flows = {name: _concept_facts(payload, "us-gaap", tags, "USD") for name, tags in FLOW_CONCEPTS.items()}
    instants = {name: _concept_facts(payload, "us-gaap", tags, "USD") for name, tags in INSTANT_CONCEPTS.items()}
    weighted_shares = _concept_facts(payload, "us-gaap", SHARE_FLOW_CONCEPTS, "shares")
    shares = _concept_facts(payload, "dei", ["EntityCommonStockSharesOutstanding"], "shares")
    if not shares:
        shares = _concept_facts(payload, "us-gaap", ["CommonStockSharesOutstanding"], "shares")

    metadata: dict[str, dict] = {}
    for facts in [*flows.values(), *instants.values(), weighted_shares, shares]:
        for fact in facts:
            metadata.setdefault(fact["accn"], fact)

    rows: list[dict] = []
    for accession, meta in metadata.items():
        form = meta["form"]
        filed = pd.Timestamp(meta["filed"])
        period = _select_period(flows["revenue"], accession, form, filed)
        if period is None:
            continue
        period_start, fiscal_end, period_days = period
        current = {name: _duration_value(facts, accession, fiscal_end, period_days) for name, facts in flows.items()}
        prior = {name: _prior_duration_value(facts, accession, fiscal_end, period_days) for name, facts in flows.items()}
        assets = _instant_value(instants["assets"], accession, fiscal_end)
        liabilities = _instant_value(instants["liabilities"], accession, fiscal_end)
        equity = _instant_value(instants["equity"], accession, fiscal_end)
        if pd.isna(liabilities) and pd.notna(assets) and pd.notna(equity):
            liabilities = assets - equity
        base = {
            "cik": int(payload["cik"]),
            "accession": accession,
            "form": form,
            "filed": filed,
            "available_date": filed + pd.Timedelta(days=1),
            "period_start": period_start,
            "fiscal_end": fiscal_end,
            "period_days": period_days,
            "filing_lag_days": (filed - fiscal_end).days,
            "assets": assets,
            "liabilities": liabilities,
            "weighted_average_shares": _duration_value(
                weighted_shares, accession, fiscal_end, period_days
            ),
            "shares_outstanding": _shares_value(shares, accession, filed),
        }
        for name in TTM_FLOWS:
            base[f"reported_{name}"] = current[name]
            base[f"prior_ytd_{name}"] = prior[name]
        for ticker in tickers:
            rows.append({"ticker": ticker, **base})
    return rows


def _ttm_value(annual: dict | None, row: dict, name: str) -> float:
    current = row[f"reported_{name}"]
    if row["form"] in ANNUAL_FORMS:
        return current
    prior = row[f"prior_ytd_{name}"]
    if annual is None or pd.isna(current) or pd.isna(prior):
        return np.nan
    annual_value = annual.get(f"reported_{name}", np.nan)
    return annual_value + current - prior if pd.notna(annual_value) else np.nan


def _finalize_ttm(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_ticker[row["ticker"]].append(row)

    output: list[dict] = []
    for ticker_rows in by_ticker.values():
        annual_history: list[dict] = []
        finalized: list[dict] = []
        ordered = sorted(ticker_rows, key=lambda x: (x["available_date"], x["fiscal_end"], x["accession"]))
        for raw in ordered:
            row = dict(raw)
            eligible_annual = [
                x for x in annual_history
                if x["fiscal_end"] < row["fiscal_end"]
                and 0 < (row["fiscal_end"] - x["fiscal_end"]).days <= 460
                and x["available_date"] <= row["available_date"]
            ]
            annual = max(eligible_annual, key=lambda x: (x["fiscal_end"], x["available_date"])) if eligible_annual else None
            for name in TTM_FLOWS:
                row[f"ttm_{name}"] = _ttm_value(annual, row, name)

            prior_year = [
                x for x in finalized
                if 330 <= (row["fiscal_end"] - x["fiscal_end"]).days <= 400
                and pd.notna(x.get("ttm_revenue"))
            ]
            prior_ttm = max(prior_year, key=lambda x: (x["fiscal_end"], x["available_date"])) if prior_year else None
            row["revenue_growth"] = _safe_divide(
                row["ttm_revenue"], prior_ttm["ttm_revenue"] if prior_ttm else np.nan
            ) - 1 if prior_ttm else np.nan
            row["net_margin"] = _safe_divide(row["ttm_net_income"], row["ttm_revenue"])
            row["cash_quality"] = _safe_divide(
                row["ttm_operating_cash_flow"], row["ttm_net_income"], absolute_denominator=True
            )
            row["roa"] = _safe_divide(row["ttm_net_income"], row["assets"])
            row["liabilities_to_assets"] = _safe_divide(row["liabilities"], row["assets"])
            row["capex_to_revenue"] = _safe_divide(row["ttm_capex"], row["ttm_revenue"])
            row["free_cash_flow_margin"] = _safe_divide(
                row["ttm_operating_cash_flow"] - row["ttm_capex"], row["ttm_revenue"]
            )
            row["accruals_to_assets"] = _safe_divide(
                row["ttm_net_income"] - row["ttm_operating_cash_flow"], row["assets"]
            )
            finalized.append(row)
            if row["form"] in ANNUAL_FORMS:
                annual_history.append(row)
        output.extend(finalized)
    return output


def extract_payload(payload: dict, tickers: list[str]) -> list[dict]:
    return _finalize_ttm(_raw_snapshots(payload, tickers))


def extract_company(path: Path, tickers: list[str]) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return extract_payload(payload, tickers)


def main() -> None:
    mapping = target_companies()
    cik_tickers = mapping.groupby("cik")["ticker"].apply(list).to_dict()
    files = sorted((ROOT / "data/sec/companyfacts").glob("CIK*.json"))
    rows: list[dict] = []
    failures: list[dict] = []
    for index, path in enumerate(files, 1):
        cik = int(path.stem[3:])
        try:
            rows.extend(extract_company(path, cik_tickers.get(cik, [])))
        except Exception as exc:
            failures.append({"file": path.name, "error": str(exc)})
        if index % 50 == 0:
            print(f"parsed {index}/{len(files)}; snapshots={len(rows)}; failures={len(failures)}", flush=True)

    output = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    output = output.sort_values(["ticker", "available_date", "fiscal_end", "accession"])
    output = output.drop_duplicates(["ticker", "accession"], keep="last")
    target = ROOT / "data/sec/quarterly_fundamentals.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(target, index=False)
    pd.DataFrame(failures, columns=["file", "error"]).to_csv(
        ROOT / "data/sec/quarterly_parse_failures.csv", index=False
    )
    print(
        f"saved {len(output):,} rows, {output.ticker.nunique()} tickers, "
        f"{output.filed.min()} -> {output.filed.max()}"
    )
    print(output.notna().mean().sort_values().to_string())


if __name__ == "__main__":
    main()
