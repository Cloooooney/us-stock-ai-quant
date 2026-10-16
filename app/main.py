"""Bilingual analysis app. Start with ``start_app.bat`` or:

    python -m streamlit run app/main.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repository root

import pandas as pd
import streamlit as st

from app.analysis import FACTOR_NAMES, run_checkup
from app.data import download_adjusted_close, forward_ledgers, read_csv
from app.i18n import LANGUAGES, finding_text, t
from automation.status import ledger_status
from paper_trading.ledger import read_events

BENCHMARKS = ("SPY", "RSP")
EXAMPLE = pd.DataFrame({"ticker": ["AAPL", "MSFT", "NVDA", "TSLA"], "weight": [30.0, 25.0, 25.0, 20.0]})
LEVEL = {"warning": st.warning, "info": st.info, "good": st.success}

st.set_page_config(page_title="US Equity Quant Analyzer", layout="wide")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_prices(tickers: tuple[str, ...], start: str):
    return download_adjusted_close(list(tickers), start)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_factors():
    from research.factor_attribution import load_factors

    return load_factors()


def pct(value) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.1%}"


def num(value) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.2f}"


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def checkup_page(lang: str) -> None:
    st.header(t("nav_checkup", lang))
    st.write(t("checkup_intro", lang))
    holdings = st.data_editor(
        EXAMPLE, num_rows="dynamic", width="stretch", key="holdings",
        column_config={"ticker": st.column_config.TextColumn(t("col_ticker", lang)),
                       "weight": st.column_config.NumberColumn(t("col_weight", lang), min_value=0.0)})
    years = st.slider(t("years", lang), min_value=3, max_value=20, value=10)
    if not st.button(t("run", lang), type="primary"):
        return

    start = date(date.today().year - years, date.today().month, 1).isoformat()
    try:
        from app.analysis import normalize_weights

        weights, _ = normalize_weights(holdings)
    except ValueError as error:
        st.error(str(error))
        return
    with st.spinner(t("loading", lang)):
        prices, failed = cached_prices(tuple(sorted(set(weights.index) | set(BENCHMARKS))), start)
        try:
            factors, factor_error = cached_factors(), None
        except Exception as error:  # network or format problems must not block the checkup
            factors, factor_error = None, error
    if failed:
        st.error(t("download_failed", lang, tickers=", ".join(failed)))
        if set(failed) & set(weights.index):
            return
    if factor_error is not None:
        st.warning(t("factors_unavailable", lang, error=factor_error))

    try:
        result = run_checkup(holdings, prices, factors, BENCHMARKS)
    except ValueError as error:
        st.error(str(error))
        return
    for problem in result.problems:
        if problem.startswith("invalid_weight:"):
            st.warning(t("invalid_weight", lang, tickers=problem.split(":", 1)[1]))
        else:
            st.info(t(problem, lang))

    st.subheader(t("summary", lang))
    for finding in result.findings:
        LEVEL[finding.level](finding_text(finding, lang))

    st.subheader(t("performance", lang))
    rows = ["annual_return", "annual_volatility", "sharpe_0rf", "max_drawdown", "total_return", "worst_month"]
    table = {t("portfolio", lang): result.stats, **result.benchmark_stats}
    shown = pd.DataFrame({name: [num(s.get(r)) if r == "sharpe_0rf" else pct(s.get(r)) for r in rows]
                          for name, s in table.items()}, index=[t(r, lang) for r in rows])
    st.dataframe(shown, width="stretch")
    st.caption(f"{t('months', lang)}: {result.info['months']} ({result.info['first_month']} – {result.info['last_month']})"
               f" · {t('beta', lang)}: {num(result.relative.get('SPY', {}).get('beta'))}")

    growth = pd.DataFrame({t("portfolio", lang): result.portfolio, **result.benchmarks}).add(1).cumprod()
    growth.index = growth.index.to_timestamp()
    st.markdown(f"**{t('growth', lang)}**")
    st.line_chart(growth)

    left, right = st.columns(2)
    with left:
        st.subheader(t("concentration", lang))
        c = result.concentration
        st.metric(t("largest", lang), f"{c['largest_ticker']} {c['largest_weight']:.0%}")
        st.metric(t("top3", lang), f"{c['top3_weight']:.0%}")
        st.metric(t("effective", lang), f"{c['effective_holdings']:.1f}")
    with right:
        st.subheader(t("weights_used", lang))
        st.dataframe(result.weights.rename(t("col_weight", lang)).map(lambda w: f"{w:.1%}"),
                     width="stretch")

    if result.attribution is not None:
        st.subheader(t("attribution", lang))
        st.caption(t("attribution_help", lang))
        a = result.attribution
        factor_rows = [{"factor": t(f"factor_{name}", lang),
                        "beta": f"{a[f'beta_{key}']:+.2f}" + ("*" if abs(a[f"t_{key}"]) >= 2 else ""),
                        "t": f"{a[f't_{key}']:+.2f}"} for key, name in FACTOR_NAMES.items()]
        st.dataframe(pd.DataFrame(factor_rows), hide_index=True, width="stretch")
        st.caption(f"{t('alpha', lang)}: {a['alpha_annual']:+.2%} (t = {a['alpha_t']:+.2f}) · "
                   f"{t('r2', lang)}: {a['r2']:.0%}")


def forward_page(lang: str) -> None:
    st.header(t("nav_forward", lang))
    st.write(t("forward_intro", lang))
    for key, path in forward_ledgers().items():
        model = key.upper()
        st.subheader(model)
        status = ledger_status(path)
        if not status.get("exists"):
            st.info(t("no_ledger", lang, model=model))
            continue
        if not status["valid"]:
            st.error(t("ledger_invalid", lang, model=model, detail=status["detail"]))
            continue
        events = read_events(path)
        signals = [e for e in events if e["event_type"] == "SIGNAL"]
        periods = [e for e in events if e["event_type"] == "PERIOD"]
        if signals:
            latest = signals[-1]
            st.markdown(f"**{t('latest_holdings', lang, date=latest['signal_date'])}**")
            st.dataframe(pd.DataFrame(latest["holdings"]), hide_index=True, width="stretch")
        st.caption(t("observations", lang, n=sum(1 for p in periods if p["calendar_months"] == 1)))
        if not periods:
            st.info(t("no_periods", lang))
            continue
        rows = []
        for p in periods:
            row = {"signal": p["signal_date"], model: p[key]["net_return"],
                   "PIT EW": p["point_in_time_equal_weight"]["return"], "SPY": p["spy"]["return"]}
            row.update({etf: v.get("return") for etf, v in p.get("etf_benchmarks", {}).items()})
            rows.append(row)
        frame = pd.DataFrame(rows).set_index("signal").astype(float)
        st.markdown(f"**{t('periods', lang)}**")
        st.dataframe(frame.map(pct), width="stretch")
        st.line_chart(frame.fillna(0).add(1).cumprod())


def research_page(lang: str) -> None:
    st.header(t("nav_research", lang))
    st.write(t("research_intro", lang))
    for label, relative in (("V4", "reports/ai_v4_fundamentals/performance_summary.csv"),
                            ("V6", "reports/ai_v6_factor/performance_summary.csv")):
        frame = read_csv(relative)
        st.subheader(label)
        if frame is None:
            st.info(t("research_missing", lang, path=relative))
        else:
            st.dataframe(frame.round(4), hide_index=True, width="stretch")
    loadings = read_csv("reports/factor_attribution/factor_loadings.csv")
    if loadings is not None:
        st.subheader(t("research_attribution", lang))
        cols = ["strategy", "regression", "alpha_annual", "alpha_t", "r2",
                *[f"beta_{f}" for f in FACTOR_NAMES]]
        st.dataframe(loadings.loc[loadings["split"].eq("full_oos"), cols].round(3),
                     hide_index=True, width="stretch")
    versus = read_csv("reports/factor_attribution/versus_etfs.csv")
    if versus is not None:
        st.subheader(t("research_versus", lang))
        pivot = versus.loc[versus["split"].eq("full_oos")].pivot(index="strategy", columns="etf",
                                                                  values="excess_annual")
        st.dataframe(pivot.map(pct), width="stretch")


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

lang = st.sidebar.radio("语言 / Language", list(LANGUAGES), format_func=LANGUAGES.get, horizontal=True)
st.sidebar.title(t("app_title", lang))
pages = {"checkup": checkup_page, "forward": forward_page, "research": research_page}
page = st.sidebar.radio(" ", list(pages), format_func=lambda key: t(f"nav_{key}", lang),
                        label_visibility="collapsed")
st.sidebar.caption(t("disclaimer", lang))
pages[page](lang)
