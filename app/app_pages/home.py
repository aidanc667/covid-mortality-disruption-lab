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
        "No precomputed results found yet. Run `python scripts/run_covid_disruption_pipeline.py` "
        "(or the real pipeline, once available) to populate outputs/models/.",
        icon=":material/warning:",
    )
else:
    summary = load_disruption_summary()
    neg_control = load_negative_control().iloc[0]

    with st.container(horizontal=True):
        with st.container(border=True):
            n_disrupted = int((summary["persistence_class"] != "No significant disruption").sum())
            st.metric("Causes with a significant disruption", f"{n_disrupted} of {len(summary)}")
            st.caption("6 test causes, FDR-corrected (§7a)")
        with st.container(border=True):
            n_fdr = int(summary["fdr_significant"].sum())
            st.metric("Survive FDR correction", f"{n_fdr} of {len(summary)}")
            st.caption("Benjamini-Hochberg across the 6-cause family")
        with st.container(border=True):
            reversed_causes = summary.loc[summary["persistence_class"] == "Reversed", "cause"]
            st.metric("Reversed trajectory", reversed_causes.iloc[0] if len(reversed_causes) else "None")
            st.caption("Spiked, then declined below the pre-pandemic trend")
        with st.container(border=True):
            passed = bool(neg_control["passed"])
            st.metric("Negative control", "Passed" if passed else "FAILED", delta=None)
            st.caption("Congenital malformations — no plausible COVID mechanism")

    if not passed:
        st.error(
            "The negative control did not pass — per research_protocol.md §7 method 4, this "
            "is a hard gate. Results on the other 6 causes should not be trusted until this "
            "is resolved.",
            icon=":material/error:",
        )

st.subheader("Explore")
st.write(
    "**Disruption overview** — every cause's trajectory against its expected pre-pandemic trend, side by side.\n\n"
    "**Persistence explorer** — did each disruption persist, resolve, or reverse through 2024?\n\n"
    "**Geographic heterogeneity** — which county characteristics are associated with disruption size.\n\n"
    "**County deep dive** — inspect one county's disruption relative to its context.\n\n"
    "**Data quality** — suppression, the vintage-bridging discontinuity, and the negative control, shown rather than hidden.\n\n"
    "**Methods** — every statistical choice, threshold, and pre-registered hypothesis, made explicit."
)
heterogeneity_synthetic_banner()

with st.expander("Ethics statement", icon=":material/balance:"):
    st.write(
        "This project uses publicly available aggregate data and is intended for research and "
        "educational purposes. It does not provide medical advice or individual-level risk predictions."
    )
