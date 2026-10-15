from pathlib import Path
import json
from models.fundamental_ridge import FUNDAMENTALS
from models.v5 import build_v5_selection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v5_sector_guard"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    selected, _ = build_v5_selection(ROOT)
    signal_date = selected["date"].max()
    cols = ["date", "execution_date", "portfolio_rank", "ticker", "company_name", "sic", "sic_division", "sic_description",
            "prediction", *FUNDAMENTALS, "filed", "available_date", "fiscal_end"]
    selected[cols].to_csv(OUT / "latest_preview_not_forward_result.csv", index=False)
    manifest = {"version": "v5", "created_after_signal": True, "preview_is_not_forward_performance": True,
                "industry_rule": "two-digit SIC max 4; SIC division max 6 of 20",
                "honest_forward_start": "first month-end signal after 2026-10-05",
                "orders_enabled": False, "signal_date": str(signal_date.date())}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(selected[cols].to_string(index=False))
    print("\nSIC counts:\n", selected.groupby(["sic_major", "sic_description"]).size().to_string())
    print("\nDivision counts:\n", selected.groupby("sic_division").size().to_string())


if __name__ == "__main__": main()
