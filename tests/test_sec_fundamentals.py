import pandas as pd


def test_sec_features_are_delayed_and_unique():
    try: d = pd.read_parquet("data/sec/annual_fundamentals.parquet")
    except FileNotFoundError: return
    assert (d["available_date"] > d["filed"]).all()
    assert not d.duplicated(["ticker", "accession"]).any()
    assert (d["fiscal_end"] < d["filed"]).all()
