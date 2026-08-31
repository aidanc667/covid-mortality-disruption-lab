"""HRSA Area Health Resources File (AHRF) ingestion — healthcare access.

URL and structure verified directly during this project's build (downloaded
and inspected the live 2024-2025 release): the ZIP contains several topical
CSVs sharing a `fips_st_cnty` key; this module reads only the health-
professions file (`AHRF2025hp.csv`, ~1,900 columns) and pulls the specific
primary-care physician count column, rather than loading the whole file.

AHRF column names are cryptic and versioned by data year (e.g. the "23"
suffix below means "2023 data," which is what the 2024-2025 AHRF release
actually contains for this field — confirmed by inspecting the real header).
These will need updating for future AHRF releases; VARIABLE_COLUMNS exists
so that update is a one-line diff, not a re-discovery.
"""
from __future__ import annotations

import zipfile

import pandas as pd
import requests

from src.utils.caching import is_cached, write_with_provenance
from src.utils.config import DATA_RAW

HRSA_RAW_DIR = DATA_RAW / "hrsa"

# Verified (HTTP 200, real ZIP contents inspected) during this project's build.
AHRF_ZIP_URL = "https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip"
AHRF_HP_MEMBER = "NCHWA-2024-2025+AHRF+COUNTY+CSV/AHRF2025hp.csv"

FIPS_COLUMN = "fips_st_cnty"

# name -> AHRF column, verified against the live 2024-2025 hp.csv header.
# "23" = 2023 source-year data, per AHRF's own naming convention (brief's
# per-variable-reference-year caveat, see DATA_SOURCES.md #8).
VARIABLE_COLUMNS = {
    "primary_care_physicians_count": "phys_nf_prim_care_pc_exc_rsdt_23",
}


def download_ahrf() -> bytes:
    path = HRSA_RAW_DIR / "ahrf_2024_2025.zip"
    if is_cached(path):
        return path.read_bytes()
    resp = requests.get(AHRF_ZIP_URL, timeout=180)
    resp.raise_for_status()
    write_with_provenance(path, resp.content, source_url=AHRF_ZIP_URL, source_note="HRSA AHRF 2024-2025, county CSV bundle")
    return resp.content


def load_primary_care_physicians() -> pd.DataFrame:
    import io

    content = download_ahrf()
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        if AHRF_HP_MEMBER not in names:
            raise ValueError(
                f"Expected member '{AHRF_HP_MEMBER}' not found in the AHRF zip. "
                f"Actual members: {names}. HRSA may have renamed the internal "
                "folder/file for a newer release — update AHRF_HP_MEMBER in "
                "src/ingestion/hrsa.py."
            )
        wanted_cols = [FIPS_COLUMN] + list(VARIABLE_COLUMNS.values())
        header = pd.read_csv(zf.open(AHRF_HP_MEMBER), nrows=0)
        missing = [c for c in wanted_cols if c not in header.columns]
        if missing:
            raise ValueError(
                f"AHRF health-professions file is missing expected column(s) {missing}. "
                "HRSA revises these column names' year suffix with each release "
                "(e.g. '..._23' -> '..._24') — update VARIABLE_COLUMNS in "
                "src/ingestion/hrsa.py to the current names, then re-run."
            )
        df = pd.read_csv(zf.open(AHRF_HP_MEMBER), usecols=wanted_cols, dtype={FIPS_COLUMN: str})

    df = df.rename(columns={FIPS_COLUMN: "county_fips", **{v: k for k, v in VARIABLE_COLUMNS.items()}})
    df["county_fips"] = df["county_fips"].str.zfill(5)
    return df
