import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from src.ingestion.census import (
    fetch_acs5_variables,
    fetch_pep_population,
    _get_api_key,
    CensusAPIKeyMissing,
    EARLIEST_ACS5_END_YEAR,
)


def test_get_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    with pytest.raises(CensusAPIKeyMissing):
        _get_api_key()


def test_get_api_key_returns_value(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "abc123")
    assert _get_api_key() == "abc123"


def test_fetch_acs5_rejects_years_before_earliest_vintage(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "abc123")
    with pytest.raises(ValueError, match="do not exist before"):
        fetch_acs5_variables(EARLIEST_ACS5_END_YEAR - 1)


def _mock_response(rows):
    resp = MagicMock()
    resp.json.return_value = rows
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_acs5_variables_parses_and_labels_window(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "abc123")
    header = ["S1901_C01_012E", "S1701_C03_001E", "S1501_C02_015E", "S2701_C05_001E", "state", "county"]
    row = ["55000", "12.5", "28.3", "8.1", "01", "001"]
    with patch("src.ingestion.census.requests.get", return_value=_mock_response([header, row])):
        df = fetch_acs5_variables(2015)
    assert df.loc[0, "county_fips"] == "01001"
    assert df.loc[0, "median_household_income_acs5_2011_2015"] == 55000.0
    assert df.loc[0, "poverty_rate_acs5_2011_2015"] == 12.5


def test_fetch_pep_population_parses_rows(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "abc123")
    header = ["POP", "NAME", "state", "county"]
    row = ["54000", "Autauga County, Alabama", "01", "001"]
    with patch("src.ingestion.census.requests.get", return_value=_mock_response([header, row])):
        df = fetch_pep_population(2019)
    assert df.loc[0, "county_fips"] == "01001"
    assert df.loc[0, "population"] == 54000
    assert df.loc[0, "year"] == 2019
