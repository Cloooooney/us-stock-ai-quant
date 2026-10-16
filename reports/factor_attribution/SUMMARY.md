# Factor Attribution

Fama-French five factors plus momentum, Newey-West t-statistics. `absolute` regresses return minus the risk-free rate; `active` regresses return minus the point-in-time equal-weight universe. |t| below 2 means the intercept is not distinguishable from zero.

## Full out-of-sample period (2018 onward)

| Strategy | Regression | Alpha / yr | Alpha t | R² | Mkt | SMB | HML | RMW | CMA | Mom |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1_lightgbm_price | absolute | +0.78% | +0.16 | 0.77 | +1.25 | +0.24 | +0.39 | -0.47 | -0.12 | -0.61 |
| v1_lightgbm_price | active_vs_equal_weight | +2.36% | +0.54 | 0.43 | +0.26 | +0.05 | +0.16 | -0.62 | -0.20 | -0.54 |
| v2_cross_sectional | absolute | -5.83% | -1.64 | 0.73 | +1.22 | +0.22 | +0.54 | +0.02 | -0.16 | +0.02 |
| v2_cross_sectional | active_vs_equal_weight | -4.26% | -1.35 | 0.16 | +0.24 | +0.02 | +0.30 | -0.13 | -0.24 | +0.09 |
| v3_risk_control | absolute | +0.75% | +0.15 | 0.69 | +0.91 | +0.28 | +0.16 | -0.48 | +0.04 | -0.51 |
| v3_risk_control | active_vs_equal_weight | +2.32% | +0.48 | 0.26 | -0.08 | +0.09 | -0.08 | -0.63 | -0.04 | -0.44 |
| v4_fundamental_ridge | absolute | -2.31% | -0.86 | 0.83 | +1.01 | +0.14 | +0.07 | +0.33 | -0.07 | +0.09 |
| v4_fundamental_ridge | active_vs_equal_weight | -0.73% | -0.37 | 0.31 | +0.02 | -0.06 | -0.17 | +0.18 | -0.15 | +0.16 |
| point_in_time_equal_weight | absolute | -1.58% | -1.19 | 0.94 | +0.98 | +0.19 | +0.24 | +0.15 | +0.08 | -0.07 |
| spy | absolute | -0.23% | -0.38 | 0.97 | +1.01 | -0.11 | +0.09 | +0.07 | -0.05 | +0.01 |

## Reading

No strategy shows an intercept with |t| ≥ 2 in the full out-of-sample period: after known factor exposures, there is no statistically detectable alpha.

Factor betas with |t| ≥ 2 show which known exposures explain the returns. If a strategy's return is mostly explained by factors that a low-cost ETF already provides, the ETF is the cheaper implementation.

## Versus benchmark ETFs (2018 onward)

Mean excess return per year over each ETF across the same holding periods. V4 must beat RSP and the closest factor ETF to justify its complexity.

| Strategy | ETF | Excess / yr | t | Hit rate | Months |
| --- | --- | ---: | ---: | ---: | ---: |
| v1_lightgbm_price | MTUM | +0.36% | +0.05 | 46% | 103 |
| v1_lightgbm_price | QUAL | +1.10% | +0.16 | 52% | 103 |
| v1_lightgbm_price | RSP | +2.94% | +0.49 | 53% | 103 |
| v1_lightgbm_price | USMV | +5.04% | +0.66 | 51% | 103 |
| v1_lightgbm_price | VLUE | +0.25% | +0.04 | 54% | 103 |
| v2_cross_sectional | MTUM | -3.93% | -0.73 | 46% | 103 |
| v2_cross_sectional | QUAL | -3.19% | -0.76 | 48% | 103 |
| v2_cross_sectional | RSP | -1.35% | -0.44 | 51% | 103 |
| v2_cross_sectional | USMV | +0.75% | +0.16 | 47% | 103 |
| v2_cross_sectional | VLUE | -4.04% | -0.80 | 48% | 103 |
| v3_risk_control | MTUM | -3.45% | -0.46 | 40% | 103 |
| v3_risk_control | QUAL | -2.71% | -0.41 | 47% | 103 |
| v3_risk_control | RSP | -0.87% | -0.15 | 48% | 103 |
| v3_risk_control | USMV | +1.23% | +0.17 | 50% | 103 |
| v3_risk_control | VLUE | -3.56% | -0.56 | 50% | 103 |
| v4_fundamental_ridge | MTUM | -1.71% | -0.47 | 55% | 103 |
| v4_fundamental_ridge | QUAL | -0.97% | -0.42 | 52% | 103 |
| v4_fundamental_ridge | RSP | +0.87% | +0.34 | 53% | 103 |
| v4_fundamental_ridge | USMV | +2.97% | +1.12 | 52% | 103 |
| v4_fundamental_ridge | VLUE | -1.82% | -0.34 | 54% | 103 |
| point_in_time_equal_weight | MTUM | -2.21% | -0.54 | 46% | 103 |
| point_in_time_equal_weight | QUAL | -1.47% | -0.64 | 50% | 103 |
| point_in_time_equal_weight | RSP | +0.37% | +1.82 | 65% | 103 |
| point_in_time_equal_weight | USMV | +2.47% | +0.89 | 51% | 103 |
| point_in_time_equal_weight | VLUE | -2.32% | -0.60 | 50% | 103 |
| spy | MTUM | +0.06% | +0.02 | 45% | 103 |
| spy | QUAL | +0.80% | +0.78 | 49% | 103 |
| spy | RSP | +2.64% | +1.27 | 53% | 103 |
| spy | USMV | +4.74% | +1.77 | 58% | 103 |
| spy | VLUE | -0.05% | -0.01 | 50% | 103 |
