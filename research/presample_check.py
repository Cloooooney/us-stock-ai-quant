"""Pre-sample check: the frozen V6 and V7 on 2012-2017 signals.

Pre-registered in docs/superpowers/specs/2026-10-19-presample-and-factor-lab.md
(Part A). No rule or setting is changed; this only runs the frozen models on
months they have never been evaluated on.

    python -m research.presample_check
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/presample_v6"
START, END = "2012-01-01", "2017-12-31"
T_THRESHOLD = 1.65
PREREGISTRATION = "docs/superpowers/specs/2026-10-19-presample-and-factor-lab.md"


def reading(mean_excess: float, t: float) -> str:
    if mean_excess > 0 and t >= T_THRESHOLD:
        return "consistent_with_edge"
    if mean_excess <= 0:
        return "inconsistent_with_edge"
    return "inconclusive"


def excess_stats(strategy: pd.Series, benchmark: pd.Series, execution: pd.Series, factors) -> dict:
    from backtests.run_v7_factor import newey_west_mean_t
    from research.factor_attribution import attribute

    excess = (strategy - benchmark)
    excess.index = pd.to_datetime(execution).dt.to_period("M")
    excess = excess.dropna()
    t = newey_west_mean_t(excess)
    out = {"months": int(len(excess)), "mean_monthly_excess": float(excess.mean()),
           "annual_excess": float(excess.mean() * 12), "newey_west_t": t,
           "months_ahead": float((excess > 0).mean()), "reading": reading(float(excess.mean()), t)}
    if factors is not None:
        alpha = attribute(excess, factors, None)
        out["factor_alpha_annual"] = alpha["alpha_annual"]
        out["factor_alpha_t"] = alpha["alpha_t"]
    return out


def main() -> None:
    from backtests.run_v6_factor import align_benchmarks, apply_cost_scenario, safe_metrics, spy_returns_for_horizons
    from models.v6_factor import run_v6_variant
    from models.v7_factor import SCORES, attach_v7_features, run_v7, score_v7
    from models.walk_forward import Config, load_source
    from research.factor_attribution import load_factors

    OUT.mkdir(parents=True, exist_ok=True)
    cfg = Config(first_prediction=START, top_n=20, cost_bps=10)
    dataset = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    dataset = dataset.loc[dataset["date"].between(START, END)]
    fundamentals = pd.read_parquet(ROOT / "data/sec/quarterly_fundamentals.parquet")
    prices, _, _ = load_source(ROOT)
    research = attach_v7_features(dataset, fundamentals, prices)
    scored = score_v7(research)

    _, v6, _ = run_v6_variant(research, cfg, variant="blend")
    v7, _, dedupe = run_v7(scored, cfg, SCORES["fallback"])
    combined = align_benchmarks(v6, scored, spy_returns_for_horizons(prices, scored))
    combined["net_return_25bps"] = apply_cost_scenario(combined, 25)
    combined = combined.merge(v7[["date", "net_return"]].rename(columns={"net_return": "v7_net_return"}),
                              on="date", how="left", validate="one_to_one")
    try:
        factors = load_factors()
    except Exception:  # attribution is reported, not required for the reading
        factors = None

    performance = pd.DataFrame([{"strategy": name, **safe_metrics(combined[column])} for name, column in (
        ("v6_10bps", "net_return"), ("v6_25bps", "net_return_25bps"), ("v7_10bps", "v7_net_return"),
        ("point_in_time_equal_weight", "equal_weight_return"), ("spy", "spy_return"))])
    coverage = research.groupby(research["date"].dt.year)[["roa", "sales_yield"]].apply(
        lambda frame: frame.notna().mean()).round(3)
    summary = {
        "preregistration": PREREGISTRATION, "signals": [str(combined["date"].min().date()),
                                                        str(combined["date"].max().date())],
        "v6_vs_equal_weight": excess_stats(combined["net_return"], combined["equal_weight_return"],
                                           combined["execution_date"], factors),
        "v7_vs_equal_weight": excess_stats(combined["v7_net_return"], combined["equal_weight_return"],
                                           combined["execution_date"], factors),
        "v6_vs_spy": excess_stats(combined["net_return"], combined["spy_return"], combined["execution_date"], None),
        "v7_dedupe_months": int(len(dedupe)),
        "fundamental_coverage_by_year": {str(k): v for k, v in coverage.to_dict(orient="index").items()},
    }
    combined.to_csv(OUT / "monthly_returns.csv", index=False)
    performance.to_csv(OUT / "performance.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(performance.round(4).to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
