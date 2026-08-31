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


def classify_persistence(
    deviations: list[DeviationResult], acute_years: tuple[int, int], post_acute_years: tuple[int, int]
) -> str:
    """Three-way persistence classification per design spec section 5.2:
    "Persisted", "Resolved", or "Reversed" for causes with a significant
    acute-phase (2020-2021) disruption; "No significant disruption" if
    the acute phase itself never cleared significance. A binary
    persisted/resolved scheme would flatten a reversal pattern (e.g.
    overdose spiking, then declining below its pre-pandemic trend) into
    a false "resolved," which is why this is three-way, not two."""
    acute = [d for d in deviations if acute_years[0] <= d.year <= acute_years[1]]
    post_acute = [d for d in deviations if post_acute_years[0] <= d.year <= post_acute_years[1]]

    acute_significant = [d for d in acute if d.significant]
    if not acute_significant:
        return "No significant disruption"

    acute_sign = np.sign(np.mean([d.deviation for d in acute_significant]))

    post_significant = [d for d in post_acute if d.significant]
    if not post_significant:
        return "Resolved"

    post_sign = np.sign(np.mean([d.deviation for d in post_significant]))
    return "Persisted" if post_sign == acute_sign else "Reversed"


def compute_acute_pvalue(
    trend: BaselineTrend, deviations: list[DeviationResult], acute_years: tuple[int, int]
) -> float:
    """Two-tailed p-value testing whether the mean deviation across
    acute_years is significantly different from zero, via a one-sample
    t-test against the trend's model-based prediction standard error
    (averaged across the acute years, since extrapolation distance
    varies slightly year to year). This is what feeds
    src.analysis.excess_mortality.benjamini_hochberg for the 6-cause FDR
    correction (design spec section 5.5) -- compute_deviations only
    flags per-year significance, it doesn't produce a single per-cause
    p-value for ranking causes against each other.

    Returns 1.0 (not significant) if every acute year is missing, rather
    than raising -- a cause with fully suppressed acute-period data
    should not be treated as automatically significant or crash the
    6-cause family test."""
    acute = [
        d for d in deviations
        if acute_years[0] <= d.year <= acute_years[1] and not np.isnan(d.deviation)
    ]
    if not acute:
        return 1.0

    mean_deviation = float(np.mean([d.deviation for d in acute]))
    avg_year = float(np.mean([d.year for d in acute]))
    se_pred = trend.residual_std * np.sqrt(
        1 + 1 / trend.n + (avg_year - trend.x_mean) ** 2 / trend.sxx
    )
    se_of_mean = se_pred / np.sqrt(len(acute))
    if se_of_mean == 0:
        return 0.0 if mean_deviation != 0 else 1.0

    t_stat = mean_deviation / se_of_mean
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=trend.n - 2))
    return float(p_value)


def benjamini_hochberg(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Standard Benjamini-Hochberg step-up FDR procedure. Sort p-values
    ascending; find the largest rank k where p(k) <= (k/m)*alpha; every
    p-value at or below that rank survives correction. Per design spec
    section 5.5, applied across the 6 substantive test causes (excluding
    the COVID-19 reference series and the drowning negative control)."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)

    max_rank_significant = 0
    for rank, (_, p) in enumerate(items, start=1):
        if p <= (rank / m) * alpha:
            max_rank_significant = rank

    survives = {}
    for rank, (key, _) in enumerate(items, start=1):
        survives[key] = rank <= max_rank_significant
    return survives
