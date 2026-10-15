"""Validation-selected market-regime overlay for the original ML ranking.

This changes portfolio exposure, not the stock-selection model. All regime inputs
are observable at the month-end signal; trades still occur the next session.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from models.walk_forward import metrics

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/ai_walk_forward"
OUT = ROOT / "reports/ai_v3_risk_control"


def market_regime() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/pit/prices.parquet", columns=["date", "ticker", "adj_close"])
    s = p.loc[p["ticker"].eq("SPY")].sort_values("date").copy()
    s["ma200"] = s["adj_close"].rolling(200).mean()
    s["risk_on"] = s["adj_close"] >= s["ma200"]
    month_end = s.groupby(s["date"].dt.to_period("M")).tail(1)
    return month_end[["date", "risk_on"]]


def apply_overlay(base: pd.DataFrame, defensive_exposure: float, cost_bps: float = 10) -> pd.DataFrame:
    x = base.merge(market_regime(), on="date", how="left").copy()
    x["exposure"] = x["risk_on"].map({True: 1.0, False: defensive_exposure}).fillna(defensive_exposure)
    x["previous_exposure"] = x["exposure"].shift().fillna(0)
    # Conservative cost proxy: underlying stock turnover plus changing the equity allocation.
    traded_fraction = x["turnover"] * x[["exposure", "previous_exposure"]].min(axis=1) + (x["exposure"] - x["previous_exposure"]).abs()
    x["overlay_return"] = x["gross_return"] * x["exposure"] - traded_fraction * cost_bps / 10_000
    return x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE / "monthly_returns.csv", parse_dates=["date", "execution_date"])
    candidates = []
    for exposure in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = apply_overlay(base, exposure)
        v = x.loc[x["date"].between("2018-01-01", "2022-12-31")]
        candidates.append({"defensive_exposure": exposure, **metrics(v["overlay_return"])})
    grid = pd.DataFrame(candidates)
    selected = float(grid.sort_values(["sharpe_0rf", "max_drawdown"], ascending=False).iloc[0]["defensive_exposure"])
    result = apply_overlay(base, selected)
    summary = []
    for split, a, b in (("validation", "2018-01-01", "2022-12-31"), ("test", "2023-01-01", "2099-01-01"),
                        ("full_oos", "2018-01-01", "2099-01-01")):
        z = result.loc[result["date"].between(a, b)]
        for name, col in (("ml_v3_risk_control", "overlay_return"), ("point_in_time_equal_weight", "equal_weight_return"), ("spy", "spy_return")):
            summary.append({"split": split, "strategy": name, **metrics(z[col])})
    summary = pd.DataFrame(summary)
    grid.to_csv(OUT / "validation_exposure_selection.csv", index=False)
    result.to_csv(OUT / "monthly_returns.csv", index=False)
    summary.to_csv(OUT / "performance_summary.csv", index=False)
    curves = (1 + result.set_index("date")[["overlay_return", "equal_weight_return", "spy_return"]]).cumprod()
    curves.columns = ["ML v3 risk-controlled", "PIT equal weight", "SPY"]
    curves.plot(figsize=(11, 6), title=f"ML risk overlay; validation-selected defensive exposure={selected:.0%}")
    plt.grid(alpha=.25); plt.ylabel("Growth of $1"); plt.tight_layout(); plt.savefig(OUT / "equity_curve.png", dpi=160); plt.close()
    print("Validation-only exposure selection:\n", grid.to_string(index=False))
    print(f"\nFrozen defensive exposure: {selected:.0%}\n\nResults:\n", summary.to_string(index=False))


if __name__ == "__main__": main()
