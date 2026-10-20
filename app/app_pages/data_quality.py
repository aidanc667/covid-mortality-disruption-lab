import streamlit as st

from app.components.data_loading import (
    TEST_CAUSES,
    county_cause_label,
    data_available,
    display_cause,
    heterogeneity_synthetic_banner,
    load_bridging_summary,
    load_county_bridging_check,
    load_disruption_summary,
    load_heterogeneity_summary,
    load_negative_control,
    load_sensitivity_check,
    sensitivity_check_available,
    synthetic_banner,
)
from app.components.ui import takeaway_html

st.title("Data quality")
synthetic_banner()

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

st.html(takeaway_html(
    "Every check is shown here, including the ones that flagged problems: the negative control, "
    "multiple-testing correction, the database-vintage seam, and four sensitivity checks."
))

neg_tab, testing_tab, bridging_tab, sensitivity_tab = st.tabs(
    ["Negative control", "Multiple testing", "Vintage bridging", "Sensitivity"]
)

with neg_tab:
    neg_control = load_negative_control().iloc[0]
    passed = bool(neg_control["passed"])

    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric("Status", "Passed" if passed else "FAILED")
        with st.container(border=True):
            st.caption("Classification", help="Computed on raw death counts (the actual gating metric), not age-adjusted rate. See note below.")
            st.badge(
                neg_control["persistence_class_counts"],
                color="gray" if neg_control["persistence_class_counts"] == "No significant disruption" else "red",
            )
        with st.container(border=True):
            st.metric("p-value", f"{neg_control['p_value_counts']:.4g}", help="Computed on raw death counts, the gating metric.")

    st.caption(
        f"Cause: **{neg_control['cause']}**. Gate decision computed on {neg_control['gate_metric']}, "
        f"not age-adjusted rate. See note below."
    )

    if passed:
        st.success(
            f"{neg_control['cause']} mortality, a cause concentrated in infancy with no "
            "direct COVID mechanism, shows no significant disruption on raw death counts, "
            "as expected. This does not prove the methodology is artifact-free, but a failure "
            "here would have been strong evidence of one.",
            icon=":material/check_circle:",
        )
    else:
        st.error(
            "The negative control shows a significant disruption on raw death counts. Per "
            "research_protocol.md §7 method 4, this is a hard gate. Results on the other 6 "
            "causes should not be trusted until this is resolved (check for a vintage-bridging "
            "artifact or a generic 2020 data-quality issue before trusting any other result on "
            "this page).",
            icon=":material/error:",
        )

    with st.expander("Why raw counts, not age-adjusted rate?"):
        st.write(neg_control["note"])
        st.caption(
            f"For reference, the rate-based test alone gave: {neg_control['persistence_class_rate']} "
            f"(p={neg_control['p_value_rate']:.4g}). The 6 substantive test causes are unaffected by "
            "this issue and still use age-adjusted rate as their primary outcome (research_protocol.md §3): "
            "all have rates well above this negative control's ~3/100k, where 1-decimal rounding is a much "
            "smaller fraction of the signal."
        )

with testing_tab:
    st.markdown("**Across the 6 test causes**")
    summary = load_disruption_summary()
    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric(
                "Raw p<0.05", int((summary["p_value"] < 0.05).sum()),
                help="Of the 6-cause family, how many clear the standard (uncorrected) significance threshold.",
            )
        with st.container(border=True):
            st.metric(
                "FDR-significant", int(summary["fdr_significant"].sum()),
                help="Of the 6-cause family, how many still clear the stricter, multiple-testing-adjusted threshold.",
            )
    st.caption(
        "Benjamini-Hochberg correction is applied across the 6 substantive test causes as one "
        "family (research_protocol.md §7a), a stricter bar than testing each cause in isolation."
    )
    st.markdown("**Across each cause's context variables (county stage)**")
    heterogeneity_synthetic_banner()
    het = load_heterogeneity_summary()
    for cause in het["cause"].unique():
        cause_het = het[het["cause"] == cause]
        with st.container(horizontal=True):
            st.write(f"**{county_cause_label(cause)}**")
            st.caption(f"{int(cause_het['fdr_significant'].sum())} of {len(cause_het)} context variables FDR-significant")

