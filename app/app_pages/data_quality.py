import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, load_heterogeneity_summary,
    data_available, synthetic_banner, TEST_CAUSES,
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
        st.metric("Classification", neg_control["persistence_class"])
    with st.container(border=True):
        st.metric("p-value", f"{neg_control['p_value']:.4g}")

if passed:
    st.success(
        "Accidental drowning mortality — a cause with no plausible COVID mechanism — shows "
        "no significant disruption, as expected. This does not prove the methodology is "
        "artifact-free, but a failure here would have been strong evidence that it is.",
        icon=":material/check_circle:",
    )
else:
    st.error(
        "The negative control shows a significant disruption. Per research_protocol.md §7 "
        "method 4, this is a hard gate — results on the other 6 causes should not be trusted "
        "until this is resolved (check for a vintage-bridging artifact or a generic 2020 "
        "data-quality issue before trusting any other result on this page).",
        icon=":material/error:",
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
het = load_heterogeneity_summary()
for cause in het["cause"].unique():
    cause_het = het[het["cause"] == cause]
    with st.container(horizontal=True):
        st.write(f"**{cause}**")
        st.caption(f"{int(cause_het['fdr_significant'].sum())} of {len(cause_het)} context variables FDR-significant")

st.subheader("Vintage-bridging discontinuity")
st.info(
    "This synthetic demo run does not exercise the real vintage-bridging check "
    "(`src/cleaning/bridging.is_bridging_reliable`) since the synthetic national series is "
    "generated as one continuous fixture, not pulled from two separate CDC WONDER database "
    "vintages. Once real data is loaded, this section will show the median relative offset "
    "measured from the 2018–2020 overlap years and flag if it exceeds the 10% reliability "
    "threshold (research_protocol.md §9).",
    icon=":material/info:",
)
