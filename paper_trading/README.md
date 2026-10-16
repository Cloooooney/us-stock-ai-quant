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
9. Records simulated fills for every ledgered signal whose next-session opening data are now available.
10. Records one holding-period observation for every signal whose next rebalance has executed.

Running it after the close of the first trading day records the signal and its fills in one pass. Running it earlier records the signal only; the fills are added on the next run, even if that run happens after a later month-end.

## Append-Only Ledger

`v5_ledger.jsonl` is the formal append-only paper-trading ledger. Every event contains the previous event's hash. Editing, deleting, or reordering a line invalidates the chain. Do not modify this file with a text editor or spreadsheet program.

The ledger holds three event types:

| Event | Written when | Contents |
| --- | --- | --- |
| `SIGNAL` | First run after a completed month-end that follows the freeze | The 20 frozen V5 holdings and the full scored point-in-time universe. Written once; later runs never recompute it. |
| `ENTRY` | The benchmark calendar has a session after the signal | Next-session opening fills for the ledgered `SIGNAL` holdings. A holding with no bar that day is listed in `unfilled_held_as_cash` and earns 0% for the period. |
| `PERIOD` | The session after the next `SIGNAL` is available | Net V5 return, point-in-time equal-weight return, and SPY return for the holding period, with per-holding detail. |

`PERIOD` uses the historical backtest conventions so forward and historical numbers are comparable: adjusted open after the signal to adjusted open after the next signal, names that stop trading exit at their last adjusted close, V5 pays 10 bps times name turnover (100% for the first period), and the equal-weight universe and SPY carry no costs. All prices in one `PERIOD` come from the same data snapshot, so dividends paid during the period are included.

If a month-end run is missed, the earlier portfolio is treated as held until the next recorded signal. That observation is flagged with `calendar_months` greater than 1 and does not count toward the six-month review gate.

Each formal signal is also saved under `paper_trading/signals/`, and period results are summarized in `reports/v5_forward/period_returns.csv` and `reports/v5_forward/summary.json`. Preview files are not formal performance observations.

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

The forward command is idempotent: it will not write duplicate `SIGNAL`, `ENTRY`, or `PERIOD` events for the same month, and it refuses to record a signal older than the latest ledgered one.
