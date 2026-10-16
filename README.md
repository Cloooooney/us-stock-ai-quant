# US Equity AI Quant Research

An educational research project for testing US equity selection models with point-in-time index membership, filing-date-aligned SEC fundamentals, transaction costs, walk-forward validation, and forward paper tracking.

> This repository is research software, not investment advice. No model in this project has demonstrated reliable live alpha, and broker order submission is disabled.

## Current Status

The project progressed through several deliberately constrained model versions:

- **Baseline:** price momentum, trend, and low-volatility signals on a small teaching universe.
- **V1-V3:** point-in-time S&P 500 walk-forward ML experiments. These versions failed the acceptance criteria and were rejected.
- **V4:** a Ridge model using SEC fundamentals aligned to actual filing availability. It produced positive historical returns but did not beat SPY in the final test period.
- **V5:** V4 scores with SIC-based sector concentration limits. Its rules were frozen on October 5, 2026, and it is waiting for genuinely forward data.
- **V6 research branch:** a frozen equal-weight blend of quarterly point-in-time momentum, quality, and value ranks. It beats point-in-time equal weight over the full historical period but narrowly trails SPY and therefore is not promoted.

V5 holds 20 equal-weight stocks, limits concentration to four stocks per two-digit SIC and six per SIC division, expires annual fundamentals after 550 days, and assumes 10 bps transaction costs. Orders remain disabled.

## Historical Evidence

The V4 final test covered 2023-2026:

| Strategy | Annual return | Volatility | Sharpe (0% risk-free) | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: |
| Fundamental Ridge | 9.22% | 15.23% | 0.61 | -9.35% |
| Point-in-time equal weight | 11.13% | 12.68% | 0.88 | -11.42% |
| SPY | 20.77% | 12.04% | 1.73 | -7.80% |

The model made money in this historical test but underperformed simple benchmarks. That is not sufficient evidence for live deployment.

V6 covers 104 monthly holding periods from 2018 through August 2026. After 10 bps costs it returned 13.71% annualized, versus 10.32% for point-in-time equal weight and 13.97% for SPY. At 25 bps it returned 13.07%. Its Sharpe ratio was 0.70 versus 0.82 for SPY, and removing its best three months reduced annual return to 9.30%. See [docs/V6_RESULTS.md](docs/V6_RESULTS.md) for the full audit and rejection decision.

## Research Safeguards

- Historical point-in-time S&P 500 membership.
- Next-session execution after each signal.
- SEC facts available only after their filing date plus one calendar day.
- Walk-forward training with labels fully completed before the training cutoff.
- Validation-only model selection and a final diagnostic test period.
- Explicit transaction costs and turnover measurement.
- Stale-fundamental expiry and neutral imputation without missingness signals.
- Frozen V5 rules and a tamper-evident forward paper ledger.

## Setup

Python 3.11 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Data

Raw and derived market data are intentionally excluded from Git. The local pipeline downloads point-in-time market/index data and SEC Company Facts, validates them, and rebuilds the monthly research dataset.

Run the monthly update from the repository root:

```powershell
.\.venv\Scripts\python.exe -m data_pipeline.run_monthly_cycle
```

The pipeline validates schema, duplicate keys, positive prices, date monotonicity, fundamental availability dates, and label timing before replacing core datasets.

## Main Research Commands

```powershell
# Teaching baseline
.\.venv\Scripts\python.exe -m backtests.run_baseline

# Walk-forward price model
.\.venv\Scripts\python.exe -m backtests.run_ai_walk_forward

# Fundamental Ridge model
.\.venv\Scripts\python.exe -m backtests.run_fundamental_ridge

# Build quarterly point-in-time SEC snapshots for V6
.\.venv\Scripts\python.exe -m data_pipeline.build_sec_quarterly_features

# Run the frozen V6 research backtest
.\.venv\Scripts\python.exe -m backtests.run_v6_factor

# Build the latest V5 preview
.\.venv\Scripts\python.exe -m backtests.build_v5_forward_preview

# Run the non-official local execution rehearsal
.\.venv\Scripts\python.exe -m paper_trading.run_rehearsal

# Run the formal frozen forward tracker
.\.venv\Scripts\python.exe -m paper_trading.run_v5_forward

# Download benchmark ETFs (RSP, QUAL, VLUE, MTUM, USMV)
.\.venv\Scripts\python.exe -m data_pipeline.update_benchmark_etfs

# Fama-French five-factor plus momentum attribution of historical returns
.\.venv\Scripts\python.exe -m research.factor_attribution
```

## Forward Validation

The September 30, 2026 V5 preview predates the frozen model and is only an execution-pipeline rehearsal. It must not be counted as forward performance.

The first eligible signal must come from a completed month-end after October 5, 2026. V5 is tracked against point-in-time equal weight, SPY, RSP, and the QUAL, VLUE, MTUM, and USMV factor ETFs under the same timing. Six complete monthly observations are only an operational check. Any live allocation requires at least 24 complete monthly observations, positive net excess return over RSP and the closest factor ETF, and residual alpha after factor attribution. A short profitable streak will not trigger parameter changes or live deployment. See [docs/ROADMAP.md](docs/ROADMAP.md).

See [paper_trading/README.md](paper_trading/README.md) for operating details and [reports/v5_sector_guard/MODEL_CARD.md](reports/v5_sector_guard/MODEL_CARD.md) for the frozen model rules.

## Repository Layout

```text
backtests/        research and backtest entry points
data_pipeline/    market and SEC update pipeline
models/           model training and portfolio construction
paper_trading/    local simulation and frozen forward ledger
reports/          compact research summaries, model cards, and charts
strategies/       teaching baseline strategy
tests/            timing, data, model, ledger, and simulation tests
```

## Important Limitations

- Current SIC classifications are a present-day snapshot and are not backfilled into V5 history.
- V6 has no historical point-in-time sector classification and can hold multiple share classes of the same issuer.
- Historical delisted-company and ticker-to-CIK coverage remains imperfect.
- Cross-industry accounting ratios are not fully comparable.
- Free data sources can be revised or become unavailable.
- Local simulation does not test broker authentication, rejected orders, partial fills, latency, or outages.