with bridging_tab:
    bridging = load_bridging_summary()
    n_unreliable = int((~bridging["reliable"]).sum())
    if n_unreliable == 0:
        st.success(
            "In 2018–2019, the years both CDC databases cover (D76, 1999–2020, and D158, 2018–2024), "
            "every cause matched exactly on deaths, population, crude rate and age-adjusted rate, well "
            "within the 10% reliability threshold (research_protocol.md §9).",
            icon=":material/check_circle:",
        )
    else:
        cause_word, verb = ("cause", "exceeds") if n_unreliable == 1 else ("causes", "exceed")
        st.error(
            f"{n_unreliable} {cause_word} {verb} the 10% vintage-bridging reliability threshold; their "
            "results should be treated with extra caution.",
            icon=":material/error:",
        )
    bridging_display = bridging.copy()
    bridging_display["cause"] = bridging_display["cause"].map(display_cause)
    st.dataframe(
        bridging_display.sort_values("median_relative_offset", ascending=False),
        column_config={
            "cause": st.column_config.TextColumn("Cause", width="large"),
            "reliable": st.column_config.CheckboxColumn("Reliable (≤10%)"),
            "median_relative_offset": st.column_config.NumberColumn("Median relative offset", format="percent"),
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Measured from the 2018–2019 years present in both database vintages "
        "(`src/cleaning/bridging.estimate_vintage_offset`). This does not correct the data, it "
        "only measures the size of the jump, so a real discontinuity is never mistaken for a "
        "COVID effect."
    )
    county_check = load_county_bridging_check().iloc[0]
    # Same 10% reliability threshold as the national check above.
    county_ok = county_check["max_relative_rate_diff"] <= 0.10
    st.caption(
        f"**County level:** heart disease for 2018–2019 was pulled from both databases and compared "
        f"county by county ({int(county_check['n_counties']):,} counties). Deaths matched in "
        f"{county_check['share_deaths_identical']:.0%} of counties with reported deaths and population in "
        f"{county_check['share_population_identical']:.0%}; the largest rate difference among the "
        f"{int(county_check['n_with_reliable_rate']):,} counties with a reliable rate was "
        f"{county_check['max_relative_rate_diff']:.1%}. "
        + ("That's within the 10% threshold, which supports comparing 2015–19 (older database) with "
           "2020–24 (newer database) at county level; it was checked on heart disease only."
           if county_ok else
           "That exceeds the 10% threshold, so county comparisons across the two databases need caution.")
    )

with sensitivity_tab:
    if not sensitivity_check_available():
        st.info(
            "Not yet run. `python -m scripts.run_sensitivity_check` re-fits the primary method four "
            "different ways (baseline window, significance threshold, curved trend, steady-percentage trend) to check "
            "whether results depend on those choices.",
            icon=":material/info:",
        )
    else:
        sens = load_sensitivity_check()
        test_cause_checks = sens[sens["cause"].isin(TEST_CAUSES)]

        shape_checks = {
            "baseline_trend_shape (linear vs quadratic)": "fit as a curve",
            "trend_scale (linear vs log-linear)": "fit as a steady percentage change per year",
        }
        shape_rows = test_cause_checks[test_cause_checks["check"].isin(shape_checks) & ~test_cause_checks["agrees"]]
        if len(shape_rows):
            parts = [f"{display_cause(r['cause']).lower()}'s 2020–21 result "
                     + (f"loses significance (p = {r['alt_p_value']:.2g})" if r["alt_p_value"] >= 0.05
                        else "changes classification")
                     + f" when the pre-pandemic trend is {shape_checks[r['check']]}"
                     for _, r in shape_rows.iterrows()]
            n = shape_rows["cause"].nunique()
            st.error(
                f"**{n} of 6 test causes {'is' if n == 1 else 'are'} not robust to the trend's shape.** "
                f"{'; '.join(parts).capitalize()}. Part of what the "
                "straight-line method reads as a 2020 disruption could instead come from the shape of the "
                "pre-existing trend.",
                icon=":material/warning:",
            )
        for check_name, check_label, description in [
            ("baseline_window (1999 vs 2010)", "1. Baseline window (1999–2019 vs. 2010–2019)",
             "Does a shorter, more recent baseline change the result?"),
            ("significance_threshold (0.05 vs 0.01)", "2. Significance threshold (α=0.05 vs. α=0.01)",
             "Does a stricter significance bar change the result?"),
            ("baseline_trend_shape (linear vs quadratic)", "3. Baseline trend shape (linear vs. quadratic)",
             "Does allowing the pre-pandemic trend to curve, instead of forcing a straight line, change the result?"),
            ("trend_scale (linear vs log-linear)", "4. Trend scale (linear vs. log-linear)",
             "Does a trend that changes by a steady percentage each year, instead of a steady amount, change the result?"),
        ]:
            check_rows = sens[sens["check"] == check_name]
            disagree = check_rows.loc[~check_rows["agrees"], "cause"]
            n_disagree = len(disagree)
            disagree_word = "disagreement" if n_disagree == 1 else "disagreements"
            only_control = n_disagree > 0 and disagree.str.startswith("Congenital").all()
            label = f"{check_label}: {n_disagree} {disagree_word}" + (" (negative control only)" if only_control else "")
            with st.expander(label, expanded=(n_disagree > 0)):
                st.caption(description)
                check_rows_display = check_rows.copy()
                check_rows_display["cause"] = check_rows_display["cause"].map(display_cause)
                st.dataframe(
                    check_rows_display[["cause", "primary_classification", "primary_p_value", "alt_classification", "alt_p_value", "agrees"]],
                    column_config={
                        "cause": st.column_config.TextColumn("Cause", width="large"),
                        "primary_classification": st.column_config.TextColumn("Classification (primary)", width="medium"),
                        "primary_p_value": st.column_config.NumberColumn("p-value (primary)", format="%.4g"),
                        "alt_classification": st.column_config.TextColumn("Classification (alternate)", width="medium"),
                        "alt_p_value": st.column_config.NumberColumn("p-value (alternate)", format="%.4g"),
                        "agrees": st.column_config.CheckboxColumn("Agrees"),
                    },
                    hide_index=True,
                    width="stretch",
                )

        st.caption(
            "The negative control's baseline-window row (age-adjusted rate) disagreeing across windows "
            "reproduces the already-documented rounding artifact (see \"Why raw counts, not "
            "age-adjusted rate?\" in the Negative control tab), not a new instability. Its actual gate metric (raw death "
            "counts, separate row above) is stable across both windows."
        )
