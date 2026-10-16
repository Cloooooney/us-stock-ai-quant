# V6 Research Results

## Decision

V6 is technically complete but does **not** pass the economic promotion gate. It beats the point-in-time equal-weight benchmark over the full period, but it does not beat SPY after 10 bps costs and it is not robust to removing its three best months. V6 must not replace V5 or submit broker orders.

The blend was frozen before the backtest was observed. No sleeve or weight was selected after seeing the diagnostic period.

## Data and Timing

- Backtest signals: January 2018 through August 2026, 104 monthly holding periods.
- SEC cache: 590 company files.
- Parsed quarterly/annual snapshots: 31,672 rows across 578 tickers.
- Latest SEC filing in the cache: October 9, 2026.
- Filing availability: filing date plus one calendar day.
- Portfolio: top 20, equal weight, next-session execution.
- Primary transaction cost: 10 bps per one-way turnover; stress case: 25 bps.

The parser produced zero file failures. In the latest backtest months, revenue growth and net margin covered about 93% of the universe; valuation features covered about 92% for sales and earnings yield and about 60% for free-cash-flow yield.

## Primary Results

| Period | Strategy | Annual return | Volatility | Sharpe (0% risk-free) | Maximum drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| 2018-2022 development | V6 blend, 10 bps | 9.64% | 21.51% | 0.45 | -26.65% |
| 2018-2022 development | PIT equal weight | 9.81% | 22.28% | 0.44 | -30.84% |
| 2018-2022 development | SPY | 9.44% | 20.07% | 0.47 | -23.31% |
| 2023-2026 diagnostic | V6 blend, 10 bps | 19.50% | 17.00% | 1.15 | -12.24% |
| 2023-2026 diagnostic | PIT equal weight | 11.01% | 12.69% | 0.87 | -11.34% |
| 2023-2026 diagnostic | SPY | 20.44% | 11.91% | 1.72 | -7.80% |
| 2018-2026 full | V6 blend, 10 bps | 13.71% | 19.67% | 0.70 | -26.65% |
| 2018-2026 full | V6 blend, 25 bps | 13.07% | 19.67% | 0.66 | -26.79% |
| 2018-2026 full | PIT equal weight | 10.32% | 18.75% | 0.55 | -30.84% |
| 2018-2026 full | SPY | 13.97% | 17.07% | 0.82 | -23.31% |

The full-period V6 return trails SPY by about 0.26 percentage points per year and has lower Sharpe and a deeper drawdown. In the diagnostic period it also trails SPY in both return and risk-adjusted return.

## Robustness

Removing the three best V6 months (March 2020, September 2022, and October 2024) reduces full-period V6 annual return to 9.30%, versus 10.78% for SPY on the same remaining months. Development-period V6 falls to 4.54%, below both equal weight at 4.63% and SPY at 4.95%.

The mean monthly cross-sectional rank information coefficient is only 0.0065. The full-period diagnostic sleeve results were:

| Sleeve | Annual return | Sharpe | Maximum drawdown |
| --- | ---: | ---: | ---: |
| Momentum | 17.65% | 0.66 | -28.26% |
| Quality | 15.61% | 0.73 | -27.42% |
| Value | 9.11% | 0.35 | -44.00% |
| Frozen blend | 13.71% | 0.70 | -26.65% |

These sleeve results are diagnostic only. Choosing momentum or quality now would be retrospective selection on an already observed test period.

## Audit Findings and Corrections

Two implementation issues were found before accepting the report:

1. SPY initially used the earliest exit date among all stocks, so a delisted stock could shorten the benchmark horizon. V6 now uses the dominant calendar date and has a regression test.
2. Yahoo historical close prices are restated for later splits while historical SEC share counts are not. Some issuers also publish share tags in thousands or millions. V6 now prefers diluted weighted-average shares, reconciles large unit mismatches against entity shares, and applies post-filing split factors. Regression tests cover both directions of unit mismatch and a later 50-for-1 split.

After correction, selected market capitalizations ranged from about $5.24 billion upward, no selected row used a future filing, and no selected filing exceeded the 460-day age limit.

## Remaining Limitations

- No point-in-time historical sector classification is available, so the historical V6 portfolio has no sector cap.
- Multiple listed share classes can create duplicate issuer exposure; this occurred in 51 months and is not retroactively changed in the frozen result.
- The 2023-2026 period was previously inspected in earlier model work and is not an untouched test.
- Free upstream market and SEC data can be corrected or revised.
- Backtests do not model partial fills, market impact, taxes, borrow constraints, broker failures, or live operational risk.

## Next Decision

Keep V6 as a reproducible research branch. Do not tune the frozen blend against these results. A future V7 should start from a new written hypothesis, add point-in-time industry normalization and issuer-level concentration controls, and reserve genuinely future paper observations for evaluation.
