"""Runs the full detection + heterogeneity pipeline end-to-end on the
SYNTHETIC mortality fixture (src/utils/synthetic_mortality.py), joined with
REAL context data already ingested (CHR&R, USDA, HRSA). Precomputes results
to outputs/models/ so the Streamlit app never re-runs change-point models on
page load (brief section 46).

THIS PRODUCES NO REAL RESEARCH RESULTS. Every number under "mortality" here
traces back to fabricated data. Re-run against a real WONDER export by
generating that export (docs/manual_data_acquisition.md), clearing the
synthetic marker (src/utils/synthetic_mortality.clear_synthetic_marker),
and re-running this script — the analysis code itself does not change.
"""
import numpy as np
import pandas as pd

from src.ingestion.cdc_wonder import load_manual_export
from src.ingestion.county_health_rankings import load_year as load_chr_year
from src.ingestion.usda_food_atlas import load_atlas
from src.ingestion.hrsa import load_primary_care_physicians
from src.cleaning.mortality import compute_county_eligibility, build_county_series
from src.analysis.changepoints import fit_segmented_regression, fit_pelt, fit_binseg, summarize_method_agreement
from src.analysis.trajectory import classify_trajectory
from src.utils.config import DATA_PROCESSED, OUTPUTS_MODELS
from src.utils.synthetic_mortality import is_synthetic_active


def main():
    if not is_synthetic_active():
        print("WARNING: synthetic marker not set — refusing to guess whether input data is real. "
              "If this IS real WONDER data, call mark_synthetic_active() removal explicitly reviewed, "
              "or adjust this script once a real-data path exists.")

    print("Loading mortality panel...")
    mortality = load_manual_export()
    df = mortality.df
    print(f"  {mortality.n_rows} county-year rows, {df['county_fips'].nunique()} counties, "
          f"{mortality.n_suppressed} suppressed, {mortality.n_unreliable} unreliable")

    print("Computing county eligibility (research_protocol.md #6)...")
    eligibility = compute_county_eligibility(df)
    eligible_counties = eligibility.loc[eligibility["data_eligible_changepoint"], "county_fips"].tolist()
    print(f"  {len(eligible_counties)}/{len(eligibility)} counties eligible for change-point modeling")

    print("Running change-point detection (segmented regression, PELT, binary segmentation)...")
    results = []
    for fips in eligible_counties:
        series = build_county_series(df, fips)
        years = series["year"].to_numpy()
        rates = series["age_adjusted_rate"].to_numpy(dtype=float)

        seg = fit_segmented_regression(years, rates)
        pelt_bps = fit_pelt(years, rates)
        binseg_bps = fit_binseg(years, rates)

        agreement = summarize_method_agreement({
            "segmented_regression": seg.breakpoint_year,
            "pelt": pelt_bps[0] if pelt_bps else None,
            "binseg": binseg_bps[0] if binseg_bps else None,
        })

        results.append({
            "county_fips": fips,
            "breakpoint_year": seg.breakpoint_year,
            "pre_slope": seg.pre_slope,
            "post_slope": seg.post_slope,
            "slope_diff": seg.slope_diff,
            "p_value": seg.p_value,
            "has_significant_break": seg.has_significant_break,
            "n_obs": seg.n_obs,
            "pelt_breakpoint": pelt_bps[0] if pelt_bps else None,
            "binseg_breakpoint": binseg_bps[0] if binseg_bps else None,
            "method_agreement_count": agreement["agreement_count"],
            "method_agreement_summary": agreement["summary"],
            "trajectory_class": classify_trajectory(seg),
        })

    changepoints = pd.DataFrame(results)
    changepoints = eligibility.merge(changepoints, on="county_fips", how="left")
    # Ineligible counties keep trajectory_class as an explicit non-classification, never blank/zero.
    changepoints["trajectory_class"] = changepoints["trajectory_class"].fillna("Insufficient data")

    print("Merging real context data (CHR&R, USDA, HRSA)...")
    chr_df = load_chr_year(2024)
    usda_df = load_atlas()
    hrsa_df = load_primary_care_physicians()

    context = (
        changepoints[["county_fips"]]
        .merge(chr_df, on="county_fips", how="left")
        .merge(usda_df, on="county_fips", how="left")
        .merge(hrsa_df, on="county_fips", how="left")
    )

    OUTPUTS_MODELS.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    changepoints.to_parquet(OUTPUTS_MODELS / "county_changepoints.parquet", index=False)
    context.to_parquet(OUTPUTS_MODELS / "county_context.parquet", index=False)
    df.to_parquet(DATA_PROCESSED / "mortality_panel.parquet", index=False)

    print(f"\nTrajectory class distribution (eligible counties only):")
    print(changepoints[changepoints["data_eligible_changepoint"]]["trajectory_class"].value_counts())
    print(f"\nWrote: {OUTPUTS_MODELS / 'county_changepoints.parquet'}")
    print(f"Wrote: {OUTPUTS_MODELS / 'county_context.parquet'}")
    print(f"Wrote: {DATA_PROCESSED / 'mortality_panel.parquet'}")


if __name__ == "__main__":
    main()
