import numpy as np
import pandas as pd

from scripts.run_covid_disruption_pipeline import analyze_cause, ACUTE_YEARS, FULL_PERIOD_YEARS


def _make_d76_d158(post_values, cause="Test cause"):
    """Builds minimal synthetic (d76_df, d158_df) frames analyze_cause can run
    against directly, bypassing real file loading. Baseline (1999-2019) is a
    near-flat line with tiny noise; post_values supplies 2020-2024's
    age_adjusted_rate so each scenario can control exactly when a deviation
    appears."""
    years = np.arange(1999, 2020)
    baseline_rate = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    d76_df = pd.DataFrame({"cause": cause, "year": years, "age_adjusted_rate": baseline_rate})
    d158_df = pd.DataFrame({
        "cause": cause, "year": [2020, 2021, 2022, 2023, 2024], "age_adjusted_rate": post_values,
    })
    return d76_df, d158_df


def test_analyze_cause_returns_full_period_fields():
    d76_df, d158_df = _make_d76_d158([20.0, 20.05, 20.1, 19.9, 20.0])
    result = analyze_cause(d76_df, d158_df, "Test cause")
    assert "full_period_p_value" in result
    assert "full_period_pct_deviation" in result


def test_full_period_pvalue_catches_a_delayed_disruption_the_acute_test_misses():
    """Mirrors the real Alzheimer's finding this project surfaced: acute
    years (2020-2021) sit right on trend while later years (2022-2024) drop
    well below it. The acute-only test should see nothing; pooling all five
    years should find it."""
    d76_df, d158_df = _make_d76_d158([20.0, 20.05, 15.0, 13.0, 11.0])
    result = analyze_cause(d76_df, d158_df, "Test cause")
    assert result["p_value"] > 0.5
    assert result["full_period_p_value"] < 0.01
    assert result["full_period_pct_deviation"] < 0


def test_full_period_pvalue_agrees_with_acute_when_disruption_is_immediate_and_sustained():
    d76_df, d158_df = _make_d76_d158([35.0, 36.0, 35.5, 36.5, 35.0])
    result = analyze_cause(d76_df, d158_df, "Test cause")
    assert result["p_value"] < 0.001
    assert result["full_period_p_value"] < 0.001
    assert result["full_period_pct_deviation"] > 0


def test_full_period_pvalue_uses_all_five_post_years():
    assert FULL_PERIOD_YEARS == (2020, 2024)
    assert ACUTE_YEARS == (2020, 2021)
