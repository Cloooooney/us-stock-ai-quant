# V7 Pre-Registration

Written and committed on October 16, 2026, **before any V7 backtest was run**. Everything below is fixed; the backtest may only report against it. V6 continues unchanged in its own forward record.

## Hypotheses

V7 changes V6 in exactly two ways. Each has a reason that does not come from V6's results.

1. **One position per issuer (correctness fix).** V6 can hold two share classes of the same company (for example GOOGL and GOOG), which doubles one issuer's weight; this happened in 51 historical months. Issuers are identified by SEC CIK. This is adopted unconditionally because it removes an unintended concentration, not because it is expected to raise returns.
2. **An improvement sleeve (new information).** V6 measures the level of profitability. Whether profitability is improving is information V6 does not use and that the factor ETFs (QUAL, VLUE, MTUM) do not target. Hypothesis: companies whose trailing-twelve-month profitability improved over the past year outperform their universe over the next month.

### Considered and excluded

- **Industry-relative ranking and industry caps.** Only a present-day SIC snapshot exists. Applying it to history would use future classification information. Deferred until point-in-time industry codes can be built (for example from SEC filing headers).
- **Any change to V6's sleeves, features, or weights.** V6's diagnostic ablations (for example momentum alone) have been seen; choosing among them now would be retrospective selection.

## Fixed Definitions

Universe, timing, and costs are identical to V6: point-in-time S&P 500 members at each completed month-end, next-session open execution, top 20 equal weight, 10 bps per unit of name turnover (25 bps stress case), SEC facts usable from `filed + 1 day`, filings older than 460 days ignored, missing values ranked neutral at 0.5.

### Improvement features

For each quarterly or annual snapshot, the comparison snapshot is the latest one for the same ticker whose fiscal period ended 330 to 400 days earlier and that was already available when the current snapshot became available. Features are the differences:

| Feature | Definition | Direction |
| --- | --- | --- |
| `d_roa` | ROA minus ROA one year earlier | higher is better |
| `d_net_margin` | TTM net margin minus its value one year earlier | higher is better |
| `d_fcf_margin` | TTM free-cash-flow margin minus its value one year earlier | higher is better |

If either snapshot lacks the input, the feature is missing (neutral rank). No winsorization beyond ranking.

### Scores

- Momentum, quality, and value sleeves: exactly as V6.
- Improvement sleeve: the equal-weight mean of the three improvement feature ranks.
- **V7 candidate score:** equal-weight mean of the four sleeves.
- **V7 fallback score:** V6's three-sleeve blend.

### Selection

Rank by score (ties broken by ticker). Walk down the list and skip any ticker whose CIK is already selected; tickers without a CIK count as their own issuer. Stop at 20.

## Decision Rule

Only the **development period, signals January 2018 through December 2022**, decides. Later months are reported as diagnostics and cannot change the decision.

The improvement sleeve is adopted, making the candidate score V7's score, only if **both** hold in the development period:

1. Mean monthly Spearman rank IC of the improvement sleeve against next-month returns is positive with Newey-West t ≥ 1.65.
2. The equal-weight top-quintile portfolio of the improvement sleeve, minus the equal-weight universe, has a positive Fama-French five-factor plus momentum intercept with Newey-West t ≥ 1.65.

Otherwise V7 uses the fallback score, which makes V7 identical to V6 except for issuer de-duplication.

There is no parameter search and no other variant. The thresholds are one-sided 5% tests because the sign of the effect is specified in advance.

## Reporting

`backtests/run_v7_factor.py` writes to `reports/ai_v7_factor/`:

- the decision-rule inputs and the resulting decision (`decision.json`);
- development, diagnostic, and full-period performance for the chosen V7, V6, point-in-time equal weight, and SPY at 10 and 25 bps;
- months in which issuer de-duplication changed the holdings;
- the frozen configuration.

The development-period result of the chosen V7 versus V6 is reported but does not gate anything: V7's credibility comes from its forward record.

## Forward Tracking

After the backtest has run and the decision is recorded, V7 is frozen. Its first eligible forward signal is the first completed month-end after the freeze. It is tracked in its own ledger under the same rules as V5 and V6, and the Alpaca paper account continues to follow V6 unless a later decision changes `broker/config.json` on the basis of forward evidence.
