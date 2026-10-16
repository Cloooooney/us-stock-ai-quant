# Automation

The forward record runs itself once this is installed. Nothing here changes model rules.

## What Runs Where

| Where | When | What |
| --- | --- | --- |
| Your Windows computer (Task Scheduler) | Weekdays at 2:30 PM local time, doing work only on calendar days 1-10 | Updates `main`, runs `data_pipeline.run_monthly_cycle` for V5 then V6, writes `automation/status.json`, and pushes changed ledgers and reports to GitHub |
| Claude scheduled task (cloud) | Monthly, after the local window | Reads `automation/status.json` and both ledgers from GitHub, validates the hash chains, reviews results against the benchmarks, and sends a notification |

The tracker is idempotent, so the extra weekday runs record nothing twice. They exist so a missed day (computer off, upstream data late) is retried automatically.

## One-Time Setup

From the repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File automation\install_task.ps1
Start-ScheduledTask -TaskName 'us-stock-ai-quant forward cycle'
```

The second command runs it once now. Outside days 1-10 it only logs that nothing is due; to force a full test run, use:

```powershell
powershell -ExecutionPolicy Bypass -File automation\run_forward_cycle.ps1 -Force
```

To remove the task: `powershell -ExecutionPolicy Bypass -File automation\install_task.ps1 -Remove`.

## Requirements

- The computer must be on and you must be signed in to Windows at some point on the due days; if it is asleep at 2:30 PM, the task runs when it wakes.
- Git must be able to push without prompting (it already can if `git push` works in PowerShell).
- The working tree must not have uncommitted changes to tracked files. The runner refuses to touch the repository otherwise and records nothing, so your own edits are never committed by accident.

## Outputs

- `paper_trading/v5_ledger.jsonl`, `paper_trading/v6_ledger.jsonl`: the formal hash-chained records, now committed so each GitHub commit adds an external timestamp to the forward record.
- `paper_trading/signals/`, `reports/v5_forward/`, `reports/v6_forward/`: per-signal snapshots and period summaries.
- `automation/status.json`: last attempt, result, failing step, and per-ledger counts. On failure it includes the end of the run log.
- `automation/logs/`: full run logs, kept locally only.
