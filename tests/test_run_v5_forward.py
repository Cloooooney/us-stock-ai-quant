import pandas as pd
import pytest

from paper_trading.ledger import read_events, validate
from paper_trading.run_v5_forward import COST_BPS, ETF_BENCHMARKS, TOP_N, track, write_reports

FEATURES = ["roa"]
HOLDINGS = [f"H{i:02d}" for i in range(TOP_N)]
OTHERS = ["X01", "X02", "X03"]
UNIVERSE = sorted(HOLDINGS + OTHERS)


def growth(ticker: str) -> float:
    if ticker[1:].isdigit():
        return 0.001 * (int(ticker[1:]) % 7 - 3)
    return 0.0005 if ticker == "SPY" else 0.0001 * (len(ticker) + ord(ticker[0]) % 5)


def make_prices(end: str, tickers=None, skip=()) -> pd.DataFrame:
    """Deterministic business-day prices; adjusted open equals the raw open."""
    tickers = tickers or [*UNIVERSE, "SPY"]
    days = pd.bdate_range("2026-10-01", end)
    rows = []
    for ticker in tickers:
        for n, day in enumerate(days):
            if (ticker, str(day.date())) in skip:
                continue
            price = 50.0 * (1 + growth(ticker)) ** n
            rows.append({"ticker": ticker, "date": day, "open": price, "close": price, "adj_close": price})
    return pd.DataFrame(rows)


def price_on(ticker: str, date: str) -> float:
    n = list(pd.bdate_range("2026-10-01", date)).index(pd.Timestamp(date))
    return 50.0 * (1 + growth(ticker)) ** n


def selection(signal_date: str, tickers=HOLDINGS) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.Timestamp(signal_date), "ticker": tickers,
                         "portfolio_rank": range(1, len(tickers) + 1),
                         "prediction": [1 - i / 100 for i in range(len(tickers))],
                         "sic": "3571", "sic_division": "manufacturing", "roa": 0.1})


def events(path, kind):
    return [e for e in read_events(path) if e["event_type"] == kind]


def test_pre_freeze_signal_records_nothing(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    result = track(ledger, selection("2026-09-30"), UNIVERSE, make_prices("2026-10-30"), FEATURES)
    assert not ledger.exists()
    assert result["signals"] == 0 and "not after" in result["notes"][0]


def test_entry_uses_ledgered_signal_not_a_fresh_selection(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    first = track(ledger, selection("2026-10-30"), UNIVERSE, make_prices("2026-10-30"), FEATURES)
    assert first["signals"] == 1 and first["entries"] == 0
    assert first["pending_entries"] == ["2026-10-30"]

    # A later run recomputes different holdings for the same month (e.g. after an SEC refresh).
    drifted = selection("2026-10-30", HOLDINGS[:-1] + ["X01"])
    second = track(ledger, drifted, UNIVERSE, make_prices("2026-11-03"), FEATURES)
    [entry] = events(ledger, "ENTRY")
    assert [f["ticker"] for f in entry["fills"]] == HOLDINGS
    assert entry["execution_date"] == "2026-11-02"
    assert any("ledgered SIGNAL is kept" in note for note in second["notes"])
    assert len(events(ledger, "SIGNAL")) == 1


def test_halted_holding_is_held_as_cash_and_earns_zero(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02", skip={("H03", "2026-11-02")})
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)
    track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES)
    [entry, _] = events(ledger, "ENTRY")
    assert entry["unfilled_held_as_cash"] == ["H03"]
    assert len(entry["fills"]) == TOP_N - 1
    [period] = events(ledger, "PERIOD")
    halted = next(h for h in period["holdings"] if h["ticker"] == "H03")
    assert halted == {"ticker": "H03", "return": 0.0, "status": "unfilled_cash"}
    assert period["v5"]["unfilled_cash"] == 1


def test_missed_entry_is_backfilled_and_period_matches_backtest_rules(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    track(ledger, selection("2026-10-30"), UNIVERSE, make_prices("2026-10-30"), FEATURES)
    # Next run happens only after the November month-end.
    result = track(ledger, selection("2026-11-30"), UNIVERSE, make_prices("2026-12-02"), FEATURES)

    assert [e["signal_date"] for e in events(ledger, "ENTRY")] == ["2026-10-30", "2026-11-30"]
    [period] = events(ledger, "PERIOD")
    assert period["entry_execution_date"] == "2026-11-02"
    assert period["exit_execution_date"] == "2026-12-01"
    assert period["calendar_months"] == 1

    def ret(t):
        return price_on(t, "2026-12-01") / price_on(t, "2026-11-02") - 1

    gross = sum(ret(t) for t in HOLDINGS) / TOP_N
    assert period["v5"]["turnover"] == 1.0
    assert period["v5"]["net_return"] == pytest.approx(gross - COST_BPS / 10_000, abs=1e-9)
    assert period["point_in_time_equal_weight"]["return"] == pytest.approx(
        sum(ret(t) for t in UNIVERSE) / len(UNIVERSE), abs=1e-9)
    assert period["spy"]["return"] == pytest.approx(ret("SPY"), abs=1e-9)
    assert result["complete_monthly_observations"] == 1
    assert result["review_gate_reached"] is False
    assert validate(ledger)[0]


def test_second_period_charges_only_name_turnover(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2027-01-05")
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)
    track(ledger, selection("2026-11-30", HOLDINGS[:-2] + ["X01", "X02"]), UNIVERSE, prices, FEATURES)
    track(ledger, selection("2026-12-31"), UNIVERSE, prices, FEATURES)
    first, second = events(ledger, "PERIOD")
    assert (first["observation"], second["observation"]) == (1, 2)
    assert second["v5"]["turnover"] == pytest.approx(2 / TOP_N)
    assert second["v5"]["cost"] == pytest.approx(2 / TOP_N * COST_BPS / 10_000)


def test_rerun_is_idempotent(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02")
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)
    track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES)
    before = ledger.read_text(encoding="utf-8")
    track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES)
    assert ledger.read_text(encoding="utf-8") == before


