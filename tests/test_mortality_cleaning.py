import pandas as pd

from src.cleaning.mortality import compute_county_eligibility, build_county_series
from src.utils.config import PRIMARY_WINDOW


def _panel(years, rate=25.0, population=100_000, suppressed_years=(), unreliable_years=()):
    rows = []
    for y in years:
        rows.append({
            "county_fips": "01001",
            "year": y,
            "age_adjusted_rate": rate,
            "population": population,
            "age_adjusted_rate_suppressed": y in suppressed_years,
            "age_adjusted_rate_unreliable": y in unreliable_years,
        })
    return pd.DataFrame(rows)


def test_eligible_county_with_enough_years_and_population():
    years = range(PRIMARY_WINDOW[0], PRIMARY_WINDOW[1] + 1)  # 22 years, all usable
    df = _panel(years, population=100_000)
    result = compute_county_eligibility(df)
    row = result.iloc[0]
    assert row["data_eligible_changepoint"]
    assert row["meets_year_threshold"]
    assert row["meets_population_threshold"]


def test_ineligible_county_too_few_usable_years():
    years = range(PRIMARY_WINDOW[0], PRIMARY_WINDOW[1] + 1)
    suppressed = list(years)[:15]  # only 7 usable years left
    df = _panel(years, population=100_000, suppressed_years=suppressed)
    result = compute_county_eligibility(df)
    row = result.iloc[0]
    assert not row["data_eligible_changepoint"]
    assert not row["meets_year_threshold"]


def test_ineligible_county_below_population_threshold():
    years = range(PRIMARY_WINDOW[0], PRIMARY_WINDOW[1] + 1)
    df = _panel(years, population=10_000)
    result = compute_county_eligibility(df)
    row = result.iloc[0]
    assert not row["data_eligible_changepoint"]
    assert not row["meets_population_threshold"]


def test_ineligible_counties_retained_not_dropped():
    years = range(PRIMARY_WINDOW[0], PRIMARY_WINDOW[1] + 1)
    df = _panel(years, population=1_000)
    result = compute_county_eligibility(df)
    assert len(result) == 1  # present, just flagged ineligible
    assert not result.iloc[0]["data_eligible_changepoint"]


def test_build_county_series_nulls_suppressed_and_unreliable_not_zero():
    years = [2010, 2011, 2012]
    df = _panel(years, rate=25.0, suppressed_years=[2011], unreliable_years=[2012])
    series = build_county_series(df, "01001")
    assert series.loc[series["year"] == 2010, "age_adjusted_rate"].iloc[0] == 25.0
    assert pd.isna(series.loc[series["year"] == 2011, "age_adjusted_rate"].iloc[0])
    assert pd.isna(series.loc[series["year"] == 2012, "age_adjusted_rate"].iloc[0])
