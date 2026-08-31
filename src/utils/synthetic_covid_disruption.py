"""Generates SYNTHETIC multi-cause national/state/county mortality series
for pipeline development, while the real 8-series WONDER pull (6 test
causes + COVID-19 reference + drowning negative control, per
docs/research_protocol.md #3) is still pending.

THIS IS NOT REAL DATA -- see src/utils/synthetic_mortality.py's module
docstring for the full rationale; the same guardrails apply here
(SYNTHETIC_DATA_ACTIVE marker, no real conclusions). This module
generates series shaped to match the project's own PRE-REGISTERED
PRIORS (research_protocol.md #3), so the demo app shows internally
consistent, plausible-looking results -- it does not, and cannot,
validate whether those priors are correct. Only the real data pull can
do that.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BASELINE_YEARS = np.arange(1999, 2020)
POST_YEARS = np.arange(2020, 2025)
ALL_YEARS = np.concatenate([BASELINE_YEARS, POST_YEARS])

# Per-cause: baseline level/slope, and post-2020 shock shape. Shock shape is
# a list of 5 additive shifts (2020-2024) added on top of the extrapolated
# baseline trend. Chosen to reproduce the pre-registered prior for each
# cause (research_protocol.md #3) -- e.g. overdose spikes hard then reverses
# below trend, cancer and drowning show no shock at all.
CAUSE_SPECS = {
    "Diseases of heart": {
        "baseline_level": 168.0, "baseline_slope": -1.2,
        "shock": [22.0, 18.0, 6.0, 3.0, 1.0],  # spikes, mostly resolves
        "noise_sd": 1.5,
    },
    "Diabetes mellitus": {
        "baseline_level": 24.0, "baseline_slope": -0.15,
        "shock": [4.5, 5.0, 3.0, 2.8, 2.5],  # spikes, stays mildly elevated -> persists
        "noise_sd": 0.6,
    },
    "Alzheimer's disease": {
        "baseline_level": 31.0, "baseline_slope": 0.6,
        "shock": [9.0, 11.0, 8.0, 7.0, 6.5],  # large, sustained -> persists
        "noise_sd": 0.8,
    },
    "Cerebrovascular disease": {
        "baseline_level": 38.0, "baseline_slope": -0.5,
        "shock": [2.0, 1.5, 0.5, 0.0, -0.5],  # small, likely non-significant
        "noise_sd": 1.4,
    },
    "Drug overdose": {
        "baseline_level": 15.0, "baseline_slope": 1.1,
        "shock": [9.0, 12.0, 2.0, -4.0, -7.0],  # spikes hard, then reverses below trend
        "noise_sd": 0.7,
    },
    "Malignant neoplasms": {
        "baseline_level": 172.0, "baseline_slope": -1.8,
        "shock": [0.3, -0.2, 0.4, -0.1, 0.2],  # essentially flat -> null, by design
        "noise_sd": 1.6,
    },
    "Accidental drowning": {
        "baseline_level": 1.1, "baseline_slope": 0.0,
        "shock": [0.02, -0.03, 0.01, 0.0, -0.02],  # negative control: no shock
        "noise_sd": 0.05,
    },
}


def generate_national_series(seed: int = 42) -> pd.DataFrame:
    """One row per (cause, year), national-level age-adjusted rate per
    100k, for both the 1999-2019 baseline and 2020-2024 post-shock
    period, for the 6 test causes + drowning negative control (7 rows
    of CAUSE_SPECS -- COVID-19 itself is handled separately by
    generate_covid_reference_series since it has no baseline)."""
    rng = np.random.default_rng(seed)
    rows = []
    for cause, spec in CAUSE_SPECS.items():
        baseline_vals = spec["baseline_level"] + spec["baseline_slope"] * (BASELINE_YEARS - BASELINE_YEARS[0])
        baseline_vals = baseline_vals + rng.normal(0, spec["noise_sd"], size=len(BASELINE_YEARS))

        extrapolated = spec["baseline_level"] + spec["baseline_slope"] * (POST_YEARS - BASELINE_YEARS[0])
        post_vals = extrapolated + np.array(spec["shock"]) + rng.normal(0, spec["noise_sd"], size=len(POST_YEARS))

        for year, val in zip(BASELINE_YEARS, baseline_vals):
            rows.append({"cause": cause, "year": int(year), "age_adjusted_rate": max(float(val), 0.0)})
        for year, val in zip(POST_YEARS, post_vals):
            rows.append({"cause": cause, "year": int(year), "age_adjusted_rate": max(float(val), 0.0)})

    return pd.DataFrame(rows)


def generate_covid_reference_series(seed: int = 43) -> pd.DataFrame:
    """COVID-19 didn't exist before 2020, so it has no baseline trend --
    reference-only series, 2020-2024, for display alongside the 6 test
    causes (research_protocol.md #3)."""
    rng = np.random.default_rng(seed)
    shape = np.array([98.0, 78.0, 30.0, 14.0, 9.0])  # steep decline after the acute waves
    values = shape + rng.normal(0, 3.0, size=len(shape))
    return pd.DataFrame({
        "cause": "COVID-19",
        "year": POST_YEARS.astype(int),
        "age_adjusted_rate": np.maximum(values, 0.0),
    })


def generate_county_heterogeneity_data(
    county_fips_list: list[str],
    context_df: pd.DataFrame,
    context_col: str = "pct_uninsured_chr",
    effect_size: float = 40.0,
    causes: list[str] = ("Diabetes mellitus", "Drug overdose"),
    seed: int = 44,
) -> pd.DataFrame:
    """Per-county pre/post period rows for the heterogeneity demo, for a
    subset of causes. Disruption magnitude is deliberately correlated
    with a REAL context variable (context_col, from the already-ingested
    CHR&R/USDA/HRSA data -- default: uninsured rate) so the
    heterogeneity regression (src/analysis/heterogeneity.py) has an
    actual, findable relationship to detect. A first version of this
    function generated county-level noise that was *labeled* as
    correlated with a "poverty-like effect" but never actually linked
    to any real variable -- the regression correctly found nothing,
    which is a synthetic-fixture bug, not a finding, caught by running
    the full pipeline and inspecting output rather than by unit tests
    alone."""
    rng = np.random.default_rng(seed)
    context_lookup = context_df.set_index("county_fips")[context_col]
    context_mean = context_lookup.mean()

    rows = []
    for cause in causes:
        spec = CAUSE_SPECS[cause]
        for fips in county_fips_list:
            context_val = context_lookup.get(fips, context_mean)
            if pd.isna(context_val):
                context_val = context_mean
            county_effect = effect_size * (context_val - context_mean) + rng.normal(0, 1.5)
            for period, years in (("pre", BASELINE_YEARS[-3:]), ("post", POST_YEARS[:3])):
                base = spec["baseline_level"] + spec["baseline_slope"] * (years - BASELINE_YEARS[0])
                if period == "post":
                    base = base + np.mean(spec["shock"][:3]) + county_effect
                vals = base + rng.normal(0, spec["noise_sd"], size=len(years))
                for year, val in zip(years, vals):
                    rows.append({
                        "cause": cause, "county_fips": fips, "year": int(year),
                        "period": period, "age_adjusted_rate": max(float(val), 0.0),
                    })
    return pd.DataFrame(rows)
