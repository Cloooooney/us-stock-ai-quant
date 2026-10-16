"""Run the pre-registered V7 backtest and record its decision.

Follows docs/superpowers/specs/2026-10-16-v7-factor-model-design.md exactly:
the improvement sleeve is adopted only if it passes both development-period
tests; later months are diagnostics. Writes reports/ai_v7_factor/ and freezes V7.

    python -m backtests.run_v7_factor
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtests.run_v6_factor import (PERIODS, align_benchmarks, apply_cost_scenario, safe_metrics,
                                     spy_returns_for_horizons)
from models.v6_factor import run_v6_variant
from models.v7_factor import SCORES, attach_v7_features, run_v7, score_v7
from models.walk_forward import Config, load_source

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ai_v7_factor"
DEVELOPMENT = ("2018-01-01", "2022-12-31")
T_THRESHOLD = 1.65
TOP_QUANTILE = 0.8
PREREGISTRATION = "docs/superpowers/specs/2026-10-16-v7-factor-model-design.md"


def monthly_rank_ic(scored: pd.DataFrame, column: str) -> pd.Series:
    def ic(group: pd.DataFrame) -> float:
        valid = group[[column, "target_return"]].dropna()
        return valid[column].corr(valid["target_return"], method="spearman") if len(valid) >= 3 else np.nan

    return scored.groupby("date").apply(ic).dropna()


def top_quantile_spread(scored: pd.DataFrame, column: str, quantile: float = TOP_QUANTILE) -> pd.Series:
    """Equal-weight top-quantile return minus the equal-weight universe, indexed
    by the calendar month in which each holding period executes."""
    rows = {}
    for signal, group in scored.groupby("date", sort=True):
        ranks = group[column].rank(pct=True)
        top = group.loc[ranks > quantile, "target_return"].mean()
        month = pd.to_datetime(group["execution_date"]).mode().iloc[0].to_period("M")
        rows[month] = top - group["target_return"].mean()
    return pd.Series(rows).sort_index()


def newey_west_mean_t(series: pd.Series) -> float:
    from research.factor_attribution import ols_newey_west

    fit = ols_newey_west(series.to_numpy(dtype=float), np.empty((len(series), 0)))
    return float(fit["t"][0])


def decide(scored: pd.DataFrame, factors: pd.DataFrame) -> dict:
    from research.factor_attribution import attribute

    dev = scored.loc[scored["date"].between(*DEVELOPMENT)]
    ic = monthly_rank_ic(dev, "improvement_score")
    spread = top_quantile_spread(dev, "improvement_score")
    alpha = attribute(spread, factors, None)
    ic_t = newey_west_mean_t(ic)
    passes_ic = bool(ic.mean() > 0 and ic_t >= T_THRESHOLD)
    passes_alpha = bool(alpha["alpha_monthly"] > 0 and alpha["alpha_t"] >= T_THRESHOLD)
    adopted = passes_ic and passes_alpha
    return {"preregistration": PREREGISTRATION, "development_period": list(DEVELOPMENT),
            "rank_ic": {"months": int(len(ic)), "mean": float(ic.mean()), "newey_west_t": ic_t,
                        "positive_month_share": float((ic > 0).mean()), "passes": passes_ic},
            "top_quintile_alpha": {"months": alpha["months"], "alpha_annual": alpha["alpha_annual"],
                                   "newey_west_t": alpha["alpha_t"], "r2": alpha["r2"], "passes": passes_alpha},
            "threshold_t": T_THRESHOLD, "improvement_sleeve_adopted": adopted,
            "score": SCORES["candidate"] if adopted else SCORES["fallback"]}


def performance(combined: pd.DataFrame) -> pd.DataFrame:
    columns = {"v7_10bps": "net_return", "v7_25bps": "net_return_25bps", "v6_10bps": "v6_net_return",
               "point_in_time_equal_weight": "equal_weight_return", "spy": "spy_return"}
    rows = []
    for period, start, end in PERIODS:
        section = combined.loc[combined["date"].between(start, end)]
        for strategy, column in columns.items():
            rows.append({"period": period, "strategy": strategy, **safe_metrics(section[column]),
                         "avg_turnover": section["turnover"].mean() if strategy.startswith("v7") else np.nan})
    return pd.DataFrame(rows)


def main() -> None:
    from research.factor_attribution import load_factors

    OUT.mkdir(parents=True, exist_ok=True)
    config = Config(first_prediction="2018-01-01", top_n=20, cost_bps=10)
    dataset = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    fundamentals = pd.read_parquet(ROOT / "data/sec/quarterly_fundamentals.parquet")
    prices, _, _ = load_source(ROOT)
    research = attach_v7_features(dataset, fundamentals, prices)
    research = research.loc[research["date"] >= pd.Timestamp(config.first_prediction)].copy()
    scored = score_v7(research)

    decision = decide(scored, load_factors())
    returns, holdings, dedupe = run_v7(scored, config, decision["score"])
    returns["net_return_25bps"] = apply_cost_scenario(returns, 25)
    _, v6_returns, _ = run_v6_variant(research, config, variant="blend")
    combined = align_benchmarks(returns, scored, spy_returns_for_horizons(prices, scored))
    combined = combined.merge(v6_returns[["date", "net_return"]].rename(columns={"net_return": "v6_net_return"}),
                              on="date", how="left", validate="one_to_one")

    frozen = {"model": "v7_unique_issuer" + ("_improvement" if decision["improvement_sleeve_adopted"] else ""),
              "frozen_on": date.today().isoformat(), "score": decision["score"], "top_n": config.top_n,
              "primary_cost_bps": config.cost_bps, "stress_cost_bps": 25, "fundamental_max_age_days": 460,
              "one_position_per_issuer": True, "preregistration": PREREGISTRATION,
              "first_signal": str(scored["date"].min().date()), "last_signal": str(scored["date"].max().date())}
    performance(combined).to_csv(OUT / "performance_summary.csv", index=False)
    combined.to_csv(OUT / "monthly_returns.csv", index=False)
    holdings.to_csv(OUT / "monthly_holdings.csv", index=False)
    dedupe.to_csv(OUT / "dedupe_changes.csv", index=False)
    (OUT / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    (OUT / "frozen_config.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    print(json.dumps(decision, indent=2))
    print(pd.read_csv(OUT / "performance_summary.csv").round(4).to_string(index=False))
    print(f"\nDe-duplication changed holdings in {len(dedupe)} months.")


if __name__ == "__main__":
    main()
