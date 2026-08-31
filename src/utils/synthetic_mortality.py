"""Generates a SYNTHETIC diabetes-mortality dataset, shaped exactly like a
real CDC WONDER "Underlying Cause of Death" export, for pipeline development
only — while the real data is blocked on the manual export step in
docs/manual_data_acquisition.md.

THIS IS NOT REAL DATA. Every trajectory, breakpoint, and death count here is
fabricated by a synthetic-data generator, not sourced from CDC. Per brief
section 56 ("do not fabricate results"), this must never be presented as, or
mistaken for, an actual research finding. Guardrails:

1. Output files are named with a SYNTHETIC_ prefix, never matching the real
   file glob a human would use for an actual WONDER export.
2. `mark_synthetic_active()` / `is_synthetic_active()` manage a repo-level
   marker file (`data/SYNTHETIC_DATA_ACTIVE`) that downstream code (the
   Streamlit app, report generator) MUST check and display a prominent
   warning banner whenever it exists — see app/components for the banner.
3. County FIPS codes are drawn from real counties (the CHR&R/USDA/HRSA data
   already ingested for real), so joins exercise real geography — but the
   mortality VALUES themselves are entirely fabricated.

Once a real WONDER export exists, delete the SYNTHETIC_* files, remove the
marker (`clear_synthetic_marker()`), and re-run the real pipeline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.config import DATA_RAW, PROJECT_ROOT

SYNTHETIC_MARKER = PROJECT_ROOT / "data" / "SYNTHETIC_DATA_ACTIVE"
SYNTHETIC_EXPORT_PATH = DATA_RAW / "cdc_wonder" / "SYNTHETIC_ucd_1999_2020.txt"


def mark_synthetic_active(note: str) -> None:
    SYNTHETIC_MARKER.parent.mkdir(parents=True, exist_ok=True)
    SYNTHETIC_MARKER.write_text(
        "This project is currently running on SYNTHETIC placeholder mortality data.\n"
        "No number downstream of this file represents a real research finding.\n"
        f"{note}\n"
    )


def clear_synthetic_marker() -> None:
    SYNTHETIC_MARKER.unlink(missing_ok=True)


def is_synthetic_active() -> bool:
    return SYNTHETIC_MARKER.exists()


def _simulate_county_trajectory(rng: np.random.Generator, years: np.ndarray, has_break: bool) -> np.ndarray:
    """Return a per-year 'true' age-adjusted rate for one county (per 100k),
    piecewise-linear if has_break, flat-trend otherwise. Purely synthetic."""
    baseline = rng.uniform(15, 35)
    if not has_break:
        slope = rng.uniform(-0.3, 0.3)
        return baseline + slope * (years - years[0])

    break_year = int(rng.normal(2010, 3))
    break_year = min(max(break_year, years[0] + 5), years[-1] - 5)
    pre_slope = rng.uniform(0.1, 0.6)
    post_slope = rng.uniform(-1.2, -0.3)
    rate = np.empty_like(years, dtype=float)
    for i, y in enumerate(years):
        if y <= break_year:
            rate[i] = baseline + pre_slope * (y - years[0])
        else:
            level_at_break = baseline + pre_slope * (break_year - years[0])
            rate[i] = level_at_break + post_slope * (y - break_year)
    return rate


def generate_synthetic_wonder_export(
    county_fips_list: list[str],
    county_names: dict[str, str] | None = None,
    year_range: tuple[int, int] = (1999, 2020),
    seed: int = 42,
) -> pd.DataFrame:
    """Build a synthetic county x year mortality table with the exact column
    names a real WONDER export uses (see src/ingestion/cdc_wonder.py
    EXPECTED_COLUMNS), including realistic suppression behavior."""
    rng = np.random.default_rng(seed)
    years = np.arange(year_range[0], year_range[1] + 1)
    rows = []

    for fips in county_fips_list:
        population_base = rng.lognormal(mean=10.5, sigma=1.3)  # ~ hundreds to low millions
        population_growth = rng.uniform(-0.005, 0.02)
        has_break = rng.random() < 0.55
        true_rate = _simulate_county_trajectory(rng, years, has_break)
        name = (county_names or {}).get(fips, f"County {fips}")

        for i, year in enumerate(years):
            population = max(int(population_base * (1 + population_growth) ** i), 200)
            expected_deaths = true_rate[i] / 100_000 * population
            deaths = rng.poisson(max(expected_deaths, 0.1))
            crude_rate = deaths / population * 100_000
            age_adjusted_rate = crude_rate * rng.uniform(0.92, 1.08)  # simplistic placeholder, not real standardization

            if deaths < 10:
                deaths_out, crude_out, aa_out = "Suppressed", "Suppressed", "Suppressed"
            elif deaths < 20:
                deaths_out, crude_out, aa_out = str(deaths), f"{crude_rate:.1f}", "Unreliable"
            else:
                deaths_out, crude_out, aa_out = str(deaths), f"{crude_rate:.1f}", f"{age_adjusted_rate:.1f}"

            rows.append({
                "County": f"{name}, SYNTH",
                "County Code": fips,
                "Year": year,
                "Deaths": deaths_out,
                "Population": population,
                "Crude Rate": crude_out,
                "Age Adjusted Rate": aa_out,
            })

    return pd.DataFrame(rows)


def write_synthetic_export(df: pd.DataFrame, path=SYNTHETIC_EXPORT_PATH) -> None:
    """Write in the same tab-delimited-with-footer shape
    src/ingestion/cdc_wonder._read_wonder_export expects to parse."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(df.columns)]
    for _, row in df.iterrows():
        lines.append("\t".join(str(v) for v in row))
    lines.append("---")
    lines.append('"Total"\t""\t""\t"0"\t"0"\t"0"\t"0"')
    path.write_text("\n".join(lines))
