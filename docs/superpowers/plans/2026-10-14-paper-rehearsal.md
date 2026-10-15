# V5 Paper Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a non-official offline paper-trading rehearsal for the frozen V5 model without touching its formal forward ledger.

**Architecture:** A pure calculation module converts holdings and point-in-time prices into whole-share simulated fills and marked-to-market results. A separate CLI loads the existing V5 preview, runs both the portfolio and SPY through the same engine, and writes explicitly non-official reports.

**Tech Stack:** Python 3, pandas, pytest, parquet/CSV/JSON

**Spec:** `docs/superpowers/specs/2026-10-14-paper-rehearsal-design.md`

## Global Constraints

- Do not connect to a broker or submit external orders.
- Do not modify the V5 selection logic, frozen date, or formal ledger.
- Use adjusted next-day open fills and latest common-date adjusted closes.
- Estimate both entry and hypothetical exit costs at 10 bps.
- Label every generated result as rehearsal-only and non-official.

## Review Focus

- Duplicate holdings must fail instead of receiving double allocation; Task 1 tests this.
- A missing next-day fill or common valuation mark must fail closed; Task 1 tests this.
- Invalid cash, cost, or price values must fail with a useful error; Task 1 tests this.
- The CLI must not write the formal V5 ledger; Task 2 asserts outputs are isolated.
- Portfolio and SPY must use identical dates and cost treatment; Task 2 asserts the comparison fields.

---

### Task 1: Deterministic paper execution engine

**Files:**
- Create: `paper_trading/simulator.py`
- Create: `tests/test_paper_simulator.py`

**Interfaces:**
- Consumes: holdings with `ticker` and `date`; prices with `ticker`, `date`, `open`, `close`, and `adj_close`.
- Produces: `simulate_equal_weight_portfolio(holdings, prices, initial_cash, cost_bps, valuation_date=None) -> tuple[pd.DataFrame, dict]`.

- [x] **Step 1: Write failing tests** for whole-share sizing, adjusted-open fills, entry/exit costs, latest valuation, duplicate holdings, and incomplete price data.
- [x] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests\test_paper_simulator.py -q` and confirm failure because `paper_trading.simulator` does not exist.
- [x] **Step 3: Implement** `simulate_equal_weight_portfolio` with strict input validation and deterministic output columns.
- [x] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests\test_paper_simulator.py -q` and confirm all Task 1 tests pass.

### Task 2: Rehearsal CLI, reports, and operating instructions

**Files:**
- Create: `paper_trading/run_rehearsal.py`
- Create: `tests/test_run_rehearsal.py`
- Modify: `paper_trading/README.md`
- Create at runtime: `reports/paper_rehearsal/summary.json`
- Create at runtime: `reports/paper_rehearsal/positions.csv`

**Interfaces:**
- Consumes: Task 1 `simulate_equal_weight_portfolio`, `reports/v5_sector_guard/latest_preview_not_forward_result.csv`, and `data/pit/prices.parquet`.
- Produces: `run(root: Path, initial_cash: float = 100000.0, cost_bps: int = 10) -> dict` plus a `python -m paper_trading.run_rehearsal` CLI.

- [x] **Step 1: Write a failing end-to-end test** using a temporary preview and parquet dataset; assert isolated report paths, mandatory rehearsal labels, and matched portfolio/SPY dates.
- [x] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests\test_run_rehearsal.py -q` and confirm failure because the runner does not exist.
- [x] **Step 3: Implement** `run` and the argparse CLI, then document the exact command and interpretation limits.
- [x] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests\test_run_rehearsal.py -q` and confirm Task 2 passes.
- [x] **Step 5: Run** `.\.venv\Scripts\python.exe -m paper_trading.run_rehearsal` on the real project data and inspect both reports.
- [x] **Step 6: Run** `.\.venv\Scripts\python.exe -m pytest -q` and require the complete suite to pass.
