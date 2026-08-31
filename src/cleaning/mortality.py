"""Applies the county change-point eligibility criteria fixed in
docs/research_protocol.md #6, to the loaded WONDER panel (real or, while
mortality data is blocked, the synthetic fixture in
src/utils/synthetic_mortality.py — the eligibility logic itself doesn't
care which).
"""
from __future__ import annotations

import pandas as pd

from src.utils.config import (
    MIN_NONSUPPRESSED_YEARS,
    MIN_COUNTY_POPULATION,
    PRIMARY_WINDOW,
)


def compute_county_eligibility(df: pd.DataFrame) -> pd.DataFrame:
    """Given the standardized WONDER panel (columns from
    src/ingestion/cdc_wonder.load_manual_export), return one row per county
    with the fields needed to decide change-point eligibility, per
    research_protocol.md #6:
      - at least MIN_NONSUPPRESSED_YEARS with a usable (non-suppressed,
        non-unreliable) age-adjusted rate
      - mid-period population >= MIN_COUNTY_POPULATION

    Ineligible counties are RETAINED with data_eligible_changepoint=False,
    never dropped from the table (brief section 6/9) — dropping them here
    would erase them from the Data Quality and Breakpoint Explorer views
    the app is required to show.
    """
    start, end = PRIMARY_WINDOW
    window = df[(df["year"] >= start) & (df["year"] <= end)].copy()

    window["usable_rate"] = ~(
        window["age_adjusted_rate_suppressed"] | window["age_adjusted_rate_unreliable"]
    )

    by_county = window.groupby("county_fips").agg(
        n_years_present=("year", "nunique"),
        n_usable_years=("usable_rate", "sum"),
        mid_period_population=("population", "median"),
    ).reset_index()

    by_county["meets_year_threshold"] = by_county["n_usable_years"] >= MIN_NONSUPPRESSED_YEARS
    by_county["meets_population_threshold"] = by_county["mid_period_population"] >= MIN_COUNTY_POPULATION
    by_county["data_eligible_changepoint"] = (
        by_county["meets_year_threshold"] & by_county["meets_population_threshold"]
    )
    return by_county


def build_county_series(df: pd.DataFrame, county_fips: str) -> pd.DataFrame:
    """Return one county's year-ordered series (year, age_adjusted_rate),
    with suppressed/unreliable years as NaN — never coerced to zero or
    interpolated, per research_protocol.md #8. Downstream change-point code
    must handle these gaps explicitly (e.g. by excluding them from the
    fitted series while keeping the year axis intact for plotting)."""
    county = df[df["county_fips"] == county_fips].sort_values("year")
    out = county[["year", "age_adjusted_rate", "age_adjusted_rate_suppressed", "age_adjusted_rate_unreliable"]].copy()
    out.loc[out["age_adjusted_rate_suppressed"] | out["age_adjusted_rate_unreliable"], "age_adjusted_rate"] = pd.NA
    return out.reset_index(drop=True)
