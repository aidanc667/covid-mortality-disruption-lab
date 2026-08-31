import numpy as np
import pandas as pd
import pytest

from src.analysis.heterogeneity import compute_county_disruption, regress_disruption_on_context


def test_compute_county_disruption_computes_difference_correctly():
    pre = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "year": [2018, 2019, 2018, 2019],
        "age_adjusted_rate": [20.0, 20.0, 30.0, 30.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "year": [2020, 2021, 2020, 2021],
        "age_adjusted_rate": [25.0, 25.0, 30.0, 32.0],
    })
    result = compute_county_disruption(pre, post)
    row_01001 = result[result["county_fips"] == "01001"].iloc[0]
    assert row_01001["disruption"] == pytest.approx(5.0)
    row_01003 = result[result["county_fips"] == "01003"].iloc[0]
    assert row_01003["disruption"] == pytest.approx(1.0)


def test_compute_county_disruption_excludes_insufficient_years():
    pre = pd.DataFrame({
        "county_fips": ["01001"], "year": [2019], "age_adjusted_rate": [20.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001"], "year": [2020, 2021], "age_adjusted_rate": [25.0, 26.0],
    })
    result = compute_county_disruption(pre, post, min_years_each_period=2)
    assert len(result) == 0  # only 1 pre-period year, below the minimum


def test_regress_disruption_on_context_detects_known_linear_relationship():
    rng = np.random.default_rng(0)
    counties = [f"{i:05d}" for i in range(100)]
    poverty = rng.uniform(5, 30, size=100)
    disruption = 2.0 * poverty + rng.normal(0, 0.5, size=100)  # true slope = 2.0, low noise

    disruption_df = pd.DataFrame({"county_fips": counties, "disruption": disruption})
    context_df = pd.DataFrame({"county_fips": counties, "poverty_rate": poverty})

    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    row = result[result["variable"] == "poverty_rate"].iloc[0]
    assert row["slope"] == pytest.approx(2.0, abs=0.1)
    assert row["p_value"] < 0.001
    assert row["n"] == 100


def test_regress_disruption_on_context_handles_missing_variable_data():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "poverty_rate": [15.0, np.nan]})
    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    assert result.iloc[0]["n"] == 1


def test_regress_disruption_on_context_flags_too_small_sample():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "poverty_rate": [15.0, 18.0]})
    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    row = result.iloc[0]
    assert np.isnan(row["slope"])
    assert np.isnan(row["p_value"])
