import io
import zipfile

import pandas as pd
import pytest

from src.ingestion.epa_pm25 import load_county_pm25, PM25_PARAMETER_CODE


COLUMNS = [
    "State Code", "County Code", "Site Num", "Parameter Code", "POC",
    "Parameter Name", "Pollutant Standard", "Year", "Arithmetic Mean",
]


def _make_fixture_zip(rows: list[list]) -> bytes:
    df = pd.DataFrame(rows, columns=COLUMNS)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("annual_conc_by_monitor_2020.csv", df.to_csv(index=False))
    return buf.getvalue()


def test_load_county_pm25_averages_multiple_monitors(monkeypatch):
    rows = [
        ["01", "003", "0010", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 1997", 2020, 8.0],
        ["01", "003", "0011", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 1997", 2020, 10.0],
    ]
    monkeypatch.setattr("src.ingestion.epa_pm25.download_year", lambda year: _make_fixture_zip(rows))
    df = load_county_pm25(2020)
    assert df.loc[df["county_fips"] == "01003", "pm25_avg"].iloc[0] == pytest.approx(9.0)
    assert df.loc[df["county_fips"] == "01003", "pm25_monitor_count"].iloc[0] == 2
    assert df["pm25_monitored"].all()


def test_load_county_pm25_dedupes_same_monitor_multiple_standards(monkeypatch):
    # Same monitor (site 0010, POC 1) reported under two NAAQS standards with
    # an identical Arithmetic Mean — confirmed real EPA file behavior. Must
    # not be double-counted as two monitors.
    rows = [
        ["01", "003", "0010", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 1997", 2020, 8.0],
        ["01", "003", "0010", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 2006", 2020, 8.0],
    ]
    monkeypatch.setattr("src.ingestion.epa_pm25.download_year", lambda year: _make_fixture_zip(rows))
    df = load_county_pm25(2020)
    assert df.loc[df["county_fips"] == "01003", "pm25_monitor_count"].iloc[0] == 1


def test_load_county_pm25_filters_to_pm25_parameter_only(monkeypatch):
    rows = [
        ["01", "003", "0010", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 1997", 2020, 8.0],
        ["01", "003", "0010", 44201, 1, "Ozone", "Ozone 8-hour 2015", 2020, 0.05],
    ]
    monkeypatch.setattr("src.ingestion.epa_pm25.download_year", lambda year: _make_fixture_zip(rows))
    df = load_county_pm25(2020)
    assert df.loc[df["county_fips"] == "01003", "pm25_avg"].iloc[0] == pytest.approx(8.0)


def test_load_county_pm25_unmonitored_counties_absent_not_zero(monkeypatch):
    rows = [
        ["01", "003", "0010", PM25_PARAMETER_CODE, 1, "PM2.5 - Local Conditions", "PM25 24-hour 1997", 2020, 8.0],
    ]
    monkeypatch.setattr("src.ingestion.epa_pm25.download_year", lambda year: _make_fixture_zip(rows))
    df = load_county_pm25(2020)
    assert "01005" not in set(df["county_fips"])  # not present, not zero-filled


def test_load_county_pm25_raises_on_missing_columns(monkeypatch):
    bad_df = pd.DataFrame({"Foo": [1]})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("annual_conc_by_monitor_2020.csv", bad_df.to_csv(index=False))
    monkeypatch.setattr("src.ingestion.epa_pm25.download_year", lambda year: buf.getvalue())
    with pytest.raises(ValueError, match="missing expected column"):
        load_county_pm25(2020)
