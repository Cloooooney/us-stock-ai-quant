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
| 2 | FI-002 | Residual (idiosyncratic) momentum | high | proposed for Batch 2 (caveat added 2026-10-26; one-definition rule vs FI-017 added 2026-11-09) |
| 3 | FI-009 | Net external financing (equity plus debt, cash-flow statement) | medium | see forking-path warning; decide at Batch 2 pre-registration |
| 4 | FI-010 | Off-season / long-horizon seasonal momentum | medium | added 2026-10-26; overlap check with V6 momentum first; history check added 2026-11-02; risk-vs-mispricing note 2026-11-09 |
| 5 | FI-013 | Real-time investor alpha as an added acceptance diagnostic (method, not a factor) | medium | added 2026-11-02; decide at Batch 2 pre-registration; not a trial |
| 6 | FI-003 | Signal freshness / event-time formation (method, not a factor) | medium | design note for a future V8; post-2005 evidence note 2026-11-09 |
| 7 | FI-004 | Intangible-adjusted book-to-market | low (was medium) | demoted 2026-10-26; data-history spike only if value is revisited |
| 8 | FI-014 | Operating leverage (operating costs over assets) | low | added 2026-11-02; overlap check first |
| 9 | FI-015 | R&D over market cap | low | added 2026-11-02; partial coverage, overlaps FI-004 |
| 10 | FI-005 | Earnings announcement return (EAR) from 8-K Item 2.02 dates | low | evidence weak outside microcaps |
| 11 | FI-017 | Announcement-window momentum (earnings-day returns inside the 12-1 window) | low | added 2026-11-09; alternative definition to FI-002, not an extra trial |
| 12 | FI-006 | Short-interest surprise / days to cover (FINRA) | low | history too short; start archiving |
| 13 | FI-016 | Short-volume ratio (FINRA daily files) | low | added 2026-11-02; history check first |
| 14 | FI-011 | Change in institutional ownership breadth (SEC 13F data sets) | low | added 2026-10-26; data spike only |
| 15 | FI-012 | Technology-linked momentum (USPTO patent links) | low | added 2026-10-26; heavy engineering |
| 16 | FI-007 | Opportunistic insider purchases (Form 4) | low | sparse in S&P 500 |
| 17 | FI-008 | Gross-profit surprise | low | overlaps V7 improvement sleeve |

Already tested or queued elsewhere, not duplicated here: net share issuance, return seasonality, 52-week-high ratio, and one-month reversal (factor-lab Batch 1, pre-registered 2026-10-19); profitability improvement `d_roa`, `d_net_margin`, `d_fcf_margin` (V7 improvement sleeve).

**Batch 1 outcome (read 2026-10-26 from `reports/factor_lab/batch1_results.csv`; not re-run):** none of the four passed the t ≥ 2.24 threshold. Net issuance came closest (alpha t 2.18, rank-IC t 2.01); same-month seasonality was significantly *negative* (alpha t -3.87). The trial registry now holds five candidates (V7 sleeve plus Batch 1), so Batch 2's Bonferroni threshold must account for at least 5 + the number of Batch 2 candidates.

## Base Rate: What to Expect From Any Idea Here

