# V6 Point-in-Time Factor Model Design

## Objective

V6 adds fresher point-in-time fundamentals to the existing monthly US equity system without changing or refitting the frozen V5 implementation. The model is deliberately simple: an equal-weight blend of momentum, quality, and value percentile ranks. Its purpose is to test whether economically interpretable quarterly information improves out-of-sample behavior, not to maximize an already observed backtest.

## Frozen Decisions

- The V5 code and reports remain unchanged.
- Signals are formed at the completed month end and executed at the next available open.
- SEC facts become usable on `filed + 1 calendar day`; a signal may only use a filing whose `available_date <= signal_date`.
- The portfolio holds 20 equal-weight stocks and charges 10 bps per one-way turnover in the primary result.
- The three sleeves and all within-sleeve feature weights are equal. No weight search is permitted after results are observed.
- Historical selection does not use the current SIC snapshot. Current SIC data may cap forward holdings, but applying it retrospectively would introduce classification look-ahead.
- The already inspected 2023-2026 period is diagnostic, not a new untouched test. Genuine new evidence starts after V6 is frozen.

## Quarterly SEC Data

The builder reads cached SEC Company Facts JSON and emits one row for every 10-Q, 10-Q/A, 10-K, 10-K/A, 20-F, 20-F/A, 40-F, or 40-F/A accession.

For 10-Q filings, the primary duration is the longest current fiscal-year-to-date period ending at the latest fiscal end, normally about 90, 180, or 270 days. This aligns revenue and net income with cash flow and capital expenditure, which are commonly disclosed only year-to-date. Annual filings use a 300-430 day duration.

For every accession, only facts carrying that accession are treated as newly disclosed. Prior-year comparative values in the same filing are safe to use because they were included in that filing. Previously filed annual values may be carried forward, but facts from later accessions may never rewrite an earlier snapshot.

Trailing-twelve-month flows are calculated as:

`latest known annual + current YTD - prior-year comparable YTD`

Annual filings use the reported annual value directly. Amendments create later snapshots rather than silently replacing information at an earlier date.

The output includes:

- TTM revenue, net income, operating cash flow, and capital expenditure
- TTM revenue growth
- net margin, return on assets, cash quality, leverage
- free-cash-flow margin and accruals to assets
- shares outstanding and filing age metadata

## Valuation Construction

At each signal date, V6 joins the latest eligible filing to the monthly model row. Yahoo's historical close series is restated for later stock splits, so V6 restates filing-date shares by the product of split events after the filing. This is a unit conversion, not an economic signal. Diluted weighted-average shares are preferred; instantaneous entity shares are the fallback. If the two SEC fields differ by more than 100 times because one issuer reports a value in thousands or millions, the larger positive value is used before split restatement.

Value features are sales yield, earnings yield, and free-cash-flow yield. Invalid or non-positive market capitalizations become missing rather than being forced to extreme values.

## Factor Score

Every raw feature is converted to a same-date percentile rank. Missing values receive a neutral rank of 0.5 so that missing SEC coverage cannot become an accidental positive or negative signal.

- Momentum: 6-month and 12-month price momentum, higher is better.
- Quality: revenue growth, net margin, ROA, cash quality, free-cash-flow margin, low accruals, and low leverage.
- Value: sales yield, earnings yield, and free-cash-flow yield, higher is better.
- Final score: equal-weight mean of the three sleeve scores.

The portfolio selects the 20 highest final scores and weights them equally.

## Evaluation

The primary report compares V6 with point-in-time equal weight and SPY over identical signal months. It also reports:

- annualized return, volatility, zero-rate Sharpe ratio, maximum drawdown, total return, and turnover;
- 10 bps and 25 bps transaction-cost scenarios;
- 2018-2022 development and 2023-present diagnostic subperiods;
- monthly cross-sectional rank information coefficient;
- sleeve ablations and a result with the three best V6 months removed.

Sleeve ablations are diagnostic only; they are not candidates for retrospective model selection.

## Release Gate

V6 is technically releasable when point-in-time tests, parser tests, factor-direction tests, portfolio tests, and the full existing suite pass. It is economically promotable only if the frozen blend shows stable excess performance rather than a single favorable subperiod. Failure to beat both benchmarks is a research result, not permission to tune on the diagnostic period.

## Known Limitations

- SEC tag aliases and filing conventions vary by issuer.
- Share counts can be stale between filings; SEC issuers can also use inconsistent thousand/million scales, which V6 reconciles with a tested deterministic rule.
- Foreign issuers may provide only annual 20-F/40-F data.
- Historical point-in-time sector classifications are unavailable, so the historical test cannot fairly reproduce V5's current-sector cap.
- Survivorship bias is reduced by point-in-time membership, but source data and ticker mapping can still contain errors.
- A backtest cannot demonstrate future profitability; live paper trading after the freeze remains required.
