"""Runs the full COVID disruption pipeline on SYNTHETIC multi-cause data
(src/utils/synthetic_covid_disruption.py), while the real 8-series WONDER
pull is still pending. Precomputes results to outputs/models/ so the
Streamlit app never re-runs the analysis on page load (brief section 46).

THIS PRODUCES NO REAL RESEARCH RESULTS -- see
src/utils/synthetic_mortality.py and src/utils/synthetic_covid_disruption.py
for the synthetic-data guardrails. Re-run against real data once the 8
WONDER exports exist, by swapping generate_national_series()/
generate_county_heterogeneity_data() for real ingested panels -- every
downstream function (fit_baseline_trend, compute_deviations, etc.) takes
plain years/values arrays or county-keyed DataFrames, so nothing else in
this script needs to change.
"""
import numpy as np
import pandas as pd

from src.analysis.excess_mortality import (
    fit_baseline_trend, compute_deviations, classify_persistence,
    compute_acute_pvalue, benjamini_hochberg,
)
from src.analysis.changepoints import fit_pelt, fit_binseg
from src.analysis.heterogeneity import compute_county_disruption, regress_disruption_on_context
from src.ingestion.county_health_rankings import load_year as load_chr_year
from src.utils.config import OUTPUTS_MODELS
from src.utils.synthetic_covid_disruption import (
    generate_national_series, generate_covid_reference_series, generate_county_heterogeneity_data,
)
from src.utils.synthetic_mortality import mark_synthetic_active

ACUTE_YEARS = (2020, 2021)
POST_ACUTE_YEARS = (2022, 2024)
TEST_CAUSES = [
    "Diseases of heart", "Diabetes mellitus", "Alzheimer's disease",
    "Cerebrovascular disease", "Drug overdose", "Malignant neoplasms",
]
NEGATIVE_CONTROL = "Accidental drowning"


def analyze_cause(national_df: pd.DataFrame, cause: str) -> dict:
    series = national_df[national_df["cause"] == cause].sort_values("year")
    baseline = series[series["year"] <= 2019]
    post = series[series["year"] >= 2020]

    trend = fit_baseline_trend(baseline["year"].to_numpy(), baseline["age_adjusted_rate"].to_numpy())
    deviations = compute_deviations(trend, post["year"].to_numpy(), post["age_adjusted_rate"].to_numpy())
    p_value = compute_acute_pvalue(trend, deviations, ACUTE_YEARS)
    # The combined-period p-value test gates persistence classification,
    # not the per-year prediction-interval flags -- they're different
    # tests that can disagree on borderline cases (found by running this
    # pipeline against cerebrovascular disease: per-year flags said "not
    # significant" while the combined test's p=0.024 said it was). Both
    # numbers are shown together in the app, so they must agree.
    persistence = classify_persistence(
        deviations, ACUTE_YEARS, POST_ACUTE_YEARS, acute_significant=(p_value < 0.05)
    )

    full_years = series["year"].to_numpy()
    full_values = series["age_adjusted_rate"].to_numpy()
    pelt_bps = fit_pelt(full_years, full_values, min_size=3, penalty=3.0)
    binseg_bps = fit_binseg(full_years, full_values, min_size=3, n_bkps=1)
    cross_check_near_2020 = any(abs(bp - 2020) <= 2 for bp in pelt_bps + binseg_bps)

    return {
        "cause": cause,
        "persistence_class": persistence,
        "p_value": p_value,
        "cross_check_confirms_2020": cross_check_near_2020,
        "deviations": deviations,
        "trend": trend,
    }


