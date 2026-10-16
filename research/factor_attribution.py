"""Factor attribution of historical strategy returns.

Regresses monthly strategy returns on the Fama-French five factors plus
momentum and reports Newey-West (HAC) t-statistics. Two regressions per
strategy and split:

absolute  strategy return minus the risk-free rate, on all six factors.
          A significant intercept is return not explained by known factors.
active    strategy return minus the point-in-time equal-weight universe, on
          the same factors. This isolates what the stock selection adds on top
          of simply holding the universe, and which factor tilts it takes.

Alignment: each backtest row is labelled by its month-end signal date but earns
from the next session's open to the open after the following month-end, so it
is matched to the calendar month of its ``execution_date``.

Factor data come from Kenneth R. French's data library and are cached under
``data/factors/``. Run from the repository root:

    python -m research.factor_attribution
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/factors"
OUT = ROOT / "reports/factor_attribution"
ETF_PRICES = ROOT / "data/pit/benchmark_etfs.parquet"
FF_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
FF_FILES = {"five_factors": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
            "momentum": "F-F_Momentum_Factor_CSV.zip"}
FACTORS = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]
RENAME = {"Mkt-RF": "mkt_rf", "SMB": "smb", "HML": "hml", "RMW": "rmw", "CMA": "cma", "RF": "rf", "Mom": "mom"}

# name -> (report directory, return column)
STRATEGIES = {
    "v1_lightgbm_price": ("ai_walk_forward", "net_return"),
    "v2_cross_sectional": ("ai_v2_cross_sectional", "net_return"),
    "v3_risk_control": ("ai_v3_risk_control", "overlay_return"),
    "v4_fundamental_ridge": ("ai_v4_fundamentals", "net_return"),
    "v6_factor_blend": ("ai_v6_factor", "net_return"),
    "v7_factor": ("ai_v7_factor", "net_return"),  # skipped until the V7 backtest has run
}
OWN_EW = "::equal_weight"  # suffix for a strategy's own equal-weight universe
BENCHMARK_SOURCE = "ai_v4_fundamentals"
SPLITS = {"validation": ("2018-01-01", "2022-12-31"), "test": ("2023-01-01", "2099-12-31"),
          "full_oos": ("2018-01-01", "2099-12-31")}


# ---------------------------------------------------------------------------
# Factor data
# ---------------------------------------------------------------------------

def parse_french_csv(text: str) -> pd.DataFrame:
    """Parse the monthly table of a Kenneth French CSV file into decimals,
    indexed by monthly Period. The annual table that follows is ignored."""
    lines = text.splitlines()
    header_at = next(i for i, line in enumerate(lines) if line.startswith(",") and line.strip(", "))
    columns = [RENAME.get(c.strip(), c.strip().lower()) for c in lines[header_at].split(",")[1:]]
    rows, index = [], []
    for line in lines[header_at + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if not re.fullmatch(r"\d{6}", parts[0]):
            if rows:
                break
            continue
        index.append(pd.Period(f"{parts[0][:4]}-{parts[0][4:]}", freq="M"))
        rows.append([float(p) for p in parts[1:len(columns) + 1]])
    frame = pd.DataFrame(rows, index=pd.PeriodIndex(index, name="month"), columns=columns)
    return frame.where(frame > -99.0) / 100.0


def _read_zip_csv(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        return archive.read(name).decode("latin-1")


def load_factors(cache: Path = CACHE, refresh: bool = False) -> pd.DataFrame:
    cache.mkdir(parents=True, exist_ok=True)
    parts = []
    for key, filename in FF_FILES.items():
        path = cache / filename
        if refresh or not path.exists():
            import requests

            response = requests.get(f"{FF_BASE}/{filename}", timeout=60,
                                    headers={"User-Agent": "AIQuantResearch/1.0"})
            response.raise_for_status()
            path.write_bytes(response.content)
        parts.append(parse_french_csv(_read_zip_csv(path.read_bytes())))
    return pd.concat(parts, axis=1, join="inner").dropna()


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

def newey_west_lags(n: int) -> int:
    return max(1, int(math.floor(4 * (n / 100) ** (2 / 9))))


def ols_newey_west(y: np.ndarray, x: np.ndarray, lags: int | None = None) -> dict:
    """OLS with an intercept and Bartlett-kernel HAC standard errors."""
    y = np.asarray(y, float)
    design = np.column_stack([np.ones(len(y)), np.asarray(x, float)])
    n, k = design.shape
    if n <= k:
        raise ValueError(f"need more than {k} observations, got {n}")
    lags = newey_west_lags(n) if lags is None else lags
    xtx_inv = np.linalg.inv(design.T @ design)
    beta = xtx_inv @ design.T @ y
    resid = y - design @ beta
    scores = design * resid[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        weight = 1 - lag / (lags + 1)
        gamma = scores[lag:].T @ scores[:-lag]
        meat += weight * (gamma + gamma.T)
    cov = xtx_inv @ meat @ xtx_inv * n / (n - k)
    se = np.sqrt(np.diag(cov))
    total = (y - y.mean()) @ (y - y.mean())
    r2 = 1 - resid @ resid / total if total > 0 else float("nan")
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta / se
    return {"beta": beta, "se": se, "t": t, "r2": float(r2), "n": n, "lags": lags,
            "resid_vol_annual": float(resid.std(ddof=k) * math.sqrt(12))}


def attribute(returns: pd.Series, factors: pd.DataFrame, rf: pd.Series | None) -> dict:
    """Regress monthly returns (indexed by Period) on the factor columns."""
    joined = pd.concat([returns.rename("y"), factors[FACTORS]], axis=1, join="inner").dropna()
    y = joined["y"] - (rf.reindex(joined.index) if rf is not None else 0.0)
    fit = ols_newey_west(y.to_numpy(), joined[FACTORS].to_numpy())
    out = {"months": fit["n"], "first_month": str(joined.index.min()), "last_month": str(joined.index.max()),
           "alpha_monthly": float(fit["beta"][0]), "alpha_annual": float(fit["beta"][0] * 12),
           "alpha_t": float(fit["t"][0]), "r2": fit["r2"], "residual_vol_annual": fit["resid_vol_annual"],
           "newey_west_lags": fit["lags"]}
    for i, name in enumerate(FACTORS, start=1):
        out[f"beta_{name}"] = float(fit["beta"][i])
        out[f"t_{name}"] = float(fit["t"][i])
    return out


# ---------------------------------------------------------------------------
# Strategy returns
# ---------------------------------------------------------------------------

def load_strategy_returns(reports: Path = ROOT / "reports") -> pd.DataFrame:
    """Monthly returns for every strategy plus the two benchmarks, indexed by
    the calendar month in which each holding period executes."""
    columns = {}
    for name, (folder, column) in STRATEGIES.items():
        path = reports / folder / "monthly_returns.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path, parse_dates=["execution_date"])
        frame = frame.set_index(frame["execution_date"].dt.to_period("M"))
        columns[name] = frame[column]
        if "equal_weight_return" in frame and folder != BENCHMARK_SOURCE:
            columns[name + OWN_EW] = frame["equal_weight_return"]
    base = pd.read_csv(reports / BENCHMARK_SOURCE / "monthly_returns.csv", parse_dates=["execution_date"])
    base = base.set_index(base["execution_date"].dt.to_period("M"))
    columns["point_in_time_equal_weight"] = base["equal_weight_return"]
    columns["spy"] = base["spy_return"]
    out = pd.DataFrame(columns)
    out.index.name = "month"
    if out.index.duplicated().any():
        raise ValueError("two holding periods execute in the same calendar month")
    return out


def run_attribution(returns: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, (start, end) in SPLITS.items():
        window = returns.loc[(returns.index >= pd.Period(start[:7], "M")) &
                             (returns.index <= pd.Period(end[:7], "M"))]
        for name in [c for c in window.columns if not c.endswith(OWN_EW)]:
            series = window[name].dropna()
            if len(series) < 24:
                continue
            rows.append({"strategy": name, "split": split, "regression": "absolute",
                         **attribute(series, factors, factors["rf"])})
            if name not in {"point_in_time_equal_weight", "spy"}:
                # Each model is measured against the equal-weight version of its own universe.
                benchmark = window.get(name + OWN_EW, window["point_in_time_equal_weight"])
                active = (window[name] - benchmark).dropna()
                rows.append({"strategy": name, "split": split, "regression": "active_vs_equal_weight",
                             **attribute(active, factors, None)})
    return pd.DataFrame(rows)


def etf_holding_returns(etf_prices: pd.DataFrame, execution_dates: pd.Series) -> pd.DataFrame:
    """ETF open-to-open returns between consecutive backtest execution dates,
    which is the backtest's own entry-to-exit window, indexed by execution month."""
    frame = etf_prices.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["adj_open"] = frame["open"] * frame["adj_close"] / frame["close"]
    opens = frame.pivot(index="date", columns="ticker", values="adj_open").sort_index()
    dates = pd.to_datetime(pd.Series(execution_dates)).dt.normalize().drop_duplicates().sort_values()
    rows = {}
    for entry, exit_ in zip(dates.iloc[:-1], dates.iloc[1:]):
        if entry in opens.index and exit_ in opens.index:
            rows[entry.to_period("M")] = opens.loc[exit_] / opens.loc[entry] - 1
    out = pd.DataFrame(rows).T
    out.index.name = "month"
    return out


