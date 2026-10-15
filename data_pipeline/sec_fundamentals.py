from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_ticker_cik() -> pd.DataFrame:
    raw = json.loads((ROOT / "data/sec_company_tickers.json").read_text(encoding="utf-8"))
    rows = [{"ticker": x["ticker"].replace(".", "-"), "cik": int(x["cik_str"]),
             "company_name": x["title"]} for x in raw.values()]
    return pd.DataFrame(rows).drop_duplicates("ticker")


def coverage_report() -> pd.DataFrame:
    members = pd.read_parquet(ROOT / "data/pit/members.parquet")
    mapped = set(load_ticker_cik()["ticker"])
    rows = []
    requested = list(pd.date_range("2018-12-31", "2025-12-31", freq="YE")) + [members["date"].max()]
    for date in requested:
        actual = members.loc[members["date"] <= date, "date"].max()
        universe = set(members.loc[members["date"].eq(actual), "ticker"])
        rows.append({"requested_date": date, "membership_date": actual, "members": len(universe),
                     "cik_mapped": len(universe & mapped), "coverage": len(universe & mapped) / len(universe)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = coverage_report()
    path = ROOT / "reports/sec_fundamentals"; path.mkdir(parents=True, exist_ok=True)
    out.to_csv(path / "current_cik_mapping_coverage.csv", index=False)
    print(out.to_string(index=False))
