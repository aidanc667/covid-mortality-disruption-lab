import numpy as np
import pandas as pd
import pytest

from src.analysis.heterogeneity import (
    compute_county_disruption, regress_disruption_on_context,
    compute_selection_bias, check_within_sample_robustness,
)


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


def test_compute_county_disruption_attaches_county_name_when_present():
    # county_deep_dive.py needs a human-readable name for its selector --
    # counties are otherwise only identifiable by opaque 5-digit FIPS
    # codes, which nobody has memorized. Real CDC WONDER county exports
    # carry a "County" column (renamed "county" by
    # src/ingestion/cdc_wonder.load_manual_export); this must be threaded
    # through the pre/post aggregation to the final disruption table.
    pre = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "county": ["Autauga County, AL"] * 2 + ["Baldwin County, AL"] * 2,
        "year": [2018, 2019, 2018, 2019],
        "age_adjusted_rate": [20.0, 20.0, 30.0, 30.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "county": ["Autauga County, AL"] * 2 + ["Baldwin County, AL"] * 2,
        "year": [2020, 2021, 2020, 2021],
        "age_adjusted_rate": [25.0, 25.0, 30.0, 32.0],
    })
    result = compute_county_disruption(pre, post)
    assert result[result["county_fips"] == "01001"].iloc[0]["county_name"] == "Autauga County, AL"
    assert result[result["county_fips"] == "01003"].iloc[0]["county_name"] == "Baldwin County, AL"


def test_compute_county_disruption_missing_county_column_does_not_raise():
    # Older synthetic fixtures and this module's own other tests don't
    # carry a "county" column at all -- must degrade gracefully, not KeyError.
    pre = pd.DataFrame({
        "county_fips": ["01001", "01001"], "year": [2018, 2019], "age_adjusted_rate": [20.0, 20.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001"], "year": [2020, 2021], "age_adjusted_rate": [25.0, 25.0],
    })
    result = compute_county_disruption(pre, post)
    assert "county_name" not in result.columns or result["county_name"].isna().all()


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


def test_compute_selection_bias_detects_systematic_difference():
    # Included counties are all low-rurality; excluded are all high-rurality --
    # this is exactly the real pattern found in the county heterogeneity stage
    # (suppression disproportionately excludes small, rural counties).
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003", "01005"], "disruption": [1.0, 2.0, 3.0]})
    context_df = pd.DataFrame({
        "county_fips": ["01001", "01003", "01005", "01007", "01009", "01011"],
        "pct_rural": [0.1, 0.2, 0.3, 0.8, 0.9, 1.0],
    })
    result = compute_selection_bias(disruption_df, context_df, "pct_rural")
    assert result["n_included"] == 3
    assert result["n_excluded"] == 3
    assert result["mean_included"] == pytest.approx(0.2, abs=1e-9)
    assert result["mean_excluded"] == pytest.approx(0.9, abs=1e-9)


def test_compute_selection_bias_handles_no_exclusions():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "pct_rural": [0.1, 0.2]})
    result = compute_selection_bias(disruption_df, context_df, "pct_rural")
    assert result["n_excluded"] == 0
    assert np.isnan(result["mean_excluded"])


def test_check_within_sample_robustness_detects_relationship_driven_by_one_half():
    # True relationship exists only among the lower half of context_var;
    # upper half is flat noise. The full-sample slope alone would hide this.
    rng = np.random.default_rng(0)
    n = 100
    context_var = np.concatenate([rng.uniform(0, 0.5, n // 2), rng.uniform(0.5, 1.0, n // 2)])
    disruption = np.concatenate([
        -20.0 * rng.uniform(0, 0.5, n // 2) + rng.normal(0, 0.2, n // 2),  # strong real relationship
        rng.normal(0, 5.0, n // 2),  # pure noise, no relationship
    ])
    counties = [f"{i:05d}" for i in range(n)]
    disruption_df = pd.DataFrame({"county_fips": counties, "disruption": disruption})
    context_df = pd.DataFrame({"county_fips": counties, "pct_rural": context_var})

    result = check_within_sample_robustness(disruption_df, context_df, "pct_rural")
    lower = result[result["half"] == "lower_half"].iloc[0]
    upper = result[result["half"] == "upper_half"].iloc[0]
    assert lower["p_value"] < 0.05
    assert upper["p_value"] > 0.05


def test_check_within_sample_robustness_flags_too_small_half():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "pct_rural": [0.1, 0.9]})
    result = check_within_sample_robustness(disruption_df, context_df, "pct_rural")
    assert result["n"].sum() >= 2
    assert np.isnan(result[result["half"] == "lower_half"].iloc[0]["slope"])
