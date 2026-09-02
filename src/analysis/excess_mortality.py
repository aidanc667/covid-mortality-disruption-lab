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


def compute_residual_autocorrelation(years: np.ndarray, values: np.ndarray, trend: BaselineTrend, lag: int = 1) -> float:
    """Lag-k autocorrelation of the baseline trend's own residuals, as a
    diagnostic for research_protocol.md #12's documented limitation: the
    OLS prediction-interval math in compute_deviations assumes
    independent, identically distributed residuals year to year, but
    annual mortality residuals are plausibly serially correlated (a rough
    year tends to be followed by another rough year, from shared
    underlying causes like flu-season overlap or economic conditions).
    Strong positive autocorrelation here means the prediction interval is
    probably too narrow and p-values overconfident -- this function
    quantifies that risk per cause rather than leaving it as an
    unverified caveat."""
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]

    resid = values - (trend.slope * years + trend.intercept)
    if len(resid) <= lag + 1:
        return float("nan")

    r = np.corrcoef(resid[:-lag], resid[lag:])[0, 1]
    return float(r)


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
    deviations: list[DeviationResult],
    acute_years: tuple[int, int],
    post_acute_years: tuple[int, int],
    acute_significant: bool | None = None,
) -> str:
    """Three-way persistence classification per design spec section 5.2:
    "Persisted", "Resolved", or "Reversed" for causes with a significant
    acute-phase (2020-2021) disruption; "No significant disruption" if
    the acute phase itself never cleared significance. A binary
    persisted/resolved scheme would flatten a reversal pattern (e.g.
    overdose spiking, then declining below its pre-pandemic trend) into
    a false "resolved," which is why this is three-way, not two.

    `acute_significant`: by default (None), derived from whether any
    individual acute year's per-year prediction-interval flag is True.
    Pass this explicitly (e.g. from compute_acute_pvalue < alpha) when a
    combined-period test should gate the classification instead --
    otherwise a borderline cause can end up with a persistence_class of
    "No significant disruption" while its own p-value (from the same
    acute period, via the combined test) is reported as significant
    elsewhere, which is a real contradiction, not just a stylistic one:
    both numbers claim to answer "was the acute-period disruption real,"
    and they must agree when both are shown together, e.g. in the
    orchestration pipeline that feeds this project's app."""
    acute = [d for d in deviations if acute_years[0] <= d.year <= acute_years[1]]
    post_acute = [d for d in deviations if post_acute_years[0] <= d.year <= post_acute_years[1]]

    if acute_significant is None:
        acute_significant = any(d.significant for d in acute)
    if not acute_significant:
        return "No significant disruption"

    acute_with_deviation = [d for d in acute if not np.isnan(d.deviation)]
    acute_sign = np.sign(np.mean([d.deviation for d in acute_with_deviation]))

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


def compute_hac_pvalue(
    baseline_years: np.ndarray, baseline_values: np.ndarray,
    post_years: np.ndarray, post_values: np.ndarray,
    acute_years: tuple[int, int], max_lag: int | None = None,
) -> float:
    """Same acute-window test as compute_acute_pvalue, but with Newey-West
    (HAC) autocorrelation-robust standard errors instead of the classical
    OLS prediction-interval formula, which assumes independent residuals
    year to year -- research_protocol.md #12 documents this as a real,
    likely understated limitation: measured lag-1 autocorrelation is
    0.50-0.82 for half the test causes (diabetes, drug overdose,
    Alzheimer's, cerebrovascular disease), not the near-zero the classical
    formula effectively assumes.

    Refits the baseline regression independently (BaselineTrend only
    stores summary statistics -- n, x_mean, sxx, residual_std -- not the
    raw per-year residuals HAC needs) using a small-sample Newey-West lag
    length (Newey & West 1994's rule of thumb, floor(4*(n/100)^(2/9)),
    which works out to 1-2 lags for this project's 10-21-year baselines).

    Two pieces combine into the total prediction variance:
    1. HAC-robust uncertainty in the fitted line's own height at the
       acute years' average year: a sandwich covariance estimator on the
       regression coefficients (Bartlett-kernel-weighted, following
       Newey-West), replacing the classical residual_std^2 * (X'X)^-1.
    2. The variance of the mean of the acute years' own new deviations,
       computed directly from the baseline's empirical lag-0 and lag-1
       autocovariances instead of assumed independent. This project's
       ACUTE_YEARS is always a 2-year window (2020-2021), for which
       Var(mean of 2 correlated draws) = (gamma_0 + gamma_1) / 2 is exact,
       not an approximation -- so this function only supports a 2-year
       window and raises rather than silently generalizing an unverified
       formula to a different window size.

    Uses the same df = n - 2 reference t-distribution as
    compute_acute_pvalue for comparability, though HAC's own asymptotic
    justification technically calls for a normal reference distribution;
    a pragmatic, documented choice rather than a rigorously derived one,
    matching this project's other finite-sample approximations (e.g.
    scripts/run_sensitivity_check.py's fit_quadratic_and_test).

    Returns 1.0 if every acute year is missing or fewer than 4 baseline
    years remain, rather than raising."""
    if acute_years[1] - acute_years[0] != 1:
        raise ValueError(
            f"compute_hac_pvalue's variance-of-mean formula is only exact for a "
            f"2-year acute window; got {acute_years}."
        )

    baseline_years = np.asarray(baseline_years, dtype=float)
    baseline_values = np.asarray(baseline_values, dtype=float)
    mask = ~np.isnan(baseline_values)
    baseline_years, baseline_values = baseline_years[mask], baseline_values[mask]
    n = len(baseline_years)
    if n < 4:
        return 1.0

    X = np.column_stack([np.ones(n), baseline_years])
    beta, *_ = np.linalg.lstsq(X, baseline_values, rcond=None)
    residuals = baseline_values - X @ beta

    if max_lag is None:
        max_lag = max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    max_lag = min(max_lag, n - 2)

    scores = X * residuals[:, None]
    S = scores.T @ scores
    for lag in range(1, max_lag + 1):
        weight = 1 - lag / (max_lag + 1)
        cross = scores[lag:].T @ scores[:-lag]
        S += weight * (cross + cross.T)
    xtx_inv = np.linalg.inv(X.T @ X)
    cov_beta_hac = xtx_inv @ S @ xtx_inv

    post_years = np.asarray(post_years, dtype=float)
    post_values = np.asarray(post_values, dtype=float)
    acute_mask = (
        (post_years >= acute_years[0]) & (post_years <= acute_years[1]) & ~np.isnan(post_values)
    )
    acute_years_arr = post_years[acute_mask]
    acute_values_arr = post_values[acute_mask]
    if len(acute_years_arr) == 0:
        return 1.0

    expected = beta[0] + beta[1] * acute_years_arr
    mean_deviation = float(np.mean(acute_values_arr - expected))
    avg_year = float(np.mean(acute_years_arr))

    row = np.array([1.0, avg_year])
    var_line = float(row @ cov_beta_hac @ row)

    gamma0 = float(np.mean(residuals**2))
    gamma1 = float(np.mean(residuals[1:] * residuals[:-1])) if n > 1 else 0.0
    if len(acute_years_arr) == 2:
        var_new_mean = (gamma0 + gamma1) / 2
    else:
        # Only one acute year present (the other suppressed/missing) --
        # no averaging across two correlated draws, so just that single
        # new draw's own variance.
        var_new_mean = gamma0

    se = np.sqrt(var_line + var_new_mean)
    if se == 0:
        return 0.0 if mean_deviation != 0 else 1.0

    t_stat = mean_deviation / se
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 2))
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
