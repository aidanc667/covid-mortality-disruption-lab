from src.analysis.changepoints import SegmentedRegressionResult
from src.analysis.trajectory import classify_trajectory


def _result(slope_diff, significant=True):
    return SegmentedRegressionResult(
        breakpoint_year=2010, pre_slope=0.5, post_slope=0.5 + slope_diff,
        slope_diff=slope_diff, p_value=0.01, has_significant_break=significant, n_obs=22,
    )


def test_improving_when_significant_and_slope_diff_below_negative_threshold():
    assert classify_trajectory(_result(-0.5)) == "Improving"


def test_worsening_when_significant_and_slope_diff_above_positive_threshold():
    assert classify_trajectory(_result(0.5)) == "Worsening"


def test_stable_when_significant_but_small_slope_diff():
    assert classify_trajectory(_result(0.1)) == "Stable"


def test_stable_when_no_significant_break_regardless_of_slope_diff():
    assert classify_trajectory(_result(-2.0, significant=False)) == "Stable"


def test_stable_when_no_breakpoint_detected_at_all():
    result = SegmentedRegressionResult(None, None, None, None, None, False, 10)
    assert classify_trajectory(result) == "Stable"
