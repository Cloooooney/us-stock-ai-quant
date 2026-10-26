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
| 2 | FI-002 | Residual (idiosyncratic) momentum | high | proposed for Batch 2 (caveat added 2026-10-26) |
| 3 | FI-009 | Net external financing (equity plus debt, cash-flow statement) | medium | see forking-path warning; decide at Batch 2 pre-registration |
| 4 | FI-010 | Off-season / long-horizon seasonal momentum | medium | added 2026-10-26; overlap check with V6 momentum first |
| 5 | FI-003 | Signal freshness / event-time formation (method, not a factor) | medium | design note for a future V8 |
| 6 | FI-004 | Intangible-adjusted book-to-market | low (was medium) | demoted 2026-10-26; data-history spike only if value is revisited |
| 7 | FI-005 | Earnings announcement return (EAR) from 8-K Item 2.02 dates | low | evidence weak outside microcaps |
| 8 | FI-006 | Short-interest surprise / days to cover (FINRA) | low | history too short; start archiving |
| 9 | FI-011 | Change in institutional ownership breadth (SEC 13F data sets) | low | added 2026-10-26; data spike only |
| 10 | FI-012 | Technology-linked momentum (USPTO patent links) | low | added 2026-10-26; heavy engineering |
| 11 | FI-007 | Opportunistic insider purchases (Form 4) | low | sparse in S&P 500 |
| 12 | FI-008 | Gross-profit surprise | low | overlaps V7 improvement sleeve |

Already tested or queued elsewhere, not duplicated here: net share issuance, return seasonality, 52-week-high ratio, and one-month reversal (factor-lab Batch 1, pre-registered 2026-10-19); profitability improvement `d_roa`, `d_net_margin`, `d_fcf_margin` (V7 improvement sleeve).

**Batch 1 outcome (read 2026-10-26 from `reports/factor_lab/batch1_results.csv`; not re-run):** none of the four passed the t ≥ 2.24 threshold. Net issuance came closest (alpha t 2.18, rank-IC t 2.01); same-month seasonality was significantly *negative* (alpha t -3.87). The trial registry now holds five candidates (V7 sleeve plus Batch 1), so Batch 2's Bonferroni threshold must account for at least 5 + the number of Batch 2 candidates.

## Base Rate: What to Expect From Any Idea Here

