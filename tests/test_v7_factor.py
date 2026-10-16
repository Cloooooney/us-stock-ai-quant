import numpy as np
import pandas as pd
import pytest

from backtests.run_v7_factor import decide
from models.v6_factor import run_v6_variant, score_factors
from models.v7_factor import (SCORES, add_improvement_features, attach_v7_features, run_v7,
                              select_unique_issuers)
from models.walk_forward import Config
from research.factor_attribution import FACTORS

from test_run_v6_forward import synthetic_universe


def snapshot(fiscal_end, available, roa, accession, margin=0.1, fcf=0.05, ticker="AAA", cik=1):
    return {"ticker": ticker, "cik": cik, "accession": accession, "fiscal_end": pd.Timestamp(fiscal_end),
            "available_date": pd.Timestamp(available), "filed": pd.Timestamp(available) - pd.Timedelta(days=1),
            "roa": roa, "net_margin": margin, "free_cash_flow_margin": fcf}


def test_improvement_uses_only_prior_year_snapshots_already_available():
    rows = pd.DataFrame([
        snapshot("2024-03-31", "2024-05-01", 0.05, "q1-24"),
        snapshot("2024-06-30", "2024-08-01", 0.06, "q2-24"),
        snapshot("2025-03-31", "2025-05-01", 0.09, "q1-25", margin=0.15),
        # An amendment of Q1 2024 filed after Q1 2025 must not be used for Q1 2025.
        snapshot("2024-03-31", "2025-06-01", 0.01, "q1-24-amended"),
        snapshot("2025-06-30", "2025-08-01", 0.10, "q2-25"),
    ])
    out = add_improvement_features(rows).set_index("accession")
    assert out.loc["q1-25", "d_roa"] == pytest.approx(0.04)          # 0.09 - 0.05, not the later amendment
    assert out.loc["q1-25", "d_net_margin"] == pytest.approx(0.05)
    assert out.loc["q2-25", "d_roa"] == pytest.approx(0.04)          # 0.10 - 0.06
    assert np.isnan(out.loc["q1-24", "d_roa"])                        # no prior year
    assert np.isnan(out.loc["q2-24", "d_roa"])                        # 91 days is not a year


def test_v7_features_attach_by_snapshot_and_expire_with_it():
    fundamentals = pd.DataFrame([snapshot("2024-03-31", "2024-05-01", 0.05, "a"),
                                 snapshot("2025-03-31", "2025-05-01", 0.08, "b")])
    fundamentals["form"] = "10-Q"
    dataset = pd.DataFrame({"date": pd.to_datetime(["2025-05-30", "2026-12-31"]), "ticker": "AAA"})
    prices = pd.DataFrame({"date": dataset["date"], "ticker": "AAA", "close": 10.0})
    out = attach_v7_features(dataset, fundamentals, prices).set_index("date")
    assert out.loc["2025-05-30", "d_roa"] == pytest.approx(0.03)
    assert out.loc["2025-05-30", "cik"] == 1
    assert np.isnan(out.loc["2026-12-31", "d_roa"])                   # filing older than 460 days


def test_one_position_per_issuer():
    group = pd.DataFrame({"ticker": ["GOOGL", "GOOG", "AAA", "BBB", "CCC"], "cik": [1652044, 1652044, 1, np.nan, 3],
                          "score": [0.9, 0.9, 0.8, 0.8, 0.1]})
    selected = select_unique_issuers(group, "score", top_n=3)
    assert selected["ticker"].tolist() == ["GOOG", "AAA", "BBB"]      # tie broken by ticker; GOOGL skipped
    assert selected["portfolio_rank"].tolist() == [1, 2, 3]


