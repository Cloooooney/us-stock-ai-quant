import numpy as np
import pandas as pd

from models.v6_factor import run_v6_variant, score_factors, select_v6_holdings
from models.walk_forward import Config
from paper_trading.ledger import read_events
from paper_trading.run_v6_forward import FEATURES, V6
from paper_trading.run_v5_forward import TOP_N, track, write_reports

from test_run_v5_forward import HOLDINGS, UNIVERSE, make_prices


def synthetic_universe(dates, n=30, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for date in dates:
        for i in range(n):
            # Rounded momentum creates ties so the tie-break is exercised.
            rows.append({"date": pd.Timestamp(date), "ticker": f"T{i:02d}",
                         "execution_date": pd.Timestamp(date) + pd.Timedelta(days=1),
                         "mom_126": round(float(rng.normal()), 1), "mom_252": round(float(rng.normal()), 1),
                         "roa": float(rng.normal()) if i % 3 else np.nan,
                         "target_return": float(rng.normal(0, 0.05))})
    return pd.DataFrame(rows)


def test_forward_selection_matches_backtest_selection():
    dates = ["2026-07-31", "2026-08-31"]
    data = synthetic_universe(dates)
    _, _, holdings = run_v6_variant(data, Config(first_prediction="2026-01-01", top_n=5), variant="blend")
    scored = score_factors(data)
    for date in dates:
        backtest = holdings.loc[holdings["date"].eq(pd.Timestamp(date))].sort_values("rank")["ticker"].tolist()
        forward = select_v6_holdings(scored, pd.Timestamp(date), top_n=5)["ticker"].tolist()
        assert forward == backtest


def v6_selection(signal_date):
    frame = pd.DataFrame({"date": pd.Timestamp(signal_date), "ticker": HOLDINGS,
                          "portfolio_rank": range(1, TOP_N + 1),
                          "prediction": [0.9 - i / 100 for i in range(TOP_N)],
                          "accession": [f"0000-26-{i:06d}" for i in range(TOP_N)], "form": "10-Q"})
    for feature in FEATURES:
        frame[feature] = 0.5
    frame.loc[0, "market_cap"] = np.nan
    return frame


def test_v6_uses_its_own_freeze_date_model_name_and_fields(tmp_path):
    ledger = tmp_path / "v6.jsonl"
    early = track(ledger, v6_selection("2026-09-30"), UNIVERSE, make_prices("2026-10-30"), FEATURES, spec=V6)
    assert early["signals"] == 0 and "2026-10-15 freeze" in early["notes"][0]

    prices = make_prices("2026-12-02")
    track(ledger, v6_selection("2026-10-30"), UNIVERSE, prices, FEATURES, spec=V6)
    summary = track(ledger, v6_selection("2026-11-30"), UNIVERSE, prices, FEATURES, spec=V6)
    events = read_events(ledger)
    assert {e["model"] for e in events} == {"v6_equal_weight_momentum_quality_value"}
    signal = events[0]
    assert signal["holdings"][0]["accession"] == "0000-26-000000"
    assert signal["holdings"][0]["form"] == "10-Q"
    assert signal["holdings"][0]["market_cap"] is None
    assert "sic" not in signal["holdings"][0]
    [period] = [e for e in events if e["event_type"] == "PERIOD"]
    assert "v6" in period and "v5" not in period
    assert "v6_net" in summary["cumulative"]

    write_reports(ledger, summary, tmp_path / "reports", tmp_path / "signals", spec=V6)
    assert (tmp_path / "signals/v6_2026-10-30.json").exists()
    assert "v6_net_return" in pd.read_csv(tmp_path / "reports/period_returns.csv").columns