Chen and Welch, "What Useful Alphas?" (July 2026 draft, <https://arxiv.org/abs/2607.06502>), use the Open Source Asset Pricing data (about 200 published anomalies) to ask what a non-microcap manager could have earned after 2005. In the top-3,000 / top-90%-of-cap universe after 2005 the median long-short anomaly earned about 7 bp a month (t 0.45; only 67% positive); post-2005 alone removes about 60% of the in-sample return and the large-cap restriction about half of the rest. After trading costs the mean is roughly zero, and a luck adjustment shrinks the best survivor from 66 bp to about 6 bp. Categories with something left: **profitability** (cash-based and R&D-adjusted operating profitability, gross profitability), **financing** (net external financing), the realized-implied volatility spread, and **seasonal / off-season momentum**. Plain momentum, value, and intangibles had essentially nothing left in that universe.

Implication for this backlog: the prior for any single candidate on the S&P 500 is close to zero, so Batch 2 should stay small (two or three candidates), favor information types outside OSAP's price/accounting set (text, FI-001), and treat a near-miss in Batch 1 as no evidence at all.

**2026-11-02 additions.** Two more sources point the same way. Loughran, "Do Factors Matter?", *Critical Finance Review* 2025, <https://nowpublishers.com/article/Details/CFR-0160>, finds over 1983-2021 that most Fama-French six-factor and q5 characteristics have not worked for large firms for a long time; stocks making up under 8% of market value drive the patterns. Goncalves, Loudis, and Ogden, "Real Time Investor Alphas and the Survival of the Anomaly Zoo" (July 2026, working paper, <https://portal.northernfinanceassociation.org/viewp.php?n=2240218512>), find that across 177 anomalies the average post-publication factor-regression alpha is highly significant (t 9.43) while an investor who must estimate the allocation in real time gets about zero (t 0.38); see FI-013.

Reading note on Chen and Welch: their "intangibles are dead" statement is about the category median. R&D over market cap (raw 41 bp, shrunk 3 bp a month) and operating leverage (raw 38 bp, shrunk 3 bp) still appear in their top-10 table, and the paper does not reconcile the two statements or classify them. Those two were missed in the 2026-10-26 run and are now FI-014 and FI-015.

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
- **2026-11-02 update:** A targeted search again found no rigorous post-2020 return study, so decay remains unknown. Jehnen, Villalba-Diez, and Ordieres-Mere, *Frontiers in Artificial Intelligence* 2026, <https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1752103/xml>, show on S&P 500 10-K MD&A (test years 2022-2023) that text topics add about 2 points of ROC-AUC to forecasting the direction of ROA change. This is indirect support that filing text carries fundamental information on large caps; it has no portfolio test.

### FI-002 Residual (idiosyncratic) momentum (high)

- **Description:** 12-1 month momentum computed on residuals from a rolling factor regression, scaled by residual volatility.
- **Rationale:** Total-return momentum mixes stock-specific under-reaction with factor exposure; the factor part creates momentum crashes. Residual momentum isolates the firm-specific, more persistent part.
- **Primary source:** Blitz, Huij, and Martens, "Residual Momentum", *Journal of Empirical Finance* 2011; Blitz, Hanauer, and Vidojevic, "The Idiosyncratic Momentum Anomaly", *International Review of Economics & Finance* 2020 (summary: <https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/>).
- **Out-of-sample / decay:** Huij and Lansdorp (2017) find it holds after publication (2009-2015); the 2020 paper reports Sharpe 0.48 vs 0.25 for total-return momentum over 1926-2015, not explained by FF5 plus UMD, and works internationally. Large-cap-specific results not confirmed this week.
- **Data / point-in-time:** Free; prices only. Caveat: the Ken French library revises historical factor returns, so to stay point-in-time use residuals against the in-house point-in-time equal-weight universe (or SPY) rather than downloaded FF factors.
- **Overlap:** Partly overlaps V6's momentum sleeve. The acceptance test must therefore be incremental: intercept after FF5 plus UMD **and** low enough correlation with V6 to add information. If it only replaces V6 momentum, that is a V8 design change, not a new factor.
- **Turnover / cost:** Medium (similar to 12-1 momentum, somewhat lower in the literature). Moderate cost sensitivity at 10-25 bps.
- **2026-10-26 caveat:** Chen and Welch (2026) find the momentum category had essentially no return in large caps after 2005. Residual momentum was not reported separately there, but the base rate for a momentum variant on the S&P 500 is poor. Keep in Batch 2 only if the batch still has room after FI-001; the incremental-over-V6 test stays mandatory.
- **2026-11-02 update:** A targeted search found no large-cap or net-of-cost evidence from the last year. The CXO summary of Blitz, Hanauer, and Vidojevic (data through 2015, <https://www.cxoadvisory.com/momentum-investing/idiosyncratic-pure-or-residual-momentum-as-a-stock-return-predictor>) reports gross results only, no large-cap split, and turnover modestly *higher* than conventional momentum, per the corresponding author. That conflicts with the "somewhat lower" turnover above; treat cost sensitivity as at least equal to 12-1 momentum until measured.
- **2026-11-09 update:** Gérard and Jehl, "The Many Facets of Stock Momentum", *Financial Analysts Journal* 82(1), 2025, <https://rpc.cfainstitute.org/research/financial-analysts-journal/2025/many-facets-of-stock-momentum>, separate momentum into a factor part and a stock-specific part measured by the earnings-announcement returns inside the formation window; per the abstract the stock-specific part predicts returns in the US, Europe, and Japan over about 30 years and does not reverse. This supports the premise of FI-002 (the firm-specific component is the persistent one) but offers a second, regression-free way to measure it (FI-017). Full text, large-cap results, and post-2005 numbers were not read (paywalled). **One-definition rule:** Batch 2 may include FI-002 *or* FI-017, chosen and justified before any result is seen, never both and never the better of the two afterwards.

### FI-003 Signal freshness / event-time formation (medium, method)

- **Description:** Anomaly returns concentrate in the first month after the underlying information is released; forming portfolios on stale data understates predictability.
- **Source:** Bowles, Reed, Ringgenberg, and Thornock, "Anomaly Time", *Journal of Finance* 2024, <https://scholarsarchive.byu.edu/facpub/8579>.
- **Relevance:** V6 uses fundamentals up to 460 days old with equal weight on fresh and stale snapshots. A freshness-weighted version of existing quality/value/improvement signals is the natural design question for a V8. It is not a new factor and changing frozen V6/V7 is out of scope; record here so a future pre-registration can include it as one fixed alternative rather than a search.
- **Data:** Free; filing dates already in the pipeline. Turnover rises modestly.
- **2026-11-09 note:** The same authors' "Predicting Anomalies" (Bowles, Reed, Ringgenberg, and Thornock, August 2024 working paper, <https://jhfinance.web.unc.edu/wp-content/uploads/sites/12369/2024/11/Predicting-Anomalies.pdf>; 28 Compustat anomalies, 1990-2019) ask whether forecasting the next annual signal from year-to-date data can front-run the release. In 2005-2019 the gain was about zero (martingale forecast -13 bp, machine-learning forecast 7 bp over three months, against 110 bp under perfect foresight; no t-statistics or large-cap split in what was read). For this project the lesson is narrow: use fresh data as soon as it is filed (FI-003), but do not try to forecast unreleased fundamentals.

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
- **2026-11-02 update:** The Yang et al. abstract still could not be found. The older source is Chiu and Haight, "Gross Profit Surprises and Future Stock Returns" (October 2014 draft, <https://cba.lmu.edu/media/lmucollegeofbusinessadministration/undergrad/Gross%20Profit%20Surprises.pdf>): 1977-2010, seasonal change in quarterly gross profit scaled by market value, Carhart alpha 0.95% a month (t 8.49), incremental to earnings surprise. It reports no large-cap result and ends in 2010, so priority stays low.

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
- **2026-11-02 correction:** The two Chen-Welch survivors are "off-season momentum" (raw 54 bp, shrunk 5 bp a month) and "seasonal momentum (16yr+)" (raw 48 bp, shrunk 4 bp). The description above cites years 2-5 and 6-10; those horizons are not the 16yr+ survivor. A 16-year lookback needs prices from about 1996 for a 2012 signal, which this project's monthly dataset (first signal January 2012) probably cannot supply. Only the off-season variant is a candidate, and its lookback must be checked against available price history (not returns) before pre-registration.
- **2026-11-09 note:** Wang, "Is Return Seasonality Due to Risk or Mispricing? Evidence from Anomaly Seasonality", SSRN 6441120, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6441120> (unrefereed; read only through a QuantSeeker recap dated 2026-04-14), reports across 125 anomaly portfolios that a stock-level seasonality factor cuts seasonality-strategy alpha from 1.45% to 0.27% a month. Not a new idea; it says seasonal effects in other anomalies are largely the stock-level effect, so FI-010 should not be paired with any seasonal variant of another candidate. Priority unchanged.

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

### FI-013 Real-time investor alpha as an added acceptance diagnostic (medium, method)

- **Description:** Besides the factor-regression intercept, report the Sharpe gain an investor would have had combining the candidate with the market using weights estimated only from past data.
- **Rationale:** A regression alpha uses the full-sample optimal weight, which nobody knew in advance. If the optimal weight is unstable, the alpha is not attainable in real time.
- **Primary source:** Goncalves, Loudis, and Ogden (July 2026, working paper, unrefereed), <https://portal.northernfinanceassociation.org/viewp.php?n=2240218512>. 177 anomalies, 1926-2023.
- **Evidence:** Average post-publication factor alpha t 9.43; average real-time alpha t 0.38. Median optimal weight falls from 0.63 to 0.36 after publication, with rank correlation 0.39 between the two. 10.7% of real-time alphas have t > 1.64, against 48.0% for regression alphas. Combining anomalies can give positive real-time alphas, but only with shrinkage.
- **Relevance:** The project's acceptance test is exactly a regression intercept, so it may accept signals that were not usable in practice. V6's fixed equal-weight sleeves avoid estimating weights, which is in keeping with this result.
- **Data / overlap:** No new data. Not a factor. Applied only to candidates already being tested, so it adds no trial, but it must be fixed in the pre-registration before results are seen, and the paper's exact estimator should be read first. With only about 130 monthly observations in 2012-2022 it would be noisy, so use it as a reported diagnostic, not a new pass condition, unless Batch 2 decides otherwise in advance.
- **Turnover / cost:** Not applicable.

### FI-014 Operating leverage (low)

- **Description:** Operating costs (cost of goods sold plus SG&A) divided by total assets; higher values predict higher returns.
- **Rationale:** Fixed operating costs amplify exposure to demand shocks, so the premium is a risk story rather than mispricing.
- **Primary source:** Novy-Marx, "Operating Leverage", *Review of Finance* 2011. Post-2005 large-cap survival: Chen and Welch (2026), <https://arxiv.org/abs/2607.06502>, raw 38 bp, shrunk 3 bp a month.
- **Out-of-sample / decay:** Among the top-10 survivors, but shrunk return is trivial and no individual t-statistic was checked this week.
- **Data / point-in-time:** Free XBRL cost and asset tags from `filed + 1 day`. COGS tags vary by issuer and financials have no comparable measure, so coverage needs a spike.
- **Overlap:** Not named in V6 or V7, but the numerator relates to margins and asset turnover, so it may overlap V6 quality and FF5 RMW. A cross-sectional correlation check uses no returns and should come first.
- **Turnover / cost:** Low (slow-moving annual-style ratio).

### FI-015 R&D over market cap (low)

- **Description:** Trailing R&D expense divided by market value; higher values predict higher returns.
- **Rationale:** Expensing R&D understates the value of research-intensive firms, and investors may under-price the resulting intangibles.
- **Primary source:** Chan, Lakonishok, and Sougiannis, "The Stock Market Valuation of Research and Development Expenditures", *Journal of Finance* 2001. Post-2005 large-cap survival: Chen and Welch (2026), raw 41 bp, shrunk 3 bp a month.
- **Out-of-sample / decay:** Survives in the Chen-Welch table even though the intangibles category median is zero; the paper does not explain the difference.
- **Data / point-in-time:** Free XBRL R&D tag from `filed + 1 day`, usable from 2012 without the long capitalization history FI-004 needs.
- **Overlap:** Same economic bet as FI-004, in a simpler form, so test at most one. Many S&P 500 firms report no R&D, so it is effectively a tilt within technology and health care; any test should treat that sector concentration as a known risk.
- **Turnover / cost:** Low.

### FI-016 Short-volume ratio (low)

- **Description:** Daily FINRA-reported short sale volume divided by reported volume, as a level and relative to the stock's own norm; high values predict lower returns.
- **Rationale:** Short sellers are relatively informed, and the abnormal ratio may reveal short-horizon private information before it is priced.
- **Primary source:** HKUST thesis, 2019, sample 2010-2018, <https://lbezone.hkust.edu.hk/rse/?p=51474> (title and author not shown on the page). Not peer-reviewed. Abnormal-ratio predictability is reported as concentrated in large, liquid stocks, which is unusual and is the only reason this is listed.
- **Out-of-sample / decay:** None found. Sample ends 2018.
- **Data / point-in-time:** Free and published by 6 p.m. ET on trade date, with occasional "Updated" files, <https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files>. FINRA's page shows consolidated files from August 2018 only; the thesis uses data from 2010, so older files must exist somewhere, but that was not verified. Without them the 2012-2022 development period cannot be covered. Keep original and updated versions when archiving.
- **Overlap:** Same family as FI-006, with different data. Not in FF5+UMD, V6, or V7. The data cover only trades reported to FINRA facilities, and the ratio includes market-maker shorting, so it is noisy.
- **Turnover / cost:** Unmeasured. The daily ratio is volatile, but the source reports predictability fading slowly over up to a year, so a monthly version may be feasible. Assume medium-high until shown otherwise.

### FI-017 Announcement-window momentum (low)

- **Description:** Sum of a stock's abnormal returns over the three-day windows around its earnings announcements that fall inside the 12-1 month momentum formation window (typically three or four announcements).
- **Rationale:** Returns on earnings days are mostly firm-specific news, so their sum isolates the stock-specific part of momentum without estimating a factor model; investors under-react to that news, while the factor part of momentum is what crashes.
- **Primary source:** Gérard and Jehl, *Financial Analysts Journal* 2025 (see FI-002). Abstract only was read: US, Europe, and Japan, about 30 years, predicts returns, no long-run reversal. Long-short size, factor alphas, large-cap results, and turnover not yet verified.
- **Out-of-sample / decay:** Unknown. Close relatives are weak in large caps: post-earnings-announcement drift (FI-005; Martineau 2022) and plain momentum after 2005 (Chen and Welch 2026).
- **Data / point-in-time:** Free. EDGAR 8-K Item 2.02 acceptance timestamps give announcement dates; an announcement after the close must be assigned to the next trading day. 8-K Item 2.02 exists from August 2004, which covers the 2012-2022 development period. Prices already in the pipeline.
- **Overlap:** Subset of V6 momentum by construction and a cousin of FI-005; not a separate FF5+UMD factor. It is an alternative *definition* of the FI-002 idea, so it would replace FI-002 in a batch rather than add a trial.
- **Turnover / cost:** Medium (monthly re-formation, but the signal changes only when a new announcement enters or one drops out of the window). Lower than 12-1 momentum is plausible, unmeasured.
- **Why low:** abstract-only evidence and a poor base rate for momentum variants on large caps. Raise to medium only if the full text shows a large-cap or value-weighted result after 2005; even then it competes with FI-002 for one slot.

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

| Earnings date advances and delays (added 2026-11-02) | Johnson and So, "Time Will Tell", *JFQA* 2018, <https://ideas.repec.org/a/cup/jfinqa/v53y2018i06p2431-2464_00.html> | Needs the scheduling disclosure weeks ahead of the announcement, sourced from a paid calendar (Wall Street Horizon). Actual 8-K Item 2.02 dates reveal an advance only at the announcement, so a free proxy is a different signal the evidence does not cover. |
| Overnight vs intraday return continuation (added 2026-11-02) | Lou, Polk, and Skouras, "A Tug of War", *JFE* 2019, <https://personal.lse.ac.uk/polk/research/TugOfWar.pdf> | Overnight and intraday legs largely offset (3.47% against -3.02% a month in the value-weight overnight sort, 1993-2013), so capturing it needs daily open/close trading, incompatible with a monthly book. The authors say costs make it much less attractive. |
| Topic features from 10-K MD&A (FinTextSim) (added 2026-11-02) | Jehnen et al., *Frontiers in AI* 2026 | Classifies ROA direction, with no return or portfolio test; a learned model over filings, not a defined predictor. Noted under FI-001 as indirect support only. |
| GPT tone of 10-K risk factors (added 2026-11-02) | Magner, Henriquez, and Sanhueza, *Finance Research Letters* 2025, <https://ideas.repec.org/a/eee/finlet/v81y2025ics1544612325007317.html> | Predicts index returns, not the cross-section; LLM training data cannot be made point-in-time for a historical test. |
| "Pure news" residual tone (added 2026-11-09) | Didisheim, Kelly, Pourmohammadi, and Tian, "The Inefficient Pricing of News", NBER w35093, April 2026, <https://www.nber.org/papers/w35093> | Strong claim (larger and longer-lived than every anomaly in the Jensen-Kelly-Pedersen set, predicts up to 18 months), but it needs a commercial news archive (source not stated in the abstract; full text not read) and LLM/text models whose training data cannot be made point-in-time. A free analogue built on 8-K press-release text would be a different signal; revisit only after FI-001's text pipeline exists. |
| Daily Return Information factor (added 2026-11-09) | Cakici, Fieberg, Neszveda, Bianchi, and Zaremba, "A Unified Framework for Anomalies based on Daily Returns", January 2026 (summary: <https://larryswedroe.substack.com/p/unlocking-hidden-patterns>) | Elastic-net fit on the past month's daily returns: a fitted model, not a fixed predictor, so testing it means model search on the inspected sample; short-horizon signal with high turnover; no large-cap result found. |
| LLM-guided hypothesis discovery (added 2026-11-09) | Liu, Liu, Liu, and Mei, SSRN 6569258, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6569258> | 280 generated accounting ideas, 6-9 survive: a mined list that inherits the multiple-testing problem; any survivor would still need its own source and rationale. |
| Option-to-stock volume around earnings (added 2026-11-09) | Taheri Hosseinkhani, SSRN 6448100, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6448100> | Needs historical option volume (paid); coefficient reportedly flips sign in 2020-2024. |
| Factor Max (factor-timing signal) (added 2026-11-09) | Alpha Architect summary, April 2026, <https://alphaarchitect.com/factor-max/> | Times factor returns rather than ranking stocks; outside this backlog's scope. |
| Separate vs composite value-momentum books (added 2026-11-09) | Morales, SSRN 6255159, <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6255159> | Portfolio-construction claim, not a predictor (top 1,000 US stocks 2000-2026, separate sleeves +52 bp a year at matched risk, per a QuantSeeker recap; abstract not retrievable). Relevant to how V6 blends sleeves, but V6 is frozen; note for any V8 design, single-author and unrefereed. |

## Data Sources to Watch

- **EDGAR full-text filings** (free, acceptance timestamps): needed for FI-001.
- **EDGAR 8-K Item 2.02** (free): exact earnings-announcement dates, useful for FI-003 and FI-005 and for checking the `filed + 1 day` convention.
- **FINRA equity short interest** (free, twice monthly, ~7 business-day lag, rolling five-year API): archive forward for FI-006.
- **EDGAR Form 4** (free XML): FI-007. The SEC also publishes structured Insider Transactions Data Sets (Forms 3, 4, 5; <https://catalog-beta.data.gov/dataset/insider-transactions-data-sets>), which would avoid XML parsing; coverage dates and filing-date fields were not stated on that page and need confirming.
- **FINRA daily short sale volume** (free, same-day, consolidated files from August 2018 on FINRA's page): FI-016. Confirm where earlier files live.
- **Form SHO / Rule 13f-2 aggregate short positions:** not available. Reporting exemption extended to January 2, 2028, with first filings due February 14, 2028, while the SEC responds to a Fifth Circuit remand and may amend the rule (<https://www.morganlewis.com/pubs/2025/12/short-sale-reporting-on-form-sho-compliance-date-further-extended-to-2028>). Recheck in 2027.
- **SEC fails-to-deliver data** (free, since 2004): no strong large-cap evidence found yet; noted only.
- **SEC Form 13F data sets** (free, quarterly, July 2013 onward, <https://www.sec.gov/dera/data/form-13f>): FI-011. Confirm the acceptance-date field from the table definitions before any spike.
- **SEC Financial Statement and Notes data sets** (free, <https://www.sec.gov/data-research/financial-statement-notes-data-sets>): bulk XBRL including notes; a possible cross-check for the existing XBRL pipeline (single-source risk in ROADMAP Phase 1).
- **EDGAR log files**: not usable (gap 2017-2020, ended June 2025).
- **Open Source Asset Pricing** (Chen and Zimmermann, <https://www.openassetpricing.com/>): use its signal documentation to check whether a proposed definition matches the literature before pre-registering. Its portfolios are CRSP/Compustat-based and are reference only, not project inputs.

## Changelog

### 2026-11-09

- Fourth scouting run, 17 web searches plus page reads. Checked `reports/factor_lab/trial_registry.csv` on `main`: unchanged at five candidates, so the Batch 2 thresholds recorded on 2026-11-02 still apply. No other research changes on `main` since the last run (forward-record updates only).
- Added FI-017 announcement-window momentum (low), from Gérard and Jehl (FAJ 2025). It is an alternative definition of FI-002's firm-specific momentum, so a one-definition rule now applies: at most one of FI-002 and FI-017 in Batch 2, chosen before results.
- Notes added to FI-002 (Gérard and Jehl), FI-003 (Bowles et al. "Predicting Anomalies": front-running unreleased fundamentals earned about nothing after 2005), and FI-010 (Wang: anomaly seasonality is mostly stock-level seasonality). No priority changes.
- Rejected six (pure-news text residual, daily-return elastic-net factor, LLM-generated hypotheses, option-to-stock volume, factor timing, separate-vs-composite value-momentum).
- Could not read: the full text of NBER w35093 and the FAJ paper (paywalled or blocked), the SSRN 6255159 abstract. Figures for those come from abstracts or secondary recaps and are marked as such.
- Recommendation for Batch 2 unchanged: FI-001 first; FI-002 (or FI-017, not both) only if the batch has room; FI-009 only under its forking-path conditions; FI-013 as a reported diagnostic. Nothing new this week is strong enough to add.

### 2026-11-02

- Third scouting run, 17 searches. No new paper this week offers a strong new predictor for large caps.
- Read `reports/factor_lab/trial_registry.csv` on `main`: still five candidates. With a Bonferroni one-sided 5% test on the cumulative count, the threshold for Batch 2 would be t >= 2.45 with two candidates (seven total) or t >= 2.50 with three (eight total), assuming the existing formula is carried forward.
- Added FI-013 real-time investor alpha (medium, method), FI-014 operating leverage (low), FI-015 R&D over market cap (low), FI-016 short-volume ratio (low). FI-014 and FI-015 come from re-reading the Chen-Welch survivor table, which the last run did not fully record; they are not new research.
- Base-rate section: added Loughran (2025) and Goncalves, Loudis, and Ogden (2026), and a note on the Chen-Welch category median versus individual survivors.
- Corrected FI-010: the 16yr+ survivor is outside this project's likely history; only the off-season variant remains a candidate. FI-002: noted conflicting turnover evidence. FI-001 and FI-008: no change in priority.
- Rejected four ideas (earnings date revisions, overnight/intraday continuation, FinTextSim topics, GPT risk-factor tone). Added Form SHO delay, insider data sets, and FINRA daily short volume to data sources.
- Recommendation for Batch 2 unchanged: FI-001 first; FI-002 only if the batch has room; FI-009 only with the independent rationale already required. New this week: fix FI-013 as a reported diagnostic in the pre-registration. No new factor qualifies.

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
