from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from models.walk_forward import Config, build_monthly_dataset, fit_predict, load_source, metrics, portfolio_returns, spy_monthly_returns

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "ai_walk_forward"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); cfg = Config()
    cache = ROOT / "data/pit/monthly_ml_dataset_v2.parquet"
    if cache.exists(): ds = pd.read_parquet(cache)
    else:
        prices, intervals, _ = load_source(ROOT)
        ds = build_monthly_dataset(prices, intervals); ds.to_parquet(cache, index=False)
    pred = fit_predict(ds, cfg)
    returns, holdings = portfolio_returns(pred, cfg)
    ew = pred.groupby("date", as_index=False)["target_return"].mean().rename(columns={"target_return": "equal_weight_return"})
    prices, _, _ = load_source(ROOT)
    spy = spy_monthly_returns(prices, pd.Series(sorted(ds["date"].unique())))
    returns = returns.merge(ew, on="date", how="left").merge(spy, on="date", how="left")
    returns.to_csv(OUT / "monthly_returns.csv", index=False)
    holdings.to_csv(OUT / "monthly_holdings.csv", index=False)
    pred.to_parquet(OUT / "all_predictions.parquet", index=False)
    splits = {"validation": ("2018-01-01", "2022-12-31"), "test": ("2023-01-01", "2099-01-01"),
              "full_oos": ("2018-01-01", "2099-01-01")}
    summary = []
    for name, (a, b) in splits.items():
        x = returns.loc[returns["date"].between(a, b)]
        for strategy, col in (("ml", "net_return"), ("point_in_time_equal_weight", "equal_weight_return"), ("spy", "spy_return")):
            summary.append({"split": name, "strategy": strategy, **metrics(x[col]),
                            "avg_turnover": x["turnover"].mean() if strategy == "ml" else 0.0})
    pd.DataFrame(summary).to_csv(OUT / "performance_summary.csv", index=False)
    curves = (1 + returns.set_index("date")[["net_return", "equal_weight_return", "spy_return"]]).cumprod()
    curves.columns = ["ML net", "PIT equal weight", "SPY"]
    curves.plot(figsize=(11, 6), title="Point-in-time S&P 500 ML strategy (out-of-sample)")
    plt.ylabel("Growth of $1"); plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(OUT / "equity_curve.png", dpi=160); plt.close()
    (OUT / "run_config.json").write_text(json.dumps(cfg.__dict__, indent=2), encoding="utf-8")
    print(pd.DataFrame(summary).to_string(index=False))
    print("\nLatest holdings:\n", holdings.loc[holdings.date.eq(holdings.date.max())].sort_values("rank").to_string(index=False))


if __name__ == "__main__": main()
