# AI Walk-Forward Backtest Conclusion (October 5, 2026)

## Decision

**This version failed. It must not proceed to paper orders or live trading.**

The model uses historical point-in-time S&P 500 membership, selects 20 stocks monthly, and executes at the next trading session's open. Transaction costs are deducted from turnover at 10 bps. Training uses a rolling five-year window with quarterly retraining, and every label must be fully completed before its training cutoff.

## Out-of-Sample Results

| Period | Strategy | Annual return | Annual volatility | Sharpe (0% risk-free) | Maximum drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| 2018-2022 | ML | 7.32% | 38.14% | 0.19 | -48.61% |
| 2018-2022 | Dynamic equal weight | 9.96% | 22.20% | 0.45 | -30.60% |
| 2018-2022 | SPY | 9.44% | 20.07% | 0.47 | -23.31% |
| 2023-2026 | ML | 15.72% | 20.23% | 0.78 | -21.78% |
| 2023-2026 | Dynamic equal weight | 11.13% | 12.68% | 0.88 | -11.42% |
| 2023-2026 | SPY | 20.77% | 12.04% | 1.73 | -7.80% |

## Why It Failed

1. Test-period return was lower than SPY with materially higher risk.
2. The model failed clearly in the 2018-2022 validation period, so improvement after 2023 cannot be treated as a stable pattern.
3. Average monthly turnover was roughly 80%, making the strategy cost-sensitive. At 10/25/50 bps, the 20-stock test portfolio produced approximately 15.72%/14.08%/11.41% annualized returns.
4. Across 250 random 20-stock paths, the 95th percentile annualized return was approximately 16.43%. The model's 15.72% did not clear that threshold.
5. Free historical delisting data remain incomplete, so residual survivorship bias may affect earlier samples.

## Next Iteration

- Reduce turnover and introduce market- or sector-neutral treatment before adding complexity.
- Add genuinely different information sources such as valuation, earnings quality, and analyst expectations; price-only features provide insufficient incremental information.
- Use purged walk-forward validation, multiple market regimes, and multiple-testing corrections.
- Advance a new model to at least three months of paper tracking only if it beats SPY, dynamic equal weight, and the 95th percentile of random selection.

## Subsequent Optimization Record

- V2 (cross-sectional ranks, relative-return targets, and a holding buffer): 10.15% test annual return, 0.57 Sharpe, and -18.40% maximum drawdown. Risk fell, but return fell more; rejected.
- V3 (SPY 200-day moving-average risk control with defensive exposure selected only on validation data): 12.26% test annual return, 0.65 Sharpe, and -21.78% maximum drawdown. It still materially lagged SPY; rejected.
- Signal diagnostics: V1 and V2 produced mean monthly test Rank IC values of -0.0169 and -0.0107, respectively, with positive IC in only about 43% of months. The models did not demonstrate stable cross-sectional predictive power.

Further LightGBM tuning was therefore stopped. The next research step required filing-date-aligned fundamentals such as earnings quality, valuation, and balance-sheet changes, plus reliable historical sector classifications. Continuing to tune the price model would have increased overfitting risk.
