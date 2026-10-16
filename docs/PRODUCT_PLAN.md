# Product Plan

Written October 16, 2026. The research found no model that reliably beats a low-cost index (see `docs/ROADMAP.md` and `reports/factor_attribution/CONCLUSION.md`). The product is built around what the evidence does support: most investors lose money through behaviour, costs, concentration, and strategies that only look good in hindsight. A tool that tells the truth about those helps people keep money they would otherwise lose, and the frozen models remain a transparent, optional extra.

## Two Tracks

| Track | Who | What | Boundary |
| --- | --- | --- | --- |
| Analysis app | Other people (and the owner) | Explains a portfolio or strategy: history, risk, concentration, factor exposure, and whether a simple ETF would have done as well. Shows the frozen models' forward record honestly. | Analysis and education only. No personalized buy or sell instructions and no access to anyone's money. |
| Automated trading | The owner only | Places orders for the owner's own brokerage account through a broker API. | Paper trading first. Live orders only for a model that passes the release gate in `docs/ROADMAP.md`, at a small allocation, with a hard stop. |

Giving other people specific trade recommendations or trading on their behalf can require investment-adviser registration in the United States. Before either, get advice from a securities lawyer or partner with a registered platform.

## Analysis App (`app/`)

Runs locally first (`start_app.bat`), bilingual (Chinese and English).

### Version 1

1. **Portfolio checkup.** Input tickers and weights. Output: monthly-rebalanced historical return, volatility, Sharpe ratio, maximum drawdown, and beta against SPY and RSP; concentration (largest position, top three, effective number of holdings); Fama-French five-factor plus momentum attribution; and plain-language findings in both languages.
2. **Model forward record.** Reads the V5 and V6 ledgers: latest holdings, each holding period against equal weight, SPY, and the benchmark ETFs, and progress toward the 6- and 24-month gates.
3. **Research history.** V1-V6 backtest summaries and attribution conclusions, including the negative results.

### Later

- Strategy checkup: describe a stock-selection rule and test it point in time with the existing backtest engine.
- Cost and tax drag estimates for a given trading frequency.
- Public deployment once the local version is stable.

## Automated Trading for the Owner

1. Open an Alpaca paper-trading account and store keys in `.env` (ignored by Git).
2. Connect the forward tracker to the paper account: submit the month's target holdings at the next open, record broker fills next to the simulated fills, and reconcile them.
3. Run at least three months of paper trading to measure slippage, rejected orders, and outages.
4. Live orders only after the release gate, sized as a small fraction of investable assets, with a kill switch on a 10% drawdown relative to RSP.

The owner's core holdings stay in diversified low-cost index funds throughout.
