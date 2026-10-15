# V5 Forward Paper-Tracking Guide

## Current State

- V5 freeze date: October 5, 2026.
- First eligible signal: the first completed month-end after the freeze date.
- Broker orders: disabled.
- Minimum review window: six complete monthly observations.

## Month-End Run

Run this on the first trading day after each month-end, once public market data have been updated:

```powershell
.\.venv\Scripts\python.exe -m data_pipeline.run_monthly_cycle
```

The workflow:

1. Downloads market data and historical index membership into a temporary location.
2. Checks duplicate keys, positive prices, non-regressing dates, and upstream validation results.
3. Atomically replaces core data only after validation and records SHA-256 hashes.
4. Refreshes current SEC submissions.
5. Refreshes Company Facts only for companies with a newly detected annual filing.
6. Rebuilds annual fundamentals and the monthly ML dataset.
7. Rechecks execution dates, label dates, and missing values.
8. Generates the V5 signal and appends it to the hash-chained ledger.
9. Records simulated fills once next-session opening data are available.

## Append-Only Ledger

`v5_ledger.jsonl` is the formal append-only paper-trading ledger. Every event contains the previous event's hash. Editing, deleting, or reordering a line invalidates the chain. Do not modify this file with a text editor or spreadsheet program.

Each formal signal is also saved under `paper_trading/signals/` for manual review. Preview files are not formal performance observations.

## Pre-Freeze Execution Rehearsal

Before the first eligible signal, the complete local execution path can be rehearsed offline:

```powershell
.\.venv\Scripts\python.exe -m paper_trading.run_rehearsal
```

The command uses $100,000 of virtual capital, whole shares, next-session adjusted opening prices, and 10 bps costs on each side. It also calculates an SPY comparison. Output is written to `reports/paper_rehearsal/` and is ignored by Git.

This rehearsal validates only the signal-to-order, fill, valuation, and benchmark-comparison code path. It uses a preview signal seen before the model freeze and is explicitly labeled with `rehearsal_only: true` and `official_forward_result: false`. It cannot be counted as forward evidence or used to claim that the model is profitable.

## Independent Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m paper_trading.run_v5_forward
```

The forward command is idempotent: it will not write duplicate `SIGNAL` or `ENTRY` events for the same month.
