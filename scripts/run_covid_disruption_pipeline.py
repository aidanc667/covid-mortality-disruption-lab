"""Runs the full COVID disruption pipeline.

Both the national-level disruption/persistence/negative-control analysis
AND the county-level heterogeneity analysis now run on REAL CDC WONDER
data -- see docs/manual_data_acquisition.md for the 15 national exports
(7 D76 + 8 D158) and the 4 county-level exports (D76 + D158, diabetes and
drug overdose). Nothing in this pipeline is synthetic anymore; the marker
system (src/utils/synthetic_mortality.py) is kept only so the app can
detect and warn if someone re-runs an older synthetic-only script against
these outputs.
"""
from pathlib import Path

import pandas as pd

from src.analysis.excess_mortality import (
    fit_baseline_trend, compute_deviations, classify_persistence,
    compute_acute_pvalue, benjamini_hochberg,
)
from src.analysis.changepoints import fit_pelt, fit_binseg
from src.analysis.heterogeneity import compute_county_disruption, regress_disruption_on_context
from src.cleaning.bridging import estimate_vintage_offset, is_bridging_reliable
from src.ingestion.cdc_wonder import load_manual_export
from src.ingestion.county_health_rankings import load_year as load_chr_year
from src.utils.config import OUTPUTS_MODELS, DATA_RAW
from src.utils.synthetic_mortality import clear_synthetic_marker, SYNTHETIC_MARKER, SYNTHETIC_HETEROGENEITY_MARKER

HETEROGENEITY_CAUSES = ["Diabetes mellitus", "Drug overdose"]
HETEROGENEITY_PRE_YEARS = (2015, 2019)
HETEROGENEITY_POST_YEARS = (2020, 2024)
# County-level heterogeneity uses crude rate, not age-adjusted rate, for
# both periods: CDC WONDER does not offer age-adjustment at all when a
# D158 query is grouped by County (confirmed 2026-09-01 on the real
# diabetes and overdose pulls -- no Age Adjusted Rate columns, no
# "Standard Population" line in the query parameters). Using age-adjusted
# rate for one period and crude for the other would not be comparable, so
# both periods use crude_rate -- see research_protocol.md's 2026-09-01
# addendum for the resulting limitation (crude rate doesn't control for a
# county's own population-aging trajectory).
HETEROGENEITY_VALUE_COL = "crude_rate"

ACUTE_YEARS = (2020, 2021)
POST_ACUTE_YEARS = (2022, 2024)
OVERLAP_YEARS = [2018, 2019]
TEST_CAUSES = [
    "Diseases of heart", "Diabetes mellitus", "Alzheimer's disease",
    "Cerebrovascular disease", "Drug overdose", "Malignant neoplasms",
]
NEGATIVE_CONTROL = "Congenital malformations, deformations and chromosomal abnormalities"

CDC_WONDER_DIR = DATA_RAW / "cdc_wonder"

# cause (matching TEST_CAUSES/NEGATIVE_CONTROL exactly) -> file slug used in
# docs/manual_data_acquisition.md's naming convention.
CAUSE_SLUGS = {
    "Diseases of heart": "heart",
    "Diabetes mellitus": "diabetes",
    "Alzheimer's disease": "alzheimers",
    "Cerebrovascular disease": "cerebrovascular",
    "Drug overdose": "overdose",
    "Malignant neoplasms": "cancer",
    "Congenital malformations, deformations and chromosomal abnormalities": "congenital",
}


