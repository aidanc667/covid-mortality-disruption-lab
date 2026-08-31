"""USDA ERS Food Environment Atlas ingestion.

URL and structure verified directly during this project's build (downloaded
and inspected the live 2025 release): a ZIP containing a single long-format
`StateAndCountyData.csv` (FIPS, State, County, Variable_Code, Value) plus a
`VariableList.csv` code dictionary. No API; direct download only.

Important, verified limitation not to lose downstream: `FOODINSEC_*`
(household food insecurity) is a STATE-level three-year-average statistic
that the Atlas broadcasts onto every county row in that state — every county
in a given state carries an identical value. It is NOT county-level
variation and must not be treated as one; retained here as
`food_insecurity_rate_state_level` to make that explicit rather than naming
it as if it varied by county.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

from src.utils.caching import is_cached, write_with_provenance
from src.utils.config import DATA_RAW

USDA_RAW_DIR = DATA_RAW / "usda"

# Verified (HTTP 200, real ZIP contents inspected) during this project's build.
CSV_ZIP_URL = "https://www.ers.usda.gov/media/5570/food-environment-atlas-csv-files.zip?v=30339"

# Our variable name -> Atlas Variable_Code, verified against the live 2025 VariableList.csv.
# LACCESS/GROC/FFR vary by county; FOODINSEC does not (see module docstring).
VARIABLE_CODES = {
    "pct_low_access_pop": "PCT_LACCESS_POP19",
    "pct_low_income_low_access": "PCT_LACCESS_LOWI19",
    "grocery_stores_per_1000": "GROCPTH20",
    "fast_food_per_1000": "FFRPTH20",
    "food_insecurity_rate_state_level": "FOODINSEC_21_23",
}


def download_atlas() -> bytes:
    path = USDA_RAW_DIR / "food_environment_atlas.zip"
    if is_cached(path):
        return path.read_bytes()
    resp = requests.get(CSV_ZIP_URL, timeout=120)
    resp.raise_for_status()
    write_with_provenance(path, resp.content, source_url=CSV_ZIP_URL, source_note="USDA ERS Food Environment Atlas, CSV bundle")
    return resp.content


def load_atlas() -> pd.DataFrame:
    """Return a county-level wide table of the variables in VARIABLE_CODES.
    Raises with the actual codes found if USDA has renamed/retired one of
    ours (they rev the year suffix on these codes with each release, e.g.
    LACCESS_POP19 -> LACCESS_POP24 — this WILL need updating periodically;
    that is a deliberate, visible failure rather than a silent gap)."""
    content = download_atlas()
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        raw = pd.read_csv(zf.open("StateAndCountyData.csv"), dtype={"FIPS": str})

    found_codes = set(raw["Variable_Code"].unique())
    missing = {name: code for name, code in VARIABLE_CODES.items() if code not in found_codes}
    if missing:
        raise ValueError(
            f"Food Environment Atlas is missing expected variable code(s): {missing}. "
            "USDA revises the year suffix on these codes with each release "
            "(e.g. LACCESS_POP19 -> a later vintage) — update VARIABLE_CODES "
            "in src/ingestion/usda_food_atlas.py to the current codes from "
            "the downloaded VariableList.csv, then re-run."
        )

    wide = raw[raw["Variable_Code"].isin(VARIABLE_CODES.values())].pivot_table(
        index="FIPS", columns="Variable_Code", values="Value", aggfunc="first"
    )
    wide = wide.rename(columns={code: name for name, code in VARIABLE_CODES.items()})
    wide.columns.name = None
    wide = wide.reset_index().rename(columns={"FIPS": "county_fips"})
    wide["county_fips"] = wide["county_fips"].astype(str).str.zfill(5)
    return wide
