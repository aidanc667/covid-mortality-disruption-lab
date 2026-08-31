"""EPA AQS PM2.5 ingestion — monitored counties only.

Verified during this project's build (real file downloaded and inspected):
EPA does NOT publish a ready-made county-level PM2.5 file. The closest
official product is `annual_conc_by_monitor_<year>.zip` from
https://aqs.epa.gov/aqsweb/airdata/download_files.html — one row per
monitor, per pollutant-standard, per year. County-level PM2.5 must be
derived by filtering to PM2.5 (Parameter Code 88101, "PM2.5 - Local
Conditions", FRM/FEM mass) and averaging across monitors within a county.

Per docs/research_protocol.md #5 and #8, this is retained ONLY as a
monitored-counties-only sensitivity covariate — roughly 20% of US counties
have a monitor at all (docs/data_feasibility_audit.md #6). Counties without
a monitor are NOT imputed; they get `pm25_monitored = False` and a NaN
value, never a filled-in estimate.
"""
from __future__ import annotations

import pandas as pd
import requests

from src.utils.caching import is_cached, write_with_provenance
from src.utils.config import DATA_RAW

EPA_RAW_DIR = DATA_RAW / "epa_pm25"

PM25_PARAMETER_CODE = 88101  # "PM2.5 - Local Conditions" (FRM/FEM), verified in the real file header.


def _year_url(year: int) -> str:
    return f"https://aqs.epa.gov/aqsweb/airdata/annual_conc_by_monitor_{year}.zip"


def download_year(year: int) -> bytes:
    path = EPA_RAW_DIR / f"annual_conc_by_monitor_{year}.zip"
    if is_cached(path):
        return path.read_bytes()
    url = _year_url(year)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    write_with_provenance(path, resp.content, source_url=url, source_note=f"EPA AQS annual monitor concentrations, {year}")
    return resp.content


def load_county_pm25(year: int) -> pd.DataFrame:
    """Return one row per monitored county for `year`: county_fips,
    pm25_avg (mean of that county's monitors' annual arithmetic means),
    pm25_monitor_count, pm25_monitored=True. Counties absent from the
    result are unmonitored for that year, not zero/missing-imputed."""
    import io
    import zipfile

    content = download_year(year)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        member = zf.namelist()[0]
        df = pd.read_csv(zf.open(member), dtype={"State Code": str, "County Code": str})

    required = {"State Code", "County Code", "Parameter Code", "Arithmetic Mean", "Site Num"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"EPA AQS annual monitor file for {year} is missing expected column(s) {missing}. "
            f"Actual columns: {list(df.columns)}. EPA may have changed this file's layout — "
            "update src/ingestion/epa_pm25.py accordingly."
        )

    pm25 = df[df["Parameter Code"] == PM25_PARAMETER_CODE].copy()
    # Same monitor can appear multiple times for different "Pollutant Standard"
    # thresholds (e.g. 1997 vs 2006/2012 NAAQS) with an identical Arithmetic
    # Mean (confirmed in the real file) — dedupe per monitor before averaging
    # across monitors, or multi-standard monitors would be double-counted.
    pm25 = pm25.drop_duplicates(subset=["State Code", "County Code", "Site Num", "POC"])

    pm25["county_fips"] = pm25["State Code"] + pm25["County Code"]
    county = (
        pm25.groupby("county_fips")["Arithmetic Mean"]
        .agg(pm25_avg="mean", pm25_monitor_count="count")
        .reset_index()
    )
    county["pm25_monitored"] = True
    return county
