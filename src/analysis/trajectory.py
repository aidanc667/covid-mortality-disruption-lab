"""County trajectory classification, per docs/research_protocol.md #15 and
the 2026-08-29 addendum defining the classification thresholds."""
from __future__ import annotations

from src.analysis.changepoints import SegmentedRegressionResult

SLOPE_DIFF_THRESHOLD = 0.3  # age-adjusted deaths per 100k per year; see research_protocol.md addendum


def classify_trajectory(result: SegmentedRegressionResult) -> str:
    if not result.has_significant_break or result.slope_diff is None:
        return "Stable"
    if result.slope_diff <= -SLOPE_DIFF_THRESHOLD:
        return "Improving"
    if result.slope_diff >= SLOPE_DIFF_THRESHOLD:
        return "Worsening"
    return "Stable"
