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
