import pandas as pd
import pytest

from paper_trading.simulator import simulate_equal_weight_portfolio


def sample_holdings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": pd.to_datetime(["2026-09-30", "2026-09-30"]),
        }
    )


def sample_prices() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2026-10-01", "open": 20.0, "close": 20.0, "adj_close": 10.0},
            {"ticker": "AAA", "date": "2026-10-02", "open": 11.0, "close": 11.0, "adj_close": 11.0},
            {"ticker": "BBB", "date": "2026-10-01", "open": 20.0, "close": 20.0, "adj_close": 20.0},
            {"ticker": "BBB", "date": "2026-10-02", "open": 19.0, "close": 19.0, "adj_close": 19.0},
        ]
    ).assign(date=lambda frame: pd.to_datetime(frame["date"]))


def test_simulation_uses_adjusted_open_whole_shares_and_two_sided_costs():
    positions, summary = simulate_equal_weight_portfolio(
        sample_holdings(), sample_prices(), initial_cash=1_000.0, cost_bps=100
    )

    by_ticker = positions.set_index("ticker")
    assert by_ticker.loc["AAA", "fill_price"] == pytest.approx(10.0)
    assert by_ticker.loc["AAA", "shares"] == 49
    assert by_ticker.loc["BBB", "shares"] == 24
    assert summary["signal_date"] == "2026-09-30"
    assert summary["execution_date"] == "2026-10-01"
    assert summary["valuation_date"] == "2026-10-02"
    assert summary["entry_cost"] == pytest.approx(9.7)
    assert summary["cash"] == pytest.approx(20.3)
    assert summary["market_value"] == pytest.approx(995.0)
    assert summary["account_equity"] == pytest.approx(1_015.3)
    assert summary["estimated_exit_cost"] == pytest.approx(9.95)
    assert summary["net_liquidation_value"] == pytest.approx(1_005.35)
    assert summary["net_return_if_liquidated"] == pytest.approx(0.00535)


def test_simulation_rejects_duplicate_holdings():
    holdings = pd.concat([sample_holdings(), sample_holdings().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        simulate_equal_weight_portfolio(holdings, sample_prices(), 1_000.0, 10)


def test_simulation_rejects_missing_common_valuation_price():
    prices = sample_prices().loc[
        ~((sample_prices()["ticker"] == "BBB") & (sample_prices()["date"] == pd.Timestamp("2026-10-02")))
    ]
    with pytest.raises(ValueError, match="valuation"):
        simulate_equal_weight_portfolio(sample_holdings(), prices, 1_000.0, 10)


@pytest.mark.parametrize(
    ("initial_cash", "cost_bps", "message"),
    [(0.0, 10, "initial_cash"), (1_000.0, -1, "cost_bps")],
)
def test_simulation_rejects_invalid_account_inputs(initial_cash, cost_bps, message):
    with pytest.raises(ValueError, match=message):
        simulate_equal_weight_portfolio(sample_holdings(), sample_prices(), initial_cash, cost_bps)
