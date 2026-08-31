import numpy as np
import pytest

from src.analysis.excess_mortality import fit_baseline_trend


def test_fit_baseline_trend_recovers_known_linear_relationship():
    years = np.arange(1999, 2020)
    values = 2.0 + 0.5 * (years - 1999)  # exact linear, no noise
    trend = fit_baseline_trend(years, values)
    assert trend.slope == pytest.approx(0.5, abs=1e-9)
    assert trend.intercept == pytest.approx(2.0 - 0.5 * 1999, abs=1e-6)
    assert trend.residual_std == pytest.approx(0.0, abs=1e-9)
    assert trend.n == 21


def test_fit_baseline_trend_ignores_nan_values():
    years = np.arange(1999, 2010)
    values = 2.0 + 0.5 * (years - 1999)
    values = values.astype(float)
    values[3] = np.nan  # a suppressed year
    trend = fit_baseline_trend(years, values)
    assert trend.n == 10
    assert trend.slope == pytest.approx(0.5, abs=1e-9)


def test_fit_baseline_trend_raises_with_too_few_points():
    years = np.array([2018, 2019])
    values = np.array([20.0, 21.0])
    with pytest.raises(ValueError, match="at least 3"):
        fit_baseline_trend(years, values)


from src.analysis.excess_mortality import compute_deviations


def test_compute_deviations_flat_trend_no_shock_not_significant():
    years = np.arange(1999, 2020)
    values_noisy = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values_noisy)
    result = compute_deviations(trend, np.array([2020]), np.array([20.05]))
    assert result[0].significant is False


def test_compute_deviations_detects_large_upward_shock():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    result = compute_deviations(trend, np.array([2020]), np.array([35.0]))
    assert result[0].significant is True
    assert result[0].deviation == pytest.approx(35.0 - result[0].expected)


def test_compute_deviations_handles_nan_observed_as_not_significant():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    result = compute_deviations(trend, np.array([2020]), np.array([np.nan]))
    assert result[0].significant is False
    assert np.isnan(result[0].observed)


def test_compute_deviations_prediction_interval_widens_with_extrapolation_distance():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    near = compute_deviations(trend, np.array([2020]), np.array([20.0]))[0]
    far = compute_deviations(trend, np.array([2050]), np.array([20.0]))[0]
    near_width = near.pi_high - near.pi_low
    far_width = far.pi_high - far.pi_low
    assert far_width > near_width


from src.analysis.excess_mortality import DeviationResult, classify_persistence


def _dev(year, deviation, significant):
    return DeviationResult(
        year=year, observed=20.0 + deviation, expected=20.0, deviation=deviation,
        pi_low=19.0, pi_high=21.0, significant=significant,
    )


def test_classify_persistence_no_significant_acute_disruption():
    deviations = [_dev(2020, 0.1, False), _dev(2021, -0.2, False), _dev(2022, 0.0, False)]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "No significant disruption"


def test_classify_persistence_persisted_same_direction():
    deviations = [
        _dev(2020, 5.0, True), _dev(2021, 6.0, True),
        _dev(2022, 4.0, True), _dev(2023, 4.5, True), _dev(2024, 5.0, True),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Persisted"


def test_classify_persistence_resolved_when_post_acute_not_significant():
    deviations = [
        _dev(2020, 5.0, True), _dev(2021, 6.0, True),
        _dev(2022, 0.1, False), _dev(2023, -0.1, False), _dev(2024, 0.05, False),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Resolved"


def test_classify_persistence_reversed_when_sign_flips():
    deviations = [
        _dev(2020, 8.0, True), _dev(2021, 9.0, True),
        _dev(2022, -6.0, True), _dev(2023, -7.0, True), _dev(2024, -5.0, True),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Reversed"


from src.analysis.excess_mortality import benjamini_hochberg


def test_benjamini_hochberg_known_worked_example():
    # Hand-computed: alpha=0.05, m=5. BH critical value at rank k is
    # (k/5)*0.05 = 0.01, 0.02, 0.03, 0.04, 0.05 for ranks 1-5.
    # sorted p: a=.001<=.01 ok, b=.01<=.02 ok, c=.03<=.03 ok, d=.04<=.04 ok, e=.5<=.05 fails
    # -> a,b,c,d survive; e does not.
    p_values = {"a": 0.001, "b": 0.01, "c": 0.03, "d": 0.04, "e": 0.5}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert result == {"a": True, "b": True, "c": True, "d": True, "e": False}


def test_benjamini_hochberg_all_survive_when_all_tiny():
    p_values = {"a": 0.0001, "b": 0.0002, "c": 0.0003}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert all(result.values())


def test_benjamini_hochberg_none_survive_when_all_large():
    p_values = {"a": 0.9, "b": 0.8, "c": 0.95}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert not any(result.values())


def test_benjamini_hochberg_returns_all_original_keys():
    p_values = {"cancer": 0.3, "overdose": 0.001}
    result = benjamini_hochberg(p_values)
    assert set(result.keys()) == {"cancer", "overdose"}


from src.analysis.excess_mortality import compute_acute_pvalue


def test_compute_acute_pvalue_large_for_no_deviation():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    deviations = compute_deviations(trend, np.array([2020, 2021]), np.array([20.0, 20.05]))
    p = compute_acute_pvalue(trend, deviations, acute_years=(2020, 2021))
    assert p > 0.5


def test_compute_acute_pvalue_small_for_large_deviation():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    deviations = compute_deviations(trend, np.array([2020, 2021]), np.array([35.0, 36.0]))
    p = compute_acute_pvalue(trend, deviations, acute_years=(2020, 2021))
    assert p < 0.001


def test_compute_acute_pvalue_returns_one_when_all_acute_years_missing():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    deviations = compute_deviations(trend, np.array([2020, 2021]), np.array([np.nan, np.nan]))
    p = compute_acute_pvalue(trend, deviations, acute_years=(2020, 2021))
    assert p == 1.0
