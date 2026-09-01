"""Sensitivity analysis per research_protocol.md §8: re-fit the primary
excess-mortality method with three alternate modeling choices and check
whether any of them change which causes are flagged as significantly
disrupted. Does not modify or replace the primary results in
disruption_summary.parquet -- writes a separate comparison output.

Three axes, each independent of the others (only one choice is varied at
a time, primary held fixed on the others):
1. Baseline window: 1999-2019 (primary) vs. 2010-2019 (shorter, more recent).
2. Significance threshold: alpha=0.05 (primary) vs. alpha=0.01 (stricter).
3. Baseline trend shape: linear (primary) vs. quadratic (checks whether
   assuming a straight-line pre-pandemic trend, rather than a curved one,
   drives the results).
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.analysis.excess_mortality import benjamini_hochberg
from src.utils.config import OUTPUTS_MODELS
from scripts.run_covid_disruption_pipeline import (
    ACUTE_YEARS, TEST_CAUSES, NEGATIVE_CONTROL, load_real_national_data, analyze_cause,
)

ALT_BASELINE_START_YEAR = 2010
ALT_ALPHA = 0.01


def fit_quadratic_and_test(baseline_years, baseline_values, post_years, post_values, acute_years):
    """Analogous to fit_baseline_trend + compute_acute_pvalue, but with a
    degree-2 (quadratic) baseline trend instead of linear -- checks
    whether the primary method's results depend on assuming a linear
    pre-pandemic trend. Implemented directly via the general polynomial
    prediction-interval formula (SE_pred(x0) = residual_std * sqrt(1 +
    x0_row @ inv(X'X) @ x0_row.T)), since BaselineTrend/compute_deviations
    are linear-only by design. Returns (p_value, classification) where
    classification is binary ("Significant disruption" / "No significant
    disruption") -- re-deriving the full 3-way Persisted/Resolved/Reversed
    scheme under a quadratic baseline is out of scope for this check."""
    years = np.asarray(baseline_years, dtype=float)
    values = np.asarray(baseline_values, dtype=float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]
    n = len(years)

    X = np.vstack([np.ones_like(years), years, years**2]).T
    beta, *_ = np.linalg.lstsq(X, values, rcond=None)
    resid = values - X @ beta
    dof = n - 3
    residual_std = np.sqrt(np.sum(resid**2) / dof)
    xtx_inv = np.linalg.inv(X.T @ X)

    post_years = np.asarray(post_years, dtype=float)
    post_values = np.asarray(post_values, dtype=float)
    acute_mask = (post_years >= acute_years[0]) & (post_years <= acute_years[1]) & ~np.isnan(post_values)
    acute_years_arr = post_years[acute_mask]
    acute_values_arr = post_values[acute_mask]
    if len(acute_years_arr) == 0:
        return 1.0, "No significant disruption"

    expected = beta[0] + beta[1] * acute_years_arr + beta[2] * acute_years_arr**2
    mean_deviation = float(np.mean(acute_values_arr - expected))
    avg_year = float(np.mean(acute_years_arr))
    row = np.array([1, avg_year, avg_year**2])
    se_pred = residual_std * np.sqrt(1 + row @ xtx_inv @ row)
    se_of_mean = se_pred / np.sqrt(len(acute_years_arr))

    if se_of_mean == 0:
        p_value = 0.0 if mean_deviation != 0 else 1.0
    else:
        t_stat = mean_deviation / se_of_mean
        p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df=dof)))

    classification = "Significant disruption" if p_value < 0.05 else "No significant disruption"
    return p_value, classification


def main():
    print("Loading real national WONDER data for sensitivity check...")
    d76_df, d158_df, _ = load_real_national_data()

    rows = []

    # Axis 1: baseline window (1999-2019 vs 2010-2019)
    print(f"Axis 1: baseline window (1999 vs {ALT_BASELINE_START_YEAR})...")
    window_p = {}
    for cause in TEST_CAUSES + [NEGATIVE_CONTROL]:
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=1999)
        alt = analyze_cause(d76_df, d158_df, cause, baseline_start_year=ALT_BASELINE_START_YEAR)
        window_p[cause] = (primary["p_value"], alt["p_value"])
        rows.append({
            "cause": cause, "check": "baseline_window (1999 vs 2010)",
            "primary_classification": primary["persistence_class"], "primary_p_value": primary["p_value"],
            "alt_classification": alt["persistence_class"], "alt_p_value": alt["p_value"],
            "agrees": primary["persistence_class"] == alt["persistence_class"],
        })
    # The negative control's row above uses age_adjusted_rate for a
    # consistent comparison shape with the other causes -- but its actual
    # gate (main pipeline) uses raw death counts, since WONDER's 1-decimal
    # rate rounding makes the rate-based test oversensitive at this
    # cause's low magnitude (research_protocol.md's 2026-09-01 addenda).
    # Re-run on the real gating metric too, so a reader doesn't mistake
    # the rate-based row's disagreement for evidence the gate is unstable.
    nc_primary_counts = analyze_cause(d76_df, d158_df, NEGATIVE_CONTROL, value_col="deaths", baseline_start_year=1999)
    nc_alt_counts = analyze_cause(
        d76_df, d158_df, NEGATIVE_CONTROL, value_col="deaths", baseline_start_year=ALT_BASELINE_START_YEAR
    )
    rows.append({
        "cause": NEGATIVE_CONTROL, "check": "baseline_window (1999 vs 2010) [actual gate metric: deaths]",
        "primary_classification": nc_primary_counts["persistence_class"], "primary_p_value": nc_primary_counts["p_value"],
        "alt_classification": nc_alt_counts["persistence_class"], "alt_p_value": nc_alt_counts["p_value"],
        "agrees": nc_primary_counts["persistence_class"] == nc_alt_counts["persistence_class"],
    })

    # Axis 2: significance threshold (alpha=0.05 vs alpha=0.01)
    print(f"Axis 2: significance threshold (0.05 vs {ALT_ALPHA})...")
    for cause in TEST_CAUSES:
        primary = analyze_cause(d76_df, d158_df, cause, alpha=0.05)
        alt = analyze_cause(d76_df, d158_df, cause, alpha=ALT_ALPHA)
        rows.append({
            "cause": cause, "check": f"significance_threshold (0.05 vs {ALT_ALPHA})",
            "primary_classification": primary["persistence_class"], "primary_p_value": primary["p_value"],
            "alt_classification": alt["persistence_class"], "alt_p_value": alt["p_value"],
            "agrees": primary["persistence_class"] == alt["persistence_class"],
        })

    # Axis 3: baseline trend shape (linear vs quadratic)
    print("Axis 3: baseline trend shape (linear vs quadratic)...")
    for cause in TEST_CAUSES:
        primary = analyze_cause(d76_df, d158_df, cause)
        baseline = d76_df[(d76_df["cause"] == cause) & (d76_df["year"] <= 2019)].sort_values("year")
        post = d158_df[(d158_df["cause"] == cause) & (d158_df["year"] >= 2020)].sort_values("year")
        quad_p, quad_class = fit_quadratic_and_test(
            baseline["year"].to_numpy(), baseline["age_adjusted_rate"].to_numpy(),
            post["year"].to_numpy(), post["age_adjusted_rate"].to_numpy(), ACUTE_YEARS,
        )
        primary_binary = "No significant disruption" if primary["persistence_class"] == "No significant disruption" else "Significant disruption"
        rows.append({
            "cause": cause, "check": "baseline_trend_shape (linear vs quadratic)",
            "primary_classification": primary_binary, "primary_p_value": primary["p_value"],
            "alt_classification": quad_class, "alt_p_value": quad_p,
            "agrees": primary_binary == quad_class,
        })

    comparison_df = pd.DataFrame(rows)

    OUTPUTS_MODELS.mkdir(parents=True, exist_ok=True)
    comparison_df.to_parquet(OUTPUTS_MODELS / "sensitivity_check.parquet", index=False)

    print("\nSensitivity check results:")
    for check in comparison_df["check"].unique():
        sub = comparison_df[comparison_df["check"] == check]
        print(f"\n--- {check} ---")
        print(sub[["cause", "primary_classification", "primary_p_value", "alt_classification", "alt_p_value", "agrees"]].to_string(index=False))

    test_cause_rows = comparison_df[comparison_df["cause"].isin(TEST_CAUSES)]
    n_disagree = int((~test_cause_rows["agrees"]).sum())
    if n_disagree == 0:
        print("\nAll 6 test causes agree across every sensitivity axis checked.")
    else:
        print(f"\n{n_disagree} (cause, axis) combination(s) disagree -- see table above.")

    print(f"\nWrote {OUTPUTS_MODELS / 'sensitivity_check.parquet'}")


if __name__ == "__main__":
    main()
