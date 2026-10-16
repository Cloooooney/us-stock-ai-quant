# Factor Attribution Conclusion (October 16, 2026)

Run with `python -m research.factor_attribution` on Fama-French five factors plus momentum and ETF data through October 15, 2026. Full out-of-sample period, 103 monthly holding periods from February 2018. Newey-West t-statistics.

## Decision

**No historical model has detectable alpha. V4 is market beta plus a mild profitability tilt, and QUAL delivered more for less.** V5 forward tracking continues as an honest experiment, but nothing here supports allocating capital to V1-V4.

## Checks That the Tool Is Measuring the Right Thing

| Series | Result | Expected |
| --- | --- | --- |
| SPY, absolute | market beta 1.01, R² 0.97, alpha -0.23% a year (t -0.38) | beta near 1, alpha near 0 |
| Point-in-time equal weight vs RSP | +0.37% a year (t +1.82), same direction in 65% of months | close to RSP, slightly above because RSP charges a 0.20% fee |
| SPY vs RSP | +2.64% a year | cap-weight beat equal-weight in this period |

The in-house equal-weight universe tracks a real, investable equal-weight fund to within about 0.2% a year after fees. That bounds residual survivorship bias **at the universe level** as small for 2018 onward. It does not rule out bias in which individual names the models select.

## Findings

| Model | Alpha / yr (t), absolute | Active alpha vs equal weight / yr (t) | What explains it |
| --- | --- | --- | --- |
| V1 LightGBM price | +0.78% (+0.16) | +2.36% (+0.54) | market beta 1.25, negative profitability (-0.47), negative momentum (-0.61) |
| V2 cross-sectional | -5.83% (-1.64) | -4.26% (-1.35) | market beta 1.22, value tilt (+0.54) |
| V3 risk control | +0.75% (+0.15) | +2.32% (+0.48) | negative profitability (-0.48), negative momentum (-0.51) |
| V4 fundamental Ridge | -2.31% (-0.86) | -0.73% (-0.37) | market beta 1.01, profitability (+0.33), R² 0.83 |

1. **No intercept reaches |t| ≥ 2.** After known factors, none of the models adds anything distinguishable from zero.
2. **The price models (V1, V3) are short quality and short momentum.** They tend to buy unprofitable recent losers, a short-term reversal and junk tilt. That explains their high volatility (38% for V1 in validation) without adding return.
3. **V4 is mostly the market plus some quality.** It trailed QUAL by 0.97% a year and beat RSP by an insignificant 0.87% a year (t +0.34). A single low-cost ETF would have been the cheaper implementation of the same exposure.

## Consequences for the Roadmap

- Every new signal must show a positive intercept after Fama-French five factors plus momentum in the validation period before it is considered. Raw return or Rank IC alone is not enough, because the profitability and value premia are already available in ETFs.
- Phase 1 should prioritize information the factor ETFs do not already use: quarterly updates (faster than annual-filing factors), valuation measured with filing-date discipline, and changes in fundamentals rather than levels.
- Universe-level survivorship bias looks small, so paid delisting data can wait until a candidate signal exists.
- V4's quality tilt means the realistic expectation for V5's forward record is roughly QUAL-like returns with extra tracking error.

## Limitations

- 103 months is short: an information ratio of 0.5 needs roughly 16 years to reach t = 2, so absence of evidence is not proof of zero skill. It is, however, no basis for allocating money.
- Monthly alignment uses the calendar month of each execution date; the holding window runs open to open and is offset from calendar months by about one day.
- The 2023-2026 period has already been inspected repeatedly, so even these results are not a clean test.

## Addendum: V6 (October 16, 2026)

| Measure | V6 factor blend |
| --- | --- |
| Absolute alpha | +0.96% a year (t +0.32); market beta 1.00, value beta +0.34 (significant) |
| Active alpha vs its own equal-weight universe | +2.68% a year (t +0.85), R² 0.12 |
| Excess vs RSP / QUAL / MTUM / VLUE / USMV | +3.49% / +1.65% / +0.92% / +0.81% / +5.59% a year, all \|t\| < 2 |

V6 is the first version whose point estimate beats every benchmark ETF, and unlike V4 its active return is **not** explained by known factors (R² 0.12, no significant active beta). Neither result is statistically significant, and V6's own robustness check shows the edge disappears without its three best months.

Decision: V6 is the strongest candidate so far, so it gets a genuine forward record. Its rules were frozen on October 15, 2026, before the first eligible October 30 signal, so it can be tracked forward under the same conditions as V5 without any retuning.
