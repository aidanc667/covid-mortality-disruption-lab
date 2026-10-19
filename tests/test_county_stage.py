"""run_county_stage: FDR is applied within each cause, not across causes,
and the county cause list the app reads matches what the pipeline produced."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_covid_disruption_pipeline import run_county_stage

VARS = ["pct_uninsured_chr", "pct_smokers", "pct_obese", "median_income_chr", "pct_rural"]


def _county_data(seed, signal_var, n=60):
    rng = np.random.default_rng(seed)
    fips = [f"{i:05d}" for i in range(1, n + 1)]
    context = pd.DataFrame({"county_fips": fips, **{v: rng.uniform(0, 1, n) for v in VARS}})
    noise = rng.normal(0, 1, n)
    disruption = pd.DataFrame({"county_fips": fips, "disruption": 30 * context[signal_var] + noise if signal_var else noise})
    return disruption, context


def test_fdr_is_applied_within_each_cause():
    strong, context = _county_data(1, "pct_smokers")
    null, _ = _county_data(2, None)
    het, bias, robustness = run_county_stage({"A": strong, "B": null}, context)
    # Each cause gets its own family of 5 tests.
    assert het.groupby("cause").size().to_dict() == {"A": 5, "B": 5}
    a = het[het["cause"] == "A"].set_index("variable")
    assert bool(a.loc["pct_smokers", "fdr_significant"]) is True
    # Cause B's flags depend only on B's own p-values: recompute BH by hand for B alone.
    b = het[het["cause"] == "B"].sort_values("p_value")
    m, ranks = len(b), np.arange(1, len(b) + 1)
    passes = b["p_value"].to_numpy() <= ranks / m * 0.05
    k = ranks[passes].max() if passes.any() else 0
    expected = ranks <= k
    assert list(b["fdr_significant"].astype(bool)) == list(expected)
    assert set(bias["cause"]) == {"A", "B"} and set(robustness["cause"]) == {"A", "B"}


MODELS = Path(__file__).resolve().parent.parent / "outputs" / "models"


@pytest.mark.skipif(not (MODELS / "disruption_summary.parquet").exists(), reason="pipeline outputs not present")
def test_app_county_causes_match_pipeline_outputs():
    from app.components.data_loading import HETEROGENEITY_CAUSES, TEST_CAUSES
    summary = pd.read_parquet(MODELS / "disruption_summary.parquet").set_index("cause")
    disrupted = [c for c in TEST_CAUSES if summary.loc[c, "persistence_class"] != "No significant disruption"]
    assert HETEROGENEITY_CAUSES == disrupted
    for cause in HETEROGENEITY_CAUSES:
        assert (MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet").exists()
    het = pd.read_parquet(MODELS / "heterogeneity_summary.parquet")
    assert list(dict.fromkeys(het["cause"])) == HETEROGENEITY_CAUSES
