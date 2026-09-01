import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, load_heterogeneity_summary, load_bridging_summary,
    data_available, synthetic_banner, heterogeneity_synthetic_banner, TEST_CAUSES,
)

st.title("Data quality")
synthetic_banner()
st.caption("The vintage-bridging discontinuity, the negative control, and multiple-testing correction are shown directly, not hidden (research_protocol.md §7a, §9).")

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

st.subheader("Negative control (hard gate)")
neg_control = load_negative_control().iloc[0]
passed = bool(neg_control["passed"])

with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Status", "Passed" if passed else "FAILED")
    with st.container(border=True):
        st.metric("Classification (raw counts, gating metric)", neg_control["persistence_class_counts"])
    with st.container(border=True):
        st.metric("p-value (raw counts)", f"{neg_control['p_value_counts']:.4g}")

st.caption(
    f"Cause: **{neg_control['cause']}**. Gate decision computed on {neg_control['gate_metric']}, "
    f"not age-adjusted rate — see note below."
)

if passed:
    st.success(
        f"{neg_control['cause']} mortality — a cause concentrated in infancy with no "
        "plausible COVID mechanism — shows no significant disruption on raw death counts, "
        "as expected. This does not prove the methodology is artifact-free, but a failure "
        "here would have been strong evidence that it is.",
        icon=":material/check_circle:",
    )
else:
    st.error(
        "The negative control shows a significant disruption on raw death counts. Per "
        "research_protocol.md §7 method 4, this is a hard gate — results on the other 6 "
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
        "this issue and still use age-adjusted rate as their primary outcome (research_protocol.md §3) — "
        "all have rates well above this negative control's ~3/100k, where 1-decimal rounding is a much "
        "smaller fraction of the signal."
    )

st.subheader("Multiple-testing correction")
summary = load_disruption_summary()
with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("6-cause family, raw p<0.05", int((summary["p_value"] < 0.05).sum()))
    with st.container(border=True):
        st.metric("6-cause family, FDR-significant", int(summary["fdr_significant"].sum()))
st.caption(
    "Benjamini-Hochberg correction is applied across the 6 substantive test causes as one "
    "family (research_protocol.md §7a) — a stricter bar than testing each cause in isolation."
)

st.subheader("Heterogeneity-stage multiple testing")
heterogeneity_synthetic_banner()
het = load_heterogeneity_summary()
for cause in het["cause"].unique():
    cause_het = het[het["cause"] == cause]
    with st.container(horizontal=True):
        st.write(f"**{cause}**")
        st.caption(f"{int(cause_het['fdr_significant'].sum())} of {len(cause_het)} context variables FDR-significant")

st.subheader("Vintage-bridging discontinuity")
bridging = load_bridging_summary()
n_unreliable = int((~bridging["reliable"]).sum())
if n_unreliable == 0:
    st.success(
        "All causes' 2018–2019 overlap between the D76 (1999–2020) and D158 (2018–2024) "
        "database vintages is within the 10% reliability threshold (research_protocol.md §9) — "
        "in fact the median relative offset is 0% for every cause, since the two overlap years "
        "matched exactly on every metric (deaths, population, crude rate, age-adjusted rate).",
        icon=":material/check_circle:",
    )
else:
    st.error(
        f"{n_unreliable} cause(s) exceed the 10% vintage-bridging reliability threshold — their "
        "results should be treated with extra caution.",
        icon=":material/error:",
    )
st.dataframe(
    bridging.sort_values("median_relative_offset", ascending=False),
    column_config={
        "cause": "Cause",
        "reliable": st.column_config.CheckboxColumn("Reliable (≤10%)"),
        "median_relative_offset": st.column_config.NumberColumn("Median relative offset", format="percent"),
    },
    hide_index=True,
)
st.caption(
    "Measured from the 2018–2019 years present in both database vintages "
    "(`src/cleaning/bridging.estimate_vintage_offset`). This does not correct the data — it "
    "only measures the size of the jump, so a real discontinuity is never mistaken for a "
    "COVID effect."
)
