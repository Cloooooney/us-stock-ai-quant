"""Factor lab: test a pre-registered batch of candidate factors.

Batch 1 is pre-registered in
docs/superpowers/specs/2026-10-19-presample-and-factor-lab.md (Part B). The
evaluation functions are generic so later batches reuse them with a threshold
that accounts for every candidate tested so far (trial_registry.csv).

    python -m research.factor_lab
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/factor_lab"
PREREGISTRATION = "docs/superpowers/specs/2026-10-19-presample-and-factor-lab.md"
DEV_END = "2022-12-31"
COST_BPS = 10
TOP, BOTTOM = 0.8, 0.2
BATCH1 = {"net_issuance": -1, "seasonality": 1, "high_52w": 1, "short_reversal": 1}  # +1: higher is better
PRIOR_WINDOW_DAYS = (330, 400)
MAX_AGE_DAYS = 460
SEASONAL_YEARS, SEASONAL_MIN = 5, 3


def bonferroni_t(candidates: int, alpha: float = 0.05) -> float:
    """One-sided normal critical value at alpha / candidates."""
    from statistics import NormalDist

    return float(NormalDist().inv_cdf(1 - alpha / candidates))


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------

def split_product(splits: pd.DataFrame | None, after, through) -> float:
    """Product of split ratios in one ticker's split table dated in (after, through]."""
    if splits is None or splits.empty:
        return 1.0
    rows = splits.loc[(splits["date"] > after) & (splits["date"] <= through)]
    return float(rows["stock_splits"].prod()) if len(rows) else 1.0


