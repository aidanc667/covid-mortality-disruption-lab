import numpy as np
import pandas as pd
import pytest

from src.analysis.baseline_sensitivity import latest_year_window_check


def _series(cause, values_by_year):
    return pd.DataFrame({"cause": cause, "year": list(values_by_year), "age_adjusted_rate": list(values_by_year.values())})


def _flattening(latest_value):
    """Falls 25 -> 20 over 1999-2009, then flat at 20 through 2019 (small alternating
    noise so the fit has nonzero residual variance), then `latest_value` in 2024."""
    v = {y: 25 - 0.5 * (y - 1999) for y in range(1999, 2010)}
    v.update({y: 20 + (0.05 if y % 2 else -0.05) for y in range(2010, 2020)})
    v[2024] = latest_value
    return v


def test_flattened_series_reads_above_on_long_window_but_within_on_short():
    # By construction: a 1999-2019 line keeps falling past 20, so a 2024 value of
    # 20 sits above it; the flat 2010-2019 line predicts ~20, so it's within range.
    out = latest_year_window_check(_series("X", _flattening(20.0)), ["X"], primary_start={})
    row = out.iloc[0]
    assert (row["primary_window"], row["alt_window"]) == ("1999-2019", "2010-2019")
    assert row["primary_status"] == "above"
    assert row["alt_status"] == "within"
    assert abs(row["alt_pct"]) < 1.0
    assert bool(row["baseline_sensitive"]) is True


def test_primary_2010_cause_uses_1999_as_the_alternate():
    out = latest_year_window_check(_series("X", _flattening(20.0)), ["X"], primary_start={"X": 2010})
    row = out.iloc[0]
    assert (row["primary_window"], row["alt_window"]) == ("2010-2019", "1999-2019")
    assert (row["primary_status"], row["alt_status"]) == ("within", "above")


def test_straight_line_series_is_not_baseline_sensitive():
    rng = np.random.default_rng(0)
    v = {y: 50 - 0.8 * (y - 1999) + rng.normal(0, 0.3) for y in range(1999, 2020)}
    v[2024] = 50 - 0.8 * 25  # exactly on the trend
    row = latest_year_window_check(_series("Y", v), ["Y"], primary_start={}).iloc[0]
    assert row["primary_status"] == row["alt_status"] == "within"
    assert bool(row["baseline_sensitive"]) is False


def test_missing_latest_value_is_reported_as_missing_not_within():
    v = _flattening(20.0)
    v[2024] = float("nan")
    row = latest_year_window_check(_series("X", v), ["X"], primary_start={}).iloc[0]
    assert row["primary_status"] == row["alt_status"] == "missing"


def test_primary_start_outside_the_two_windows_raises():
    with pytest.raises(ValueError, match="2005"):
        latest_year_window_check(_series("X", _flattening(20.0)), ["X"], primary_start={"X": 2005})