def test_stale_data_cannot_write_an_older_signal(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02")
    track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES)
    with pytest.raises(RuntimeError, match="stale"):
        track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)


def test_skipped_month_is_flagged_and_not_counted_as_monthly(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2027-01-05")
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)
    result = track(ledger, selection("2026-12-31"), UNIVERSE, prices, FEATURES)
    [period] = events(ledger, "PERIOD")
    assert period["calendar_months"] == 2
    assert result["complete_monthly_observations"] == 0
    assert result["multi_month_periods"] == ["2026-10-30"]
    assert any("never recorded" in note for note in result["notes"])


def test_reports_are_written_from_the_ledger(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02")
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES)
    summary = track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES)
    write_reports(ledger, summary, tmp_path / "reports", tmp_path / "signals")
    table = pd.read_csv(tmp_path / "reports/period_returns.csv")
    assert table["signal_date"].tolist() == ["2026-10-30"]
    assert (tmp_path / "signals/v5_2026-10-30.json").exists()
    assert (tmp_path / "signals/v5_2026-11-30.json").exists()


def test_benchmark_cannot_be_a_holding(tmp_path):
    with pytest.raises(ValueError, match="benchmark"):
        track(tmp_path / "ledger.jsonl", selection("2026-10-30", HOLDINGS[:-1] + ["SPY"]),
              UNIVERSE + ["SPY"], make_prices("2026-11-03"), FEATURES)


def test_etf_benchmarks_are_measured_over_the_same_period(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02")
    etfs = make_prices("2026-12-02", tickers=ETF_BENCHMARKS)
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES, etfs)
    result = track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES, etfs)
    [period] = events(ledger, "PERIOD")
    for ticker in ETF_BENCHMARKS:
        expected = price_on(ticker, "2026-12-01") / price_on(ticker, "2026-11-02") - 1
        assert period["etf_benchmarks"][ticker]["return"] == pytest.approx(expected, abs=1e-9)
    assert period["excess_vs_rsp"] == pytest.approx(
        period["v5"]["net_return"] - period["etf_benchmarks"]["RSP"]["return"], abs=1e-9)
    assert result["cumulative"]["etf_benchmarks"]["RSP"]["periods_available"] == 1
    assert result["capital_gate_months"] == 24 and result["capital_gate_months_reached"] is False


def test_stale_or_missing_etf_data_never_blocks_a_period(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    prices = make_prices("2026-12-02")
    stale = make_prices("2026-11-20", tickers=ETF_BENCHMARKS)
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES, stale)
    track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES, stale)
    [period] = events(ledger, "PERIOD")
    assert period["etf_benchmarks"]["RSP"] == {
        "return": None, "reason": "prices do not cover the entry and exit sessions"}
    assert period["excess_vs_rsp"] is None
    assert period["spy"]["return"] is not None


def test_etf_in_stock_prices_uses_the_etf_file(tmp_path):
    # The upstream stock price file can carry RSP itself; it is not a scored stock.
    ledger = tmp_path / "ledger.jsonl"
    stock_rsp = make_prices("2026-12-02", tickers=["RSP"]).assign(open=1.0, close=1.0, adj_close=1.0)
    prices = pd.concat([make_prices("2026-12-02"), stock_rsp], ignore_index=True)
    etfs = make_prices("2026-12-02", tickers=["SPY", *ETF_BENCHMARKS])  # SPY in the ETF file is ignored
    track(ledger, selection("2026-10-30"), UNIVERSE, prices, FEATURES, etfs)
    result = track(ledger, selection("2026-11-30"), UNIVERSE, prices, FEATURES, etfs)
    [period] = events(ledger, "PERIOD")
    expected = price_on("RSP", "2026-12-01") / price_on("RSP", "2026-11-02") - 1
    assert period["etf_benchmarks"]["RSP"]["return"] == pytest.approx(expected, abs=1e-9)
    assert period["spy"]["return"] == pytest.approx(
        price_on("SPY", "2026-12-01") / price_on("SPY", "2026-11-02") - 1, abs=1e-9)
    assert any("ETF file" in note for note in result["notes"])


def test_etf_ticker_that_is_a_scored_stock_is_rejected(tmp_path):
    prices = pd.concat([make_prices("2026-11-03"), make_prices("2026-11-03", tickers=["RSP"])])
    etfs = make_prices("2026-11-03", tickers=["RSP"])
    with pytest.raises(ValueError, match="scored stocks"):
        track(tmp_path / "ledger.jsonl", selection("2026-10-30"), UNIVERSE + ["RSP"], prices, FEATURES, etfs)
