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


@dataclass
class DeviationResult:
    year: int
    observed: float
    expected: float
    deviation: float
    pi_low: float
    pi_high: float
    significant: bool


def compute_deviations(
    trend: BaselineTrend, years: np.ndarray, observed: np.ndarray, alpha: float = 0.05
) -> list[DeviationResult]:
    """Project the baseline trend forward to each post-period year and
    test whether the observed value falls outside its prediction
    interval. Uses the standard OLS prediction-interval formula:
    SE_pred(x0) = residual_std * sqrt(1 + 1/n + (x0 - x_mean)^2 / Sxx),
    so the interval widens the further a year is extrapolated from the
    baseline period -- this is standard, not something invented for this
    project."""
    t_crit = stats.t.ppf(1 - alpha / 2, df=trend.n - 2)
    results = []
    for year, obs in zip(years, observed):
        expected = trend.slope * year + trend.intercept
        se_pred = trend.residual_std * np.sqrt(
            1 + 1 / trend.n + (year - trend.x_mean) ** 2 / trend.sxx
        )
        margin = t_crit * se_pred
        pi_low, pi_high = expected - margin, expected + margin

        obs_is_nan = np.isnan(obs)
        deviation = np.nan if obs_is_nan else float(obs - expected)
        significant = False if obs_is_nan else not (pi_low <= obs <= pi_high)

        results.append(DeviationResult(
            year=int(year),
            observed=float(obs) if not obs_is_nan else np.nan,
            expected=float(expected),
            deviation=deviation,
            pi_low=float(pi_low),
            pi_high=float(pi_high),
            significant=bool(significant),
        ))
    return results
