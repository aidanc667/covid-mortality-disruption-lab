"""County Health Rankings & Roadmaps (CHR&R) ingestion.

Unlike CDC WONDER, CHR&R has no API and no interactive-query restriction —
each annual release is a stable, directly downloadable CSV. URLs below were
verified by HTTP request (200 OK) during this project's build, not guessed;
CHR&R's URL pattern is NOT uniform across years (compare 2010-2019 vs.
2020+), which is exactly why this is an explicit map rather than a formula.

Column names were verified against the actual 2024 CSV header. CHR&R has
changed column names/measure availability across releases (see
docs/data_feasibility_audit.md and DATA_SOURCES.md #5) — `load_year()`
validates expected columns and raises with the real header if a given year's
file doesn't match, the same discipline used in src/ingestion/cdc_wonder.py.
"""
from __future__ import annotations

import pandas as pd
import requests

from src.utils.caching import is_cached, write_with_provenance
from src.utils.config import DATA_RAW

CHR_RAW_DIR = DATA_RAW / "chr"

# Verified (HTTP 200) during this project's build — see docs/data_feasibility_audit.md #5.
# Re-verify if CHR&R restructures its site; do not extend this map by guessing a pattern.
YEAR_URLS = {
    2010: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2010.csv",
    2011: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2011.csv",
    2012: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2012.csv",
    2013: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2013.csv",
    2014: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2014.csv",
    2015: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2015.csv",
    2016: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2016.csv",
    2017: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2017.csv",
    2018: "https://www.countyhealthrankings.org/sites/default/files/analytic_data2018_0.csv",
    2019: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2019.csv",
    2020: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2020_0.csv",
    2021: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2021.csv",
    2022: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2022.csv",
    2023: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2023_0.csv",
    2024: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2024.csv",
    2025: "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2025_v3.csv",
}

# Maps our internal variable name -> CHR&R's "<Measure> raw value" column,
# verified against the 2024 header. Per-year availability is NOT guaranteed
# (brief §5, audit §5/§6) — load_year() reports which of these are actually
# present rather than assuming.
VARIABLE_COLUMNS = {
    "pct_uninsured_chr": "Uninsured Adults raw value",
    "primary_care_ratio": "Primary Care Physicians raw value",
    "pct_smokers": "Adult Smoking raw value",
    "pct_obese": "Adult Obesity raw value",
    "pct_inactive": "Physical Inactivity raw value",
    "children_poverty_rate": "Children in Poverty raw value",
    "median_income_chr": "Median Household Income raw value",
    "pct_some_college": "Some College raw value",
    "food_environment_index": "Food Environment Index raw value",
    "severe_housing_cost_burden": "Severe Housing Cost Burden raw value",
    "pm25_chr": "Air Pollution - Particulate Matter raw value",
    "pct_rural": "% Rural raw value",
}

FIPS_COLUMN = "5-digit FIPS Code"

REQUIRED_ATTRIBUTION = (
    "University of Wisconsin Population Health Institute. "
    "County Health Rankings & Roadmaps {year}. www.countyhealthrankings.org"
)


def download_year(year: int) -> "Path":  # noqa: F821 (Path imported lazily below)
    from pathlib import Path

    if year not in YEAR_URLS:
        raise ValueError(f"No verified CHR&R URL for {year}. See YEAR_URLS in this module.")
    path: Path = CHR_RAW_DIR / f"chr_{year}.csv"
    if is_cached(path):
        return path
    resp = requests.get(YEAR_URLS[year], timeout=60)
    resp.raise_for_status()
    write_with_provenance(path, resp.content, source_url=YEAR_URLS[year], source_note=f"CHR&R {year} annual release")
    return path


def load_year(year: int) -> pd.DataFrame:
    """Download (or use cached) one year's CHR&R release, and extract the
    variables this project uses. Missing columns are reported, not
    fabricated: the returned DataFrame only contains columns that actually
    exist in that year's file, and a warning-worthy gap list is attached via
    `.attrs['missing_variables']`.
    """
    path = download_year(year)
    # CHR&R's analytic CSVs carry a second header row (short machine codes,
    # e.g. "v001_rawvalue") immediately below the human-readable header row
    # used here — confirmed by inspecting the raw 2024 file. Skip it, or it
    # gets read in as a bogus data row.
    df = pd.read_csv(path, low_memory=False, skiprows=[1])

    if FIPS_COLUMN not in df.columns:
        raise ValueError(
            f"CHR&R {year} file is missing the expected FIPS column "
            f"'{FIPS_COLUMN}'. Actual columns (first 10): {list(df.columns[:10])}. "
            "CHR&R may have renamed this field for this release year — verify "
            "and update FIPS_COLUMN handling in this module."
        )

    county_fips_col = "County FIPS Code"
    if county_fips_col not in df.columns:
        raise ValueError(
            f"CHR&R {year} file is missing '{county_fips_col}', needed to drop "
            "state/national aggregate rows (which use county code '000')."
        )
    # Rows with county code "000" are state or national aggregates (e.g.
    # 5-digit FIPS "00000" = US total, "01000" = Alabama total) mixed into
    # the same file as real counties — confirmed in the raw 2024 file.
    df = df[df[county_fips_col].astype(str).str.zfill(3) != "000"].copy()

    present = {name: col for name, col in VARIABLE_COLUMNS.items() if col in df.columns}
    missing = {name: col for name, col in VARIABLE_COLUMNS.items() if col not in df.columns}

    out = df[[FIPS_COLUMN] + list(present.values())].rename(
        columns={FIPS_COLUMN: "county_fips", **{v: k for k, v in present.items()}}
    )
    out["county_fips"] = out["county_fips"].astype(str).str.zfill(5)
    for col in present:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["release_year"] = year
    out.attrs["missing_variables"] = missing
    return out
