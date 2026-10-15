# V5 Paper-Execution Rehearsal Design

## Purpose

Before the first eligible forward signal exists, use the September 30, 2026 V5 preview to run an explicitly non-official offline paper-trading rehearsal. The rehearsal validates the complete path from signal generation to order sizing, simulated fills, position valuation, and benchmark comparison.

## Goals

- Use $100,000 of virtual capital and allocate it equally across 20 stocks.
- Simulate whole-share purchases at the adjusted opening price of the first trading session after the signal.
- Estimate 10 bps costs on entry and hypothetical liquidation.
- Value positions at adjusted closing prices on the latest common trading date.
- Calculate an SPY benchmark with the same capital, dates, and cost assumptions.
- Write a positions CSV and a machine-readable JSON summary.
- Fail closed when data are missing, holdings are duplicated, prices are invalid, or a common valuation date is unavailable.

## Non-Goals

- Do not connect to a broker or send external orders.
- Do not count the September 30, 2026 preview return as post-freeze forward performance.
- Do not modify the V5 model, portfolio rules, formal hash ledger, or freeze date.
- Do not tune the model from this short rehearsal.

## Implementation Constraints

- Calculate adjusted opening price as `open * adj_close / close`.
- Set each stock's target capital to initial capital divided by the number of holdings and round shares down.
- Deduct entry notional and entry costs from cash.
- Deduct estimated exit costs from net liquidation value.
- Include `rehearsal_only: true` and `official_forward_result: false` in the report.
- Leave the formal `paper_trading.run_v5_forward` entry point unchanged.

## Deliverables

- `paper_trading/simulator.py`: deterministic local execution and valuation logic.
- `paper_trading/run_rehearsal.py`: preview and market-data runner.
- `tests/test_paper_simulator.py`: execution, cost, valuation, and fail-closed tests.
- `tests/test_run_rehearsal.py`: end-to-end report test in a temporary project tree.
- `reports/paper_rehearsal/summary.json` and `positions.csv`: local generated output, excluded from Git.
