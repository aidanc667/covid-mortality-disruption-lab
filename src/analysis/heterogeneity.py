"""County-level heterogeneity analysis: does COVID-era mortality
disruption magnitude correlate with socioeconomic/healthcare-access
context variables? Per design spec section 5.7. Associational only --
see docs/research_protocol.md's causal-language policy; nothing here
establishes that a context variable caused a difference in disruption.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

MIN_SAMPLE_SIZE = 10


def compute_county_disruption(
    pre_period: pd.DataFrame,
    post_period: pd.DataFrame,
    value_col: str = "age_adjusted_rate",
    min_years_each_period: int = 2,
) -> pd.DataFrame:
    """Per county: mean rate in pre_period vs. post_period, and their
    difference. Only counties with at least min_years_each_period
    non-missing observations in EACH period are included -- this manages
    suppression rather than letting a single noisy year drive the
    comparison (research_protocol.md #6 applies the same discipline to
    the primary change-point eligibility criteria)."""

    def summarize(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
        g = df.groupby("county_fips")[value_col].agg(["mean", "count"])
        g.columns = [f"{value_col}_{suffix}", f"n_years_{suffix}"]
        return g

    pre = summarize(pre_period, "pre")
    post = summarize(post_period, "post")
    merged = pre.join(post, how="inner").reset_index()

    merged = merged[
        (merged["n_years_pre"] >= min_years_each_period)
        & (merged["n_years_post"] >= min_years_each_period)
    ].copy()

    merged["disruption"] = merged[f"{value_col}_post"] - merged[f"{value_col}_pre"]
    return merged


def compute_selection_bias(
    disruption_df: pd.DataFrame, context_df: pd.DataFrame, context_var: str
) -> dict:
    """Compares context_var (e.g. rurality) between counties INCLUDED in
    disruption_df and every other county present in context_df but
    excluded from it. compute_county_disruption's min_years_each_period
    filter drops counties with too much suppression, which is not random
    -- small, low-death-count counties are disproportionately suppressed,
    and small counties are disproportionately rural. If included and
    excluded counties differ systematically on the very variable being
    regressed against, that variable's regression result describes only
    the counties that survived the filter, not the full county
    population -- a real selection-bias risk found in this project's own
    data (research_protocol.md's 2026-09-01 addendum), not a hypothetical
    one, which is why this is a real check rather than a footnote."""
    included_fips = set(disruption_df["county_fips"])
    included = context_df[context_df["county_fips"].isin(included_fips)]
    excluded = context_df[~context_df["county_fips"].isin(included_fips)]
    mean_excluded = float(excluded[context_var].mean()) if len(excluded) else float("nan")
    return {
        "context_var": context_var,
        "n_included": len(included),
        "n_excluded": len(excluded),
        "mean_included": float(included[context_var].mean()),
        "mean_excluded": mean_excluded,
    }


def check_within_sample_robustness(
    disruption_df: pd.DataFrame, context_df: pd.DataFrame, context_var: str
) -> pd.DataFrame:
    """Splits the INCLUDED sample into two halves by context_var (above/
    below its own median within the included sample) and re-fits the
    bivariate regression of disruption on context_var separately within
    each half, alongside the full-sample fit. A relationship that only
    holds in one half is not the same finding as one that holds evenly
    across the variable's whole range -- the full-sample slope/p-value
    alone can't distinguish these, which is exactly how this project's
    own rurality finding turned out to differ by cause (diabetes:
    relationship holds and strengthens in the more-rural half; drug
    overdose: relationship is driven almost entirely by the less-rural
    half and is not significant among more-rural counties)."""
    merged = disruption_df.merge(context_df, on="county_fips", how="inner").dropna(
        subset=[context_var, "disruption"]
    )
    median = merged[context_var].median() if len(merged) else float("nan")

    rows = []
    halves = [
        ("full", merged),
        ("upper_half", merged[merged[context_var] >= median]),
        ("lower_half", merged[merged[context_var] < median]),
    ]
    for label, subset in halves:
        if len(subset) < MIN_SAMPLE_SIZE:
            rows.append({
                "half": label, "n": len(subset), "mean_context_var": float("nan"),
                "slope": float("nan"), "p_value": float("nan"),
            })
            continue
        slope, intercept, r, p, se = stats.linregress(subset[context_var], subset["disruption"])
        rows.append({
            "half": label, "n": len(subset), "mean_context_var": float(subset[context_var].mean()),
            "slope": slope, "p_value": p,
        })
    return pd.DataFrame(rows)


def regress_disruption_on_context(
    disruption_df: pd.DataFrame, context_df: pd.DataFrame, context_vars: list[str]
) -> pd.DataFrame:
    """Bivariate OLS of disruption magnitude on each context variable in
    turn (one row per variable): slope, p-value, sample size. FDR
    correction across context_vars is the caller's responsibility, via
    src.analysis.excess_mortality.benjamini_hochberg keyed by variable
    name -- this function does not apply it itself, matching how the
    6-cause disruption tests are corrected separately in the
    orchestration layer (design spec section 5.5)."""
    merged = disruption_df.merge(context_df, on="county_fips", how="inner")

    rows = []
    for var in context_vars:
        sub = merged[["disruption", var]].dropna()
        if len(sub) < MIN_SAMPLE_SIZE:
            rows.append({"variable": var, "slope": np.nan, "p_value": np.nan, "n": len(sub)})
            continue
        slope, intercept, r, p, se = stats.linregress(sub[var], sub["disruption"])
        rows.append({"variable": var, "slope": slope, "p_value": p, "n": len(sub)})

    return pd.DataFrame(rows)