def add_net_issuance(fundamentals: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """log(shares now / split-adjusted shares one fiscal year earlier) per snapshot,
    using only a prior snapshot already available when the current one was."""
    frame = fundamentals.copy()
    for column in ("fiscal_end", "available_date", "filed"):
        frame[column] = pd.to_datetime(frame[column])
    wavg = frame.get("weighted_average_shares", pd.Series(np.nan, index=frame.index))
    out = frame.get("shares_outstanding", pd.Series(np.nan, index=frame.index))
    frame["issuance_shares"] = wavg.where(wavg > 0, out).where(lambda s: s > 0)
    frame["net_issuance"] = np.nan
    splits = splits.loc[splits["stock_splits"].notna() & ~splits["stock_splits"].isin([0.0, 1.0])].copy()
    splits["date"] = pd.to_datetime(splits["date"])
    by_ticker = {t: g for t, g in splits.groupby("ticker")}
    lo, hi = (pd.Timedelta(days=d) for d in PRIOR_WINDOW_DAYS)
    parts = []
    for ticker, rows in frame.groupby("ticker", sort=False):
        rows = rows.sort_values(["available_date", "fiscal_end", "accession"]).copy()
        ends, avail = rows["fiscal_end"].to_numpy(), rows["available_date"].to_numpy()
        shares, filed = rows["issuance_shares"].to_numpy(dtype=float), rows["filed"].to_numpy()
        values = np.full(len(rows), np.nan)
        for i in range(len(rows)):
            gap = ends[i] - ends
            eligible = np.flatnonzero((gap >= lo) & (gap <= hi) & (avail <= avail[i]))
            if len(eligible) == 0 or not shares[i] > 0:
                continue
            j = eligible[np.lexsort((ends[eligible], avail[eligible]))][-1]
            if not shares[j] > 0:
                continue
            ratio = shares[i] / (shares[j] * split_product(by_ticker.get(ticker), filed[j], filed[i]))
            if 0.01 <= ratio <= 100:
                values[i] = math.log(ratio)
        rows["net_issuance"] = values
        parts.append(rows)
    return pd.concat(parts, ignore_index=True) if parts else frame


def seasonal_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """For each ticker and holding month m, the mean return of the same calendar
    month over the previous five years (at least three), from month-end closes."""
    daily = prices.loc[:, ["ticker", "date", "adj_close"]].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["month"] = daily["date"].dt.to_period("M")
    month_end = daily.sort_values("date").groupby(["ticker", "month"])["adj_close"].last()
    wide = month_end.unstack("ticker").sort_index()
    wide = wide.reindex(pd.period_range(wide.index.min(), wide.index.max(), freq="M"))
    returns = wide.pct_change(fill_method=None)
    # Row m holds returns of months m-12, m-24, ...: all completed before any signal for month m.
    stacked = np.stack([returns.shift(12 * k).to_numpy() for k in range(1, SEASONAL_YEARS + 1)])
    counts = np.sum(~np.isnan(stacked), axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-NaN slices
        mean = np.nanmean(stacked, axis=0)
    mean[counts < SEASONAL_MIN] = np.nan
    result = pd.DataFrame(mean, index=pd.PeriodIndex(returns.index, name="holding_month"),
                          columns=pd.Index(returns.columns, name="ticker"))
    long = result.stack().rename("seasonality").reset_index()
    return long.dropna(subset=["seasonality"])


def build_candidates(dataset: pd.DataFrame, fundamentals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    from models.v6_factor import attach_valuation_features, merge_quarterly_fundamentals, score_factors

    valued = attach_valuation_features(merge_quarterly_fundamentals(dataset, fundamentals), prices)
    splits = prices.loc[:, ["ticker", "date", "stock_splits"]] if "stock_splits" in prices else \
        pd.DataFrame(columns=["ticker", "date", "stock_splits"])
    issuance = add_net_issuance(fundamentals, splits)[["ticker", "accession", "net_issuance"]]
    out = valued.merge(issuance.drop_duplicates(["ticker", "accession"], keep="last"),
                       on=["ticker", "accession"], how="left", validate="many_to_one")
    out.loc[out["fundamental_age_days"] > MAX_AGE_DAYS, "net_issuance"] = np.nan
    seasonal = seasonal_signal(prices)
    out["holding_month"] = pd.to_datetime(out["date"]).dt.to_period("M") + 1
    out = out.merge(seasonal, on=["ticker", "holding_month"], how="left", validate="many_to_one")
    out["high_52w"] = out["drawdown_252"]
    out["short_reversal"] = -out["mom_21"]
    return score_factors(out)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_month(group: pd.DataFrame, column: str, direction: int, previous_top: set | None) -> tuple[dict, set]:
    universe_return = group["target_return"].mean()
    valid = group[[column, "target_return", "ticker", "v6_score"]].dropna(subset=[column, "target_return"])
    if len(valid) < 25:
        return {}, previous_top or set()
    signal = valid[column] * direction
    ranks = signal.rank(pct=True)
    top = valid.loc[ranks > TOP]
    bottom = valid.loc[ranks <= BOTTOM]
    names = set(top["ticker"])
    turnover = 1.0 if not previous_top else 1 - len(names & previous_top) / max(len(names), 1)
    spread = top["target_return"].mean() - universe_return
    return {"ic": signal.corr(valid["target_return"], method="spearman"),
            "spread": spread, "net_spread": spread - turnover * COST_BPS / 10_000,
            "long_short": top["target_return"].mean() - bottom["target_return"].mean(),
            "turnover": turnover, "corr_v6": signal.corr(valid["v6_score"], method="spearman"),
            "coverage": len(valid) / len(group),
            "month": pd.to_datetime(group["execution_date"]).mode().iloc[0].to_period("M")}, names


def monthly_panel(scored: pd.DataFrame, column: str, direction: int) -> pd.DataFrame:
    rows, previous = [], None
    for date, group in scored.groupby("date", sort=True):
        row, previous = evaluate_month(group, column, direction, previous)
        if row:
            rows.append({"date": date, **row})
    return pd.DataFrame(rows)


def summarize(panel: pd.DataFrame, factors: pd.DataFrame, threshold: float) -> dict:
    from backtests.run_v7_factor import newey_west_mean_t
    from research.factor_attribution import attribute

    dev = panel.loc[panel["date"] <= pd.Timestamp(DEV_END)]
    diag = panel.loc[panel["date"] > pd.Timestamp(DEV_END)]
    ic_t = newey_west_mean_t(dev["ic"].dropna())
    spread = dev.set_index("month")["spread"]
    alpha = attribute(spread, factors, None)
    tests = {"rank_ic_mean": float(dev["ic"].mean()), "rank_ic_t": ic_t,
             "alpha_annual": alpha["alpha_annual"], "alpha_t": alpha["alpha_t"],
             "net_spread_annual": float(dev["net_spread"].mean() * 12)}
    passed = bool(tests["rank_ic_mean"] > 0 and ic_t >= threshold and alpha["alpha_annual"] > 0
                  and alpha["alpha_t"] >= threshold and tests["net_spread_annual"] > 0)
    return {**tests, "months": int(len(dev)), "passes": passed,
            "diagnostic_rank_ic_mean": float(diag["ic"].mean()) if len(diag) else None,
            "eligible_for_v8": bool(passed and len(diag) and diag["ic"].mean() > 0),
            "long_short_annual": float(dev["long_short"].mean() * 12),
            "top_quintile_turnover": float(dev["turnover"].iloc[1:].mean()) if len(dev) > 1 else None,
            "mean_corr_with_v6": float(dev["corr_v6"].mean()), "coverage": float(dev["coverage"].mean())}


def registry(batch_results: dict, threshold: float) -> pd.DataFrame:
    rows = []
    v7 = ROOT / "reports/ai_v7_factor/decision.json"
    if v7.exists():
        decision = json.loads(v7.read_text(encoding="utf-8"))
        rows.append({"date": "2026-10-16", "batch": "v7", "candidate": "improvement_sleeve",
                     "threshold_t": decision["threshold_t"], "passes": decision["improvement_sleeve_adopted"]})
    for name, result in batch_results.items():
        rows.append({"date": "2026-10-19", "batch": "factor_lab_1", "candidate": name,
                     "threshold_t": round(threshold, 3), "passes": result["passes"]})
    return pd.DataFrame(rows)


def main() -> None:
    import pyarrow.parquet as pq

    from models.walk_forward import load_source
    from research.factor_attribution import load_factors

    OUT.mkdir(parents=True, exist_ok=True)
    threshold = bonferroni_t(len(BATCH1))
    dataset = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    fundamentals = pd.read_parquet(ROOT / "data/sec/quarterly_fundamentals.parquet")
    _, _, recycled = load_source(ROOT)
    path = ROOT / "data/pit/prices.parquet"
    wanted = [c for c in ["ticker", "date", "close", "adj_close", "stock_splits"] if c in pq.read_schema(path).names]
    prices = pd.read_parquet(path, columns=wanted)
    prices = prices.loc[~prices["ticker"].isin(recycled)]
    scored = build_candidates(dataset, fundamentals, prices)
    factors = load_factors()

    results, panels = {}, []
    for name, direction in BATCH1.items():
        panel = monthly_panel(scored, name, direction)
        results[name] = summarize(panel, factors, threshold)
        panels.append(panel.assign(candidate=name))
    decision = {"preregistration": PREREGISTRATION, "development_end": DEV_END, "threshold_t": threshold,
                "candidates": results, "passed": [n for n, r in results.items() if r["passes"]],
                "eligible_for_v8": [n for n, r in results.items() if r["eligible_for_v8"]]}
    pd.DataFrame(results).T.to_csv(OUT / "batch1_results.csv")
    pd.concat(panels, ignore_index=True).to_csv(OUT / "batch1_monthly.csv", index=False)
    registry(results, threshold).to_csv(OUT / "trial_registry.csv", index=False)
    (OUT / "batch1_decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(pd.DataFrame(results).T.round(4).to_string())
    print(json.dumps({k: decision[k] for k in ("threshold_t", "passed", "eligible_for_v8")}, indent=2))


if __name__ == "__main__":
    main()
