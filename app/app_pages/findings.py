import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, load_heterogeneity_summary,
    load_sensitivity_check, data_available, sensitivity_check_available, synthetic_banner, TEST_CAUSES,
)

st.title("Findings")
synthetic_banner()
st.caption(
    "What the completed analysis found, in plain language. Full methodology: see Methods. "
    "Every number below is drawn live from the same precomputed results as the rest of the app."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

summary = load_disruption_summary()
neg_control = load_negative_control().iloc[0]
het = load_heterogeneity_summary()

n_disrupted = int((summary["persistence_class"] != "No significant disruption").sum())
n_fdr = int(summary["fdr_significant"].sum())

st.markdown(
    f"### Of the 6 major causes of death tested, **{n_disrupted} show a statistically significant, "
    "still-unresolved deviation** from their pre-pandemic trend, four years after the pandemic began."
)
st.write(
    "None of the disrupted causes have resolved back to their expected trend by 2024, and none have "
    "reversed direction. The one cause with no significant disruption is itself a real, meaningful "
    "result, not a gap in the data."
)

st.subheader("Headline results")
display = summary.sort_values("p_value").copy()
st.dataframe(
    display[["cause", "persistence_class", "p_value", "fdr_significant", "acute_pct_deviation", "latest_pct_deviation"]],
    column_config={
        "cause": "Cause",
        "persistence_class": "Result",
        "p_value": st.column_config.NumberColumn("p-value", format="%.3g"),
        "fdr_significant": st.column_config.CheckboxColumn("Survives FDR"),
        "acute_pct_deviation": st.column_config.NumberColumn("2020–21 deviation", format="%+.1f%%"),
        "latest_pct_deviation": st.column_config.NumberColumn("2024 deviation", format="%+.1f%%"),
    },
    hide_index=True,
)
st.caption(
    "\"Deviation\" is the effect size — how far the observed rate is from the expected pre-pandemic "
    "trend, as a percent. Significance (p-value) and magnitude (deviation) are different claims: a "
    "cause can be statistically significant while still small in absolute terms, or vice versa."
)

st.subheader("The two results that weren't supposed to happen this way")
st.write(
    "This project pre-registered a confidence level for each cause *before* looking at any 2020–2024 "
    "data (see Methods → Pre-registered hypotheses). Two results contradict those stated priors — and "
    "that's exactly what makes them worth highlighting: a result that confirms what you expected is "
    "much easier to have gotten by accident than one that surprises you."
)

cancer = summary[summary["cause"] == "Malignant neoplasms"].iloc[0]
alz = summary[summary["cause"] == "Alzheimer's disease"].iloc[0]

with st.container(border=True):
    st.write("**Cancer was expected to show nothing, and it didn't.**")
    st.write(
        f"The pre-registered prior for malignant neoplasms was explicitly a null result, with \"low\" "
        "confidence by design — the reasoning was that delayed cancer screening and treatment during "
        "the pandemic would take years longer than the 2024 data window to show up as excess "
        f"mortality. Instead, cancer shows a **{cancer['persistence_class'].lower()}** disruption "
        f"(p = {cancer['p_value']:.3g}, survives FDR correction) — though a real, FDR-significant, "
        f"still-persisting one, its magnitude is modest ({cancer['acute_pct_deviation']:+.1f}% in "
        f"2020–21, {cancer['latest_pct_deviation']:+.1f}% by 2024) next to the larger disruptions below. "
        "Either the deferred-care effect on cancer mortality moved faster than expected, or something "
        "else is contributing — this analysis can't distinguish between those, but the result itself is "
        "real and worth investigating further."
    )

with st.container(border=True):
    st.write("**Alzheimer's was expected to show a large effect, and it didn't.**")
    st.write(
        "The pre-registered prior was \"high confidence\" of a large disruption, on the theory that "
        "pandemic-era isolation and care-facility disruption would show up clearly in dementia "
        f"mortality. It didn't — p = {alz['p_value']:.2g}, nowhere close to significant. This doesn't "
        "mean isolation had no effect on people with Alzheimer's; it means that effect, if real, isn't "
        "visible in national mortality *rates* over this window using this method."
    )

st.subheader("Validating the method itself: the negative control")
passed = bool(neg_control["passed"])
with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Negative control", "Passed" if passed else "FAILED")
    with st.container(border=True):
        st.metric("Cause tested", neg_control["cause"].split(",")[0])
    with st.container(border=True):
        st.metric("p-value (gating metric)", f"{neg_control['p_value_counts']:.3g}")
st.write(
    "Before trusting any of the above, the pipeline runs the identical method on a cause with no "
    "plausible COVID mechanism — congenital malformations and chromosomal abnormalities, concentrated "
    "in infancy and driven by prenatal/genetic factors. It passed: no significant disruption. This "
    "doesn't prove every positive result above is real, but a failure here would have been strong "
    "evidence the method was just detecting noise or a database artifact — and it didn't fail."
)
with st.expander("This wasn't the first choice — a real methodological correction"):
    st.write(
        "Accidental drowning was the original negative control, and it failed — it showed a real, "
        "statistically robust increase in deaths starting in 2020, confirmed on raw counts (not a "
        "rounding artifact). That's consistent with published CDC reporting on pandemic-era increases "
        "in drowning deaths (pool/beach closures, lifeguard shortages, more unsupervised time in home "
        "pools). Drowning was swapped out because it was never actually COVID-independent — not because "
        "the method failed. Full account in `research_protocol.md`'s 2026-09-01 addenda."
    )

st.subheader("Robustness: does this depend on modeling choices?")
if sensitivity_check_available():
    sens = load_sensitivity_check()
    test_sens = sens[sens["cause"].isin(TEST_CAUSES)]
    for check_name, label in [
        ("baseline_window (1999 vs 2010)", "Baseline window (1999–2019 vs. shorter 2010–2019)"),
        ("significance_threshold (0.05 vs 0.01)", "Significance threshold (α=0.05 vs. stricter α=0.01)"),
        ("baseline_trend_shape (linear vs quadratic)", "Baseline trend shape (linear vs. curved/quadratic)"),
    ]:
        check_rows = test_sens[test_sens["check"] == check_name]
        n_disagree = int((~check_rows["agrees"]).sum())
        if n_disagree == 0:
            st.success(f"**{label}:** all 6 test causes agree. Not an artifact of this choice.", icon=":material/check_circle:")
        else:
            disagreeing = check_rows.loc[~check_rows["agrees"], "cause"].tolist()
            st.warning(
                f"**{label}:** {n_disagree} cause(s) disagree — {', '.join(disagreeing)}. "
                "See Data Quality for the full breakdown.",
                icon=":material/warning:",
            )
    st.caption(
        "The trend-shape check found a real, material limitation: heart disease and cerebrovascular "
        "disease's significance depends on assuming a straight-line (not curved) pre-pandemic trend. "
        "Diabetes, drug overdose, and cancer hold up across every axis tested — those three are the "
        "most robust of the 5 disrupted causes."
    )
else:
    st.info("Run `python -m scripts.run_sensitivity_check` to populate this section.", icon=":material/info:")

st.subheader("Which counties were hit hardest (diabetes and drug overdose)")
st.write(
    "For the two causes with real county-level data — diabetes and drug overdose, ~3,000 counties "
    "each, pre-period 2015–2019 vs. post-period 2020–2024 — disruption magnitude is strongly "
    "associated with socioeconomic and healthcare-access context:"
)
for cause in ["Diabetes mellitus", "Drug overdose"]:
    cause_het = het[het["cause"] == cause].sort_values("p_value")
    n_fdr_het = int(cause_het["fdr_significant"].sum())
    st.write(f"**{cause}** — {n_fdr_het} of {len(cause_het)} context variables survive FDR correction:")
    st.dataframe(
        cause_het[["variable", "slope", "p_value", "fdr_significant"]],
        column_config={
            "variable": "Context variable",
            "slope": st.column_config.NumberColumn("Direction/magnitude", format="%.2f"),
            "p_value": st.column_config.NumberColumn("p-value", format="%.3g"),
            "fdr_significant": st.column_config.CheckboxColumn("FDR-significant"),
        },
        hide_index=True,
    )
st.write(
    "Higher uninsured rate, smoking rate, and obesity rate all predict **larger** disruption for both "
    "causes. Higher median household income predicts **smaller** disruption for both. Higher rurality "
    "predicts **smaller** disruption for both — the one genuinely counterintuitive result, running "
    "against a common assumption that rural areas were hit hardest by pandemic-era healthcare "
    "disruption. These are associations, not causal claims: this county-level stage also uses crude "
    "rate rather than age-adjusted rate (WONDER doesn't offer age-adjustment at county granularity), "
    "so part of any measured disruption could reflect each county's own population-aging trajectory "
    "rather than a COVID-era shift — see Data Quality for the full caveat."
)

st.subheader("What this data cannot tell you")
st.write(
    "Mortality data alone cannot separate several very different mechanisms that would all produce "
    "the same statistical signature: direct viral harm, deferred or interrupted medical care, "
    "healthcare-system strain, and economic/isolation stress. A \"Persisted\" classification for heart "
    "disease could be any of these, in any combination — that's why every result here is described as "
    "\"associated with\" or \"consistent with,\" never \"caused by\" (see Methods → Causal language policy)."
)

st.caption(
    "All national-level results use 15 real CDC WONDER exports; all county-level results use 4 real "
    "CDC WONDER exports. Nothing in this project is synthetic. Full provenance: "
    "`docs/manual_data_acquisition.md`."
)
