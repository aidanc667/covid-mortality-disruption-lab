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


def test_fdr_is_applied_within_each_cause(monkeypatch):
    import scripts.run_covid_disruption_pipeline as pipeline
    from src.analysis.excess_mortality import benjamini_hochberg

    # Feed fixed p-values so the test pins the FDR family, not the regression.
    # Cause B's best p (0.008) passes BH within B's own 5 tests (threshold 0.05/5 = 0.01)
    # but fails if pooled with A's 5 tests (threshold 0.05/10 = 0.005, and A's
    # p-values here are all large, so B's 0.008 is rank 1 of 10).
    p_by_cause = {"A": [0.2, 0.3, 0.4, 0.5, 0.6], "B": [0.008, 0.5, 0.6, 0.7, 0.8]}

    def fake_regress(disruption_df, context_df, context_vars):
        cause = disruption_df["cause_tag"].iloc[0]
        return pd.DataFrame({"variable": context_vars, "slope": 1.0, "p_value": p_by_cause[cause], "n": 50})

    monkeypatch.setattr(pipeline, "regress_disruption_on_context", fake_regress)
    monkeypatch.setattr(pipeline, "compute_selection_bias", lambda *a, **k: {"n_included": 1})
    monkeypatch.setattr(pipeline, "check_within_sample_robustness", lambda *a, **k: pd.DataFrame({"half": ["full"]}))
    frames = {c: pd.DataFrame({"county_fips": ["00001"], "disruption": [0.0], "cause_tag": [c]}) for c in p_by_cause}
    het, _, _ = run_county_stage(frames, pd.DataFrame())

    b = het[het["cause"] == "B"].set_index("variable")
    assert bool(b.loc[VARS[0], "fdr_significant"]) is True
    # Sanity: the same p-value would NOT survive if all 10 were one family.
    pooled = benjamini_hochberg({f"{c}{i}": p for c, ps in p_by_cause.items() for i, p in enumerate(ps)})
    assert pooled["B0"] is False


def test_regression_stage_runs_end_to_end_per_cause():
    strong, context = _county_data(1, "pct_smokers")
    null, _ = _county_data(2, None)
    het, bias, robustness = run_county_stage({"A": strong, "B": null}, context)
    assert het.groupby("cause").size().to_dict() == {"A": 5, "B": 5}
    assert bool(het[(het["cause"] == "A") & (het["variable"] == "pct_smokers")]["fdr_significant"].iloc[0])
    assert set(bias["cause"]) == {"A", "B"} and set(robustness["cause"]) == {"A", "B"}


def test_pooled_loader_checks_footer_years(tmp_path, monkeypatch):
    import scripts.run_covid_disruption_pipeline as pipeline
    monkeypatch.setattr(pipeline, "CDC_WONDER_DIR", tmp_path)
    body = '"Notes","County","County Code",Deaths,Population,Crude Rate\n,"A County, AL","01001",88,278000,31.7\n"---"\n'
    (tmp_path / "d76_county_pooled_diabetes_2015_2019.csv").write_text(body + '"Year/Month: 2015; 2016; 2017; 2018; 2019"\n')
    (tmp_path / "d158_county_pooled_diabetes_2020_2024.csv").write_text(body + '"Year/Month: 2020; 2021; 2022; 2023; 2024"\n')
    pre, post = pipeline.load_pooled_county_data("Diabetes mellitus")
    assert len(pre) == len(post) == 1
    # A 2015-2019 file saved under the 2020-2024 name must fail.
    (tmp_path / "d158_county_pooled_diabetes_2020_2024.csv").write_text(body + '"Year/Month: 2015; 2016; 2017; 2018; 2019"\n')
    with pytest.raises(ValueError, match="footer"):
        pipeline.load_pooled_county_data("Diabetes mellitus")

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
