from pathlib import Path
import pandas as pd
from models.walk_forward import FEATURES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/signal_diagnostics"


def monthly_ic(frame: pd.DataFrame, signal: str) -> pd.Series:
    return frame.groupby("date").apply(lambda x: x[signal].corr(x["target_return"], method="spearman"), include_groups=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ds = pd.read_parquet(ROOT / "data/pit/monthly_ml_dataset_v2.parquet")
    pred1 = pd.read_parquet(ROOT / "reports/ai_walk_forward/all_predictions.parquet")
    pred2 = pd.read_parquet(ROOT / "reports/ai_v2_cross_sectional/all_predictions.parquet")
    rows = []
    for label, frame, signals in (("raw_features", ds, FEATURES), ("ml_v1", pred1, ["prediction"]), ("ml_v2", pred2, ["prediction"])):
        for signal in signals:
            ic = monthly_ic(frame, signal)
            for split, a, b in (("validation", "2018-01-01", "2022-12-31"), ("test", "2023-01-01", "2099-01-01")):
                z = ic.loc[(ic.index >= a) & (ic.index <= b)].dropna()
                rows.append({"source": label, "signal": signal, "split": split, "mean_rank_ic": z.mean(),
                             "ic_std": z.std(), "positive_month_ratio": (z > 0).mean(), "months": len(z)})
    report = pd.DataFrame(rows)
    report.to_csv(OUT / "monthly_rank_ic.csv", index=False)
    print(report.to_string(index=False))


if __name__ == "__main__": main()
