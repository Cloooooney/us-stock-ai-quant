"""Chinese and English text for the analysis app."""
from __future__ import annotations

LANGUAGES = {"zh": "中文", "en": "English"}

TEXT = {
    "app_title": {"zh": "美股量化分析工具", "en": "US Equity Quant Analyzer"},
    "disclaimer": {
        "zh": "本工具仅用于研究和教育，不构成投资建议。历史表现不代表未来收益，所有结论都可能出错。",
        "en": "For research and education only, not investment advice. Past performance does not "
              "predict future returns, and every conclusion here can be wrong.",
    },
    "nav_checkup": {"zh": "持仓体检", "en": "Portfolio checkup"},
    "nav_forward": {"zh": "模型实盘记录", "en": "Model forward record"},
    "nav_research": {"zh": "历史研究结果", "en": "Research history"},
    "language": {"zh": "语言", "en": "Language"},

    # Checkup page
    "checkup_intro": {
        "zh": "输入你的持仓和比例（百分比或小数都可以），工具会按每月再平衡回测它的历史表现，"
              "并和 SPY（标普 500）、RSP（等权标普 500）对比。",
        "en": "Enter your holdings and weights (percentages or fractions). The tool backtests the "
              "portfolio with monthly rebalancing and compares it with SPY (S&P 500) and RSP "
              "(equal-weight S&P 500).",
    },
    "col_ticker": {"zh": "股票代码", "en": "Ticker"},
    "col_weight": {"zh": "比例", "en": "Weight"},
    "years": {"zh": "回测年数", "en": "Years of history"},
    "run": {"zh": "开始体检", "en": "Run checkup"},
    "loading": {"zh": "正在下载行情和因子数据…", "en": "Downloading prices and factor data…"},
    "download_failed": {"zh": "以下代码没有下载到数据：{tickers}", "en": "No data downloaded for: {tickers}"},
    "factors_unavailable": {"zh": "因子数据下载失败，已跳过因子归因：{error}",
                            "en": "Factor data could not be loaded; attribution skipped: {error}"},
    "invalid_weight": {"zh": "以下代码的比例无效，已忽略：{tickers}", "en": "Ignored invalid weights for: {tickers}"},
    "duplicates_combined": {"zh": "重复的代码已合并。", "en": "Duplicate tickers were combined."},
    "summary": {"zh": "结论", "en": "Findings"},
    "performance": {"zh": "历史表现", "en": "Historical performance"},
    "growth": {"zh": "1 美元的增长", "en": "Growth of $1"},
    "weights_used": {"zh": "使用的比例", "en": "Weights used"},
    "concentration": {"zh": "集中度", "en": "Concentration"},
    "attribution": {"zh": "因子归因", "en": "Factor attribution"},
    "attribution_help": {
        "zh": "把组合的月度超额收益拆解到市场、规模、价值、盈利能力、投资和动量六个常见因子上。"
              "带 * 的因子在统计上显著（|t| ≥ 2）。",
        "en": "Splits the portfolio's monthly excess return across six common factors: market, size, "
              "value, profitability, investment, and momentum. * marks a significant exposure (|t| ≥ 2).",
    },
    "portfolio": {"zh": "你的组合", "en": "Your portfolio"},
    "metric": {"zh": "指标", "en": "Metric"},
    "annual_return": {"zh": "年化收益", "en": "Annual return"},
    "annual_volatility": {"zh": "年化波动", "en": "Annual volatility"},
    "sharpe_0rf": {"zh": "夏普比率（无风险利率按 0）", "en": "Sharpe ratio (0% risk-free)"},
    "max_drawdown": {"zh": "最大回撤", "en": "Maximum drawdown"},
    "total_return": {"zh": "累计收益", "en": "Total return"},
    "worst_month": {"zh": "最差月份", "en": "Worst month"},
    "months": {"zh": "月数", "en": "Months"},
    "beta": {"zh": "相对 SPY 的 beta", "en": "Beta to SPY"},
    "largest": {"zh": "最大持仓", "en": "Largest position"},
    "top3": {"zh": "前三大合计", "en": "Top three combined"},
    "effective": {"zh": "等效持仓数", "en": "Effective number of holdings"},
    "alpha": {"zh": "Alpha（年化）", "en": "Alpha (annual)"},
    "r2": {"zh": "因子解释度 R²", "en": "Share explained by factors (R²)"},

    # Findings
    "f_short_history": {"zh": "只有 {months} 个月的共同历史，结论很不可靠。",
                        "en": "Only {months} months of shared history; conclusions are very unreliable."},
    "f_limited_by": {"zh": "{ticker} 上市较晚，回测从 {first} 开始。",
                     "en": "{ticker} has the shortest history, so the backtest starts in {first}."},
    "f_large_position": {"zh": "{ticker} 占 {weight:.0%}，单只股票出问题就会重伤整个组合。",
                         "en": "{ticker} is {weight:.0%} of the portfolio; one bad outcome there hurts everything."},
    "f_few_holdings": {"zh": "等效持仓只有 {n:.1f} 只，分散程度很低。",
                       "en": "Only {n:.1f} effective holdings; diversification is low."},
    "f_high_beta": {"zh": "beta 为 {beta:.2f}：大盘跌 10% 时，这个组合历史上平均跌约 {loss:.0%}。",
                    "en": "Beta is {beta:.2f}: when the market fell 10%, this portfolio fell about {loss:.0%} on average."},
    "f_low_beta": {"zh": "beta 为 {beta:.2f}，比大盘更稳，但牛市里通常也涨得更少。",
                   "en": "Beta is {beta:.2f}: steadier than the market, usually with smaller gains in rallies."},
    "f_deep_drawdown": {"zh": "历史最大回撤 {drawdown:.0%}，问问自己当时能否坚持不卖。",
                        "en": "Worst peak-to-trough loss was {drawdown:.0%}; ask whether you would have held on."},
    "f_index_was_better": {
        "zh": "同期直接买 SPY 收益更高、风险调整后也更好（年化差 {gap:+.1%}）。一只低成本指数基金就能做得更好。",
        "en": "Simply holding SPY returned more with a better risk-adjusted result ({gap:+.1%} a year). "
              "A low-cost index fund would have done better.",
    },
    "f_beat_index_history": {
        "zh": "历史上它在收益和风险调整后收益上都跑赢了 SPY（年化 {gap:+.1%}）。但要看下面的因子归因，判断这是否只是某种风格的运气。",
        "en": "Historically it beat SPY on both return and risk-adjusted return ({gap:+.1%} a year). "
              "Check the factor attribution below to see whether that was just a style tailwind.",
    },
    "f_mixed_vs_index": {"zh": "相对 SPY 有得有失：收益和风险调整后收益只有一项更好。",
                         "en": "Mixed versus SPY: better on return or on risk-adjusted return, not both."},
    "f_attribution_skipped": {"zh": "历史不足 {months} 个月，未做因子归因。",
                              "en": "Less than {months} months of history; factor attribution skipped."},
    "f_alpha_significant": {
        "zh": "扣除已知因子后仍有年化 {alpha:+.1%} 的 alpha（t = {t:.2f}）。这很少见，但可能来自少数几只股票的运气，未必能延续。",
        "en": "After known factors there is {alpha:+.1%} a year of alpha (t = {t:.2f}). That is rare, but it "
              "may come from a few lucky stocks and need not persist.",
    },
    "f_no_alpha": {
        "zh": "扣除已知因子后没有统计上可靠的超额收益（alpha {alpha:+.1%}，t = {t:.2f}）；{r2:.0%} 的波动可以被因子解释。",
        "en": "No statistically reliable return beyond known factors (alpha {alpha:+.1%}, t = {t:.2f}); "
              "factors explain {r2:.0%} of its movement.",
    },
    "f_factor_tilts": {"zh": "显著的风格暴露：{tilts}。这些风格都可以用低成本 ETF 直接买到。",
                       "en": "Significant style exposures: {tilts}. Each is available in low-cost ETFs."},
    "f_past_not_future": {"zh": "以上都是历史结果，不代表未来。", "en": "All of this is history, not a forecast."},

    "factor_market": {"zh": "市场", "en": "market"},
    "factor_size": {"zh": "小盘", "en": "size (small caps)"},
    "factor_value": {"zh": "价值", "en": "value"},
    "factor_profitability": {"zh": "盈利能力", "en": "profitability"},
    "factor_investment": {"zh": "保守投资", "en": "conservative investment"},
    "factor_momentum": {"zh": "动量", "en": "momentum"},
    "tilt_positive": {"zh": "偏向", "en": "toward"},
    "tilt_negative": {"zh": "背离", "en": "away from"},

    # Forward page
    "forward_intro": {
        "zh": "V5 和 V6 的规则在 10 月冻结后，从 2026 年 10 月 30 日的月末信号开始做真实的前瞻记录，每月自动更新。"
              "至少 6 个月只够检查流程，24 个月以上才可能考虑小额实盘。",
        "en": "V5 and V6 rules were frozen in October; their genuine forward record starts with the "
              "October 30, 2026 month-end signal and updates automatically each month. Six months is only "
              "an operational check; at least 24 are needed before any small live allocation.",
    },
    "no_ledger": {"zh": "{model} 还没有正式记录。第一笔信号预计在 2026 年 11 月 2 日收盘后自动写入。",
                  "en": "{model} has no formal record yet. The first signal is expected after the November 2, 2026 close."},
    "ledger_invalid": {"zh": "{model} 的 ledger 校验失败：{detail}", "en": "{model} ledger failed validation: {detail}"},
    "latest_holdings": {"zh": "最新持仓（信号日 {date}）", "en": "Latest holdings (signal {date})"},
    "periods": {"zh": "月度结果", "en": "Monthly results"},
    "no_periods": {"zh": "还没有完整的持有期。第一个结果要等下一个月末信号成交之后。",
                   "en": "No complete holding period yet. The first result arrives after the next month-end signal executes."},
    "observations": {"zh": "完整月度观测：{n} / 24", "en": "Complete monthly observations: {n} / 24"},

    # Research page
    "research_intro": {
        "zh": "每个版本的历史回测和因子归因结论，包括失败的版本。这些都是已经看过的历史数据，不能当作未来的证据。",
        "en": "Backtest and attribution results for every version, including the failures. All of this "
              "history has already been seen and is not evidence about the future.",
    },
    "research_attribution": {"zh": "因子归因（2018 年起）", "en": "Factor attribution (2018 onward)"},
    "research_versus": {"zh": "相对 ETF 的年化超额收益", "en": "Annual excess return versus ETFs"},
    "research_missing": {"zh": "缺少 {path}", "en": "Missing {path}"},
}


def t(key: str, lang: str, **params) -> str:
    entry = TEXT[key]
    text = entry.get(lang) or entry["en"]
    return text.format(**params) if params else text


def finding_text(finding, lang: str) -> str:
    params = dict(finding.params)
    if finding.key == "high_beta":
        params["loss"] = params["beta"] * 0.10
    if finding.key == "factor_tilts":
        sep = "；" if lang == "zh" else "; "
        params["tilts"] = sep.join(
            f"{t('tilt_' + tilt['direction'], lang)}{'' if lang == 'zh' else ' '}{t('factor_' + tilt['factor'], lang)}"
            f" ({tilt['beta']:+.2f})" for tilt in params["tilts"])
    return t("f_" + finding.key, lang, **params)
