"""V7: V6 plus one position per issuer and a pre-registered improvement sleeve.

See docs/superpowers/specs/2026-10-16-v7-factor-model-design.md. Nothing here
changes V6; V6's functions are reused as they are.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from models.v6_factor import _rank_factors, attach_valuation_features, merge_quarterly_fundamentals, score_factors
from models.walk_forward import Config, portfolio_returns

IMPROVEMENT_FACTORS = {"d_roa": 1, "d_net_margin": 1, "d_fcf_margin": 1}
IMPROVEMENT_SOURCES = {"d_roa": "roa", "d_net_margin": "net_margin", "d_fcf_margin": "free_cash_flow_margin"}
PRIOR_WINDOW_DAYS = (330, 400)
MAX_AGE_DAYS = 460  # same expiry as V6
SCORES = {"candidate": "v7_candidate_score", "fallback": "v6_score"}


def add_improvement_features(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Year-over-year changes per snapshot, using only snapshots already
    available when the current one became available."""
    frame = fundamentals.copy()
    for column in ("fiscal_end", "available_date"):
        frame[column] = pd.to_datetime(frame[column])
    for feature in IMPROVEMENT_FACTORS:
        frame[feature] = np.nan
    lo, hi = (pd.Timedelta(days=d) for d in PRIOR_WINDOW_DAYS)
    parts = []
    for _, rows in frame.groupby("ticker", sort=False):
        rows = rows.sort_values(["available_date", "fiscal_end", "accession"]).copy()
        ends, avail = rows["fiscal_end"].to_numpy(), rows["available_date"].to_numpy()
        values = {f: rows[s].to_numpy(dtype=float) for f, s in IMPROVEMENT_SOURCES.items()}
        for i in range(len(rows)):
            gap = ends[i] - ends
            eligible = np.flatnonzero((gap >= lo) & (gap <= hi) & (avail <= avail[i]))
            if len(eligible) == 0:
                continue
            j = eligible[np.lexsort((ends[eligible], avail[eligible]))][-1]  # latest available, then latest period
            for feature, source in values.items():
                rows.iloc[i, rows.columns.get_loc(feature)] = source[i] - source[j]
        parts.append(rows)
    return pd.concat(parts, ignore_index=True) if parts else frame


def attach_v7_features(dataset: pd.DataFrame, fundamentals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """V6's point-in-time merge and valuation, then the improvement features and
    CIK of the exact snapshot each row uses."""
    valued = attach_valuation_features(merge_quarterly_fundamentals(dataset, fundamentals), prices)
    extra = add_improvement_features(fundamentals)[["ticker", "accession", "cik", *IMPROVEMENT_FACTORS]]
    extra = extra.drop_duplicates(["ticker", "accession"], keep="last")
    out = valued.merge(extra, on=["ticker", "accession"], how="left", validate="many_to_one")
    stale = out["fundamental_age_days"] > MAX_AGE_DAYS
    out.loc[stale, list(IMPROVEMENT_FACTORS)] = np.nan
    return out


def score_v7(data: pd.DataFrame) -> pd.DataFrame:
    scored = score_factors(data)  # momentum, quality, value, and V6 blend exactly as V6
    scored, ranks = _rank_factors(scored, IMPROVEMENT_FACTORS)
    scored["improvement_score"] = scored[ranks].mean(axis=1)
    scored["v7_candidate_score"] = scored[["momentum_score", "quality_score", "value_score",
                                           "improvement_score"]].mean(axis=1)
    return scored


def select_unique_issuers(group: pd.DataFrame, score: str, top_n: int = 20) -> pd.DataFrame:
    """Top ``top_n`` by score (ties by ticker), skipping a second share class of
    an issuer already selected. Rows without a CIK count as their own issuer."""
    ordered = group.sort_values([score, "ticker"], ascending=[False, True], kind="mergesort")
    chosen, issuers = [], set()
    for index, row in ordered.iterrows():
        issuer = row["cik"] if pd.notna(row.get("cik")) else f"ticker:{row['ticker']}"
        if issuer in issuers:
            continue
        issuers.add(issuer)
        chosen.append(index)
        if len(chosen) == top_n:
            break
    selected = ordered.loc[chosen].copy()
    selected["portfolio_rank"] = range(1, len(selected) + 1)
    return selected


def run_v7(scored: pd.DataFrame, cfg: Config, score: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Backtest returns, holdings, and the months where de-duplication changed
    the holdings relative to plain top-N selection."""
    selections, changed = [], []
    for date, group in scored.groupby("date", sort=True):
        unique = select_unique_issuers(group, score, cfg.top_n)
        plain = group.sort_values([score, "ticker"], ascending=[False, True], kind="mergesort").head(cfg.top_n)
        if set(unique["ticker"]) != set(plain["ticker"]):
            changed.append({"date": date, "removed": ",".join(sorted(set(plain["ticker"]) - set(unique["ticker"]))),
                            "added": ",".join(sorted(set(unique["ticker"]) - set(plain["ticker"])))})
        selections.append(unique)
    chosen = pd.concat(selections, ignore_index=True)
    chosen["prediction"] = chosen[score]
    returns, holdings = portfolio_returns(chosen, cfg)
    return returns, holdings, pd.DataFrame(changed, columns=["date", "removed", "added"])


def build_v7_signal(root, score: str, top_n: int = 20) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Frozen V7 holdings for the latest completed month-end, the scored
    universe, and prices. Nothing is fitted."""
    from pathlib import Path

    from models.walk_forward import build_latest_signal_snapshot, load_source

    root = Path(root)
    prices, intervals, _ = load_source(root)
    latest = build_latest_signal_snapshot(prices, intervals)
    fundamentals = pd.read_parquet(root / "data/sec/quarterly_fundamentals.parquet")
    scored = score_v7(attach_v7_features(latest, fundamentals, prices))
    signal_date = pd.Timestamp(latest["date"].max())
    current = scored.loc[scored["date"].eq(signal_date)]
    selected = select_unique_issuers(current, score, top_n)
    if len(selected) != top_n:
        raise ValueError(f"V7 selection produced {len(selected)} holdings instead of {top_n}")
    selected["prediction"] = selected[score]
    return selected, sorted(current["ticker"].astype(str).unique()), prices
