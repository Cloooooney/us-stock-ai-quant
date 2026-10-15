from pathlib import Path
import json
import matplotlib.pyplot as plt
import pandas as pd

from models.fundamental_ridge import FUNDAMENTALS, merge_fundamentals, run_variant
from models.walk_forward import Config, FEATURES, load_source, metrics, spy_monthly_returns

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ai_v4_fundamentals"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = Config(top_n=20, cost_bps=10)
    ds = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    fund = pd.read_parquet(ROOT / "data/sec/annual_fundamentals.parquet")
    merged = merge_fundamentals(ds, fund)
    merged.to_parquet(ROOT / "data/sec/monthly_price_fundamentals.parquet", index=False)

    variants = {"price_ridge": FEATURES, "fundamental_ridge": FUNDAMENTALS,
                "combined_ridge": [*FEATURES, *FUNDAMENTALS]}
    all_returns, predictions, holdings = {}, {}, {}
    validation = []
    for name, features in variants.items():
        predictions[name], all_returns[name], holdings[name] = run_variant(merged, features, cfg)
        v = all_returns[name].loc[all_returns[name]["date"].between("2018-01-01", "2022-12-31")]
        validation.append({"variant": name, **metrics(v["net_return"]), "avg_turnover": v["turnover"].mean()})
    validation = pd.DataFrame(validation)
    selected = validation.sort_values(["sharpe_0rf", "max_drawdown"], ascending=False).iloc[0]["variant"]
    diagnostics = []
    for variant, variant_returns in all_returns.items():
        for split, a, b in (("validation", "2018-01-01", "2022-12-31"),
                            ("test_diagnostic_only", "2023-01-01", "2099-01-01")):
            x = variant_returns.loc[variant_returns["date"].between(a, b)]
            diagnostics.append({"variant": variant, "split": split, **metrics(x["net_return"]),
                                "avg_turnover": x["turnover"].mean()})
    ret, pred, held = all_returns[selected], predictions[selected], holdings[selected]
    ew = pred.groupby("date", as_index=False)["target_return"].mean().rename(columns={"target_return": "equal_weight_return"})
    prices, _, _ = load_source(ROOT); spy = spy_monthly_returns(prices, pd.Series(sorted(ds["date"].unique())))
    ret = ret.merge(ew, on="date", how="left").merge(spy, on="date", how="left")

    summary = []
    for split, a, b in (("validation", "2018-01-01", "2022-12-31"), ("test", "2023-01-01", "2099-01-01"),
                        ("full_oos", "2018-01-01", "2099-01-01")):
        x = ret.loc[ret["date"].between(a, b)]
        for name, col in ((selected, "net_return"), ("point_in_time_equal_weight", "equal_weight_return"), ("spy", "spy_return")):
            summary.append({"split": split, "strategy": name, **metrics(x[col]),
                            "avg_turnover": x["turnover"].mean() if name == selected else 0})
    summary = pd.DataFrame(summary)
    validation.to_csv(OUT / "validation_model_selection.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(OUT / "all_variants_diagnostic_not_for_selection.csv", index=False)
    summary.to_csv(OUT / "performance_summary.csv", index=False)
    ret.to_csv(OUT / "monthly_returns.csv", index=False); held.to_csv(OUT / "monthly_holdings.csv", index=False)
    pred.to_parquet(OUT / "selected_predictions.parquet", index=False)
    coverage = merged.groupby("date")[FUNDAMENTALS].apply(lambda x: x.notna().mean()).reset_index()
    coverage.to_csv(OUT / "fundamental_coverage_by_month.csv", index=False)
    (OUT / "selection.json").write_text(json.dumps({"selected_on_validation": selected, "ridge_alpha": 100,
                                                     "candidate_count": len(variants)}, indent=2), encoding="utf-8")
    curves = (1 + ret.set_index("date")[["net_return", "equal_weight_return", "spy_return"]]).cumprod()
    curves.columns = [selected, "PIT equal weight", "SPY"]
    curves.plot(figsize=(11, 6), title="Fundamental model: frozen validation selection")
    plt.grid(alpha=.25); plt.ylabel("Growth of $1"); plt.tight_layout(); plt.savefig(OUT / "equity_curve.png", dpi=160); plt.close()
    print("Validation-only model selection:\n", validation.to_string(index=False))
    print("\nAll variants (test rows are diagnostic only, never used for selection):\n",
          pd.DataFrame(diagnostics).to_string(index=False))
    print(f"\nFrozen model: {selected}\n\nResults:\n", summary.to_string(index=False))
    print("\nRecent fundamental coverage:\n", coverage.tail(3).to_string(index=False))


if __name__ == "__main__": main()
