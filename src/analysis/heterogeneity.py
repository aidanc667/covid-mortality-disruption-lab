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
