from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from models.v6_factor import (
    FUNDAMENTAL_VALUE_COLUMNS,
    attach_valuation_features,
    merge_quarterly_fundamentals,
    run_v6_variant,
)
from models.walk_forward import Config, load_source, metrics


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ai_v6_factor"
PERIODS = (
    ("development", "2018-01-01", "2022-12-31"),
    ("diagnostic", "2023-01-01", "2099-12-31"),
    ("full", "2018-01-01", "2099-12-31"),
)
STRATEGY_COLUMNS = {
    "v6_blend_10bps": "net_return",
    "v6_blend_25bps": "net_return_25bps",
    "point_in_time_equal_weight": "equal_weight_return",
    "spy": "spy_return",
}


def safe_metrics(returns: pd.Series) -> dict[str, float]:
    clean = returns.dropna()
    if clean.empty:
        return {
            "annual_return": np.nan,
            "annual_volatility": np.nan,
            "sharpe_0rf": np.nan,
            "max_drawdown": np.nan,
            "total_return": np.nan,
            "months": 0,
        }
    return metrics(clean)


def apply_cost_scenario(returns: pd.DataFrame, cost_bps: float) -> pd.Series:
    return returns["gross_return"] - returns["turnover"] * cost_bps / 10_000


def align_benchmarks(
    strategy_returns: pd.DataFrame,
    scored: pd.DataFrame,
    spy_returns: pd.DataFrame,
) -> pd.DataFrame:
    equal_weight = (
        scored.groupby("date", as_index=False)["target_return"]
        .mean()
        .rename(columns={"target_return": "equal_weight_return"})
    )
    output = strategy_returns.merge(equal_weight, on="date", how="left", validate="one_to_one")
    output = output.merge(spy_returns[["date", "spy_return"]], on="date", how="left", validate="one_to_one")
    return output.sort_values("date").reset_index(drop=True)


def drop_best_months(
    returns: pd.DataFrame,
    count: int = 3,
    column: str = "net_return",
) -> tuple[pd.DataFrame, pd.Series]:
    if count <= 0 or returns.empty:
        return returns.copy(), pd.Series(dtype="datetime64[ns]")
    indices = returns[column].nlargest(min(count, len(returns))).index
    removed = returns.loc[indices, "date"].sort_values().reset_index(drop=True)
    reduced = returns.drop(index=indices).sort_values("date").reset_index(drop=True)
    return reduced, removed


