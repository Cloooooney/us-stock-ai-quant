# Factor Idea Backlog

A living list of candidate cross-sectional predictors for the point-in-time US equity research in this repository. It is updated by a weekly scouting task and merged into `main` quarterly.

**This document only finds and evaluates ideas. Nothing here has been tested on this project's data.** Every test spends the same historical sample, so candidates are tested only in pre-registered quarterly batches (see `docs/superpowers/specs/2026-10-19-presample-and-factor-lab.md` for the format and `reports/factor_lab/trial_registry.csv` for the cumulative count that raises later thresholds). Being listed here, at any priority, is not evidence that an idea works.

## Screening Rules

An idea enters the ranked backlog only if:

1. Its inputs are free and can be made point-in-time with a filing, publication, or trade date.
2. It is not already covered by V6 (momentum, quality, value), the V7 improvement sleeve, the factor-lab Batch 1 candidates, or the Fama-French five factors plus momentum.
3. There is a credible primary source with a stated economic rationale, and preferably out-of-sample or post-publication evidence.

The project's acceptance test (ROADMAP Phase 2) is a positive intercept after Fama-French five factors plus momentum, on large caps, net of costs. Ideas whose evidence is concentrated in microcaps or illiquid stocks are down-ranked accordingly, because this project trades S&P 500 members.

Priorities: **high** = candidate for the next quarterly batch; **medium** = worth a data-pipeline spike first; **low** = keep on file.

## Ranked Backlog

| Rank | ID | Idea | Priority | Status |
| --- | --- | --- | --- | --- |
| 1 | FI-001 | Lazy Prices: year-over-year change in 10-K/10-Q text | high | proposed for Batch 2 (needs text pipeline) |
| 2 | FI-002 | Residual (idiosyncratic) momentum | high | proposed for Batch 2 |
| 3 | FI-003 | Signal freshness / event-time formation (method, not a factor) | medium | design note for a future V8 |
| 4 | FI-004 | Intangible-adjusted book-to-market | medium | data-history spike first |
| 5 | FI-005 | Earnings announcement return (EAR) from 8-K Item 2.02 dates | low | evidence weak outside microcaps |
| 6 | FI-006 | Short-interest surprise / days to cover (FINRA) | low | history too short; start archiving |
| 7 | FI-007 | Opportunistic insider purchases (Form 4) | low | sparse in S&P 500 |
| 8 | FI-008 | Gross-profit surprise | low | overlaps V7 improvement sleeve |

Already tested or queued elsewhere, not duplicated here: net share issuance, return seasonality, 52-week-high ratio, and one-month reversal (factor-lab Batch 1, pre-registered 2026-10-19); profitability improvement `d_roa`, `d_net_margin`, `d_fcf_margin` (V7 improvement sleeve).

## Idea Cards

### FI-001 Lazy Prices: year-over-year change in 10-K/10-Q text (high)

- **Description:** Cosine similarity between a firm's current periodic filing and the same filing type one year earlier; low similarity ("changers") predicts lower future returns.
- **Rationale:** Investors under-react to subtle, non-headline changes in long filings, especially in risk-factor and MD&A sections; changes often foreshadow bad news (litigation, risk, executive turnover).
- **Primary source:** Cohen, Malloy, and Nguyen, "Lazy Prices", *Journal of Finance* 2020; NBER w25084, <https://www.nber.org/papers/w25084>. Corroborating practitioner replication on the ~1,000 largest US stocks, 2007-2020, with a long-low-minus-high-similarity spread of about 5.5% a year at 6.5% volatility: Quantpedia summary of SSRN 3690461, <https://quantpedia.com/the-positive-similarity-of-company-filings-and-the-cross-section-of-stock-returns/>.
- **Out-of-sample / decay:** Original sample 1995-2014 reports large factor-adjusted alphas that are not concentrated in small caps. The Quantpedia replication extends to 2020 on large caps but is not peer-reviewed and reports no factor alphas. No rigorous post-2020 study found this week; treat decay as unknown.
- **Data / point-in-time:** Free. EDGAR full-text filings with acceptance timestamps since the mid-1990s; usable from `filed + 1 day`, same discipline as the SEC fundamentals pipeline. CIK mapping already exists.
- **Overlap:** Not a price, accounting-ratio, or Fama-French factor. Low expected correlation with V6.
- **Turnover / cost:** Low. The signal changes once per filing (quarterly), monthly holding works in the source; cost sensitivity small.
- **Main risk:** Engineering effort (download, section extraction, tokenization) and the temptation to tune text choices. Pre-register one definition (full-document cosine similarity on word counts, same form type, prior year) before looking at any result.

