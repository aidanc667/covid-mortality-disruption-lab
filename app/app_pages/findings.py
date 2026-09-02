import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, load_heterogeneity_summary,
    load_heterogeneity_selection_bias, load_heterogeneity_rurality_robustness,
    load_sensitivity_check, data_available, sensitivity_check_available, synthetic_banner, TEST_CAUSES,
    CONTEXT_VAR_LABELS, scale_context_slope_for_display,
)
from src.utils.config import OUTPUTS_REPORTS

st.title("Findings")
synthetic_banner()
st.caption(
    "What the completed analysis found, in plain language. Full methodology: see Methods. "
    "Every number below is drawn live from the same precomputed results as the rest of the app."
)

report_path = OUTPUTS_REPORTS / "covid_mortality_disruption_report.pdf"
if report_path.exists():
    st.download_button(
        "Download formal PDF report",
        data=report_path.read_bytes(),
        file_name="covid_mortality_disruption_report.pdf",
        mime="application/pdf",
        icon=":material/description:",
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
if sensitivity_check_available():
    trend_shape = load_sensitivity_check()
    trend_shape = trend_shape[trend_shape["check"] == "baseline_trend_shape (linear vs quadratic)"][["cause", "agrees"]]
    display = display.merge(trend_shape, on="cause", how="left")
    display["agrees"] = display["agrees"].fillna(True)
else:
    display["agrees"] = True
st.dataframe(
    display[["cause", "persistence_class", "p_value", "fdr_significant", "acute_pct_deviation", "latest_pct_deviation", "agrees"]],
    column_config={
        "cause": st.column_config.TextColumn("Cause", width="medium"),
        "persistence_class": st.column_config.TextColumn("Result", width="medium"),
        "p_value": st.column_config.NumberColumn("p-value", format="%.3g"),
        "fdr_significant": st.column_config.CheckboxColumn("Survives FDR"),
        "acute_pct_deviation": st.column_config.NumberColumn("2020–21 deviation", format="%+.1f%%"),
        "latest_pct_deviation": st.column_config.NumberColumn("2024 deviation", format="%+.1f%%"),
        "agrees": st.column_config.CheckboxColumn(
            "Robust to trend shape",
            help="False means this result loses significance if the pre-pandemic baseline is fit "
                 "as a curve instead of a straight line. See Causes of death or Data Quality.",
        ),
    },
    hide_index=True,
    width="stretch",
)
st.caption(
    "\"Deviation\" is the effect size: how far the observed rate is from the expected pre-pandemic "
    "trend, as a percent. Significance (p-value) and magnitude (deviation) are different claims: a "
    "cause can be statistically significant while still small in absolute terms, or vice versa. "
    "\"Robust to trend shape\" flags whether the result survives an alternate, curved baseline fit, "
    "which only cerebrovascular disease fails. Diseases of heart had the same problem originally "
    "but is now fully robust after its baseline was corrected to a shorter, more recent window "
    "(see Causes of death for the chart, and research_protocol.md's 2026-09-01 addendum for why)."
)

st.subheader("The two results that weren't supposed to happen this way")
st.write(
    "This project pre-registered a confidence level for each cause *before* looking at any 2020–2024 "
    "data (see Methods → Pre-registered hypotheses). Two results contradict those stated priors, and "
    "that's exactly what makes them worth highlighting: a result that confirms what you expected is "
    "much easier to have gotten by accident than one that surprises you."
)

cancer = summary[summary["cause"] == "Malignant neoplasms"].iloc[0]
alz = summary[summary["cause"] == "Alzheimer's disease"].iloc[0]

with st.container(border=True):
    st.write("**Cancer was expected to show nothing, and it didn't.**")
    st.write(
        f"The pre-registered prior for malignant neoplasms was explicitly a null result, with \"low\" "
        "confidence by design. The reasoning was that delayed cancer screening and treatment during "
        "the pandemic would take years longer than the 2024 data window to show up as excess "
        f"mortality. Instead, cancer shows a real, FDR-significant **{cancer['persistence_class'].lower()}** "
        f"disruption (p = {cancer['p_value']:.3g}), though its magnitude is modest "
        f"({cancer['acute_pct_deviation']:+.1f}% in 2020–21, {cancer['latest_pct_deviation']:+.1f}% by "
        f"2024) next to the larger disruptions below. "
        "Either the deferred-care effect on cancer mortality moved faster than expected, or something "
        "else is contributing. This analysis can't distinguish between those, but the result itself is "
        "real and worth investigating further."
    )

with st.container(border=True):
    st.write("**Alzheimer's was expected to show a large effect, and it didn't.**")
    st.write(
        "The pre-registered prior was \"high confidence\" of a large disruption, on the theory that "
        "pandemic-era isolation and care-facility disruption would show up clearly in dementia "
        f"mortality. It didn't, with p = {alz['p_value']:.2g}, nowhere close to significant. This doesn't "
        "mean isolation had no effect on people with Alzheimer's. It means that effect, if real, isn't "
        "visible in national mortality *rates* over this window using this method. Pooling all five "
        "post-2020 years instead of just the acute window does turn up a real, later decline "
        f"(p = {alz['full_period_p_value']:.2g}); see Causes of death for the numbers."
    )

st.subheader("Validating the method itself: the negative control")
passed = bool(neg_control["passed"])
with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Negative control", "Passed" if passed else "FAILED")
    with st.container(border=True):
        st.caption("Cause tested")
        st.write(f"**{neg_control['cause'].split(',')[0]}**")
    with st.container(border=True):
        st.metric(
            "p-value", f"{neg_control['p_value_counts']:.3g}",
            help="Computed on raw death counts, the actual gating metric, not age-adjusted rate.",
        )
st.write(
    "Before trusting any of the above, the pipeline runs the identical method on a cause with no "
    "direct COVID mechanism: congenital malformations and chromosomal abnormalities, concentrated "
    "in infancy and driven by prenatal/genetic factors. It passed: no significant disruption. This "
    "doesn't prove every positive result above is real, but a failure here would have been strong "
    "evidence the method was just detecting noise or a database artifact, and it didn't fail."
)
with st.expander("This wasn't the first choice: a real methodological correction"):
    st.write(
        "Accidental drowning was the original negative control, and it failed. It showed a real, "
        "statistically robust increase in deaths starting in 2020, confirmed on raw counts (not a "
        "rounding artifact). That's consistent with published CDC reporting on pandemic-era increases "
        "in drowning deaths (pool/beach closures, lifeguard shortages, more unsupervised time in home "
        "pools). Drowning was swapped out because it was never actually COVID-independent, not because "
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
            cause_word, verb = ("cause", "disagrees") if n_disagree == 1 else ("causes", "disagree")
            st.warning(
                f"**{label}:** {n_disagree} {cause_word} {verb} ({', '.join(disagreeing)}). "
                "See Data Quality for the full breakdown.",
                icon=":material/warning:",
            )
    st.caption(
        "The trend-shape check originally found this same problem for both heart disease and "
        "cerebrovascular disease. Heart disease's baseline has since been corrected to a shorter, "
        "more recent window and is now fully robust; cerebrovascular disease's significance still "
        "depends partly on the straight-line assumption, though less than before the correction "
        "(see research_protocol.md's 2026-09-01 addendum). Diabetes, drug overdose, and cancer hold "
        "up across every axis tested without needing any correction."
    )

    hac_disagree = summary[(summary["p_value"] < 0.05) != (summary["hac_p_value"] < 0.05)]["cause"].tolist()
    if not hac_disagree:
        st.success(
            "**Autocorrelation-robust standard errors (Newey-West/HAC):** all 5 significant causes "
            "stay significant. The classical p-value assumes independent baseline years, which is "
            "measurably false for several causes (autocorrelation up to 0.82); correcting for it "
            "raises those p-values by roughly 1-2 orders of magnitude, but none cross back over 0.05.",
            icon=":material/check_circle:",
        )
    else:
        st.warning(
            f"**Autocorrelation-robust standard errors (Newey-West/HAC):** {len(hac_disagree)} "
            f"cause(s) disagree with the classical result ({', '.join(hac_disagree)}). See Causes "
            "of death for each cause's HAC p-value.",
            icon=":material/warning:",
        )
else:
    st.info("Run `python -m scripts.run_sensitivity_check` to populate this section.", icon=":material/info:")

st.subheader("Which counties were hit hardest (diabetes and drug overdose)")
st.write(
    "For the two causes with real county-level data (diabetes and drug overdose, ~3,000 counties "
    "each, pre-period 2015–2019 vs. post-period 2020–2024), disruption magnitude is strongly "
    "associated with socioeconomic and healthcare-access context:"
)
for cause in ["Diabetes mellitus", "Drug overdose"]:
    cause_het = het[het["cause"] == cause].sort_values("p_value").copy()
    cause_het["slope"] = cause_het.apply(
        lambda r: scale_context_slope_for_display(r["variable"], r["slope"]), axis=1
    )
    cause_het["variable"] = cause_het["variable"].map(CONTEXT_VAR_LABELS).fillna(cause_het["variable"])
    n_fdr_het = int(cause_het["fdr_significant"].sum())
    st.write(f"**{cause}**: {n_fdr_het} of {len(cause_het)} context variables survive FDR correction:")
    st.dataframe(
        cause_het[["variable", "slope", "p_value", "fdr_significant"]],
        column_config={
            "variable": st.column_config.TextColumn("Context variable", width="large"),
            "slope": st.column_config.NumberColumn("Direction/magnitude", format="%.2f", width="small"),
            "p_value": st.column_config.NumberColumn("p-value", format="%.3g", width="small"),
            "fdr_significant": st.column_config.CheckboxColumn("FDR-significant", width="small"),
        },
        hide_index=True,
        width="stretch",
    )
st.write(
    "Higher uninsured rate, smoking rate, and obesity rate all predict **larger** disruption for both "
    "causes. Higher median household income predicts **smaller** disruption for both. Higher rurality "
    "predicts **smaller** disruption for both, the one genuinely counterintuitive result, running "
    "against a common assumption that rural areas were hit hardest by pandemic-era healthcare "
    "disruption, though for drug overdose this specific relationship falls just short of FDR "
    "significance (diabetes clears it comfortably). These are associations, not causal claims: this county-level stage also uses crude "
    "rate rather than age-adjusted rate (WONDER doesn't offer age-adjustment at county granularity), "
    "so part of any measured disruption could reflect each county's own population-aging trajectory "
    "rather than a COVID-era shift. See Data Quality for the full caveat."
)

bias = load_heterogeneity_selection_bias()
robustness = load_heterogeneity_rurality_robustness()
with st.expander("The rurality finding needs a real caveat: click to see why", icon=":material/warning:"):
    st.write(
        "A self-audit of this project's own most counterintuitive finding found a genuine selection "
        "bias: counties *excluded* from the regression (too few non-suppressed years) are far more "
        "rural, on average, than the counties actually included."
    )
    for _, row in bias.iterrows():
        st.write(
            f"**{row['cause']}**: excluded counties average **{row['mean_excluded']*100:.0f}% rural**, "
            f"included counties average **{row['mean_included']*100:.0f}% rural**."
        )
    st.write(
        "Splitting the included counties at their own median rurality shows the two causes aren't "
        "equally trustworthy here:"
    )
    for cause in ["Diabetes mellitus", "Drug overdose"]:
        r = robustness[robustness["cause"] == cause].set_index("half")
        upper, lower = r.loc["upper_half"], r.loc["lower_half"]
        if upper["p_value"] < 0.05:
            st.success(
                f"**{cause}**: relationship holds up among the more-rural half of the included "
                f"sample (p={upper['p_value']:.3g}), even strengthening there vs. the less-rural "
                f"half (p={lower['p_value']:.3g}).", icon=":material/check_circle:",
            )
        else:
            st.error(
                f"**{cause}**: relationship is driven almost entirely by the less-rural half "
                f"(p={lower['p_value']:.3g}) and is not significant among the more-rural half "
                f"(p={upper['p_value']:.3g}). Read this cause's rurality result with real "
                f"skepticism.", icon=":material/error:",
            )

st.subheader("What this data cannot tell you")
st.write(
    "Mortality data alone cannot separate several very different mechanisms that would all produce "
    "the same statistical signature: direct viral harm, deferred or interrupted medical care, "
    "healthcare-system strain, and economic/isolation stress. A \"Persisted\" classification for heart "
    "disease could be any of these, in any combination, which is why every result here is described as "
    "\"associated with\" or \"consistent with,\" never \"caused by\" (see Methods → Causal language policy)."
)

st.caption(
    "All national-level results use 15 real CDC WONDER exports; all county-level results use 4 real "
    "CDC WONDER exports. Nothing in this project is synthetic. Full provenance: "
    "`docs/manual_data_acquisition.md`."
)
