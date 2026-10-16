"""Portfolio checkup: pure analysis functions with no UI or network code.

Everything here works on monthly returns. A portfolio is rebalanced to its
target weights every month, which is the simplest assumption that does not
reward or punish the user for drift they did not choose.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

LARGE_POSITION = 0.25
FEW_HOLDINGS = 5
HIGH_BETA, LOW_BETA = 1.2, 0.8
DEEP_DRAWDOWN = -0.35
SHORT_HISTORY_MONTHS = 36
MIN_ATTRIBUTION_MONTHS = 36
FACTOR_NAMES = {"mkt_rf": "market", "smb": "size", "hml": "value", "rmw": "profitability",
                "cma": "investment", "mom": "momentum"}


@dataclass
class Finding:
    key: str            # template key in app.i18n
    level: str          # "warning", "info", or "good"
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def clean_ticker(raw) -> str:
    """Upper-case, trim, and use Yahoo's share-class format (BRK.B -> BRK-B)."""
    return str(raw).strip().upper().replace(".", "-")


def normalize_weights(holdings: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Clean a ticker/weight table into weights summing to 1, plus problems found.

    Weights may be entered as percentages or fractions; only their ratios matter.
    Duplicate tickers are combined.
    """
    problems: list[str] = []
    frame = holdings.loc[:, ["ticker", "weight"]].copy()
    frame["ticker"] = frame["ticker"].fillna("").map(clean_ticker)
    frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce")
    frame = frame.loc[frame["ticker"].ne("") & frame["ticker"].ne("NAN")]
    bad = frame.loc[frame["weight"].isna() | (frame["weight"] <= 0), "ticker"].tolist()
    if bad:
        problems.append("invalid_weight:" + ",".join(bad))
    frame = frame.loc[frame["weight"] > 0]
    if frame.empty:
        raise ValueError("no holdings with a positive weight")
    weights = frame.groupby("ticker")["weight"].sum()
    if frame["ticker"].duplicated().any():
        problems.append("duplicates_combined")
    return weights / weights.sum(), problems


# ---------------------------------------------------------------------------
# Returns and metrics
# ---------------------------------------------------------------------------

def monthly_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calendar-month returns from a daily adjusted-close table (dates by tickers)."""
    daily = prices.sort_index()
    daily.index = pd.to_datetime(daily.index)
    month_end = daily.groupby(daily.index.to_period("M")).last()
    last_date = daily.index.max()
    if (last_date.to_period("M").end_time.normalize() - last_date).days > 3:
        month_end = month_end.iloc[:-1]  # the current month is not finished
    returns = month_end.pct_change(fill_method=None)
    return returns.iloc[1:]  # the first month has no prior close


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> tuple[pd.Series, dict]:
    """Monthly-rebalanced portfolio return over the months every holding has data."""
    missing = sorted(set(weights.index).difference(returns.columns))
    if missing:
        raise ValueError(f"no price history for: {', '.join(missing)}")
    held = returns[list(weights.index)]
    starts = held.apply(lambda col: col.first_valid_index())
    complete = held.dropna()
    if complete.empty:
        raise ValueError("the holdings share no common history")
    series = complete.mul(weights, axis=1).sum(axis=1)
    limiting = starts.idxmax()
    info = {"first_month": str(complete.index.min()), "last_month": str(complete.index.max()),
            "months": int(len(complete)), "limited_by": limiting if starts.nunique() > 1 else None}
    return series, info


def metrics(returns: pd.Series) -> dict:
    r = returns.dropna()
    if r.empty:
        return {"months": 0}
    wealth = (1 + r).cumprod()
    years = len(r) / 12
    annual = wealth.iloc[-1] ** (1 / years) - 1
    vol = r.std(ddof=1) * math.sqrt(12) if len(r) > 1 else float("nan")
    return {"months": int(len(r)), "annual_return": float(annual), "annual_volatility": float(vol),
            "sharpe_0rf": float(annual / vol) if vol and np.isfinite(vol) else float("nan"),
            "max_drawdown": float((wealth / wealth.cummax() - 1).min()),
            "total_return": float(wealth.iloc[-1] - 1),
            "best_month": float(r.max()), "worst_month": float(r.min())}


def relative_to(portfolio: pd.Series, benchmark: pd.Series) -> dict:
    joined = pd.concat([portfolio.rename("p"), benchmark.rename("b")], axis=1, join="inner").dropna()
    if len(joined) < 12:
        return {"months": int(len(joined))}
    excess = joined["p"] - joined["b"]
    return {"months": int(len(joined)),
            "beta": float(np.cov(joined["p"], joined["b"])[0, 1] / joined["b"].var(ddof=1)),
            "correlation": float(joined["p"].corr(joined["b"])),
            "tracking_error": float(excess.std(ddof=1) * math.sqrt(12)),
            "annual_return_gap": metrics(joined["p"])["annual_return"] - metrics(joined["b"])["annual_return"],
            "months_ahead": float((excess > 0).mean())}


def concentration(weights: pd.Series) -> dict:
    ordered = weights.sort_values(ascending=False)
    return {"holdings": int(len(ordered)), "largest_ticker": str(ordered.index[0]),
            "largest_weight": float(ordered.iloc[0]), "top3_weight": float(ordered.head(3).sum()),
            "effective_holdings": float(1 / (ordered ** 2).sum())}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def significant_tilts(attribution: dict) -> list[dict]:
    tilts = []
    for factor, name in FACTOR_NAMES.items():
        if factor == "mkt_rf":
            continue
        beta, t = attribution.get(f"beta_{factor}"), attribution.get(f"t_{factor}")
        if beta is not None and t is not None and abs(t) >= 2:
            tilts.append({"factor": name, "beta": beta, "direction": "positive" if beta > 0 else "negative"})
    return tilts


def findings(stats: dict, conc: dict, vs_spy: dict, spy_stats: dict, attribution: dict | None,
             info: dict) -> list[Finding]:
    out: list[Finding] = []
    if info["months"] < SHORT_HISTORY_MONTHS:
        out.append(Finding("short_history", "warning", {"months": info["months"]}))
    if info.get("limited_by"):
        out.append(Finding("limited_by", "info", {"ticker": info["limited_by"], "first": info["first_month"]}))
    if conc["largest_weight"] > LARGE_POSITION:
        out.append(Finding("large_position", "warning",
                           {"ticker": conc["largest_ticker"], "weight": conc["largest_weight"]}))
    if conc["effective_holdings"] < FEW_HOLDINGS:
        out.append(Finding("few_holdings", "warning", {"n": conc["effective_holdings"]}))
    beta = vs_spy.get("beta")
    if beta is not None and beta > HIGH_BETA:
        out.append(Finding("high_beta", "warning", {"beta": beta}))
    elif beta is not None and beta < LOW_BETA:
        out.append(Finding("low_beta", "info", {"beta": beta}))
    if stats.get("max_drawdown", 0) < DEEP_DRAWDOWN:
        out.append(Finding("deep_drawdown", "warning", {"drawdown": stats["max_drawdown"]}))
    if spy_stats.get("months"):
        worse_return = stats["annual_return"] < spy_stats["annual_return"]
        worse_sharpe = stats["sharpe_0rf"] < spy_stats["sharpe_0rf"]
        if worse_return and worse_sharpe:
            out.append(Finding("index_was_better", "warning",
                               {"gap": stats["annual_return"] - spy_stats["annual_return"]}))
        elif not worse_return and not worse_sharpe:
            out.append(Finding("beat_index_history", "good",
                               {"gap": stats["annual_return"] - spy_stats["annual_return"]}))
        else:
            out.append(Finding("mixed_vs_index", "info", {}))
    if attribution is None:
        out.append(Finding("attribution_skipped", "info", {"months": MIN_ATTRIBUTION_MONTHS}))
    else:
        if attribution["alpha_t"] >= 2:
            out.append(Finding("alpha_significant", "good", {"alpha": attribution["alpha_annual"],
                                                            "t": attribution["alpha_t"]}))
        else:
            out.append(Finding("no_alpha", "info", {"alpha": attribution["alpha_annual"],
                                                   "t": attribution["alpha_t"], "r2": attribution["r2"]}))
        tilts = significant_tilts(attribution)
        if tilts:
            out.append(Finding("factor_tilts", "info", {"tilts": tilts}))
    out.append(Finding("past_not_future", "info", {}))
    return out


@dataclass
class Checkup:
    weights: pd.Series
    problems: list[str]
    info: dict
    portfolio: pd.Series
    benchmarks: dict[str, pd.Series]
    stats: dict
    benchmark_stats: dict[str, dict]
    relative: dict[str, dict]
    concentration: dict
    attribution: dict | None
    findings: list[Finding]


def run_checkup(holdings: pd.DataFrame, prices: pd.DataFrame, factors: pd.DataFrame | None,
                benchmarks: tuple[str, ...] = ("SPY", "RSP")) -> Checkup:
    """Full checkup from a holdings table and a daily adjusted-close table that
    includes the benchmark tickers. ``factors`` is the monthly Fama-French table
    from ``research.factor_attribution.load_factors`` or None to skip attribution."""
    from research.factor_attribution import attribute

    weights, problems = normalize_weights(holdings)
    returns = monthly_returns(prices)
    portfolio, info = portfolio_returns(returns, weights)
    bench = {b: returns[b].loc[portfolio.index].dropna() for b in benchmarks if b in returns}
    stats = metrics(portfolio)
    bench_stats = {b: metrics(series) for b, series in bench.items()}
    rel = {b: relative_to(portfolio, series) for b, series in bench.items()}
    conc = concentration(weights)
    attribution = None
    if factors is not None:
        covered = portfolio.loc[portfolio.index.isin(factors.index)]
        if len(covered) >= MIN_ATTRIBUTION_MONTHS:
            attribution = attribute(covered, factors, factors["rf"])
    found = findings(stats, conc, rel.get("SPY", {}), bench_stats.get("SPY", {}), attribution, info)
    return Checkup(weights, problems, info, portfolio, bench, stats, bench_stats, rel, conc, attribution, found)