### FI-002 Residual (idiosyncratic) momentum (high)

- **Description:** 12-1 month momentum computed on residuals from a rolling factor regression, scaled by residual volatility.
- **Rationale:** Total-return momentum mixes stock-specific under-reaction with factor exposure; the factor part creates momentum crashes. Residual momentum isolates the firm-specific, more persistent part.
- **Primary source:** Blitz, Huij, and Martens, "Residual Momentum", *Journal of Empirical Finance* 2011; Blitz, Hanauer, and Vidojevic, "The Idiosyncratic Momentum Anomaly", *International Review of Economics & Finance* 2020 (summary: <https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/>).
- **Out-of-sample / decay:** Huij and Lansdorp (2017) find it holds after publication (2009-2015); the 2020 paper reports Sharpe 0.48 vs 0.25 for total-return momentum over 1926-2015, not explained by FF5 plus UMD, and works internationally. Large-cap-specific results not confirmed this week.
- **Data / point-in-time:** Free; prices only. Caveat: the Ken French library revises historical factor returns, so to stay point-in-time use residuals against the in-house point-in-time equal-weight universe (or SPY) rather than downloaded FF factors.
- **Overlap:** Partly overlaps V6's momentum sleeve. The acceptance test must therefore be incremental: intercept after FF5 plus UMD **and** low enough correlation with V6 to add information. If it only replaces V6 momentum, that is a V8 design change, not a new factor.
- **Turnover / cost:** Medium (similar to 12-1 momentum, somewhat lower in the literature). Moderate cost sensitivity at 10-25 bps.

### FI-003 Signal freshness / event-time formation (medium, method)

- **Description:** Anomaly returns concentrate in the first month after the underlying information is released; forming portfolios on stale data understates predictability.
- **Source:** Bowles, Reed, Ringgenberg, and Thornock, "Anomaly Time", *Journal of Finance* 2024, <https://scholarsarchive.byu.edu/facpub/8579>.
- **Relevance:** V6 uses fundamentals up to 460 days old with equal weight on fresh and stale snapshots. A freshness-weighted version of existing quality/value/improvement signals is the natural design question for a V8. It is not a new factor and changing frozen V6/V7 is out of scope; record here so a future pre-registration can include it as one fixed alternative rather than a search.
- **Data:** Free; filing dates already in the pipeline. Turnover rises modestly.

### FI-004 Intangible-adjusted book-to-market (medium)

- **Description:** Book equity plus capitalized SG&A (and R&D) intangibles, divided by market value.
- **Rationale:** Expensed intangible investment makes book value meaningless for asset-light firms; adjusting restores value's signal.
- **Source:** Eisfeldt, Kim, and Papanikolaou, "Intangible Value", *Critical Finance Review* 2022; NBER w28056, <https://www.nber.org/system/files/working_papers/w28056/revisions/w28056.rev1.pdf>. Summary: <https://www.cxoadvisory.com/?p=34915>.
- **Evidence:** 1975-2018; long-HML_INT short-HML portfolio earned about 2.4% a year gross, with the gap largest in recent years. Correlation with HML about 0.81.
- **Data / point-in-time:** Free XBRL SG&A and R&D, but XBRL starts 2009-2011; a perpetual-inventory intangible stock needs roughly 10 years of flows, so the development period would be truncated or rely on a shortcut. Spike: measure coverage and how much of 2012-2022 has an adequate history before proposing a test.
- **Overlap:** HML and V6's value sleeve (which has no book-to-market at all). Must show intercept after HML; expected incremental effect is modest.
- **Turnover / cost:** Low.

### FI-005 Earnings announcement return (low)

- **Description:** Three-day abnormal return around the earnings announcement; positive announcement reactions drift.
- **Data:** Free and point-in-time: 8-K Item 2.02 acceptance dates on EDGAR plus prices; no analyst data needed.
- **Evidence against:** Martineau, "Rest in Peace Post-Earnings Announcement Drift", *Critical Finance Review* 2022, <https://cfr.ivo-welch.info/published/papers/martineau2021rest.pdf>, finds drift gone for large caps. Subrahmanyam (2025, SSRN) reconciles 2025 papers that find drift: over 2001-2024 the earnings factor has t = 2.18 for all stocks but t = 1.43 excluding microcaps (UCLA summary: <https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/>).
- **Overlap:** Partly captured by V6 momentum. Low priority for an S&P 500 universe.

### FI-006 Short-interest surprise / days to cover (low)

