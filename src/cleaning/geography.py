"""FIPS/GEOID standardization and validation, per brief section 7.

Every dataset in this project is joined on `county_fips` (5-digit GEOID:
2-digit state FIPS + 3-digit county FIPS), never on county name. This module
is the single place that validates and normalizes that key.
"""
from __future__ import annotations

import pandas as pd

# Valid state FIPS codes: 50 states + DC (11) + PR (72) + other territories
# WONDER/Census may include. Kept narrow (states + DC + PR) since this
# project's scope is U.S. county mortality; extend deliberately if a source
# is found to report other territories, not by silently accepting anything.
VALID_STATE_FIPS = {f"{i:02d}" for i in range(1, 57)} | {"72"}
VALID_STATE_FIPS -= {"03", "07", "14", "43", "52"}  # retired/reserved codes


def standardize_fips(raw: pd.Series) -> pd.Series:
    """Coerce a column of county codes (int, float, or str) to a 5-character
    zero-padded GEOID string. Does not validate — call validate_fips after."""
    return raw.astype(str).str.extract(r"(\d+)")[0].str.zfill(5)


def validate_fips(fips: pd.Series) -> pd.DataFrame:
    """Return a boolean-flagged report, one row per input value, never raising
    — invalid rows must be surfaced to the data-quality report, not dropped
    silently (brief section 9)."""
    fips = fips.astype(str)
    state_part = fips.str[:2]
    report = pd.DataFrame({
        "county_fips": fips,
        "is_correct_length": fips.str.len() == 5,
        "is_numeric": fips.str.match(r"^\d{5}$"),
        "has_valid_state_prefix": state_part.isin(VALID_STATE_FIPS),
    })
    report["is_valid"] = (
        report["is_correct_length"] & report["is_numeric"] & report["has_valid_state_prefix"]
    )
    return report


def find_duplicate_county_years(df: pd.DataFrame, fips_col: str = "county_fips", year_col: str = "year") -> pd.DataFrame:
    """Return rows that share a (county_fips, year) key more than once —
    a merge or ingestion bug, never expected in a clean panel."""
    dup_mask = df.duplicated(subset=[fips_col, year_col], keep=False)
    return df.loc[dup_mask].sort_values([fips_col, year_col])


def find_appearing_disappearing_counties(df: pd.DataFrame, fips_col: str = "county_fips", year_col: str = "year") -> pd.DataFrame:
    """Flag counties that don't appear in every year of the panel's own year
    range — could be a real boundary change (brief section 7/12) or a data
    gap; either way it must be surfaced, not assumed away."""
    all_years = sorted(df[year_col].unique())
    by_county = df.groupby(fips_col)[year_col].apply(set)
    full_set = set(all_years)
    return pd.DataFrame({
        "county_fips": by_county.index,
        "years_present": by_county.apply(len),
        "years_expected": len(full_set),
        "missing_years": by_county.apply(lambda ys: sorted(full_set - ys)),
    }).query("years_present != years_expected")
