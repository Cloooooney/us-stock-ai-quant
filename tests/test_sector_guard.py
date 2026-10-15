import pandas as pd
from models.sector_guard import select_with_sector_cap


def test_sector_cap_is_enforced():
    d = pd.DataFrame({"ticker": list("ABCDEFGH"), "prediction": range(8, 0, -1),
                      "sic_major": ["10"] * 6 + ["20"] * 2})
    out = select_with_sector_cap(d, top_n=6, max_per_sector=4)
    assert len(out) == 6
    assert out.groupby("sic_major").size().max() <= 4


def test_broad_division_cap_is_enforced():
    d = pd.DataFrame({"ticker": list("ABCDEFGHIJ"), "prediction": range(10, 0, -1),
                      "sic_major": ["60"] * 3 + ["62"] * 3 + ["64"] * 2 + ["20"] * 2})
    out = select_with_sector_cap(d, top_n=7, max_per_sector=4, max_per_division=4)
    assert (out["sic_division"] == "finance_real_estate").sum() <= 4
