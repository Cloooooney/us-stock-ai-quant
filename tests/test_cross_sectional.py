import pandas as pd
from models.cross_sectional import prepare_cross_section


def test_relative_target_has_zero_cross_sectional_mean():
    d = pd.DataFrame({"date": [pd.Timestamp("2020-01-31")] * 2,
                      "target_return": [.1, .2],
                      **{x: [1.0, 2.0] for x in ["mom_21", "mom_63", "mom_126", "mom_252", "vol_21", "vol_63", "drawdown_252", "trend_200", "volume_change_63", "reversal_5"]}})
    out = prepare_cross_section(d)
    assert abs(out["target_relative"].mean()) < 1e-12
    assert out["rank_mom_21"].between(0, 1).all()
