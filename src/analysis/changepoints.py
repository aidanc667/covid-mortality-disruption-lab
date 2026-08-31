"""Change-point detection, per docs/research_protocol.md #7.

Three independent methods, run on a single county/state/national annual
rate series with suppressed/unreliable years already NaN'd out (see
src/cleaning/mortality.build_county_series): segmented regression (primary),
PELT, and binary segmentation (both via `ruptures`). A Bayesian check is
intentionally not implemented here — the protocol scopes it to national/
state series only, run separately, not as part of this per-series module.

All three assume at most one structural break, matching the research
question's framing ("when did trajectories change," not "how many times").
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import ruptures as rpt
from scipy import stats


@dataclass
class SegmentedRegressionResult:
    breakpoint_year: int | None
    pre_slope: float | None
    post_slope: float | None
    slope_diff: float | None
    p_value: float | None
    has_significant_break: bool
    n_obs: int


def _clean_series(years: np.ndarray, rates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = ~np.isnan(rates)
    return years[mask], rates[mask]


def fit_segmented_regression(
    years: np.ndarray, rates: np.ndarray, min_segment_years: int = 5, alpha: float = 0.05
) -> SegmentedRegressionResult:
    """Grid-search the breakpoint year that minimizes total two-segment SSE,
    then test it against a single-line (no-break) null via a Chow test —
    an F-test comparing the nested one-line vs. two-line models. A
    breakpoint is only reported as detected if that test is significant at
    `alpha`; otherwise the series is treated as having no detected break,
    consistent with research_protocol.md's confirmatory framing (report
    results regardless of direction, but do not claim a break the data
    doesn't support).
    """
    years_c, rates_c = _clean_series(np.asarray(years), np.asarray(rates))
    n = len(years_c)
    if n < 2 * min_segment_years:
        return SegmentedRegressionResult(None, None, None, None, None, False, n)

    candidates = years_c[min_segment_years : n - min_segment_years]
    if len(candidates) == 0:
        return SegmentedRegressionResult(None, None, None, None, None, False, n)

    def two_segment_sse(bp: int) -> tuple[float, float, float]:
        pre_mask = years_c <= bp
        post_mask = years_c > bp
        pre_slope, pre_intercept = np.polyfit(years_c[pre_mask], rates_c[pre_mask], 1)
        post_slope, post_intercept = np.polyfit(years_c[post_mask], rates_c[post_mask], 1)
        pre_resid = rates_c[pre_mask] - (pre_slope * years_c[pre_mask] + pre_intercept)
        post_resid = rates_c[post_mask] - (post_slope * years_c[post_mask] + post_intercept)
        sse = np.sum(pre_resid**2) + np.sum(post_resid**2)
        return sse, pre_slope, post_slope

    sse_by_candidate = {bp: two_segment_sse(bp) for bp in candidates}
    best_bp = min(sse_by_candidate, key=lambda bp: sse_by_candidate[bp][0])
    best_sse, pre_slope, post_slope = sse_by_candidate[best_bp]

    one_slope, one_intercept = np.polyfit(years_c, rates_c, 1)
    one_resid = rates_c - (one_slope * years_c + one_intercept)
    sse_restricted = np.sum(one_resid**2)

    df_num, df_denom = 2, n - 4
    if df_denom <= 0 or best_sse <= 0:
        p_value = None
        significant = False
    else:
        f_stat = ((sse_restricted - best_sse) / df_num) / (best_sse / df_denom)
        f_stat = max(f_stat, 0.0)
        p_value = float(1 - stats.f.cdf(f_stat, df_num, df_denom))
        significant = p_value < alpha

    return SegmentedRegressionResult(
        breakpoint_year=int(best_bp),
        pre_slope=float(pre_slope),
        post_slope=float(post_slope),
        slope_diff=float(post_slope - pre_slope),
        p_value=p_value,
        has_significant_break=significant,
        n_obs=n,
    )


def _diff_signal_for_trend_detection(years_c: np.ndarray, rates_c: np.ndarray) -> np.ndarray:
    """`ruptures`' standard cost models (l2, l1, rbf, ...) detect shifts in
    MEAN, not shifts in TREND/slope. A diabetes-mortality breakpoint is a
    slope change, not a level shift, so running them directly on the rate
    series would silently detect the wrong kind of event. First-differencing
    turns a slope change in the level series into a mean shift in the
    differenced series, which l2-cost mean-shift detectors handle correctly.
    """
    return np.diff(rates_c)


def fit_pelt(years: np.ndarray, rates: np.ndarray, min_size: int = 5, penalty: float = 3.0) -> list[int]:
    """PELT (L2 cost, on the first-differenced series — see
    _diff_signal_for_trend_detection) cross-check. Returns candidate
    breakpoint years, defined the same way as fit_segmented_regression's
    breakpoint_year: the last year still following the pre-break trend."""
    years_c, rates_c = _clean_series(np.asarray(years), np.asarray(rates))
    if len(rates_c) < 2 * min_size:
        return []
    diff_signal = _diff_signal_for_trend_detection(years_c, rates_c)
    algo = rpt.Pelt(model="l2", min_size=max(min_size - 1, 2)).fit(diff_signal.reshape(-1, 1))
    result_indices = algo.predict(pen=penalty)
    # index k in the diff series -> change first visible in diff[k] = rate[k+1]-rate[k]
    # -> years_c[k] is the last point still on the pre-break trend.
    return [int(years_c[k]) for k in result_indices if k < len(years_c) - 1]


def fit_binseg(years: np.ndarray, rates: np.ndarray, min_size: int = 5, n_bkps: int = 1) -> list[int]:
    """Binary segmentation cross-check (on the first-differenced series —
    see _diff_signal_for_trend_detection), constrained to a single
    breakpoint to match this project's one-structural-break framing."""
    years_c, rates_c = _clean_series(np.asarray(years), np.asarray(rates))
    if len(rates_c) < 2 * min_size:
        return []
    diff_signal = _diff_signal_for_trend_detection(years_c, rates_c)
    algo = rpt.Binseg(model="l2", min_size=max(min_size - 1, 2)).fit(diff_signal.reshape(-1, 1))
    result_indices = algo.predict(n_bkps=n_bkps)
    return [int(years_c[k]) for k in result_indices if k < len(years_c) - 1]


def summarize_method_agreement(breakpoints: dict[str, int | None], tolerance: int = 1) -> dict:
    """Analytical summary of cross-method agreement — explicitly NOT a
    formal statistical probability (brief section 13). Compares all
    non-None estimates pairwise against the segmented-regression estimate
    (the primary method) within `tolerance` years.
    """
    primary = breakpoints.get("segmented_regression")
    reported = {k: v for k, v in breakpoints.items() if v is not None}
    n_methods_run = len(breakpoints)

    if primary is None:
        return {
            "primary_breakpoint": None,
            "agreement_count": 0,
            "n_methods_run": n_methods_run,
            "agreeing_methods": [],
            "summary": "No breakpoint detected by the primary method (segmented regression); no agreement to assess.",
        }

    agreeing = [k for k, v in reported.items() if abs(v - primary) <= tolerance]
    return {
        "primary_breakpoint": primary,
        "agreement_count": len(agreeing),
        "n_methods_run": n_methods_run,
        "agreeing_methods": agreeing,
        "summary": (
            f"{len(agreeing)}/{n_methods_run} methods agree within ±{tolerance} year(s) "
            f"of the primary breakpoint estimate ({primary}). This is a descriptive "
            "cross-method agreement count, not a formal statistical probability."
        ),
    }