- **Description:** Short interest relative to its own 12-month mean and volatility; a positive surprise predicts lower returns.
- **Source:** Hanauer, Lesnevski, and Smajlbegovic, "Surprise in Short Interest", SSRN 3736891 (summary: <https://www.cxoadvisory.com/short-selling/surprise-in-short-interest-as-stock-return-predictor/>). 1980-2013, long-short 0.35-0.43% a month, alphas similar to raw returns; stronger in illiquid and volatile stocks.
- **Data / point-in-time:** FINRA publishes twice-monthly short interest about 7 business days after settlement (<https://www.finra.org/finra-data/browse-catalog/equity-short-interest>), but free API history is a rolling five years and exchange-listed coverage in FINRA files dates from 2021 (Regulatory Notice 21-19). Not enough history for the 2012-2022 development period.
- **Action:** Not testable now. Cheapest useful step is to archive each FINRA release with its publication date from now on, so a clean forward sample accumulates.

### FI-007 Opportunistic insider purchases (low)

- **Description:** Insider open-market purchases, excluding routine traders, predict returns (Cohen, Malloy, and Pomorski, *Journal of Finance* 2012).
- **Data:** Free, point-in-time Form 4 XML on EDGAR (filed within two business days).
- **Concerns:** Evidence concentrated in small firms; purchases are rare among S&P 500 members, so monthly coverage would be thin and most names neutral. Keep on file; reconsider if the universe extends to the S&P 400/600 (ROADMAP Phase 2 replication).

### FI-008 Gross-profit surprise (low)

- **Description:** Unexpected quarterly gross profit (seasonal change scaled by assets or its volatility) predicts returns.
- **Source:** Yang, Cai, Rhee, and Wu, "Unexpected Gross Profit and Cross-Sectional Stock Returns", SSRN 7268289, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7268289> (abstract could not be retrieved this week; details unverified).
- **Overlap:** Close cousin of the V7 improvement sleeve (`d_net_margin`) and of PEAD. Do not test separately unless V7's sleeve fails and the paper shows gross profit carries distinct information. Revisit after reading the paper.

## Rejected

| Idea | Source | Reason |
| --- | --- | --- |
| LLM stock picking from prompts and filings | Crisóstomo and Mykhalyuk, CNMV WP 96, 2026, <https://arxiv.org/pdf/2603.19944v1> | 10 months of Spanish IBEX-35 data, no factor alphas; LLM training data cannot be made point-in-time for a historical test. |
| Isolation-forest anomaly scores | Baciu, SSRN 6656558, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6656558> | Machine-learning repackaging of existing characteristics; single-author, unrefereed. |
| AI exposure | Borri, Liu, and Tsyvinski, SSRN 7021399, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7021399> | Thematic, regime-specific risk exposure rather than mispricing; exposure measure not reproducible point-in-time from free data. |
| Brain Company filing-sentiment similarity | Quantpedia / SSRN 3690461 | Paid dataset; the free-data version of the same idea is FI-001. |
| Text-based network industry (TNIC) peer momentum | Hoberg-Phillips Data Library, <https://hobergphillips.tuck.dartmouth.edu/tnic_basedata.html> | Free data ends in 2023, is keyed for Compustat users, and its release timing relative to filing dates is not documented, so it cannot be made point-in-time reliably. |
| Super Bowl indicator | Mendez, SSRN 6950738 | Cautionary data-snooping example, not a predictor. |

## Data Sources to Watch

- **EDGAR full-text filings** (free, acceptance timestamps): needed for FI-001.
- **EDGAR 8-K Item 2.02** (free): exact earnings-announcement dates, useful for FI-003 and FI-005 and for checking the `filed + 1 day` convention.
- **FINRA equity short interest** (free, twice monthly, ~7 business-day lag, rolling five-year API): archive forward for FI-006.
- **EDGAR Form 4** (free XML): FI-007.
- **SEC fails-to-deliver data** (free, since 2004): no strong large-cap evidence found yet; noted only.
- **Open Source Asset Pricing** (Chen and Zimmermann, <https://www.openassetpricing.com/>): use its signal documentation to check whether a proposed definition matches the literature before pre-registering. Its portfolios are CRSP/Compustat-based and are reference only, not project inputs.

## Changelog

### 2026-10-19

- Created the backlog (first scouting run). Read `docs/ROADMAP.md`, `reports/factor_attribution/CONCLUSION.md`, the V7 design, and the factor-lab Batch 1 pre-registration to avoid duplicates.
- Added FI-001 to FI-008; rejected six ideas.
- Recommendation for the next quarterly batch: FI-001 (Lazy Prices) if a text pipeline can be built and its single definition pre-registered first; FI-002 (residual momentum) as the cheaper, price-only candidate, judged on incremental value over V6 momentum. Cumulative multiple-testing count already includes Batch 1's four candidates, so Batch 2's threshold must be higher.
