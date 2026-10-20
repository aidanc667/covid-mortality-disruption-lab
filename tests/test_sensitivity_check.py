import numpy as np

from scripts.run_sensitivity_check import fit_loglinear_and_test, fit_quadratic_and_test
from src.analysis.excess_mortality import (
    compute_acute_pvalue,
    compute_deviations,
    fit_baseline_trend,
)

YEARS = np.arange(1999, 2020)
POST = np.arange(2020, 2025)


def test_quadratic_test_rejects_about_5_percent_under_no_disruption():
    # Calibration with a true quadratic trend and iid noise: a correct 5%-level test
    # rejects ~5% of the time (the old formula rejected ~8%).
    rng = np.random.default_rng(7)
    curve = lambda t: 60 - 1.2 * (t - 1999) + 0.03 * (t - 1999) ** 2
    rejections, sims = 0, 4000
    for _ in range(sims):
        p, _ = fit_quadratic_and_test(YEARS, curve(YEARS) + rng.normal(0, 1, len(YEARS)),
                                      POST, curve(POST) + rng.normal(0, 1, len(POST)), (2020, 2021))
        rejections += p < 0.05
    assert 0.04 <= rejections / sims <= 0.06, rejections / sims


def test_loglinear_test_finds_no_disruption_in_a_steady_percentage_decline():
    # A rate falling 3% a year, continued unchanged into 2020-24. A straight line in
    # the rate itself can't follow that curve; a straight line in log(rate) can.
    rng = np.random.default_rng(3)
    rate = lambda t: 100 * 0.97 ** (t - 1999)
    noise = np.exp(rng.normal(0, 0.005, len(YEARS)))
    baseline = rate(YEARS) * noise
    p, cls = fit_loglinear_and_test(YEARS, baseline, POST, rate(POST), (2020, 2021))
    assert p > 0.05 and cls == "No significant disruption"
    # ...while a straight line in the rate itself, which can't follow the curve, reads the
    # same undisrupted continuation as a significant jump. That gap is what this check exposes.
    trend = fit_baseline_trend(YEARS, baseline)
    assert compute_acute_pvalue(trend, compute_deviations(trend, POST, rate(POST)), (2020, 2021)) < 0.05


def test_loglinear_test_detects_a_real_jump():
    rng = np.random.default_rng(3)
    rate = lambda t: 100 * 0.97 ** (t - 1999)
    noise = np.exp(rng.normal(0, 0.005, len(YEARS)))
    p, cls = fit_loglinear_and_test(YEARS, rate(YEARS) * noise, POST, rate(POST) * 1.10, (2020, 2021))
    assert p < 0.05 and cls == "Significant disruption"