def main():
    mark_synthetic_active(
        "Generated for the multi-cause COVID disruption pipeline, matching the "
        "pre-registered priors in docs/research_protocol.md #3."
    )

    print("Generating synthetic multi-cause national series...")
    national_df = generate_national_series()
    covid_df = generate_covid_reference_series()

    print("Running excess-mortality analysis per cause...")
    results = {cause: analyze_cause(national_df, cause) for cause in TEST_CAUSES}
    negative_control_result = analyze_cause(national_df, NEGATIVE_CONTROL)

    if negative_control_result["persistence_class"] != "No significant disruption":
        print(
            f"WARNING: negative control (drowning) shows "
            f"'{negative_control_result['persistence_class']}' -- per research_protocol.md #7 "
            "method 4, this is a hard gate. Results on the other causes should not be trusted "
            "until this is resolved."
        )
    negative_control_passed = negative_control_result["persistence_class"] == "No significant disruption"

    print("Applying FDR correction across the 6-cause family...")
    p_values = {cause: results[cause]["p_value"] for cause in TEST_CAUSES}
    fdr_survives = benjamini_hochberg(p_values)

    summary_rows = []
    for cause in TEST_CAUSES:
        r = results[cause]
        summary_rows.append({
            "cause": cause,
            "persistence_class": r["persistence_class"],
            "p_value": r["p_value"],
            "fdr_significant": fdr_survives[cause],
            "cross_check_confirms_2020": r["cross_check_confirms_2020"],
        })
    summary_df = pd.DataFrame(summary_rows)

    deviations_rows = []
    for cause in TEST_CAUSES + [NEGATIVE_CONTROL]:
        r = results[cause] if cause in results else negative_control_result
        for d in r["deviations"]:
            deviations_rows.append({
                "cause": cause, "year": d.year, "observed": d.observed, "expected": d.expected,
                "deviation": d.deviation, "pi_low": d.pi_low, "pi_high": d.pi_high,
                "significant": d.significant,
            })
    deviations_df = pd.DataFrame(deviations_rows)

    print("Running county-level heterogeneity analysis (diabetes, overdose)...")
    chr_df = load_chr_year(2024)
    sample_counties = chr_df.sample(n=300, random_state=7)["county_fips"].tolist()
    county_df = generate_county_heterogeneity_data(sample_counties, context_df=chr_df)

    heterogeneity_rows = []
    for cause in ["Diabetes mellitus", "Drug overdose"]:
        cause_df = county_df[county_df["cause"] == cause]
        pre = cause_df[cause_df["period"] == "pre"]
        post = cause_df[cause_df["period"] == "post"]
        disruption_df = compute_county_disruption(pre, post, min_years_each_period=2)

        context_vars = ["pct_uninsured_chr", "pct_smokers", "pct_obese", "median_income_chr", "pct_rural"]
        reg_result = regress_disruption_on_context(disruption_df, chr_df, context_vars)
        reg_result["cause"] = cause
        heterogeneity_rows.append(reg_result)

        disruption_df["cause"] = cause
        disruption_df.to_parquet(
            OUTPUTS_MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet", index=False
        )
    heterogeneity_summary = pd.concat(heterogeneity_rows, ignore_index=True)
    het_p_values = dict(zip(
        heterogeneity_summary["variable"] + "__" + heterogeneity_summary["cause"],
        heterogeneity_summary["p_value"].fillna(1.0),
    ))
    het_fdr = benjamini_hochberg(het_p_values)
    heterogeneity_summary["fdr_significant"] = [
        het_fdr[f"{v}__{c}"] for v, c in zip(heterogeneity_summary["variable"], heterogeneity_summary["cause"])
    ]

    OUTPUTS_MODELS.mkdir(parents=True, exist_ok=True)
    national_df.to_parquet(OUTPUTS_MODELS / "national_mortality_series.parquet", index=False)
    covid_df.to_parquet(OUTPUTS_MODELS / "covid_reference_series.parquet", index=False)
    summary_df.to_parquet(OUTPUTS_MODELS / "disruption_summary.parquet", index=False)
    deviations_df.to_parquet(OUTPUTS_MODELS / "disruption_deviations.parquet", index=False)
    heterogeneity_summary.to_parquet(OUTPUTS_MODELS / "heterogeneity_summary.parquet", index=False)

    negative_control_row = pd.DataFrame([{
        "persistence_class": negative_control_result["persistence_class"],
        "p_value": negative_control_result["p_value"],
        "passed": negative_control_passed,
    }])
    negative_control_row.to_parquet(OUTPUTS_MODELS / "negative_control.parquet", index=False)

    print("\nDisruption summary:")
    print(summary_df.to_string(index=False))
    print(f"\nNegative control (drowning) passed: {negative_control_passed}")
    print(f"\nWrote outputs to {OUTPUTS_MODELS}/")


if __name__ == "__main__":
    main()
