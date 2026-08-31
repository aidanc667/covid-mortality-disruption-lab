"""Tests for CHR&R ingestion, using a synthetic fixture shaped exactly like
the real analytic CSV (verified against the live 2024 file during this
project's build): two header rows, and national/state aggregate rows mixed
in with real counties. These two quirks caused a real bug on first run
against live data — these tests exist so it can't silently regress.
"""
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from src.ingestion.county_health_rankings import load_year, download_year, YEAR_URLS


FIXTURE_CSV = (
    "State FIPS Code,County FIPS Code,5-digit FIPS Code,State Abbreviation,Name,Release Year,Adult Smoking raw value,Adult Obesity raw value\n"
    "statecode,countycode,fipscode,state,county,year,v009_rawvalue,v011_rawvalue\n"
    "00,000,00000,US,United States,2024,0.15,0.34\n"
    "01,000,01000,AL,Alabama,2024,0.179,0.406\n"
    "01,001,01001,AL,Autauga County,2024,0.169,0.389\n"
    "01,003,01003,AL,Baldwin County,2024,0.15,0.372\n"
)


def _mock_download(tmp_path, monkeypatch):
    fixture_path = tmp_path / "chr_2024.csv"
    fixture_path.write_text(FIXTURE_CSV)
    monkeypatch.setattr("src.ingestion.county_health_rankings.download_year", lambda year: fixture_path)


def test_load_year_skips_second_header_row_and_aggregates(tmp_path, monkeypatch):
    _mock_download(tmp_path, monkeypatch)
    df = load_year(2024)
    assert set(df["county_fips"]) == {"01001", "01003"}
    assert "00000" not in set(df["county_fips"])
    assert "01000" not in set(df["county_fips"])


def test_load_year_parses_values_as_numeric(tmp_path, monkeypatch):
    _mock_download(tmp_path, monkeypatch)
    df = load_year(2024)
    row = df[df["county_fips"] == "01001"].iloc[0]
    assert row["pct_smokers"] == pytest.approx(0.169)
    assert row["pct_obese"] == pytest.approx(0.389)


def test_load_year_reports_missing_variables_not_fabricated(tmp_path, monkeypatch):
    _mock_download(tmp_path, monkeypatch)
    df = load_year(2024)
    # fixture only has smoking/obesity; everything else should be reported missing
    assert "pct_uninsured_chr" in df.attrs["missing_variables"]
    assert "pct_uninsured_chr" not in df.columns


def test_download_year_rejects_unverified_year():
    with pytest.raises(ValueError, match="No verified CHR&R URL"):
        download_year(1999)


def test_year_urls_cover_documented_range():
    assert set(YEAR_URLS.keys()) == set(range(2010, 2026))
