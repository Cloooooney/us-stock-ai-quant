# V6 Point-in-Time Factor Model Implementation Plan

**Goal:** Build and evaluate a frozen, interpretable V6 factor model using quarterly point-in-time SEC fundamentals, valuation, quality, and momentum.

**Architecture:** A new SEC parser creates accession-level quarterly snapshots and TTM features. A separate V6 model joins those snapshots to the unchanged monthly price dataset, attaches unadjusted signal-date prices, computes cross-sectional ranks, and reuses the existing portfolio return engine. A dedicated backtest produces benchmark and robustness reports without modifying V5.

**Tech Stack:** Python, pandas, NumPy, pytest, matplotlib, cached SEC Company Facts JSON, existing parquet market data.

---

### Task 1: Quarterly point-in-time SEC snapshots

**Files:**
- Create: `data_pipeline/build_sec_quarterly_features.py`
- Create: `tests/test_sec_quarterly_features.py`

1. Add failing synthetic tests for accession isolation, filing delay, duration alignment, TTM reconstruction, amendments, and division-by-zero handling.
2. Run `pytest tests/test_sec_quarterly_features.py -q` and confirm failure.
3. Implement concept aliases, accession-level extraction, current/prior YTD matching, safe TTM reconstruction, and derived ratios.
4. Run the targeted tests and refactor only while green.

### Task 2: Point-in-time merge and valuation features

**Files:**
- Create: `models/v6_factor.py`
- Create: `tests/test_v6_factor.py`

1. Add failing tests proving future filings are unavailable, stale filings expire, unadjusted close is used, invalid market caps become missing, and missing factors receive neutral ranks.
2. Implement `merge_quarterly_fundamentals`, `attach_valuation_features`, and rank helpers.
3. Run the targeted tests.

### Task 3: Frozen factor score and portfolio

**Files:**
- Modify: `models/v6_factor.py`
- Modify: `tests/test_v6_factor.py`

1. Add failing tests for factor directions, equal sleeve weights, deterministic ordering, and next-open portfolio return compatibility.
2. Implement momentum, quality, value, and final scores with frozen feature lists.
3. Implement variant scoring for diagnostics without any automatic winner selection.
4. Run the targeted tests.

### Task 4: Dataset build and research report

**Files:**
- Create: `backtests/run_v6_factor.py`
- Create: `tests/test_v6_backtest.py`
- Modify: `.gitignore`

1. Add failing unit tests for benchmark alignment, cost stress, best-month removal, and empty-period behavior.
2. Implement the report helpers and command-line entry point.
3. Build `data/sec/quarterly_fundamentals.parquet` from the cached raw SEC files.
4. Run the V6 backtest and write machine-readable outputs under `reports/ai_v6_factor/`.

### Task 5: Verification and handoff

**Files:**
- Create: `docs/V6_RESULTS.md`
- Modify: `README.md`

1. Record the frozen rules, exact data cutoff, benchmark results, robustness checks, and honest promotion decision.
2. Run all V6 tests and the complete existing test suite.
3. Inspect Git diff for accidental V5 or data changes.
4. Commit the isolated branch `codex/v6-factor-model` and report the exact verification evidence.
