from __future__ import annotations

import numpy as np
import pandas as pd

from models.walk_forward import Config, portfolio_returns


FUNDAMENTAL_VALUE_COLUMNS = [
    "ttm_revenue",
    "ttm_net_income",
    "ttm_operating_cash_flow",
    "ttm_capex",
    "revenue_growth",
    "net_margin",
    "cash_quality",
    "roa",
    "liabilities_to_assets",
    "capex_to_revenue",
    "free_cash_flow_margin",
    "accruals_to_assets",
    "weighted_average_shares",
    "shares_outstanding",
]
FUNDAMENTAL_METADATA_COLUMNS = ["accession", "form", "available_date", "filed", "fiscal_end"]

MOMENTUM_FACTORS = {"mom_126": 1, "mom_252": 1}
QUALITY_FACTORS = {
    "revenue_growth": 1,
    "net_margin": 1,
    "roa": 1,
    "cash_quality": 1,
    "free_cash_flow_margin": 1,
    "accruals_to_assets": -1,
    "liabilities_to_assets": -1,
}
VALUE_FACTORS = {"sales_yield": 1, "earnings_yield": 1, "fcf_yield": 1}
SLEEVE_COLUMNS = {
    "momentum": "momentum_score",
    "quality": "quality_score",
    "value": "value_score",
    "blend": "v6_score",
}


def merge_quarterly_fundamentals(
    dataset: pd.DataFrame,
    fundamentals: pd.DataFrame,
    max_age_days: int = 460,
) -> pd.DataFrame:
    if dataset.empty:
        return dataset.copy()
    left_all = dataset.copy()
    left_all["date"] = pd.to_datetime(left_all["date"])
    right_all = fundamentals.copy()
    for column in ("available_date", "filed", "fiscal_end"):
        right_all[column] = pd.to_datetime(right_all[column])

    right_columns = [*FUNDAMENTAL_METADATA_COLUMNS, *FUNDAMENTAL_VALUE_COLUMNS]
    for column in right_columns:
        if column not in right_all:
            right_all[column] = np.nan
    parts: list[pd.DataFrame] = []
    for ticker, left in left_all.groupby("ticker", sort=False):
        left = left.sort_values("date")
        right = right_all.loc[right_all["ticker"].eq(ticker), right_columns]
        right = right.sort_values(["available_date", "fiscal_end", "accession"])
        if right.empty:
            joined = left.copy()
            for column in right_columns:
                if column in {"available_date", "filed", "fiscal_end"}:
                    joined[column] = pd.NaT
                elif column in {"accession", "form"}:
                    joined[column] = None
                else:
                    joined[column] = np.nan
        else:
            joined = pd.merge_asof(
                left,
                right,
                left_on="date",
                right_on="available_date",
                direction="backward",
            )
        parts.append(joined)

    output = pd.concat(parts, ignore_index=True)
    known = output["available_date"].notna()
    if not (output.loc[known, "available_date"] <= output.loc[known, "date"]).all():
        raise AssertionError("future SEC filing entered a signal row")
    output["fundamental_age_days"] = (output["date"] - output["filed"]).dt.days
    stale = output["fundamental_age_days"] > max_age_days
    output.loc[stale, FUNDAMENTAL_VALUE_COLUMNS] = np.nan
    return output.sort_values(["date", "ticker"]).reset_index(drop=True)