def load_real_national_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all 15 real national WONDER exports (7 D76 + 8 D158). Returns (d76_df, d158_df,
    covid_df) -- kept as separate vintage frames rather than pre-merged,
    since the excess-mortality analysis and the bridging check each need
    them handled differently (baseline trend uses D76 only; the "post"
    comparison uses D158's 2020-2024 only; the 2018-2019 overlap in both
    is used solely for bridging, not the disruption analysis itself, per
    research_protocol.md #4/#9)."""
    d76_frames = []
    for cause, slug in CAUSE_SLUGS.items():
        path = CDC_WONDER_DIR / f"d76_national_{slug}_1999_2019.csv"
        result = load_manual_export(subdir_files=[path], cause_label=cause)
        d76_frames.append(result.df)
    d76_df = pd.concat(d76_frames, ignore_index=True)

    d158_frames = []
    for cause, slug in CAUSE_SLUGS.items():
        path = CDC_WONDER_DIR / f"d158_national_{slug}_2018_2024.csv"
        result = load_manual_export(subdir_files=[path], cause_label=cause)
        d158_frames.append(result.df)
    covid_result = load_manual_export(
        subdir_files=[CDC_WONDER_DIR / "d158_national_covid19_2018_2024.csv"], cause_label="COVID-19"
    )
    d158_frames.append(covid_result.df)
    d158_df = pd.concat(d158_frames, ignore_index=True)

    covid_df = covid_result.df[covid_result.df["year"] >= 2020].copy()
    return d76_df, d158_df, covid_df


def load_real_county_data(cause: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load one heterogeneity cause's county-level pre/post exports.
    Returns (pre_df, post_df), each already filtered to its period's year
    range (the files are already period-scoped: D76 covers only
    HETEROGENEITY_PRE_YEARS, D158 only HETEROGENEITY_POST_YEARS, so no
    extra year filtering is needed beyond what's in the file)."""
    slug = CAUSE_SLUGS[cause]
    pre_result = load_manual_export(
        subdir_files=[CDC_WONDER_DIR / f"d76_county_{slug}_2015_2019.csv"], cause_label=cause
    )
    post_result = load_manual_export(
        subdir_files=[CDC_WONDER_DIR / f"d158_county_{slug}_2020_2024.csv"], cause_label=cause
    )
    return pre_result.df, post_result.df


def check_bridging(d76_df: pd.DataFrame, d158_df: pd.DataFrame) -> pd.DataFrame:
    """Vintage-bridging reliability check per research_protocol.md #9 --
    a hard gate. Returns one row per cause with the median relative offset
    and whether it's within the 10% reliability threshold."""
    rows = []
    for cause in list(CAUSE_SLUGS.keys()):
        old = d76_df[d76_df["cause"] == cause]
        new = d158_df[d158_df["cause"] == cause]
        offset_df = estimate_vintage_offset(old, new, overlap_years=OVERLAP_YEARS)
        reliable = is_bridging_reliable(offset_df)
        median_relative_offset = (
            (offset_df["offset"] / offset_df["age_adjusted_rate_old"]).abs().median()
        )
        rows.append({"cause": cause, "reliable": reliable, "median_relative_offset": median_relative_offset})
    return pd.DataFrame(rows)


def analyze_cause(d76_df: pd.DataFrame, d158_df: pd.DataFrame, cause: str, value_col: str = "age_adjusted_rate") -> dict:
    baseline = d76_df[(d76_df["cause"] == cause) & (d76_df["year"] <= 2019)].sort_values("year")
    post = d158_df[(d158_df["cause"] == cause) & (d158_df["year"] >= 2020)].sort_values("year")

    trend = fit_baseline_trend(baseline["year"].to_numpy(), baseline[value_col].to_numpy())
    deviations = compute_deviations(trend, post["year"].to_numpy(), post[value_col].to_numpy())
    p_value = compute_acute_pvalue(trend, deviations, ACUTE_YEARS)
    # The combined-period p-value test gates persistence classification,
    # not the per-year prediction-interval flags -- they're different
    # tests that can disagree on borderline cases (found during synthetic
    # testing on cerebrovascular disease: per-year flags said "not
    # significant" while the combined test's p=0.024 said it was). Both
    # numbers are shown together in the app, so they must agree.
    persistence = classify_persistence(
        deviations, ACUTE_YEARS, POST_ACUTE_YEARS, acute_significant=(p_value < 0.05)
    )

    # Cross-check series: D76 baseline concatenated with D158's post period
    # only (never the 2018-2019 overlap from both, which would duplicate
    # those years) -- raw, unadjusted, exactly like the primary method uses
    # each vintage. Per src/cleaning/bridging.py's docstring, bridging never
    # corrects the data, only measures the jump, so if the vintage jump is
    # large it can affect this cross-check too -- which is exactly what the
    # bridging reliability gate and negative control exist to catch.
    full_years = pd.concat([baseline["year"], post["year"]]).to_numpy()
    full_values = pd.concat([baseline[value_col], post[value_col]]).to_numpy()
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
    # Both national and county-level heterogeneity analysis are now REAL --
    # clear both markers.
    clear_synthetic_marker(SYNTHETIC_MARKER)
    clear_synthetic_marker(SYNTHETIC_HETEROGENEITY_MARKER)

    print("Loading real national WONDER data (15 files: 7 D76 + 8 D158)...")
    d76_df, d158_df, covid_df = load_real_national_data()
    print(f"  D76 (1999-2019): {len(d76_df)} rows across {d76_df['cause'].nunique()} causes")
    print(f"  D158 (2018-2024): {len(d158_df)} rows across {d158_df['cause'].nunique()} causes")

    print("Checking vintage-bridging reliability (2018-2019 overlap)...")
    bridging_df = check_bridging(d76_df, d158_df)
    print(bridging_df.to_string(index=False))
    unreliable_causes = bridging_df[~bridging_df["reliable"]]["cause"].tolist()
    if unreliable_causes:
        print(f"WARNING: bridging unreliable for {unreliable_causes} -- results for these causes "
              "should be treated with extra caution (research_protocol.md #9).")

    print("Running excess-mortality analysis per cause...")
    results = {cause: analyze_cause(d76_df, d158_df, cause) for cause in TEST_CAUSES}
    # The negative control's own age-adjusted rate is low-magnitude (~3/100k)
    # and WONDER only reports it to 1 decimal, which makes the OLS baseline
    # fit artificially tight and the gate oversensitive to rounding noise
    # (confirmed on the discarded drowning control, and again here: rate-based
    # p=0.013/"Persisted" vs. counts-based p=0.68/"No significant disruption" --
    # see research_protocol.md's 2026-09-01 addendum). The 6 test causes don't
    # have this problem (all >20/100k), so only the negative control's gate
    # decision uses raw counts; its charted series still uses rate for visual
    # consistency with the other 7 series.
    negative_control_result = analyze_cause(d76_df, d158_df, NEGATIVE_CONTROL)
    negative_control_gate_result = analyze_cause(d76_df, d158_df, NEGATIVE_CONTROL, value_col="deaths")

    if negative_control_gate_result["persistence_class"] != "No significant disruption":
        print(
            f"WARNING: negative control ({NEGATIVE_CONTROL}) shows "
            f"'{negative_control_gate_result['persistence_class']}' on raw death counts -- per "
            "research_protocol.md #7 method 4, this is a hard gate. Results on the other causes "
            "should not be trusted until this is resolved."
        )
    negative_control_passed = negative_control_gate_result["persistence_class"] == "No significant disruption"

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

    # National series for the Disruption Overview chart: D76 baseline +
    # D158 post period, per cause -- same construction as the analysis
    # itself, not the raw 2018-2019-duplicated files.
    national_rows = []
    for cause in TEST_CAUSES + [NEGATIVE_CONTROL]:
        baseline = d76_df[(d76_df["cause"] == cause) & (d76_df["year"] <= 2019)]
        post = d158_df[(d158_df["cause"] == cause) & (d158_df["year"] >= 2020)]
        national_rows.append(baseline[["cause", "year", "age_adjusted_rate"]])
        national_rows.append(post[["cause", "year", "age_adjusted_rate"]])
    national_df = pd.concat(national_rows, ignore_index=True)

    print("Running county-level heterogeneity analysis (REAL -- diabetes, overdose)...")
    chr_df = load_chr_year(2024)

    heterogeneity_rows = []
    for cause in HETEROGENEITY_CAUSES:
        pre, post = load_real_county_data(cause)
        print(
            f"  {cause}: pre {len(pre)} rows / {pre['county_fips'].nunique()} counties, "
            f"post {len(post)} rows / {post['county_fips'].nunique()} counties"
        )
        disruption_df = compute_county_disruption(
            pre, post, value_col=HETEROGENEITY_VALUE_COL, min_years_each_period=2
        )
        print(f"    {len(disruption_df)} counties with >=2 non-suppressed years in both periods")

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
    bridging_df.to_parquet(OUTPUTS_MODELS / "bridging_summary.parquet", index=False)

    negative_control_row = pd.DataFrame([{
        "cause": NEGATIVE_CONTROL,
        "persistence_class_rate": negative_control_result["persistence_class"],
        "p_value_rate": negative_control_result["p_value"],
        "persistence_class_counts": negative_control_gate_result["persistence_class"],
        "p_value_counts": negative_control_gate_result["p_value"],
        "gate_metric": "deaths",
        "passed": negative_control_passed,
        "note": (
            "Gate decision uses raw death counts, not age-adjusted rate: WONDER reports this "
            "cause's rate to only 1 decimal, which at its low magnitude (~3/100k) makes the "
            "rate-based baseline fit artificially tight and the test oversensitive to rounding "
            "noise. See research_protocol.md's 2026-09-01 addendum."
        ),
    }])
    negative_control_row.to_parquet(OUTPUTS_MODELS / "negative_control.parquet", index=False)

    print("\nDisruption summary (REAL DATA):")
    print(summary_df.to_string(index=False))
    print(f"\nNegative control ({NEGATIVE_CONTROL}) passed: {negative_control_passed}")
    print(f"\nWrote outputs to {OUTPUTS_MODELS}/")


if __name__ == "__main__":
    main()