def compare_to_etfs(returns: pd.DataFrame, etf_returns: pd.DataFrame) -> pd.DataFrame:
    """Mean excess return of each strategy over each ETF with Newey-West t."""
    rows = []
    for split, (start, end) in SPLITS.items():
        lo, hi = pd.Period(start[:7], "M"), pd.Period(end[:7], "M")
        for name in [c for c in returns.columns if not c.endswith(OWN_EW)]:
            for etf in etf_returns.columns:
                excess = (returns[name] - etf_returns[etf]).dropna()
                excess = excess.loc[(excess.index >= lo) & (excess.index <= hi)]
                if len(excess) < 24:
                    continue
                fit = ols_newey_west(excess.to_numpy(), np.empty((len(excess), 0)))
                rows.append({"strategy": name, "etf": etf, "split": split, "months": len(excess),
                             "excess_annual": float(excess.mean() * 12), "excess_t": float(fit["t"][0]),
                             "hit_rate": float((excess > 0).mean()),
                             "tracking_error_annual": float(excess.std(ddof=1) * math.sqrt(12))})
    return pd.DataFrame(rows)


def describe_etfs(table: pd.DataFrame) -> str:
    shown = table.loc[table["split"].eq("full_oos")]
    lines = ["## Versus benchmark ETFs (2018 onward)", "",
             "Mean excess return per year over each ETF across the same holding periods. "
             "V4 must beat RSP and the closest factor ETF to justify its complexity.", "",
             "| Strategy | ETF | Excess / yr | t | Hit rate | Months |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in shown.itertuples():
        lines.append(f"| {row.strategy} | {row.etf} | {row.excess_annual:+.2%} | {row.excess_t:+.2f} "
                     f"| {row.hit_rate:.0%} | {row.months} |")
    return "\n".join(lines + [""])


def describe(table: pd.DataFrame) -> str:
    lines = ["# Factor Attribution", "",
             "Fama-French five factors plus momentum, Newey-West t-statistics. `absolute` regresses "
             "return minus the risk-free rate; `active` regresses return minus the point-in-time "
             "equal-weight universe. |t| below 2 means the intercept is not distinguishable from zero.", ""]
    shown = table.loc[table["split"].eq("full_oos")]
    lines += ["## Full out-of-sample period (2018 onward)", "",
              "| Strategy | Regression | Alpha / yr | Alpha t | R² | Mkt | SMB | HML | RMW | CMA | Mom |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in shown.itertuples():
        betas = " | ".join(f"{getattr(row, f'beta_{f}'):+.2f}" + ("*" if abs(getattr(row, f't_{f}')) >= 2 else "")
                           for f in FACTORS)
        lines.append(f"| {row.strategy} | {row.regression} | {row.alpha_annual:+.2%} | {row.alpha_t:+.2f} "
                     f"| {row.r2:.2f} | {betas} |")
    significant = shown.loc[shown["alpha_t"].abs() >= 2]
    lines += ["", "## Reading", ""]
    if significant.empty:
        lines.append("No strategy shows an intercept with |t| ≥ 2 in the full out-of-sample period: "
                     "after known factor exposures, there is no statistically detectable alpha.")
    else:
        for row in significant.itertuples():
            lines.append(f"- {row.strategy} ({row.regression}): alpha {row.alpha_annual:+.2%} a year, "
                         f"t = {row.alpha_t:+.2f}.")
    lines += ["", "`*` marks a factor beta with |t| ≥ 2. Those are the known exposures that explain the returns. If a strategy's "
              "return is mostly explained by factors that a low-cost ETF already provides, the ETF is the "
              "cheaper implementation.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Factor attribution of historical strategy returns.")
    parser.add_argument("--refresh", action="store_true", help="re-download factor files")
    args = parser.parse_args()
    factors = load_factors(refresh=args.refresh)
    returns = load_strategy_returns()
    table = run_attribution(returns, factors)
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "factor_loadings.csv", index=False)
    text = describe(table)
    if ETF_PRICES.exists():
        execution = pd.read_csv(ROOT / "reports" / BENCHMARK_SOURCE / "monthly_returns.csv")["execution_date"]
        versus = compare_to_etfs(returns, etf_holding_returns(pd.read_parquet(ETF_PRICES), execution))
        versus.to_csv(OUT / "versus_etfs.csv", index=False)
        text += "\n" + describe_etfs(versus)
    else:
        text += f"\n`{ETF_PRICES.relative_to(ROOT)}` not found; run `python -m data_pipeline.update_benchmark_etfs` " \
                "to add the ETF comparison.\n"
    (OUT / "SUMMARY.md").write_text(text, encoding="utf-8")
    (OUT / "run_config.json").write_text(json.dumps({
        "factor_source": FF_BASE, "factor_files": FF_FILES,
        "factor_last_month": str(factors.index.max()), "strategies": STRATEGIES,
        "alignment": "calendar month of execution_date", "standard_errors": "Newey-West, Bartlett kernel",
    }, indent=2), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
