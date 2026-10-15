# V5 Sector-Constrained Model Card

## Status

**Rules are frozen while the model waits for genuinely forward data. Orders are disabled.**

V5 inherits the V4 fundamental Ridge score and changes only portfolio construction:

- 20 equal-weight stocks.
- No more than four stocks from the same two-digit SIC.
- No more than six stocks from the same SIC division.
- Annual filings expire after 550 days.
- Missing fundamentals receive cross-sectional neutral values, and missingness is not provided to the model.
- Transaction costs are assumed to be 10 bps.

## Why V5 Has No Historical Backtest

The current SIC data are a snapshot collected on October 5, 2026. Backfilling today's sector classifications into the past would introduce point-in-time bias. The snapshot therefore was not used to rewrite historical results, and the already inspected 2023-2026 period was not used to select the sector caps.

`latest_preview_not_forward_result.csv` uses a September 30, 2026 signal, but the model was constructed after that signal. The file is only a data and sector-distribution check and cannot be counted as forward performance.

The first eligible forward signal must come from a completed month-end after the freeze date. It is expected after the October 30, 2026 close, with execution recorded from the next trading session.

## Release Gate

Collect at least six complete monthly observations while tracking V5, dynamic equal weight, and SPY. A high return over a small number of months will not justify early rule changes or live deployment.