def attach_valuation_features(data: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    price_rows = prices[["date", "ticker", "close"]].copy()
    price_rows["date"] = pd.to_datetime(price_rows["date"])
    price_rows = price_rows.drop_duplicates(["date", "ticker"], keep="last")
    price_rows = price_rows.rename(columns={"close": "signal_close"})
    output = data.copy()
    output["date"] = pd.to_datetime(output["date"])
    output = output.merge(price_rows, on=["date", "ticker"], how="left", validate="many_to_one")

    if "weighted_average_shares" not in output:
        output["weighted_average_shares"] = np.nan
    if "shares_outstanding" not in output:
        output["shares_outstanding"] = np.nan
    output["valuation_shares"] = output["weighted_average_shares"].combine_first(output["shares_outstanding"])
    both_positive = (output["weighted_average_shares"] > 0) & (output["shares_outstanding"] > 0)
    share_ratio = output["weighted_average_shares"] / output["shares_outstanding"]
    unit_mismatch = both_positive & ((share_ratio > 100) | (share_ratio < 0.01))
    output.loc[unit_mismatch, "valuation_shares"] = output.loc[
        unit_mismatch, ["weighted_average_shares", "shares_outstanding"]
    ].max(axis=1)
    output["share_split_factor"] = 1.0
    if "stock_splits" in prices and "filed" in output:
        filed = pd.to_datetime(output["filed"])
        split_rows = prices.loc[
            prices["stock_splits"].notna()
            & ~prices["stock_splits"].isin([0.0, 1.0]),
            ["ticker", "date", "stock_splits"],
        ].copy()
        split_rows["date"] = pd.to_datetime(split_rows["date"])
        for ticker, events in split_rows.groupby("ticker"):
            indices = output.index[output["ticker"].eq(ticker) & filed.notna()]
            if len(indices) == 0:
                continue
            events = events.sort_values("date")
            event_dates = events["date"].to_numpy(dtype="datetime64[ns]")
            ratios = events["stock_splits"].to_numpy(dtype=float)
            suffix_products = np.cumprod(ratios[::-1])[::-1]
            positions = np.searchsorted(
                event_dates,
                filed.loc[indices].to_numpy(dtype="datetime64[ns]"),
                side="right",
            )
            factors = np.ones(len(indices), dtype=float)
            has_future_split = positions < len(suffix_products)
            factors[has_future_split] = suffix_products[positions[has_future_split]]
            output.loc[indices, "share_split_factor"] = factors
    output["split_adjusted_shares"] = output["valuation_shares"] * output["share_split_factor"]

    market_cap = output["signal_close"] * output["split_adjusted_shares"]
    output["market_cap"] = market_cap.where(
        np.isfinite(market_cap)
        & (output["signal_close"] > 0)
        & (output["split_adjusted_shares"] > 0)
    )
    output["sales_yield"] = output["ttm_revenue"] / output["market_cap"]
    output["earnings_yield"] = output["ttm_net_income"] / output["market_cap"]
    output["fcf_yield"] = (
        output["ttm_operating_cash_flow"] - output["ttm_capex"]
    ) / output["market_cap"]
    for column in ("sales_yield", "earnings_yield", "fcf_yield"):
        output[column] = output[column].replace([np.inf, -np.inf], np.nan)
    return output


def _neutral_percentile(series: pd.Series, direction: int) -> pd.Series:
    result = pd.Series(0.5, index=series.index, dtype=float)
    valid = series.dropna()
    if len(valid) <= 1:
        return result
    values = valid if direction > 0 else -valid
    result.loc[valid.index] = (values.rank(method="average") - 1) / (len(valid) - 1)
    return result


def _rank_factors(data: pd.DataFrame, factors: dict[str, int]) -> tuple[pd.DataFrame, list[str]]:
    output = data.copy()
    rank_columns = []
    for feature, direction in factors.items():
        if feature not in output:
            output[feature] = np.nan
        rank_column = f"rank_{feature}"
        output[rank_column] = output.groupby("date", group_keys=False)[feature].transform(
            lambda series: _neutral_percentile(series, direction)
        )
        rank_columns.append(rank_column)
    return output, rank_columns


def score_factors(data: pd.DataFrame) -> pd.DataFrame:
    output = data.copy()
    sleeve_specs = (
        ("momentum_score", MOMENTUM_FACTORS),
        ("quality_score", QUALITY_FACTORS),
        ("value_score", VALUE_FACTORS),
    )
    for score_column, factors in sleeve_specs:
        output, rank_columns = _rank_factors(output, factors)
        output[score_column] = output[rank_columns].mean(axis=1)
    output["v6_score"] = output[["momentum_score", "quality_score", "value_score"]].mean(axis=1)
    output["prediction"] = output["v6_score"]
    return output


def run_v6_variant(
    data: pd.DataFrame,
    cfg: Config,
    variant: str = "blend",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if variant not in SLEEVE_COLUMNS:
        raise ValueError(f"unknown V6 variant: {variant}")
    scored = score_factors(data)
    scored["prediction"] = scored[SLEEVE_COLUMNS[variant]]
    scored = scored.sort_values(
        ["date", "prediction", "ticker"], ascending=[True, False, True], kind="mergesort"
    ).reset_index(drop=True)
    returns, holdings = portfolio_returns(scored, cfg)
    return scored, returns, holdings


def select_v6_holdings(scored: pd.DataFrame, signal_date: pd.Timestamp, top_n: int = 20) -> pd.DataFrame:
    """Top ``top_n`` names by the frozen blend on one date, with the same
    ordering and tie-break as the backtest (score descending, then ticker)."""
    current = scored.loc[pd.to_datetime(scored["date"]).eq(signal_date)].copy()
    current["prediction"] = current[SLEEVE_COLUMNS["blend"]]
    current = current.sort_values(["prediction", "ticker"], ascending=[False, True], kind="mergesort")
    selected = current.head(top_n).copy()
    if len(selected) != top_n:
        raise ValueError(f"V6 selection produced {len(selected)} holdings instead of {top_n}")
    selected["portfolio_rank"] = range(1, top_n + 1)
    return selected


def build_v6_signal(root, top_n: int = 20) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Frozen V6 holdings for the latest completed month-end, the scored
    point-in-time universe, and prices. No parameters are fitted."""
    from pathlib import Path

    from models.walk_forward import build_latest_signal_snapshot, load_source

    root = Path(root)
    prices, intervals, _ = load_source(root)
    latest = build_latest_signal_snapshot(prices, intervals)
    fundamentals = pd.read_parquet(root / "data/sec/quarterly_fundamentals.parquet")
    valued = attach_valuation_features(merge_quarterly_fundamentals(latest, fundamentals), prices)
    scored = score_factors(valued)
    signal_date = pd.Timestamp(latest["date"].max())
    selected = select_v6_holdings(scored, signal_date, top_n)
    universe = sorted(scored.loc[scored["date"].eq(signal_date), "ticker"].astype(str).unique())
    return selected, universe, prices