Chen and Welch, "What Useful Alphas?" (July 2026 draft, <https://arxiv.org/abs/2607.06502>), use the Open Source Asset Pricing data (about 200 published anomalies) to ask what a non-microcap manager could have earned after 2005. In the top-3,000 / top-90%-of-cap universe after 2005 the median long-short anomaly earned about 7 bp a month (t 0.45; only 67% positive); post-2005 alone removes about 60% of the in-sample return and the large-cap restriction about half of the rest. After trading costs the mean is roughly zero, and a luck adjustment shrinks the best survivor from 66 bp to about 6 bp. Categories with something left: **profitability** (cash-based and R&D-adjusted operating profitability, gross profitability), **financing** (net external financing), the realized-implied volatility spread, and **seasonal / off-season momentum**. Plain momentum, value, and intangibles had essentially nothing left in that universe.

Implication for this backlog: the prior for any single candidate on the S&P 500 is close to zero, so Batch 2 should stay small (two or three candidates), favor information types outside OSAP's price/accounting set (text, FI-001), and treat a near-miss in Batch 1 as no evidence at all.

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
- **2026-10-26 update:** No rigorous post-2020 study found. A QuantConnect student replication (2020-06/2026, 100 most liquid US stocks, long-only top 25 by similarity, Brain paid scores) reports Sharpe 0.56 vs SPY 0.53 with no factor alpha and only 9 of 25 parameter settings beating SPY (<https://www.quantconnect.com/research/20966/filing-language-stability-as-a-selection-signal/>). Weak, unrefereed, and paid-data based, so it neither supports nor refutes the idea; decay remains unknown. Text signals are absent from the Chen-Welch anomaly set, which is a reason to keep FI-001 first despite the low base rate.

### FI-002 Residual (idiosyncratic) momentum (high)

- **Description:** 12-1 month momentum computed on residuals from a rolling factor regression, scaled by residual volatility.
- **Rationale:** Total-return momentum mixes stock-specific under-reaction with factor exposure; the factor part creates momentum crashes. Residual momentum isolates the firm-specific, more persistent part.
- **Primary source:** Blitz, Huij, and Martens, "Residual Momentum", *Journal of Empirical Finance* 2011; Blitz, Hanauer, and Vidojevic, "The Idiosyncratic Momentum Anomaly", *International Review of Economics & Finance* 2020 (summary: <https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/>).
- **Out-of-sample / decay:** Huij and Lansdorp (2017) find it holds after publication (2009-2015); the 2020 paper reports Sharpe 0.48 vs 0.25 for total-return momentum over 1926-2015, not explained by FF5 plus UMD, and works internationally. Large-cap-specific results not confirmed this week.
- **Data / point-in-time:** Free; prices only. Caveat: the Ken French library revises historical factor returns, so to stay point-in-time use residuals against the in-house point-in-time equal-weight universe (or SPY) rather than downloaded FF factors.
- **Overlap:** Partly overlaps V6's momentum sleeve. The acceptance test must therefore be incremental: intercept after FF5 plus UMD **and** low enough correlation with V6 to add information. If it only replaces V6 momentum, that is a V8 design change, not a new factor.
- **Turnover / cost:** Medium (similar to 12-1 momentum, somewhat lower in the literature). Moderate cost sensitivity at 10-25 bps.
- **2026-10-26 caveat:** Chen and Welch (2026) find the momentum category had essentially no return in large caps after 2005. Residual momentum was not reported separately there, but the base rate for a momentum variant on the S&P 500 is poor. Keep in Batch 2 only if the batch still has room after FI-001; the incremental-over-V6 test stays mandatory.

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
- **2026-10-26 demotion (medium → low):** Chen and Welch (2026) report that value and intangibles anomalies earned essentially nothing in large caps after 2005. Combined with the truncated XBRL history, the cost of a data spike outweighs the expected value. Revisit only if a value-related V8 change is ever considered.

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

### FI-009 Net external financing (medium)

- **Description:** Net cash raised from equity and debt (issuance minus repurchases, dividends, and debt repayment) over the trailing twelve months, scaled by average total assets; high external financing predicts low returns.
- **Rationale:** Managers raise capital when it is cheap (market timing) and over-invest; investors under-react to the information in financing flows. Covers debt as well as equity, unlike net share issuance.
- **Primary source:** Bradshaw, Richardson, and Sloan, "The relation between corporate financing activities, analysts' forecasts and stock returns", *Journal of Accounting and Economics* 2006. Post-2005 large-cap evidence: Chen and Welch (2026), <https://arxiv.org/abs/2607.06502>, list it among the few survivors (about 48 bp a month raw in their survivor table, before luck shrinkage and costs).
- **Out-of-sample / decay:** One of the better-surviving anomalies in the 2026 OSAP-based study, but individual t-statistics after shrinkage are small.
- **Data / point-in-time:** Free. XBRL cash-flow statement tags (proceeds from and repayments of debt, stock issuance and repurchase, dividends), available from `filed + 1 day` with the existing SEC pipeline; history from 2009-2011 covers the 2012-2022 development period.
- **Overlap:** Partly overlaps FF5 CMA (investment) and Batch 1's net share issuance (equity component). Not in V6 or V7.
- **Turnover / cost:** Low (quarterly filing signal, slow-moving).
- **Forking-path warning:** Net issuance narrowly missed in Batch 1 (alpha t 2.18 vs 2.24). Testing a broader cousin *because* the narrow one nearly passed is exactly the selection the trial registry is meant to penalize. If included in Batch 2 it counts as a new trial, uses the textbook BRS definition with no variants, and its rationale must stand on the Chen-Welch evidence, not on Batch 1. If the high correlation with net issuance makes it effectively the same bet, prefer leaving it out.

### FI-010 Off-season / long-horizon seasonal momentum (medium)

- **Description:** Average monthly return over years 2-5 (or 6-10) **excluding** the same calendar month as the coming month ("off-season" momentum), or the long-horizon same-month average; the Chen-Welch survivors are the off-season and long-horizon seasonal variants from the Heston-Sadka line of research.
- **Rationale:** Persistent, slow-moving firm-specific return components (cash-flow seasonality, recurring investor demand) that short-horizon momentum does not capture.
- **Primary source:** Heston and Sadka, "Seasonality in the cross-section of stock returns", *Journal of Financial Economics* 2008; Keloharju, Linnainmaa, and Nyberg, "Return seasonalities", *Journal of Finance* 2016 (NBER w24676 revision: <https://www.nber.org/system/files/working_papers/w24676/revisions/w24676.rev0.pdf>). Post-2005 large-cap survival: Chen and Welch (2026).
- **Out-of-sample / decay:** Survives in the Chen-Welch large-cap post-2005 set, but Batch 1's same-month seasonality (a related definition) was strongly negative on this project's S&P 500 sample 2012-2022. That is a warning, not a reason to try the next variant.
- **Data / point-in-time:** Free; prices only; already point-in-time.
- **Overlap:** Long-horizon return averages correlate with V6 12-month momentum and with long-term reversal. Requires a cheap overlap check (correlation with V6's momentum sleeve) before any pre-registration, which uses no returns and does not spend the sample.
- **Turnover / cost:** Medium-high (the calendar-month component changes every month); cost-sensitive at 25 bps.
- **Why medium, not high:** a seasonality variant failed here already, and choosing among seasonality definitions after that result is a forking path. Include only with a definition fixed from the literature.

### FI-011 Change in institutional ownership breadth (low)

- **Description:** Quarterly change in the number of 13F filers holding a stock, scaled by the total number of filers; falling breadth signals binding short-sale constraints and predicts low returns.
- **Rationale:** Chen, Hong, and Stein (*Journal of Financial Economics* 2002): when pessimists cannot short, they exit, so breadth falls before prices adjust. Choi, Jin, and Yan (*Review of Finance* 2013, <https://revfin.org/?p=1462>) find value-weighted institutional breadth increases predict higher returns (Chinese data).
- **Out-of-sample / decay:** No recent US large-cap evidence found; effect concentrated in small, short-constrained stocks in the original work; Chen-Welch's general large-cap result suggests little is left. Treat as unverified.
- **Data / point-in-time:** Free. SEC Form 13F data sets (structured, quarterly, July 2013 onward, <https://www.sec.gov/dera/data/form-13f>); usable from each filing's acceptance date (up to 45 days after quarter end). Development period would lose 2012-mid 2013; pre-2013 needs parsing raw text filings.
- **Overlap:** Not in FF5+UMD, V6, or V7.
- **Turnover / cost:** Low-medium (quarterly).
- **Why low:** S&P 500 members are held by thousands of filers, so breadth changes are small and noisy; evidence is old and small-cap.

### FI-012 Technology-linked momentum (low)

- **Description:** Prior-month return of a firm's technology-linked peers, with links from the similarity of patent-class distributions.
- **Rationale:** Limited attention: investors are slow to price news from technologically related firms in other industries.
- **Primary source:** Lee, Sun, Wang, and Zhang, "Technological links and predictable returns", *Journal of Financial Economics* 2019 (summary: <https://alphaarchitect.com/technological-links-and-predictable-returns/>). 1963-2012; equal-weighted long-short 117 bp a month (t 5.47), value-weighted 69 bp (t 3.19); survives size, value, profitability, investment, momentum, industry and customer momentum controls.
- **Out-of-sample / decay:** None found after 2012. Stronger in low-attention, hard-to-arbitrage (smaller) firms; value-weighted result already about 40% lower.
- **Data / point-in-time:** Free USPTO grant data (PatentsView) with grant dates; requires a historical assignee-to-CIK match, which is the main engineering risk and a point-in-time risk (names change, mergers).
- **Overlap:** Distinct from industry momentum and customer momentum in the source; partly related to V6 momentum.
- **Turnover / cost:** High (monthly peer-return signal). Cost-sensitive.

## Rejected

| Idea | Source | Reason |
| --- | --- | --- |
| LLM stock picking from prompts and filings | Crisóstomo and Mykhalyuk, CNMV WP 96, 2026, <https://arxiv.org/pdf/2603.19944v1> | 10 months of Spanish IBEX-35 data, no factor alphas; LLM training data cannot be made point-in-time for a historical test. |
| Isolation-forest anomaly scores | Baciu, SSRN 6656558, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6656558> | Machine-learning repackaging of existing characteristics; single-author, unrefereed. |
| AI exposure | Borri, Liu, and Tsyvinski, SSRN 7021399, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7021399> | Thematic, regime-specific risk exposure rather than mispricing; exposure measure not reproducible point-in-time from free data. |
| Brain Company filing-sentiment similarity | Quantpedia / SSRN 3690461 | Paid dataset; the free-data version of the same idea is FI-001. |
| Text-based network industry (TNIC) peer momentum | Hoberg-Phillips Data Library, <https://hobergphillips.tuck.dartmouth.edu/tnic_basedata.html> | Free data ends in 2023, is keyed for Compustat users, and its release timing relative to filing dates is not documented, so it cannot be made point-in-time reliably. |
| Super Bowl indicator | Mendez, SSRN 6950738 | Cautionary data-snooping example, not a predictor. |
| Supply-chain propagation of FinBERT MD&A embeddings (added 2026-10-26) | arXiv 2606.29290, <https://arxiv.org/abs/2606.29290> | Signal is the 5th PCA component chosen from ten (a data-mined choice); supplier graph is static and hand-compiled, so not point-in-time; S&P 500 survivorship not addressed; internal inconsistencies in sample counts. |
| Customer momentum (added 2026-10-26) | Cohen and Frazzini, *JF* 2008; replication arXiv 2301.11394, <https://arxiv.org/abs/2301.11394> | Replication finds no significant long-short alpha after 2005 (value-weighted returns lose significance); clean customer links need Compustat Segments (paid) or hard 10-K text parsing. |
| Realized-implied volatility spread (added 2026-10-26) | Listed as a large-cap survivor by Chen and Welch 2026 | Needs historical option implied volatilities (OptionMetrics or similar), which are paid. |
| Cash-based and R&D-adjusted operating profitability (added 2026-10-26) | Ball et al., *JFE* 2016; Chen and Welch 2026 survivors | Repackages profitability already in V6 quality (ROA, cash quality, accruals) and FF5 RMW. |
| "Mosaics of Predictability" panel-tree clusters (added 2026-10-26) | Cong, Feng, He, and Wang, NBER w35158, 2026, <https://www.nber.org/papers/w35158> | A machine-learning forecasting method over many characteristics, not a single interpretable predictor; would require model search on the already-inspected sample. |
| EDGAR search-traffic attention (added 2026-10-26) | Drake et al. / Lee et al.; SEC EDGAR log files, <https://www.sec.gov/about/data/edgar-log-file-data-sets> | Logs missing July 2017-May 2020 and end June 2025, so neither the development period nor a forward record can be built. |

## Data Sources to Watch

- **EDGAR full-text filings** (free, acceptance timestamps): needed for FI-001.
- **EDGAR 8-K Item 2.02** (free): exact earnings-announcement dates, useful for FI-003 and FI-005 and for checking the `filed + 1 day` convention.
- **FINRA equity short interest** (free, twice monthly, ~7 business-day lag, rolling five-year API): archive forward for FI-006.
- **EDGAR Form 4** (free XML): FI-007.
- **SEC fails-to-deliver data** (free, since 2004): no strong large-cap evidence found yet; noted only.
- **SEC Form 13F data sets** (free, quarterly, July 2013 onward, <https://www.sec.gov/dera/data/form-13f>): FI-011. Confirm the acceptance-date field from the table definitions before any spike.
- **SEC Financial Statement and Notes data sets** (free, <https://www.sec.gov/data-research/financial-statement-notes-data-sets>): bulk XBRL including notes; a possible cross-check for the existing XBRL pipeline (single-source risk in ROADMAP Phase 1).
- **EDGAR log files**: not usable (gap 2017-2020, ended June 2025).
- **Open Source Asset Pricing** (Chen and Zimmermann, <https://www.openassetpricing.com/>): use its signal documentation to check whether a proposed definition matches the literature before pre-registering. Its portfolios are CRSP/Compustat-based and are reference only, not project inputs.

## Changelog

### 2026-10-26

- Second scouting run. Read the Batch 1 results now on `main` (all four failed; net issuance near-miss at alpha t 2.18; seasonality significantly negative) and recorded the cumulative trial count.
- Added a base-rate section from Chen and Welch, "What Useful Alphas?" (2026): median post-2005 large-cap anomaly about 7 bp a month and roughly zero after costs and luck adjustment.
- Added FI-009 net external financing (medium, with forking-path warning), FI-010 off-season seasonal momentum (medium), FI-011 ownership breadth from 13F data sets (low), FI-012 technology-linked momentum (low).
- Demoted FI-004 from medium to low; added a momentum caveat to FI-002 and a weak, inconclusive replication note to FI-001.
- Rejected six ideas (supply-chain LLM embeddings, customer momentum, realized-implied volatility spread, cash/R&D-adjusted profitability, panel-tree mosaics, EDGAR search traffic).
- Recommendation for Batch 2 unchanged in substance: FI-001 first; FI-002 only if the batch has room; FI-009 only with a definition and rationale independent of the Batch 1 near-miss. Nothing found this week is strong enough to add on its own merits.

### 2026-10-19

- Created the backlog (first scouting run). Read `docs/ROADMAP.md`, `reports/factor_attribution/CONCLUSION.md`, the V7 design, and the factor-lab Batch 1 pre-registration to avoid duplicates.
- Added FI-001 to FI-008; rejected six ideas.
- Recommendation for the next quarterly batch: FI-001 (Lazy Prices) if a text pipeline can be built and its single definition pre-registered first; FI-002 (residual momentum) as the cheaper, price-only candidate, judged on incremental value over V6 momentum. Cumulative multiple-testing count already includes Batch 1's four candidates, so Batch 2's threshold must be higher.
