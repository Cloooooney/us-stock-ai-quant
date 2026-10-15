from pathlib import Path
import numpy as np
import pandas as pd
from models.walk_forward import Config, metrics, portfolio_returns

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/ai_walk_forward"


def main() -> None:
    pred = pd.read_parquet(REPORT / "all_predictions.parquet")
    rows = []
    for top_n in (10, 20, 30, 50):
        for cost in (5, 10, 25, 50):
            ret, _ = portfolio_returns(pred, Config(top_n=top_n, cost_bps=cost))
            test = ret.loc[ret["date"] >= "2023-01-01", "net_return"]
            rows.append({"top_n": top_n, "cost_bps": cost, **metrics(test)})
    pd.DataFrame(rows).to_csv(REPORT / "stress_cost_and_portfolio_size.csv", index=False)

    # Random-selection placebo: same monthly portfolio size, 250 complete paths.
    rng = np.random.default_rng(42); random_rows = []
    for trial in range(250):
        rr = []
        for _, g in pred.loc[pred["date"] >= "2023-01-01"].groupby("date", sort=True):
            rr.append(g.sample(n=min(20, len(g)), random_state=int(rng.integers(2**31)))["target_return"].mean() - .001)
        random_rows.append({"trial": trial, **metrics(pd.Series(rr))})
    placebo = pd.DataFrame(random_rows)
    placebo.to_csv(REPORT / "random_placebo_250_paths.csv", index=False)
    print(pd.read_csv(REPORT / "stress_cost_and_portfolio_size.csv").to_string(index=False))
    print("\nRandom placebo test annual-return percentiles:", placebo["annual_return"].quantile([.05, .5, .95]).to_dict())


if __name__ == "__main__": main()
