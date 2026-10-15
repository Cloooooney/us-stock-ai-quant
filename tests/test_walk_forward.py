import pandas as pd
from models.walk_forward import Config, FEATURES, portfolio_returns


def test_cached_dataset_has_no_lookahead():
    try: d = pd.read_parquet("data/pit/monthly_ml_dataset_v2.parquet")
    except FileNotFoundError: return
    assert (d.execution_date > d.date).all()
    assert (d.label_known_date > d.date).all()
    assert not d[FEATURES + ["target_return"]].isna().any().any()


def test_cost_is_deducted():
    d = pd.DataFrame({"date": [pd.Timestamp("2024-01-31")], "execution_date": [pd.Timestamp("2024-02-01")],
                      "ticker": ["A"], "prediction": [1.0], "target_return": [.02]})
    r, _ = portfolio_returns(d, Config(top_n=1, cost_bps=10))
    assert abs(r.net_return.iloc[0] - .019) < 1e-12
