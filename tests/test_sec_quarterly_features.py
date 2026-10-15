import math

import pandas as pd

from data_pipeline.build_sec_quarterly_features import extract_payload


def _duration(start, end, value, accession, filed, form, fp):
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accession,
        "filed": filed,
        "form": form,
        "fp": fp,
        "fy": int(end[:4]),
    }


def _instant(end, value, accession, filed, form, fp):
    return {
        "end": end,
        "val": value,
        "accn": accession,
        "filed": filed,
        "form": form,
        "fp": fp,
        "fy": int(end[:4]),
    }


def _payload():
    annual_accession = "annual-2023"
    q1_accession = "q1-2024"
    q2_accession = "q2-2024"
    q2_amendment = "q2-2024-amended"

    annual = ("2023-01-01", "2023-12-31", annual_accession, "2024-02-15", "10-K", "FY")
    q1 = ("2024-01-01", "2024-03-31", q1_accession, "2024-05-01", "10-Q", "Q1")
    prior_q1 = ("2023-01-01", "2023-03-31", q1_accession, "2024-05-01", "10-Q", "Q1")
    q2_ytd = ("2024-01-01", "2024-06-30", q2_accession, "2024-08-01", "10-Q", "Q2")
    q2_only = ("2024-04-01", "2024-06-30", q2_accession, "2024-08-01", "10-Q", "Q2")
    prior_q2_ytd = ("2023-01-01", "2023-06-30", q2_accession, "2024-08-01", "10-Q", "Q2")
    amendment_ytd = ("2024-01-01", "2024-06-30", q2_amendment, "2024-08-15", "10-Q/A", "Q2")
    amendment_prior = ("2023-01-01", "2023-06-30", q2_amendment, "2024-08-15", "10-Q/A", "Q2")

    def rows(values):
        return [_duration(*period[:2], value, *period[2:]) for period, value in values]

    concepts = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": rows([
            (annual, 1_000),
            (q1, 300), (prior_q1, 200),
            (q2_ytd, 650), (q2_only, 350), (prior_q2_ytd, 450),
            (amendment_ytd, 660), (amendment_prior, 450),
        ]),
        "NetIncomeLoss": rows([
            (annual, 100),
            (q1, 30), (prior_q1, 20),
            (q2_ytd, 70), (q2_only, 40), (prior_q2_ytd, 45),
            (amendment_ytd, 72), (amendment_prior, 45),
        ]),
        "NetCashProvidedByUsedInOperatingActivities": rows([
            (annual, 120),
            (q1, 40), (prior_q1, 25),
            (q2_ytd, 75), (prior_q2_ytd, 55),
            (amendment_ytd, 78), (amendment_prior, 55),
        ]),
        "PaymentsToAcquirePropertyPlantAndEquipment": rows([
            (annual, 20),
            (q1, 5), (prior_q1, 4),
            (q2_ytd, 11), (prior_q2_ytd, 9),
            (amendment_ytd, 12), (amendment_prior, 9),
        ]),
    }
    weighted_shares = rows([
        (annual, 100),
        (q1, 100), (prior_q1, 100),
        (q2_ytd, 101), (q2_only, 102), (prior_q2_ytd, 99),
        (amendment_ytd, 103), (amendment_prior, 99),
    ])

    instant_rows = [
        ("2023-12-31", annual_accession, "2024-02-15", "10-K", "FY", 500, 200, 100),
        ("2024-03-31", q1_accession, "2024-05-01", "10-Q", "Q1", 550, 210, 100),
        ("2024-06-30", q2_accession, "2024-08-01", "10-Q", "Q2", 575, 220, 100),
        ("2024-06-30", q2_amendment, "2024-08-15", "10-Q/A", "Q2", 576, 220, 100),
    ]
    assets = [_instant(end, assets, accession, filed, form, fp)
              for end, accession, filed, form, fp, assets, _, _ in instant_rows]
    liabilities = [_instant(end, liabilities, accession, filed, form, fp)
                   for end, accession, filed, form, fp, _, liabilities, _ in instant_rows]
    shares = [_instant(end, shares, accession, filed, form, fp)
              for end, accession, filed, form, fp, _, _, shares in instant_rows]

    us_gaap = {tag: {"units": {"USD": facts}} for tag, facts in concepts.items()}
    us_gaap["Assets"] = {"units": {"USD": assets}}
    us_gaap["Liabilities"] = {"units": {"USD": liabilities}}
    us_gaap["WeightedAverageNumberOfDilutedSharesOutstanding"] = {
        "units": {"shares": weighted_shares}
    }
    return {
        "cik": 1,
        "facts": {
            "us-gaap": us_gaap,
            "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": shares}}},
        },
    }


def test_quarterly_snapshots_are_delayed_accession_isolated_and_unique():
    rows = pd.DataFrame(extract_payload(_payload(), ["TEST"]))

    assert len(rows) == 4
    assert not rows.duplicated(["ticker", "accession"]).any()
    assert (rows["available_date"] == rows["filed"] + pd.Timedelta(days=1)).all()
    assert (rows["fiscal_end"] < rows["filed"]).all()

    annual = rows.set_index("accession").loc["annual-2023"]
    assert annual["ttm_revenue"] == 1_000


def test_quarterly_ttm_uses_aligned_ytd_values_not_standalone_quarter():
    rows = pd.DataFrame(extract_payload(_payload(), ["TEST"])).set_index("accession")

    q1 = rows.loc["q1-2024"]
    assert q1["period_days"] == 90
    assert q1["ttm_revenue"] == 1_100
    assert q1["ttm_net_income"] == 110
    assert q1["ttm_operating_cash_flow"] == 135
    assert q1["ttm_capex"] == 21

    q2 = rows.loc["q2-2024"]
    assert q2["period_days"] == 181
    assert q2["reported_revenue"] == 650
    assert q2["weighted_average_shares"] == 101
    assert q2["ttm_revenue"] == 1_200
    assert q2["ttm_operating_cash_flow"] == 140


def test_amendment_creates_a_later_snapshot_and_safe_ratios():
    rows = pd.DataFrame(extract_payload(_payload(), ["TEST"])).set_index("accession")

    original = rows.loc["q2-2024"]
    amended = rows.loc["q2-2024-amended"]
    assert amended["available_date"] > original["available_date"]
    assert amended["ttm_revenue"] == 1_210
    assert math.isclose(amended["free_cash_flow_margin"], (143 - 23) / 1_210)
    assert math.isfinite(amended["accruals_to_assets"])


def test_zero_denominators_never_produce_infinity():
    payload = _payload()
    payload["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["val"] = 0
    payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"][0]["val"] = 0

    rows = pd.DataFrame(extract_payload(payload, ["TEST"]))
    numeric = rows.select_dtypes(include="number")
    assert not numeric.isin([math.inf, -math.inf]).any().any()
