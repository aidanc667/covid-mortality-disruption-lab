import numpy as np
import pytest

from src.analysis.changepoints import (
    fit_segmented_regression,
    fit_pelt,
    fit_binseg,
    summarize_method_agreement,
)


def _make_break_series(break_year=2010, pre_slope=0.5, post_slope=-1.5, noise=0.05, seed=1):
    rng = np.random.default_rng(seed)
    years = np.arange(1999, 2021)
    baseline = 25.0
    rate = np.empty_like(years, dtype=float)
    for i, y in enumerate(years):
        if y <= break_year:
            rate[i] = baseline + pre_slope * (y - years[0])
        else:
            level_at_break = baseline + pre_slope * (break_year - years[0])
            rate[i] = level_at_break + post_slope * (y - break_year)
    rate += rng.normal(0, noise, size=len(years))
    return years, rate


def _make_flat_series(seed=2, noise=0.3):
    rng = np.random.default_rng(seed)
    years = np.arange(1999, 2021)
    rate = 25.0 + rng.normal(0, noise, size=len(years))
    return years, rate


def test_segmented_regression_recovers_known_breakpoint_closely():
    years, rate = _make_break_series(break_year=2010)
    result = fit_segmented_regression(years, rate)
    assert result.has_significant_break
    assert abs(result.breakpoint_year - 2010) <= 2
    assert result.pre_slope > 0
    assert result.post_slope < 0
    assert result.slope_diff < 0


def test_segmented_regression_flat_series_no_significant_break():
    years, rate = _make_flat_series()
    result = fit_segmented_regression(years, rate)
    assert not result.has_significant_break


def test_segmented_regression_handles_nan_gaps_from_suppression():
    years, rate = _make_break_series(break_year=2010)
    rate_with_gaps = rate.copy()
    rate_with_gaps[[3, 7, 15]] = np.nan  # simulate suppressed years
    result = fit_segmented_regression(years, rate_with_gaps)
    assert result.n_obs == len(years) - 3
    assert abs(result.breakpoint_year - 2010) <= 3


def test_segmented_regression_insufficient_data_returns_none():
    years = np.arange(2015, 2021)  # only 6 years, below 2*min_segment_years default
    rate = np.linspace(20, 25, len(years))
    result = fit_segmented_regression(years, rate, min_segment_years=5)
    assert result.breakpoint_year is None
    assert not result.has_significant_break


def test_pelt_detects_break_near_known_year():
    years, rate = _make_break_series(break_year=2010)
    bps = fit_pelt(years, rate, min_size=5, penalty=1.0)
    assert any(abs(bp - 2010) <= 2 for bp in bps)


def test_binseg_detects_break_near_known_year():
    years, rate = _make_break_series(break_year=2010)
    bps = fit_binseg(years, rate, min_size=5, n_bkps=1)
    assert any(abs(bp - 2010) <= 2 for bp in bps)


def test_summarize_method_agreement_full_agreement():
    result = summarize_method_agreement({
        "segmented_regression": 2010,
        "pelt": 2010,
        "binseg": 2011,
    }, tolerance=1)
    assert result["agreement_count"] == 3
    assert result["primary_breakpoint"] == 2010


def test_summarize_method_agreement_partial_agreement():
    result = summarize_method_agreement({
        "segmented_regression": 2010,
        "pelt": 2010,
        "binseg": 2018,
    }, tolerance=1)
    assert result["agreement_count"] == 2
    assert "binseg" not in result["agreeing_methods"]


def test_summarize_method_agreement_no_primary_breakpoint():
    result = summarize_method_agreement({
        "segmented_regression": None,
        "pelt": 2010,
        "binseg": 2011,
    })
    assert result["agreement_count"] == 0
    assert result["primary_breakpoint"] is None