def spy_returns_for_horizons(prices: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    def dominant_date(series: pd.Series) -> pd.Timestamp:
        modes = series.dropna().mode()
        return modes.iloc[0] if not modes.empty else pd.NaT

    horizons = scored.groupby("date", as_index=False).agg(
        execution_date=("execution_date", dominant_date),
        exit_date=("exit_date", dominant_date),
    )
    spy = prices.loc[prices["ticker"].eq("SPY"), ["date", "open", "close", "adj_close"]].copy()
    spy["adj_open"] = spy["open"] * spy["adj_close"] / spy["close"]
    opens = spy[["date", "adj_open"]]
    output = horizons.merge(
        opens.rename(columns={"date": "execution_date", "adj_open": "entry"}),
        on="execution_date",
        how="left",
        validate="many_to_one",
    )
    output = output.merge(
        opens.rename(columns={"date": "exit_date", "adj_open": "exit"}),
        on="exit_date",
        how="left",
        validate="many_to_one",
    )
    output["spy_return"] = output["exit"] / output["entry"] - 1
    return output[["date", "spy_return"]]


def rank_information_coefficient(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, group in scored.groupby("date", sort=True):
        valid = group[["v6_score", "target_return"]].dropna()
        value = valid["v6_score"].corr(valid["target_return"], method="spearman") if len(valid) >= 3 else np.nan
        rows.append({"date": date, "rank_ic": value, "n": len(valid)})
    return pd.DataFrame(rows)


def performance_rows(returns: pd.DataFrame, label: str = "standard") -> list[dict]:
    rows = []
    for period, start, end in PERIODS:
        section = returns.loc[returns["date"].between(start, end)]
        for strategy, column in STRATEGY_COLUMNS.items():
            rows.append({
                "robustness": label,
                "period": period,
                "strategy": strategy,
                **safe_metrics(section[column]),
                "avg_turnover": section["turnover"].mean() if strategy.startswith("v6_") else 0.0,
            })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    config = Config(first_prediction="2018-01-01", top_n=20, cost_bps=10)
    dataset = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    fundamentals = pd.read_parquet(ROOT / "data/sec/quarterly_fundamentals.parquet")
    prices, _, _ = load_source(ROOT)

    merged = merge_quarterly_fundamentals(dataset, fundamentals)
    valued = attach_valuation_features(merged, prices)
    research = valued.loc[valued["date"] >= pd.Timestamp(config.first_prediction)].copy()

    scored, strategy_returns, holdings = run_v6_variant(research, config, variant="blend")
    strategy_returns["net_return_25bps"] = apply_cost_scenario(strategy_returns, 25)
    spy_returns = spy_returns_for_horizons(prices, scored)
    combined = align_benchmarks(strategy_returns, scored, spy_returns)
    if combined[["equal_weight_return", "spy_return"]].isna().any().any():
        raise ValueError("V6 benchmark alignment produced missing months")

    summary = pd.DataFrame(performance_rows(combined))
    reduced, removed_dates = drop_best_months(combined, count=3)
    robustness = pd.DataFrame(performance_rows(reduced, label="remove_best_3_v6_months"))

    ablations = []
    for variant in ("momentum", "quality", "value", "blend"):
        _, variant_returns, _ = run_v6_variant(research, config, variant=variant)
        for period, start, end in PERIODS:
            section = variant_returns.loc[variant_returns["date"].between(start, end)]
            ablations.append({
                "period": period,
                "variant": variant,
                **safe_metrics(section["net_return"]),
                "avg_turnover": section["turnover"].mean(),
            })

    rank_ic = rank_information_coefficient(scored)
    coverage_columns = [
        "shares_outstanding",
        "revenue_growth",
        "net_margin",
        "roa",
        "free_cash_flow_margin",
        "accruals_to_assets",
        "sales_yield",
        "earnings_yield",
        "fcf_yield",
    ]
    coverage = research.groupby("date")[coverage_columns].apply(lambda frame: frame.notna().mean()).reset_index()

    summary.to_csv(OUT / "performance_summary.csv", index=False)
    robustness.to_csv(OUT / "robustness_remove_best_months.csv", index=False)
    pd.DataFrame(ablations).to_csv(OUT / "factor_ablation_diagnostic.csv", index=False)
    combined.to_csv(OUT / "monthly_returns.csv", index=False)
    holdings.to_csv(OUT / "monthly_holdings.csv", index=False)
    rank_ic.to_csv(OUT / "rank_ic.csv", index=False)
    coverage.to_csv(OUT / "fundamental_coverage_by_month.csv", index=False)
    scored.to_parquet(OUT / "scored_universe.parquet", index=False)

    frozen = {
        "model": "v6_equal_weight_momentum_quality_value",
        "frozen_on": "2026-10-15",
        "first_signal": config.first_prediction,
        "last_signal": str(scored["date"].max().date()),
        "top_n": config.top_n,
        "primary_cost_bps": config.cost_bps,
        "stress_cost_bps": 25,
        "fundamental_max_age_days": 460,
        "removed_best_months": [str(date.date()) for date in removed_dates],
        "selection_policy": "No retrospective variant selection; blend was frozen before results.",
        "fundamental_columns": FUNDAMENTAL_VALUE_COLUMNS,
    }
    (OUT / "frozen_config.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")

    curves = (1 + combined.set_index("date")[[
        "net_return", "equal_weight_return", "spy_return"
    ]]).cumprod()
    curves.columns = ["V6 blend", "PIT equal weight", "SPY"]
    curves.plot(figsize=(11, 6), title="V6 point-in-time factor model")
    plt.grid(alpha=0.25)
    plt.ylabel("Growth of $1")
    plt.tight_layout()
    plt.savefig(OUT / "equity_curve.png", dpi=160)
    plt.close()

    print("Frozen V6 performance:\n", summary.to_string(index=False))
    print("\nDiagnostic factor ablations:\n", pd.DataFrame(ablations).to_string(index=False))
    print("\nRecent fundamental coverage:\n", coverage.tail(3).to_string(index=False))
    print("\nRank IC summary:\n", rank_ic["rank_ic"].describe().to_string())


if __name__ == "__main__":
    main()
