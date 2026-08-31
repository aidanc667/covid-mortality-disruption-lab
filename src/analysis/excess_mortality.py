"""Known-date interrupted time series ("excess mortality") analysis, per
docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md
sections 5.1, 5.2, and 5.5. The breakpoint (pandemic onset, 2020) is
fixed by the shock's known date, not searched for -- this is a more
defensible-against-p-hacking variant of the algorithmic breakpoint
search in src/analysis/changepoints.py, which is reused separately as
an independent cross-check (spec section 5.3), not as the primary method
here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class BaselineTrend:
    slope: float
    intercept: float
    residual_std: float
    n: int
    x_mean: float
    sxx: float  # sum((x - x_mean)^2) -- needed for prediction-interval width


def fit_baseline_trend(years: np.ndarray, values: np.ndarray) -> BaselineTrend:
    """Fit an OLS linear trend on baseline (pre-shock) years only.
    NaN values (suppressed/unreliable years) are dropped before fitting,
    never coerced to zero, per research_protocol.md #8."""
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]

    n = len(years)
    if n < 3:
        raise ValueError(f"Need at least 3 non-missing baseline years to fit a trend, got {n}.")

    slope, intercept = np.polyfit(years, values, 1)
    resid = values - (slope * years + intercept)
    residual_std = float(np.sqrt(np.sum(resid**2) / (n - 2)))
    x_mean = float(years.mean())
    sxx = float(np.sum((years - x_mean) ** 2))

    return BaselineTrend(
        slope=float(slope), intercept=float(intercept),
        residual_std=residual_std, n=n, x_mean=x_mean, sxx=sxx,
    )
