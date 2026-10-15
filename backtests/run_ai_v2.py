from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from models.cross_sectional import buffered_portfolio, fit_predict_relative, select_buffer_on_validation
from models.walk_forward import Config, load_source, metrics, spy_monthly_returns

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ai_v2_cross_sectional"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = Config(top_n=20, cost_bps=10)
    ds = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    pred = fit_predict_relative(ds, cfg)
    selected_buffer, validation_grid = select_buffer_on_validation(pred, cfg)
    ret, holdings = buffered_portfolio(pred, cfg, selected_buffer)
    ew = pred.groupby("date", as_index=False)["target_return"].mean().rename(columns={"target_return": "equal_weight_return"})
    prices, _, _ = load_source(ROOT)
    spy = spy_monthly_returns(prices, pd.Series(sorted(ds["date"].unique())))
    ret = ret.merge(ew, on="date", how="left").merge(spy, on="date", how="left")

    summary = []
    for split, a, b in (("validation", "2018-01-01", "2022-12-31"),
                        ("test", "2023-01-01", "2099-01-01"),
                        ("full_oos", "2018-01-01", "2099-01-01")):
        x = ret.loc[ret["date"].between(a, b)]
        for name, col in (("ml_v2", "net_return"), ("point_in_time_equal_weight", "equal_weight_return"), ("spy", "spy_return")):
            summary.append({"split": split, "strategy": name, **metrics(x[col]),
                            "avg_turnover": x["turnover"].mean() if name == "ml_v2" else 0})
    summary = pd.DataFrame(summary)
    summary.to_csv(OUT / "performance_summary.csv", index=False)
    validation_grid.to_csv(OUT / "validation_buffer_selection.csv", index=False)
    ret.to_csv(OUT / "monthly_returns.csv", index=False)
    holdings.to_csv(OUT / "monthly_holdings.csv", index=False)
    pred.to_parquet(OUT / "all_predictions.parquet", index=False)
    curves = (1 + ret.set_index("date")[["net_return", "equal_weight_return", "spy_return"]]).cumprod()
    curves.columns = ["ML v2 net", "PIT equal weight", "SPY"]
    curves.plot(figsize=(11, 6), title=f"ML v2 out-of-sample; validation-selected buffer={selected_buffer:g}x")
    plt.grid(alpha=.25); plt.ylabel("Growth of $1"); plt.tight_layout(); plt.savefig(OUT / "equity_curve.png", dpi=160); plt.close()
    print("Validation-only buffer selection:\n", validation_grid.to_string(index=False))
    print(f"\nFrozen buffer: {selected_buffer:g}x\n\nResults:\n", summary.to_string(index=False))


if __name__ == "__main__": main()
