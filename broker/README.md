# Alpaca Paper Trading

Mirrors the frozen model's monthly signal (V6 by default, see `config.json`) in an Alpaca **paper** account, so the order, fill, and reconciliation path is tested with a real broker before any live money is considered. Live trading is not implemented: the client only accepts the paper endpoint and refuses `"live_trading": true`.

## Setup (once)

1. Create a free account at alpaca.markets and switch to the **Paper** account in the dashboard.
2. Generate paper API keys (Key ID and Secret).
3. Create `.env` in the repository root (it is ignored by Git and never committed):

   ```text
   ALPACA_API_KEY_ID=your-paper-key-id
   ALPACA_API_SECRET_KEY=your-paper-secret
   ```

4. Test the connection; this places no orders:

   ```powershell
   .\.venv\Scripts\python.exe -m broker.paper_rebalance --check
   ```

After that the monthly cycle handles everything. Without keys the step reports `not_configured` and does nothing.

## Rehearsal Before Formal Trading

Before the first formal month, the order path can be exercised for real:

```powershell
.\.venv\Scripts\python.exe -m broker.paper_rebalance --preview    # what it would send; sends nothing
.\.venv\Scripts\python.exe -m broker.paper_rebalance --rehearse   # sends those orders now
```

Both use the frozen model's holdings for the latest completed month-end and current Yahoo Finance closes for sizing. Rehearsal orders use client IDs starting with `rehearsal-`, are recorded in `paper_trading/alpaca_rehearsal_ledger.jsonl` with `rehearsal_only: true`, and are not part of any forward record. They are refused once formal paper orders exist. The first formal rebalance simply trades from the positions the rehearsal left.

## What Happens Each Month

| Run | Action |
| --- | --- |
| After the model records its SIGNAL and ENTRY | Sizes equal-weight whole-share orders from account equity (2% cash buffer), sells names leaving the portfolio, buys new ones, skips adjustments smaller than 10% of a position, and submits market day orders. Sent after the close, they execute at the next open. Appends an ORDERS event. |
| Next weekday runs | Checks each order; when all are final, appends a FILLS event with the broker's fill prices. |

Orders use client IDs like `v6-2026-10-30-AAPL-buy`, so reruns never submit duplicates. New orders are never stacked on unreconciled ones, and a signal older than 10 days is not traded.

## Expected Differences From the Model Record

The model assumes execution at the open of the first session after the signal (for the October 30 signal, November 2). The automation runs after that session closes, so paper orders execute one session later (November 3). Paper fills therefore measure that delay plus slippage and whole-share rounding; this is the point of the exercise and is reported, not hidden.

The ledger `paper_trading/alpaca_paper_ledger.jsonl` uses the same hash chain as the model ledgers and is published with them.