def test_without_duplicates_v7_fallback_matches_v6_and_dedupe_is_logged():
    dates = ["2026-06-30", "2026-07-31", "2026-08-31"]
    data = synthetic_universe(dates)
    data["cik"] = data["ticker"].str[1:].astype(int)
    cfg = Config(first_prediction="2026-01-01", top_n=5)
    scored = score_factors(data)
    _, v6_returns, v6_holdings = run_v6_variant(data, cfg, variant="blend")
    v7_returns, v7_holdings, changed = run_v7(scored, cfg, SCORES["fallback"])
    assert v7_holdings.sort_values(["date", "ticker"])["ticker"].tolist() == \
        v6_holdings.sort_values(["date", "ticker"])["ticker"].tolist()
    assert v7_returns["net_return"].tolist() == pytest.approx(v6_returns["net_return"].tolist())
    assert changed.empty

    top = scored.loc[scored["date"].eq(pd.Timestamp(dates[0]))].nlargest(2, "v6_score")["ticker"].tolist()
    data.loc[data["ticker"].eq(top[1]), "cik"] = int(top[0][1:])      # make the top two one issuer
    _, holdings, changed = run_v7(score_factors(data), cfg, SCORES["fallback"])
    first = holdings.loc[holdings["date"].eq(pd.Timestamp(dates[0])), "ticker"]
    assert top[0] in set(first) and top[1] not in set(first) and len(first) == 5
    assert changed.iloc[0]["removed"] == top[1]


def development_panel(predictive: bool, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-31", "2022-12-31", freq="ME")
    rows = []
    for d in dates:
        score = rng.uniform(size=100)
        noise = rng.normal(0, 0.05, 100)
        rows.append(pd.DataFrame({"date": d, "ticker": [f"T{i}" for i in range(100)],
                                  "execution_date": d + pd.Timedelta(days=1), "improvement_score": score,
                                  "target_return": (0.03 * score if predictive else 0) + noise}))
    months = pd.period_range("2017-01", "2023-06", freq="M")
    factors = pd.DataFrame(rng.normal(0, 0.03, (len(months), len(FACTORS))), index=months, columns=FACTORS)
    factors["rf"] = 0.001
    return pd.concat(rows, ignore_index=True), factors


def test_decision_rule_adopts_only_a_sleeve_that_passes_both_tests():
    scored, factors = development_panel(predictive=True)
    adopted = decide(scored, factors)
    assert adopted["improvement_sleeve_adopted"] is True and adopted["score"] == SCORES["candidate"]
    assert adopted["rank_ic"]["months"] == 60

    scored, factors = development_panel(predictive=False, seed=1)
    rejected = decide(scored, factors)
    assert rejected["improvement_sleeve_adopted"] is False and rejected["score"] == SCORES["fallback"]


def test_decision_ignores_months_after_development():
    scored, factors = development_panel(predictive=False, seed=1)
    late = scored.copy()
    late["date"] = late["date"] + pd.DateOffset(years=5)              # 2023-2027: must not count
    late["target_return"] = 0.5 * late["improvement_score"]
    decision = decide(pd.concat([scored, late], ignore_index=True), factors)
    assert decision["rank_ic"]["months"] == 60 and decision["improvement_sleeve_adopted"] is False


def test_v7_forward_spec_and_inactive_until_frozen(tmp_path, monkeypatch, capsys):
    import paper_trading.run_v7_forward as forward
    from paper_trading.run_v5_forward import track
    from test_run_v5_forward import UNIVERSE, make_prices
    from test_run_v6_forward import v6_selection

    monkeypatch.setattr(forward, "FROZEN", tmp_path / "missing.json")
    forward.main()
    assert "not frozen yet" in capsys.readouterr().out

    spec = forward.spec({"model": "v7_unique_issuer", "frozen_on": "2026-10-20"})
    assert spec.key == "v7" and spec.frozen_at == pd.Timestamp("2026-10-20")
    spec = spec.__class__(**{**spec.__dict__, "ledger": tmp_path / "v7.jsonl"})
    selection = v6_selection("2026-10-30").assign(cik=1)
    for feature in forward.FEATURES:
        selection[feature] = 0.5
    result = track(spec.ledger, selection, UNIVERSE, make_prices("2026-11-03"), forward.FEATURES, spec=spec)
    assert result["signals"] == 1 and result["entries"] == 1
