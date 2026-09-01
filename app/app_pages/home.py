import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, data_available, synthetic_banner,
    heterogeneity_synthetic_banner,
)

st.title("COVID Mortality Disruption Lab")
st.caption(
    "Which causes of death were most disrupted by the COVID-19 pandemic, "
    "how persistent were those disruptions, and how did they vary across U.S. counties?"
)

synthetic_banner()

st.markdown(
    "> **Which causes of death experienced the greatest and most statistically significant "
    "disruption during the COVID-19 pandemic (2020–2024), how persistent were those "
    "disruptions through the most recent available data, and how did disruption severity "
    "vary across U.S. counties by socioeconomic status, healthcare access, and rurality?**"
)

st.write(
    "COVID-19 is treated as a system-wide shock to the healthcare/public-health system, "
    "not as the disease under study. This project asks *what* changed, *how much*, and "
    "*where* — not *why* — because mortality data alone cannot cleanly separate direct "
    "viral effects from deferred care, isolation, or economic-stress mechanisms."
)

if not data_available():
    st.warning(
        "No precomputed results found yet. Run `python -m scripts.run_covid_disruption_pipeline` "
        "to populate outputs/models/.",
        icon=":material/warning:",
    )
else:
    summary = load_disruption_summary()
    neg_control = load_negative_control().iloc[0]
    passed = bool(neg_control["passed"])

    with st.container(horizontal=True):
        with st.container(border=True):
            n_disrupted = int((summary["persistence_class"] != "No significant disruption").sum())
            st.metric("Causes with a significant disruption", f"{n_disrupted} of {len(summary)}", border=False)
            st.caption(":material/trending_up: 6 test causes, FDR-corrected (§7a)")
        with st.container(border=True):
            n_fdr = int(summary["fdr_significant"].sum())
            st.metric("Survive FDR correction", f"{n_fdr} of {len(summary)}", border=False)
            st.caption(":material/functions: Benjamini-Hochberg across the 6-cause family")
        with st.container(border=True):
            reversed_causes = summary.loc[summary["persistence_class"] == "Reversed", "cause"]
            st.metric("Reversed trajectory", reversed_causes.iloc[0] if len(reversed_causes) else "None", border=False)
            st.caption(":material/u_turn_right: Spiked, then declined below the pre-pandemic trend")
        with st.container(border=True):
            st.metric("Negative control", "Passed" if passed else "FAILED", border=False)
            st.caption(":material/verified: Congenital malformations — no plausible COVID mechanism")

    if not passed:
        st.error(
            "The negative control did not pass — per research_protocol.md §7 method 4, this "
            "is a hard gate. Results on the other 6 causes should not be trusted until this "
            "is resolved.",
            icon=":material/error:",
        )

st.subheader("Start here")
row1 = st.container(horizontal=True)
with row1:
    with st.container(border=True, width="stretch"):
        st.markdown(":material/insights: **Findings**")
        st.caption("The plain-language summary — what we found, and the two results that contradicted our own priors.")
        st.page_link("app_pages/findings.py", label="Read the findings", icon=":material/arrow_forward:")
    with st.container(border=True, width="stretch"):
        st.markdown(":material/monitor_heart: **Causes of death**")
        st.caption("Deep dive into each of the 6 causes: the data, the effect size, and possible reasons why.")
        st.page_link("app_pages/causes.py", label="Explore by cause", icon=":material/arrow_forward:")

row2 = st.container(horizontal=True)
with row2:
    with st.container(border=True, width="stretch"):
        st.markdown(":material/map: **Geographic heterogeneity**")
        st.caption("An interactive U.S. county map — where disruption was largest, and what predicts it.")
        st.page_link("app_pages/geographic_heterogeneity.py", label="See the map", icon=":material/arrow_forward:")
    with st.container(border=True, width="stretch"):
        st.markdown(":material/fact_check: **Data quality**")
        st.caption("Suppression, vintage bridging, the negative control, and sensitivity analysis — shown, not hidden.")
        st.page_link("app_pages/data_quality.py", label="Check the rigor", icon=":material/arrow_forward:")

heterogeneity_synthetic_banner()

with st.expander("Ethics statement", icon=":material/balance:"):
    st.write(
        "This project uses publicly available aggregate data and is intended for research and "
        "educational purposes. It does not provide medical advice or individual-level risk predictions."
    )
