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
