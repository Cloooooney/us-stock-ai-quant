# Roadmap

Written October 16, 2026. This roadmap separates two questions that are easy to blur: whether the research process is sound (largely yes) and whether any model has shown it can make money beyond a cheap index or factor ETF (not yet).

## Where the Evidence Stands

| Check | Result | Source |
| --- | --- | --- |
| V4 vs point-in-time equal weight, 2018-2026 out of sample | +0.5% a year, t = 0.18, tracking error about 8% | `reports/ai_v4_fundamentals/monthly_returns.csv` |
| V4 vs SPY, 2023-2026 | -7.7% a year, t = -1.56 | same |
| V4 beta to SPY | about 1.0 | same |
| Mean monthly Rank IC across diagnosed signals | about 0.00, positive in about 50% of months | `reports/signal_diagnostics/monthly_rank_ic.csv` |
| Ticker-to-CIK coverage of index members | 88% in 2018, 100% in 2026 | `reports/sec_fundamentals/current_cik_mapping_coverage.csv` |

Interpretation:

1. **No demonstrated stock-selection skill.** V4's edge over its own equal-weight universe is statistically indistinguishable from zero.
2. **The SPY gap is mostly size, not selection.** Equal-weight S&P 500 returned 11.1% a year in 2023-2026 against 20.8% for SPY. A 20-stock equal-weight portfolio with beta near 1 will trail a cap-weighted index whenever mega caps lead. The relevant benchmarks are RSP (equal-weight S&P 500) and factor ETFs, with SPY reported for context.
3. **Six months cannot separate skill from luck.** Reaching t = 2 on excess return takes roughly `48 / IR^2` months: about 16 years at an information ratio of 0.5 and 4 years at 1.0.
4. **Residual survivorship bias.** Unmatched early members are disproportionately delisted or acquired companies.
5. **Thin feature set.** Six annual-filing ratios, no valuation, no quarterly updates, so signals can be 15 months old.
6. **No clean historical test set remains.** 2023-2026 has been inspected by the baseline, V1-V5, and three V4 variants.
7. **Hardest universe.** Large-cap US equities with free, widely known accounting ratios is where an edge is least likely.

## Release Gates

| Gate | Requirement |
| --- | --- |
| Pipeline check | 6 complete monthly forward observations with no operational errors. Not evidence of skill. |
| Small live allocation | At least 24 complete monthly forward observations; positive net excess return over RSP **and** over the closest-matching factor ETF; factor attribution shows residual alpha rather than only known factor exposure. |
| Scaling | A pre-registered sequential test on forward excess returns crosses its significance boundary. |

A strategy that only reproduces a factor ETF's exposure should be replaced by that ETF.

## Phase 0: Know What We Have (October-November 2026)

- [x] Fix forward ledger accounting before the first eligible signal (PR #1).
- [x] Factor attribution of historical strategy returns on Fama-French five factors plus momentum with Newey-West t-statistics (`research/factor_attribution.py`).
- [x] Download RSP, QUAL, VLUE, MTUM, and USMV and record them as forward benchmarks in every `PERIOD` event.
- [x] Run the attribution locally and record conclusions in `reports/factor_attribution/CONCLUSION.md`: no model has detectable alpha; V4 is market beta plus a mild profitability tilt and trailed QUAL.
- [x] Run factor attribution including V6: no significant alpha, but V6's active return is not explained by known factors and beats every benchmark ETF in point estimate.
- [x] Track V6 forward in its own ledger from the October 30, 2026 signal; refresh SEC data after 10-Q filings.
- [x] Automate the monthly cycle on the local computer and a monthly remote review (`automation/README.md`).
- [ ] Record the first formal V5 and V6 signals after the October 30, 2026 close.

## Phase 1: Data Quality (November 2026-January 2027)

Priority order follows the attribution result: add information the factor ETFs do not already use.

1. [x] Quarterly 10-Q facts with trailing-twelve-month aggregation and the same filing-date delay (V6, `data_pipeline/build_sec_quarterly_features.py`).
2. [ ] Changes in fundamentals (quarter-over-quarter and year-over-year improvement) rather than only levels.
3. [x] Valuation features: sales, earnings, and free-cash-flow yield with split-restated SEC share counts (V6). Book-to-market is not yet included.
4. [ ] Issuer-level de-duplication of multiple share classes (V6 held duplicate issuers in 51 months).

V6 (frozen October 15, 2026; see `docs/V6_RESULTS.md`) blends momentum, quality, and value. It beat its equal-weight universe by about 3.4% a year over 2018-2026 but trailed SPY, and the edge disappears after removing its three best months. Factor attribution of V6 is the next check: if its return is explained by momentum, quality, and value betas, an MTUM/QUAL/VLUE mix is the cheaper implementation.
5. Survivorship: universe-level bias against RSP measured at about 0.2% a year after fees, so a paid point-in-time source with delisted securities (for example Sharadar or Norgate) waits until a candidate signal exists.
- Point-in-time SIC: test reconstructing historical industry codes from SEC filing headers and report coverage before using them.
- Reduce single-source risk: the price and membership data come from one third-party GitHub release; add a cross-check against a second source.

## Phase 2: Research Method (in parallel with Phase 1)

- Factor-by-factor evaluation first: monthly Rank IC with Newey-West t-statistics, raw and sector-neutral, plus decay over one to six months.
- Acceptance criterion: a candidate's long-short or top-quintile return must show a positive intercept after Fama-French five factors plus momentum in the validation period. Return already explained by known factors is available more cheaply in ETFs.
- Out-of-universe replication: a signal found on the S&P 500 must work, with no retuning, on the S&P 400 and S&P 600. This is the only remaining clean historical evidence.
- Keep a trial registry of every configuration tried and report deflated Sharpe ratios.

## Phase 3: Portfolio Construction

- Sector-neutral and beta-controlled weights.
- 30-50 holdings (the existing stress test already shows 30 names beating 20 on Sharpe).
- Turnover buffers; prefer tax-advantaged accounts because monthly rebalancing creates short-term gains.

## Phase 4: Toward Live Capital (no earlier than late 2027)

- Broker paper API (for example Alpaca) to test authentication, rejected orders, partial fills, and outages.
- Small live allocation only after the gate above, capped at a small fraction of investable assets.
- Hard stop: a drawdown of more than 10% relative to RSP returns the strategy to research.

The product direction built on this research (an analysis app for others, automated trading for the owner only) is in [docs/PRODUCT_PLAN.md](PRODUCT_PLAN.md).

Every new model version starts its own forward record. Results already seen cannot be reused to select it.
