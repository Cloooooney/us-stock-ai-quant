# V4 Fundamental Model Card (Frozen October 5, 2026)

## Status

**Research gate passed; trading gate failed.** The fundamental signal was more stable than the price Ridge model during validation, but it did not beat SPY in the final test and must not submit paper or live orders.

## Overfitting Controls

1. Data come from SEC Company Facts and become available no earlier than `filed + 1 calendar day`.
2. The universe uses historical point-in-time S&P 500 membership. Stocks with unmatched or missing fields remain eligible, receive a neutral cross-sectional rank of 0.5, and do not expose a missingness flag to the model.
3. Six features were fixed before the backtest: revenue growth, net margin, operating cash quality, ROA, liabilities to assets, and capital expenditure to revenue.
4. The model is a linear Ridge regression with `alpha=100`; tree depth, learning rate, and large feature combinations are not searched.
5. The 2018-2022 period is used only to select among three candidates. The 2023-2026 period is used only for final diagnosis.
6. The model selects 20 stocks monthly, executes at the next open, assumes 10 bps costs, and trains only on labels completed before the training date.
7. The 2023-2026 period has already been inspected and can no longer be treated as an independent test set. Genuinely unseen evidence begins after the freeze date.

## Results

| Period | Strategy | Annual return | Volatility | Sharpe (0% risk-free) | Maximum drawdown | Average monthly turnover |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2018-2022 | Fundamental Ridge | 11.77% | 21.73% | 0.54 | -23.98% | 16.42% |
| 2023-2026 | Fundamental Ridge | 9.22% | 15.23% | 0.61 | -9.35% | 16.25% |
| 2023-2026 | Dynamic equal weight | 11.13% | 12.68% | 0.88 | -11.42% | N/A |
| 2023-2026 | SPY | 20.77% | 12.04% | 1.73 | -7.80% | N/A |

## Coverage and Limitations

- Revenue-growth coverage was approximately 74.6% at year-end 2018, 91.9% at year-end 2022, and 96.6% in 2026.
- Liability and capital-expenditure coverage is lower; missing values receive neutral ranks.
- Annual filings expire after 550 days and revert to neutral ranks so stale facts are not carried indefinitely.
- The current SEC ticker-to-CIK table does not perfectly cover historical delisted companies, leaving residual survivorship bias.
- Banks, insurers, and general industrial companies have different financial structures. A single set of ratios has limited cross-industry comparability. Sector-neutral treatment is a logical next step, but it cannot be selected using the already inspected test period.

## Post-Freeze Rule

V4 is tracked only as a shadow model. Any new feature, weight, sector treatment, or model change must become a new version and begin evaluation on new forward data. The 2023-2026 results cannot be reused for retrospective selection.
