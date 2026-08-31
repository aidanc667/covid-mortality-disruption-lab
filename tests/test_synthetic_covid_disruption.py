import numpy as np
import pandas as pd

from src.analysis.heterogeneity import compute_county_disruption, regress_disruption_on_context
from src.utils.synthetic_covid_disruption import generate_county_heterogeneity_data


def test_generate_county_heterogeneity_data_produces_detectable_correlation():
    counties = [f"{i:05d}" for i in range(200)]
    rng = np.random.default_rng(1)
    context_df = pd.DataFrame({
        "county_fips": counties,
        "pct_uninsured_chr": rng.uniform(0.05, 0.30, size=200),
    })

    county_df = generate_county_heterogeneity_data(
        counties, context_df=context_df, causes=["Diabetes mellitus"]
    )
    cause_df = county_df[county_df["cause"] == "Diabetes mellitus"]
    pre = cause_df[cause_df["period"] == "pre"]
    post = cause_df[cause_df["period"] == "post"]
    disruption_df = compute_county_disruption(pre, post, min_years_each_period=2)

    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["pct_uninsured_chr"])
    row = result.iloc[0]
    assert row["p_value"] < 0.01
    assert row["slope"] > 0  # effect_size is positive, so higher uninsured -> larger disruption
