from __future__ import annotations
import pandas as pd


def sic_division(sic_major) -> str:
    try: n = int(sic_major)
    except (TypeError, ValueError): return "unknown"
    for lo, hi, name in ((1, 9, "agriculture"), (10, 14, "mining"), (15, 17, "construction"),
                         (20, 39, "manufacturing"), (40, 49, "transport_utilities"),
                         (50, 51, "wholesale"), (52, 59, "retail"), (60, 67, "finance_real_estate"),
                         (70, 89, "services"), (91, 99, "public_admin")):
        if lo <= n <= hi: return name
    return "unknown"


def select_with_sector_cap(predictions: pd.DataFrame, top_n: int = 20, max_per_sector: int = 4,
                           max_per_division: int = 6) -> pd.DataFrame:
    chosen, counts, division_counts = [], {}, {}
    for row in predictions.sort_values("prediction", ascending=False).itertuples():
        sector = row.sic_major if pd.notna(row.sic_major) else "unknown"
        division = sic_division(sector)
        if counts.get(sector, 0) >= max_per_sector or division_counts.get(division, 0) >= max_per_division:
            continue
        chosen.append(row.Index); counts[sector] = counts.get(sector, 0) + 1
        division_counts[division] = division_counts.get(division, 0) + 1
        if len(chosen) == top_n:
            break
    out = predictions.loc[chosen].sort_values("prediction", ascending=False).copy()
    out["sic_division"] = out["sic_major"].map(sic_division)
    out["portfolio_rank"] = range(1, len(out) + 1)
    return out
