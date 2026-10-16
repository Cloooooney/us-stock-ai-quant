import pandas as pd

from data_pipeline.incremental_sec_update import needs_refresh, recent_annual_date, recent_filing_date


def submissions(*filings):
    forms, dates = zip(*filings) if filings else ((), ())
    return {"filings": {"recent": {"form": list(forms), "filingDate": list(dates)}}}


def test_new_quarterly_filing_triggers_refresh():
    payload = submissions(("10-K", "2026-02-20"), ("10-Q", "2026-10-28"), ("8-K", "2026-10-30"))
    assert recent_filing_date(payload) == pd.Timestamp("2026-10-28")
    assert recent_annual_date(payload) == pd.Timestamp("2026-02-20")
    assert needs_refresh(payload, cached=True, known=pd.Timestamp("2026-07-30"))
    assert not needs_refresh(payload, cached=True, known=pd.Timestamp("2026-10-28"))


def test_other_forms_and_missing_cache():
    payload = submissions(("8-K", "2026-10-30"), ("4", "2026-10-31"))
    assert not needs_refresh(payload, cached=True, known=None)
    assert needs_refresh(payload, cached=False, known=pd.Timestamp("2026-10-28"))
