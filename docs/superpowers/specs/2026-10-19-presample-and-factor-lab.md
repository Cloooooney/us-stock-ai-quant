# Pre-Registration: Pre-Sample Check and Factor Lab

Written and committed on October 19, 2026, **before either analysis was run**. Everything below is fixed.

## Part A: Pre-Sample Check of the Frozen V6 and V7

### Why this is new evidence

The point-in-time monthly dataset starts with the January 2012 signal, but every V6 and V7 result so far used signals from January 2018 onward. V6 has no fitted parameters; its sleeves and equal weights were fixed on textbook grounds, not tuned on 2012-2017. Running the frozen rules on 2012-2017 is therefore an out-of-sample test that is available now instead of after years of forward tracking.

### Fixed procedure

- Signals: January 31, 2012 through December 29, 2017 (calendar 2012-2017).
- Models: V6 blend and V7 (V6 score with one position per issuer), exactly as frozen. No setting is changed.
- Same timing, costs (10 bps primary, 25 bps stress), fundamentals expiry (460 days), and benchmarks (point-in-time equal weight of the same universe, SPY) as the V6 backtest.

### Pre-registered reading of V6

Let *excess* be V6's monthly net return minus point-in-time equal weight, and *t* its Newey-West t-statistic.

| Result | Reading |
| --- | --- |
| mean excess > 0 and t ≥ 1.65 | consistent with a real edge |
| mean excess ≤ 0 | inconsistent with a real edge; V6 stays in forward tracking but is no longer the leading candidate |
| otherwise | inconclusive |

Factor alpha of the excess (Fama-French five factors plus momentum) and comparison with SPY are reported but do not change the reading. V7 is reported alongside V6 and is read the same way.

### Known limitation

Ticker-to-CIK coverage of index members is lower before 2018, so more early rows have missing fundamentals, which V6 ranks as neutral. This weakens the quality and value sleeves in early years and is reported, not corrected.

## Part B: Factor Lab, First Batch

### Candidates (exactly four, chosen for economic rationale, none tested in this project before)

| Name | Definition at each month-end signal | Better when | Rationale |
| --- | --- | --- | --- |
| `net_issuance` | log of split-adjusted share count in the latest eligible filing divided by the count in the latest filing for a fiscal period 330-400 days earlier that was already available | lower | issuers sell overvalued stock and buy back undervalued stock (Pontiff and Woodgate 2008) |
| `seasonality` | mean of the stock's returns in the same calendar month as the holding month, over the previous five years, with at least three years required | higher | recurring same-month return patterns (Heston and Sadka 2008) |
| `high_52w` | price divided by its 252-day high (the existing `drawdown_252` feature) | higher | anchoring to the 52-week high (George and Hwang 2004) |
| `short_reversal` | negative of the prior 21-day return (the existing `mom_21` feature) | higher | short-term liquidity-driven overreaction |

Share counts use the weighted-average diluted count when available and shares outstanding otherwise; the earlier count is multiplied by the stock splits dated after its filing and on or before the later filing. Ratios beyond 100x in either direction are treated as unit errors and set missing. Missing values are excluded from ranking for that candidate in that month.

### Evaluation period

Development: signals January 2012 through December 2022. Diagnostic: January 2023 onward, reported but never used for the pass decision.

### Tests (per candidate, development period)

1. Mean monthly Spearman rank IC against next-month return, Newey-West t.
2. Equal-weight top quintile minus the equal-weight universe, regressed on Fama-French five factors plus momentum; intercept and Newey-West t.
3. The same spread after subtracting 10 bps times the top quintile's monthly name turnover.

### Pass rule

Four candidates are tested, so the one-sided 5% threshold is Bonferroni-adjusted to 1.25% per candidate: **t ≥ 2.24**. A candidate passes only if test 1 and test 2 are both positive with t ≥ 2.24 **and** test 3 has a positive mean. A passing candidate becomes eligible for a future pre-registered V8 only if its diagnostic-period mean rank IC is also positive.

Also reported, not used for the decision: Q5 minus Q1 spread, average cross-sectional Spearman correlation with the V6 score, top-quintile turnover, and coverage.

There is no parameter search, no alternative definition, and no additional candidate in this batch. Every candidate tested is recorded in `reports/factor_lab/trial_registry.csv`, and later batches must raise the threshold for the cumulative number of candidates tested.
