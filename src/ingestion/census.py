"""Census Bureau ingestion: PEP annual population + ACS 5-Year subject tables.

Unlike CDC WONDER, the Census API fully supports county-level, scriptable
queries (confirmed in docs/data_feasibility_audit.md #5/#6) — no manual step
needed here.

Requires a free API key (register at https://api.census.gov/data/key_signup.html
— this project does not submit that signup on the user's behalf, since it
requires their email address). Read from the CENSUS_API_KEY environment
variable; never hardcoded.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

from src.utils.caching import is_cached, load_meta, write_with_provenance
from src.utils.config import DATA_RAW

CENSUS_RAW_DIR = DATA_RAW / "census"

# ACS 5-Year subject/data-profile tables used by this project, per
# DATA_SOURCES.md #4 and docs/data_dictionary.md. Each maps to the variable
# codes actually needed, not the full table (Census subject tables have
# hundreds of columns per table; pulling only named variables keeps requests
# small and the mapping auditable).
ACS_VARIABLES = {
    "median_household_income": "S1901_C01_012E",
    "poverty_rate": "S1701_C03_001E",
    "pct_bachelors_plus": "S1501_C02_015E",
    "pct_uninsured": "S2701_C05_001E",
}

EARLIEST_ACS5_END_YEAR = 2009  # 2005-2009 vintage, per audit #4


class CensusAPIKeyMissing(RuntimeError):
    pass


def _get_api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise CensusAPIKeyMissing(
            "CENSUS_API_KEY is not set. Register a free key at "
            "https://api.census.gov/data/key_signup.html and set it in your "
            "environment (e.g. `export CENSUS_API_KEY=...`) before running "
            "Census ingestion."
        )
    return key


def fetch_pep_population(year: int) -> pd.DataFrame:
    """County-level total population for one year from the Population
    Estimates Program. Returns columns: county_fips, year, population."""
    key = _get_api_key()
    url = f"https://api.census.gov/data/{year}/pep/population"
    params = {"get": "POP,NAME", "for": "county:*", "in": "state:*", "key": key}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["county_fips"] = df["state"] + df["county"]
    df["year"] = year
    df = df.rename(columns={"POP": "population"})
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    return df[["county_fips", "year", "population"]]


def fetch_acs5_variables(end_year: int) -> pd.DataFrame:
    """County-level ACS 5-Year estimates for one window, ending `end_year`
    (e.g. end_year=2015 -> the 2011-2015 window). Column names carry the
    window explicitly per docs/data_dictionary.md's alignment rule."""
    if end_year < EARLIEST_ACS5_END_YEAR:
        raise ValueError(
            f"ACS 5-Year estimates do not exist before the {EARLIEST_ACS5_END_YEAR - 4}-"
            f"{EARLIEST_ACS5_END_YEAR} vintage (requested end_year={end_year}). "
            "See docs/data_feasibility_audit.md #6 for the pre-2005 data gap."
        )
    key = _get_api_key()
    var_codes = list(ACS_VARIABLES.values())
    url = f"https://api.census.gov/data/{end_year}/acs/acs5/subject"
    params = {"get": ",".join(var_codes), "for": "county:*", "in": "state:*", "key": key}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["county_fips"] = df["state"] + df["county"]

    window_start = end_year - 4
    rename = {code: f"{name}_acs5_{window_start}_{end_year}" for name, code in ACS_VARIABLES.items()}
    df = df.rename(columns=rename)
    for col in rename.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")

    keep = ["county_fips"] + list(rename.values())
    return df[keep]


def cache_raw_pep(year: int) -> pd.DataFrame:
    """Fetch (or load from cache) PEP population for one year, with provenance."""
    path = CENSUS_RAW_DIR / f"pep_population_{year}.csv"
    if is_cached(path):
        return pd.read_csv(path, dtype={"county_fips": str})
    df = fetch_pep_population(year)
    write_with_provenance(
        path, df.to_csv(index=False).encode(),
        source_url=f"https://api.census.gov/data/{year}/pep/population",
        source_note=f"PEP county population, {year}",
    )
    return df
