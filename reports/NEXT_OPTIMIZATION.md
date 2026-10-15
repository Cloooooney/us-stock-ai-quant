# Next Stage: Fundamental Data Layer

The price model completed three evaluation rounds and failed. The next stage should add independent information rather than more complicated AI.

Plan:

1. Retrieve historical financial fields from SEC Company Facts and retain each fact's `filed` date.
2. Delay every quarterly fact by at least one trading session before it can enter a feature, preventing financial-statement look-ahead.
3. Build features for earnings quality, gross-margin changes, leverage, free-cash-flow yield, and valuation proxies.
4. Evaluate each factor's out-of-sample Rank IC independently before allowing it into the model.
5. Select features and rules only on 2018-2022, reserving 2023-2026 for the final test.

Data acceptance requires passing coverage, outlier, duplicate-filing, amended-filing, and disclosure-date checks.
