import pandas as pd
import pytest

from src.cleaning.geography import (
    standardize_fips,
    validate_fips,
    find_duplicate_county_years,
    find_appearing_disappearing_counties,
)


def test_standardize_fips_pads_and_strips_floats():
    raw = pd.Series([1001, "1003", 1005.0, "06065"])
    result = standardize_fips(raw)
    assert result.tolist() == ["01001", "01003", "01005", "06065"]


def test_validate_fips_flags_bad_length():
    report = validate_fips(pd.Series(["01001", "101", "010011"]))
    assert report.loc[0, "is_valid"]
    assert not report.loc[1, "is_valid"]
    assert not report.loc[2, "is_valid"]


def test_validate_fips_flags_invalid_state_prefix():
    # "99" is not a valid state FIPS prefix
    report = validate_fips(pd.Series(["99001"]))
    assert not report.loc[0, "is_valid"]
    assert not report.loc[0, "has_valid_state_prefix"]


def test_validate_fips_rejects_non_numeric():
    report = validate_fips(pd.Series(["ABCDE"]))
    assert not report.loc[0, "is_valid"]


def test_find_duplicate_county_years_detects_dupes():
    df = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003"],
        "year": [2010, 2010, 2010],
        "deaths": [5, 6, 7],
    })
    dupes = find_duplicate_county_years(df)
    assert len(dupes) == 2
    assert set(dupes["county_fips"]) == {"01001"}


def test_find_duplicate_county_years_clean_panel_returns_empty():
    df = pd.DataFrame({
        "county_fips": ["01001", "01003"],
        "year": [2010, 2010],
        "deaths": [5, 7],
    })
    assert find_duplicate_county_years(df).empty


def test_find_appearing_disappearing_counties():
    df = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003"],
        "year": [2010, 2011, 2010],
    })
    result = find_appearing_disappearing_counties(df)
    assert list(result["county_fips"]) == ["01003"]
    assert result.iloc[0]["missing_years"] == [2011]


def test_find_appearing_disappearing_counties_full_panel_returns_empty():
    df = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "year": [2010, 2011, 2010, 2011],
    })
    assert find_appearing_disappearing_counties(df).empty
