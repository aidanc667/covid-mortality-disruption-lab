"""Sensitivity analysis per research_protocol.md §8: re-fit the primary
excess-mortality method with four alternate modeling choices and check
whether any of them change which causes are flagged as significantly
disrupted. Does not modify or replace the primary results in
disruption_summary.parquet -- writes a separate comparison output.

Four axes, each independent of the others (only one choice is varied at
a time, primary held fixed on the others):
1. Baseline window: 1999-2019 (primary) vs. 2010-2019 (shorter, more recent).
2. Significance threshold: alpha=0.05 (primary) vs. alpha=0.01 (stricter).
3. Baseline trend shape: linear (primary) vs. quadratic (checks whether
   assuming a straight-line pre-pandemic trend, rather than a curved one,
   drives the results).
4. Trend scale: straight line in the rate (primary) vs. straight line in
   log(rate), i.e. a steady percentage change per year (added 2026-10-19).
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.analysis.excess_mortality import (
    benjamini_hochberg,
    compute_acute_pvalue,
    compute_deviations,
    fit_baseline_trend,
)
from src.utils.config import OUTPUTS_MODELS
from scripts.run_covid_disruption_pipeline import (
    ACUTE_YEARS, TEST_CAUSES, NEGATIVE_CONTROL, load_real_national_data, analyze_cause,
    BASELINE_START_YEAR_OVERRIDES,
)

ALT_BASELINE_START_YEAR = 2010
ALT_ALPHA = 0.01


def fit_quadratic_and_test(baseline_years, baseline_values, post_years, post_values, acute_years):
    """Analogous to fit_baseline_trend + compute_acute_pvalue, but with a
    degree-2 (quadratic) baseline trend instead of linear -- checks
    whether the primary method's results depend on assuming a linear
    pre-pandemic trend. Implemented directly via the general polynomial
    formula for the mean of k prediction errors from one fitted curve,
    SE = residual_std * sqrt(1/k + c @ inv(X'X) @ c) with c the mean of the
    acute years' design rows, since BaselineTrend/compute_deviations are
    linear-only by design. Years are centered on 2000 before squaring, which
    gives the same fit with a far better-conditioned X'X. Returns (p_value, classification) where
    classification is binary ("Significant disruption" / "No significant
    disruption") -- re-deriving the full 3-way Persisted/Resolved/Reversed
    scheme under a quadratic baseline is out of scope for this check."""
    years = np.asarray(baseline_years, dtype=float)
    values = np.asarray(baseline_values, dtype=float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]
    n = len(years)

    years = years - 2000.0
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

    acute_x = acute_years_arr - 2000.0
    rows = np.vstack([np.ones_like(acute_x), acute_x, acute_x**2]).T
    mean_deviation = float(np.mean(acute_values_arr - rows @ beta))
    c = rows.mean(axis=0)
    se_of_mean = residual_std * np.sqrt(1 / len(acute_x) + c @ xtx_inv @ c)

    if se_of_mean == 0:
        p_value = 0.0 if mean_deviation != 0 else 1.0
    else:
        t_stat = mean_deviation / se_of_mean
        p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df=dof)))

    classification = "Significant disruption" if p_value < 0.05 else "No significant disruption"
    return p_value, classification


def fit_loglinear_and_test(baseline_years, baseline_values, post_years, post_values, acute_years):
    """Same acute-window test as the primary method, but with a straight
    line fit to log(rate) instead of the rate itself: a trend that falls (or
    rises) by a steady percentage each year rather than a steady amount.
    Added 2026-10-19 as a fourth sensitivity axis (research_protocol.md's
    p-value correction addendum). Returns (p_value, binary classification),
    like fit_quadratic_and_test."""
    baseline_values = np.asarray(baseline_values, dtype=float)
    post_values = np.asarray(post_values, dtype=float)
    trend = fit_baseline_trend(baseline_years, np.log(baseline_values))
    deviations = compute_deviations(trend, np.asarray(post_years), np.log(post_values))
    p_value = compute_acute_pvalue(trend, deviations, acute_years)
    classification = "Significant disruption" if p_value < 0.05 else "No significant disruption"
    return p_value, classification


def main():
    print("Loading real national WONDER data for sensitivity check...")
    d76_df, d158_df, _ = load_real_national_data()

    rows = []

    # Axis 1: baseline window. For the 4 causes still on the original
    # 1999-2019 window, primary=1999 / alt=2010 as before. For the 2 causes
    # already corrected to a 2010-2019 primary window (research_protocol.md's
    # 2026-09-01 baseline-window addendum), primary/alt are flipped so this
    # axis still tests "does window choice matter" around whichever window
    # is actually in use, rather than comparing two windows neither of which
    # is the real primary.
    print("Axis 1: baseline window...")
    window_p = {}
    for cause in TEST_CAUSES + [NEGATIVE_CONTROL]:
        primary_start = BASELINE_START_YEAR_OVERRIDES.get(cause, 1999)
        alt_start = 1999 if cause in BASELINE_START_YEAR_OVERRIDES else ALT_BASELINE_START_YEAR
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=primary_start)
        alt = analyze_cause(d76_df, d158_df, cause, baseline_start_year=alt_start)
        window_p[cause] = (primary["p_value"], alt["p_value"])
        rows.append({
            # Check name stays constant across all causes -- app pages and
            # the report filter on this exact string -- even though which
            # year is "primary" vs "alt" flips for the 2 corrected causes.
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

    # Axis 2: significance threshold (alpha=0.05 vs alpha=0.01). Both sides
    # use each cause's actual primary baseline window (1999, or 2010 for the
    # 2 corrected causes) -- only alpha varies.
    print(f"Axis 2: significance threshold (0.05 vs {ALT_ALPHA})...")
    for cause in TEST_CAUSES:
        primary_start = BASELINE_START_YEAR_OVERRIDES.get(cause, 1999)
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=primary_start, alpha=0.05)
        alt = analyze_cause(d76_df, d158_df, cause, baseline_start_year=primary_start, alpha=ALT_ALPHA)
        rows.append({
            "cause": cause, "check": f"significance_threshold (0.05 vs {ALT_ALPHA})",
            "primary_classification": primary["persistence_class"], "primary_p_value": primary["p_value"],
            "alt_classification": alt["persistence_class"], "alt_p_value": alt["p_value"],
            "agrees": primary["persistence_class"] == alt["persistence_class"],
        })

    # Axis 3: baseline trend shape (linear vs quadratic). Both sides fit on
    # the SAME baseline window (each cause's actual primary) -- otherwise
    # this would compare "linear on 2010-2019" against "quadratic on
    # 1999-2019" for the 2 corrected causes, which isn't a fair test of
    # trend shape alone.
    print("Axis 3: baseline trend shape (linear vs quadratic)...")
    for cause in TEST_CAUSES:
        primary_start = BASELINE_START_YEAR_OVERRIDES.get(cause, 1999)
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=primary_start)
        baseline = d76_df[(d76_df["cause"] == cause) & (d76_df["year"] >= primary_start) & (d76_df["year"] <= 2019)].sort_values("year")
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

    # Axis 4: trend scale (straight line in the rate vs. in log(rate)). Same
    # baseline window as primary, like axis 3, so only the trend's scale varies.
    print("Axis 4: trend scale (linear vs log-linear)...")
    for cause in TEST_CAUSES:
        primary_start = BASELINE_START_YEAR_OVERRIDES.get(cause, 1999)
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=primary_start)
        baseline = d76_df[(d76_df["cause"] == cause) & (d76_df["year"] >= primary_start) & (d76_df["year"] <= 2019)].sort_values("year")
        post = d158_df[(d158_df["cause"] == cause) & (d158_df["year"] >= 2020)].sort_values("year")
        log_p, log_class = fit_loglinear_and_test(
            baseline["year"].to_numpy(), baseline["age_adjusted_rate"].to_numpy(),
            post["year"].to_numpy(), post["age_adjusted_rate"].to_numpy(), ACUTE_YEARS,
        )
        primary_binary = "No significant disruption" if primary["persistence_class"] == "No significant disruption" else "Significant disruption"
        rows.append({
            "cause": cause, "check": "trend_scale (linear vs log-linear)",
            "primary_classification": primary_binary, "primary_p_value": primary["p_value"],
            "alt_classification": log_class, "alt_p_value": log_p,
            "agrees": primary_binary == log_class,
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
