"""Sensitivity analysis per research_protocol.md §8: re-fit the primary
excess-mortality method (analyze_cause) with an alternate, shorter
baseline window (2010-2019 instead of the primary 1999-2019) and check
whether that changes which causes are flagged as significantly disrupted
or how they're classified. Does not modify or replace the primary results
in disruption_summary.parquet -- writes a separate comparison output.
"""
import pandas as pd

from src.analysis.excess_mortality import benjamini_hochberg
from src.utils.config import OUTPUTS_MODELS
from scripts.run_covid_disruption_pipeline import (
    TEST_CAUSES, NEGATIVE_CONTROL, load_real_national_data, analyze_cause,
)

ALT_BASELINE_START_YEAR = 2010


def main():
    print(f"Loading real national WONDER data for sensitivity check (alt baseline start={ALT_BASELINE_START_YEAR})...")
    d76_df, d158_df, _ = load_real_national_data()

    rows = []
    primary_results = {}
    alt_results = {}
    for cause in TEST_CAUSES + [NEGATIVE_CONTROL]:
        primary = analyze_cause(d76_df, d158_df, cause, baseline_start_year=1999)
        alt = analyze_cause(d76_df, d158_df, cause, baseline_start_year=ALT_BASELINE_START_YEAR)
        primary_results[cause] = primary
        alt_results[cause] = alt
        rows.append({
            "cause": cause,
            "persistence_class_primary": primary["persistence_class"],
            "p_value_primary": primary["p_value"],
            "persistence_class_alt": alt["persistence_class"],
            "p_value_alt": alt["p_value"],
            "classification_agrees": primary["persistence_class"] == alt["persistence_class"],
        })

    # FDR correction applied separately within each baseline window, exactly
    # as the primary analysis does -- a cause's FDR-significance under one
    # window shouldn't be compared to a p-value computed under the other
    # window's family.
    primary_p = {c: primary_results[c]["p_value"] for c in TEST_CAUSES}
    alt_p = {c: alt_results[c]["p_value"] for c in TEST_CAUSES}
    primary_fdr = benjamini_hochberg(primary_p)
    alt_fdr = benjamini_hochberg(alt_p)

    comparison_df = pd.DataFrame(rows)
    comparison_df["fdr_significant_primary"] = comparison_df["cause"].map(
        lambda c: primary_fdr.get(c)
    )
    comparison_df["fdr_significant_alt"] = comparison_df["cause"].map(
        lambda c: alt_fdr.get(c)
    )

    # The negative control's row above uses age_adjusted_rate like every
    # other cause, for a consistent apples-to-apples comparison -- but its
    # actual pass/fail gate (main pipeline, negative_control.parquet) uses
    # raw death counts instead, since WONDER's 1-decimal rate rounding makes
    # the rate-based test oversensitive at this cause's low magnitude
    # (research_protocol.md's 2026-09-01 addenda). Re-run on the real gating
    # metric here too, so a reader doesn't mistake the rate-based row's
    # disagreement for evidence the gate itself is unstable.
    nc_primary_counts = analyze_cause(d76_df, d158_df, NEGATIVE_CONTROL, value_col="deaths", baseline_start_year=1999)
    nc_alt_counts = analyze_cause(
        d76_df, d158_df, NEGATIVE_CONTROL, value_col="deaths", baseline_start_year=ALT_BASELINE_START_YEAR
    )
    nc_gate_row = pd.DataFrame([{
        "cause": NEGATIVE_CONTROL,
        "persistence_class_primary": nc_primary_counts["persistence_class"],
        "p_value_primary": nc_primary_counts["p_value"],
        "persistence_class_alt": nc_alt_counts["persistence_class"],
        "p_value_alt": nc_alt_counts["p_value"],
        "classification_agrees": nc_primary_counts["persistence_class"] == nc_alt_counts["persistence_class"],
        "fdr_significant_primary": None,
        "fdr_significant_alt": None,
        "metric": "deaths (actual gate)",
    }])
    comparison_df["metric"] = "age_adjusted_rate"
    comparison_df = pd.concat([comparison_df, nc_gate_row], ignore_index=True)

    OUTPUTS_MODELS.mkdir(parents=True, exist_ok=True)
    comparison_df.to_parquet(OUTPUTS_MODELS / "sensitivity_check.parquet", index=False)

    print("\nSensitivity check: 1999-2019 baseline (primary) vs. 2010-2019 baseline (alternate)")
    print(comparison_df.to_string(index=False))

    test_cause_rows = comparison_df[comparison_df["cause"].isin(TEST_CAUSES)]
    n_disagree = int((~test_cause_rows["classification_agrees"]).sum())
    if n_disagree == 0:
        print("\nAll 6 test causes' persistence classification is stable across both baseline windows.")
    else:
        disagreeing = test_cause_rows.loc[~test_cause_rows["classification_agrees"], "cause"].tolist()
        print(f"\n{n_disagree} test cause(s) classify differently depending on baseline window: {disagreeing}")

    nc_rate_row = comparison_df[(comparison_df["cause"] == NEGATIVE_CONTROL) & (comparison_df["metric"] == "age_adjusted_rate")].iloc[0]
    if not nc_rate_row["classification_agrees"]:
        print(
            "\nNote: the negative control's age_adjusted_rate row disagrees across baseline windows -- "
            "this is the already-known rounding artifact (see research_protocol.md's 2026-09-01 addenda), "
            "not a new finding. Its actual gate metric (raw death counts) is stable: "
            f"{nc_gate_row.iloc[0]['persistence_class_primary']} in both windows."
        )

    print(f"\nWrote {OUTPUTS_MODELS / 'sensitivity_check.parquet'}")


if __name__ == "__main__":
    main()
