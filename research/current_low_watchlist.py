from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]


def main():
    members = pd.read_parquet(ROOT / "data/pit/members.parquet")
    latest_date = members["date"].max()
    tickers = sorted(set(members.loc[members["date"].eq(latest_date), "ticker"]))
    yahoo = [t.replace("-", ".") if t in {"BRK-B", "BF-B"} else t for t in tickers]
    raw = yf.download(yahoo, period="18mo", interval="1d", group_by="ticker", auto_adjust=False,
                      actions=False, threads=True, progress=False)
    rows = []
    for ticker, yticker in zip(tickers, yahoo):
        try:
            frame = raw[yticker].dropna(subset=["Close"]).copy()
        except (KeyError, TypeError):
            continue
        if len(frame) < 252:
            continue
        adj = frame["Adj Close"] if "Adj Close" in frame else frame["Close"]
        close = float(adj.iloc[-1]); high = float(adj.tail(252).max())
        ret = adj.pct_change()
        rows.append({"ticker": ticker, "date": pd.Timestamp(frame.index[-1]).tz_localize(None), "price": close,
                     "drawdown_52w": close / high - 1, "return_5d": close / float(adj.iloc[-6]) - 1,
                     "return_20d": close / float(adj.iloc[-21]) - 1,
                     "above_ma20": close / float(adj.tail(20).mean()) - 1,
                     "ma20_slope": float(adj.tail(20).mean()) / float(adj.iloc[-40:-20].mean()) - 1,
                     "volatility_20d": float(ret.tail(20).std() * np.sqrt(252)),
                     "dollar_volume_20d": float((frame["Close"] * frame["Volume"]).tail(20).mean())})
    market = pd.DataFrame(rows)
    fund = pd.read_parquet(ROOT / "data/sec/annual_fundamentals.parquet")
    cutoff = market["date"].max()
    fund = fund.loc[(fund["available_date"] <= cutoff) & ((cutoff - fund["filed"]).dt.days <= 550)]
    latest_fund = fund.sort_values("available_date").groupby("ticker", as_index=False).tail(1)
    cols = ["ticker", "filed", "revenue_growth", "net_margin", "roa", "liabilities_to_assets", "cash_quality"]
    x = market.merge(latest_fund[cols], on="ticker", how="left")
    eligible = x.loc[(x["drawdown_52w"].between(-.55, -.15)) & (x["return_5d"] > 0) &
                     (x["above_ma20"] > 0) & (x["ma20_slope"] > -.02) &
                     (x["dollar_volume_20d"] > 20_000_000) & (x["roa"] > 0) &
                     (x["net_margin"] > 0) & (x["revenue_growth"] > -.10)].copy()
    factors = {"drawdown_52w": -1, "return_5d": 1, "return_20d": 1, "above_ma20": 1,
               "revenue_growth": 1, "roa": 1, "volatility_20d": -1}
    eligible["screen_score"] = 0.0
    for col, direction in factors.items():
        eligible["screen_score"] += eligible[col].rank(pct=True) * direction
    eligible = eligible.sort_values("screen_score", ascending=False)
    out = ROOT / "reports/current_low_watchlist_2026-10-14.csv"
    eligible.to_csv(out, index=False)
    print("data through", cutoff.date(), "candidates", len(eligible))
    print(eligible.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
