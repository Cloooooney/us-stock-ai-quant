from __future__ import annotations

import pandas as pd
from lightgbm import LGBMRegressor

from models.walk_forward import Config, FEATURES, metrics

RANK_FEATURES = [f"rank_{x}" for x in FEATURES]


def prepare_cross_section(dataset: pd.DataFrame) -> pd.DataFrame:
    d = dataset.copy()
    for col in FEATURES:
        d[f"rank_{col}"] = d.groupby("date")[col].rank(pct=True)
    d["target_relative"] = d["target_return"] - d.groupby("date")["target_return"].transform("mean")
    return d


def fit_predict_relative(dataset: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    d = prepare_cross_section(dataset)
    outputs, model, last_fit = [], None, None
    dates = sorted(d.loc[d["date"] >= pd.Timestamp(cfg.first_prediction), "date"].unique())
    for raw_date in dates:
        date = pd.Timestamp(raw_date)
        train = d.loc[(d["date"] >= date - pd.DateOffset(years=cfg.train_years)) &
                      (d["date"] < date) & (d["label_known_date"] <= date)]
        test = d.loc[d["date"].eq(date)].copy()
        if len(train) < 5000 or test.empty:
            continue
        fit_period = (date.year, (date.month - 1) // 3)
        if model is None or fit_period != last_fit:
            model = LGBMRegressor(
                objective="regression_l1", n_estimators=180, learning_rate=.03,
                num_leaves=11, max_depth=4, min_child_samples=120,
                colsample_bytree=.8, reg_alpha=.5, reg_lambda=2,
                random_state=cfg.seed, n_jobs=-1, verbosity=-1,
            )
            model.fit(train[RANK_FEATURES], train["target_relative"])
            last_fit = fit_period
        test["prediction"] = model.predict(test[RANK_FEATURES])
        outputs.append(test)
    return pd.concat(outputs, ignore_index=True)


def buffered_portfolio(pred: pd.DataFrame, cfg: Config, buffer_multiple: float = 2.0):
    rows, holdings, previous = [], [], set()
    buffer_rank = max(cfg.top_n, round(cfg.top_n * buffer_multiple))
    for date, group in pred.groupby("date", sort=True):
        g = group.sort_values("prediction", ascending=False).copy()
        g["model_rank"] = range(1, len(g) + 1)
        eligible_old = [t for t in previous if t in set(g.loc[g["model_rank"] <= buffer_rank, "ticker"])]
        keep = set(eligible_old[:cfg.top_n])
        for ticker in g["ticker"]:
            if len(keep) >= cfg.top_n:
                break
            keep.add(ticker)
        chosen = g.loc[g["ticker"].isin(keep)].copy()
        current = set(chosen["ticker"])
        turnover = 1.0 if not previous else 1 - len(current & previous) / cfg.top_n
        gross = chosen["target_return"].mean()
        rows.append({"date": date, "execution_date": chosen["execution_date"].min(),
                     "gross_return": gross, "net_return": gross - turnover * cfg.cost_bps / 10_000,
                     "turnover": turnover, "n": len(chosen)})
        holdings.append(chosen[["date", "execution_date", "ticker", "model_rank", "prediction", "target_return"]])
        previous = current
    return pd.DataFrame(rows), pd.concat(holdings, ignore_index=True)


def select_buffer_on_validation(pred: pd.DataFrame, cfg: Config, candidates=(1.0, 1.5, 2.0, 3.0)):
    rows = []
    for b in candidates:
        ret, _ = buffered_portfolio(pred, cfg, b)
        validation = ret.loc[ret["date"].between("2018-01-01", "2022-12-31")]
        rows.append({"buffer_multiple": b, **metrics(validation["net_return"]),
                     "avg_turnover": validation["turnover"].mean()})
    table = pd.DataFrame(rows)
    # A predeclared risk-adjusted selection rule; test data is never consulted.
    chosen = float(table.sort_values(["sharpe_0rf", "max_drawdown"], ascending=False).iloc[0]["buffer_multiple"])
    return chosen, table
