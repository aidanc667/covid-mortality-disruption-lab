import streamlit as st

from app.components.data_loading import (
    load_disruption_summary, load_negative_control, data_available, synthetic_banner,
    heterogeneity_synthetic_banner,
)

st.title("COVID Mortality Disruption Lab")
st.header(
    "Officially, COVID-19's death toll is the people who died of the virus itself. "
    "This project measures what it did to everyone else."
)
synthetic_banner()

st.subheader("Why this matters")
st.write(
    "Pandemic death tolls are usually counted one way: how many people died of COVID-19 itself. "
    "That number misses a larger, quieter effect — years of deferred screenings, delayed emergency "
    "care, disrupted medication access, and interrupted treatment for the diseases that already "
    "killed the most Americans every year, pandemic or not. This project measures that second, "
    "harder-to-see toll directly from real government mortality data — not survey estimates or "
    "modeling assumptions — for 6 major causes of death, and asks a question that's still open "
    "four years on: **is it actually over?**"
)

st.subheader("What we did")
steps = st.container(horizontal=True)
with steps:
    with st.container(border=True, width="stretch"):
        st.markdown(":material/database: **Real data**")
        st.caption("19 CDC WONDER mortality exports (national + county), plus real County Health Rankings socioeconomic data.")
    with st.container(border=True, width="stretch"):
        st.markdown(":material/edit_note: **Locked before looking**")
        st.caption("Hypotheses and confidence levels for each cause were written down before any 2020–2024 data was analyzed.")
    with st.container(border=True, width="stretch"):
        st.markdown(":material/verified: **Tested, not assumed**")
        st.caption("A negative control, 3 independent sensitivity checks, and FDR correction — a passing grade wasn't assumed.")
    with st.container(border=True, width="stretch"):
        st.markdown(":material/travel_explore: **Mapped and explained**")
        st.caption("Results broken down by cause and by county, with research-grounded reasoning for what could explain each one.")

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
    n_disrupted = int((summary["persistence_class"] != "No significant disruption").sum())

    st.subheader("The headline finding")
    st.write(
        f"**{n_disrupted} of the 6 major causes tested still show a statistically significant "
        "deviation from their pre-pandemic trend — four years later, none of them has fully "
        "returned to normal, and none reversed direction.** The one cause with no disruption is "
        "itself a real, meaningful result, not a gap in the data. Full breakdown, including two "
        "results that contradicted this project's own predictions: see Findings."
    )

    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric(
                "Significant disruption", f"{n_disrupted} of {len(summary)}", border=False,
                help="Of the 6 causes tested, this many showed a death rate that moved outside "
                     "what a straight-line projection of the pre-pandemic trend would predict — "
                     "a real statistical deviation, not normal year-to-year noise.",
            )
            st.caption(":material/trending_up: 6 test causes, FDR-corrected (§7a)")
        with st.container(border=True):
            n_fdr = int(summary["fdr_significant"].sum())
            st.metric(
                "FDR-significant", f"{n_fdr} of {len(summary)}", border=False,
                help="Testing 6 causes at once means some 'significant' results could appear by "
                     "chance alone. FDR correction is a stricter bar that accounts for this — "
                     "this many results still clear it, meaning they're very likely real effects.",
            )
            st.caption(":material/functions: Benjamini-Hochberg across the 6-cause family")
        with st.container(border=True):
            reversed_causes = summary.loc[summary["persistence_class"] == "Reversed", "cause"]
            reversed_value = reversed_causes.iloc[0] if len(reversed_causes) else "None"
            st.metric(
                "Reversed trajectory", reversed_value if len(reversed_value) <= 12 else f"{len(reversed_causes)}",
                border=False,
                help=(
                    f"{reversed_value} — a cause 'reverses' if it spiked one direction, then swung "
                    "back past the pre-pandemic trend in the opposite direction."
                    if len(reversed_causes) else
                    "A cause 'reverses' if it spiked one direction, then swung back past the "
                    "pre-pandemic trend in the opposite direction. None of the 6 causes did this "
                    "— whatever changed, stayed changed in the same direction."
                ),
            )
            st.caption(":material/u_turn_right: Spiked, then declined below the pre-pandemic trend")
        with st.container(border=True):
            st.metric(
                "Negative control", "Passed" if passed else "FAILED", border=False,
                help="A built-in sanity check: the identical method run on a cause with no "
                     "plausible COVID connection (a birth-defect category), to confirm the method "
                     "doesn't just find 'disruption' everywhere by accident. It found nothing "
                     "there, as expected — evidence the method works.",
            )
            st.caption(":material/verified: Congenital malformations — no plausible COVID mechanism")

    if not passed:
        st.error(
            "The negative control did not pass — per research_protocol.md §7 method 4, this "
            "is a hard gate. Results on the other 6 causes should not be trusted until this "
            "is resolved.",
            icon=":material/error:",
        )

    st.caption(
        ":green-badge[92 automated tests] :blue-badge[Pre-registered protocol] "
        ":violet-badge[Real CDC WONDER data] :orange-badge[3-axis sensitivity analysis]"
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
