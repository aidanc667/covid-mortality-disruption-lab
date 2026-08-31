import streamlit as st

from app.components.data_loading import synthetic_banner

st.title("Methods")
synthetic_banner()
st.caption("Every statistical choice below is fixed in docs/research_protocol.md before results are inspected.")

with st.expander("Research question", icon=":material/help:", expanded=True):
    st.write(
        "Which causes of death experienced the greatest and most statistically significant "
        "disruption during the COVID-19 pandemic (2020–2024), how persistent were those "
        "disruptions, and how did disruption severity vary across U.S. counties by "
        "socioeconomic status, healthcare access, and rurality?"
    )
    st.write(
        "COVID-19 is treated as a system-wide shock, not the disease under study — the "
        "question is scoped to *what/how much/where*, not *why*, since mortality data alone "
        "cannot separate direct viral effects from deferred care, isolation, or economic stress."
    )

with st.expander("Pre-registered hypotheses", icon=":material/fact_check:"):
    st.write("Stated before any 2020–2024 data was pulled or analyzed:")
    st.markdown(
        "| Cause | ICD-10 | Prior | Confidence |\n"
        "|---|---|---|---|\n"
        "| Drug overdose | X40-X44, X60-X64, X85, Y10-Y14 | Largest disruption; may reverse by 2023–24 | Very high |\n"
        "| Diseases of heart | I00-I09,I11,I13,I20-I51 | Real acute disruption; persistence uncertain | High |\n"
        "| Diabetes mellitus | E10-E14 | Real acute disruption; persistence uncertain | High |\n"
        "| Alzheimer's disease | G30 | Large, isolation-driven | High |\n"
        "| Cerebrovascular disease | I60-I69 | Real but harder to detect (smaller N) | Moderate |\n"
        "| Malignant neoplasms | C00-C97 | **Expected null** — measurement-lag comparison case | Low (by design) |\n"
        "| Accidental drowning | W65-W74 | **Negative control** — expected null | Validation case |\n"
        "| COVID-19 | U07.1 | Reference series, not a hypothesis test | — |\n"
    )

with st.expander("Data sources and vintage bridging", icon=":material/database:"):
    st.write("Baseline: 1999–2019, CDC WONDER \"Underlying Cause of Death, 1999-2020\" (database D76).")
    st.write("Post-shock: 2020–2024, CDC WONDER \"Underlying Cause of Death, 2018-2024, Single Race\" (database D158) — confirmed live: no 2025 data exists yet.")
    st.write(
        "The two databases use different population-estimate methodologies. The pre-trend is "
        "fit using 1999–2019 only; the entire 2020–2024 comparison uses D158 exclusively (one "
        "consistent vintage). The 2018–2020 overlap years measure the size of the database "
        "jump itself, so it isn't mistaken for a COVID effect."
    )

with st.expander("Statistical methods", icon=":material/query_stats:"):
    st.write(
        "**Known-date interrupted time series (\"excess mortality\").** Fit an expected trend "
        "on 1999–2019, project it forward with a 95% prediction interval, and flag a year as "
        "significantly disrupted if the observed value falls outside that interval. The "
        "breakpoint (2020) is fixed by the shock's known date, not searched for."
    )
    st.write(
        "**Three-way persistence classification.** For causes with a significant acute-phase "
        "(2020–2021) disruption: *Persisted* (still significant, same direction, through "
        "2024), *Resolved* (shrank back within the prediction interval), or *Reversed* "
        "(flipped sign). A binary scheme would flatten a reversal into a false \"resolved.\""
    )
    st.write(
        "**Independent cross-check.** PELT and binary segmentation (reused unmodified from "
        "the project's diabetes-pilot phase) run on each bridged series, checking whether "
        "they land on a breakpoint near March 2020 without being told to."
    )
    st.write(
        "**Negative control.** The identical pipeline run on accidental drowning mortality — "
        "a cause with no plausible COVID mechanism. A significant \"disruption\" there would "
        "indicate the method is detecting an artifact, not a real signal, and is a hard gate "
        "on trusting the other 6 causes."
    )
    st.write(
        "**Multiple-testing correction.** Benjamini-Hochberg FDR correction applied across "
        "the 6 substantive test causes as one family, separately from the heterogeneity-stage "
        "correction applied per cause across its context variables."
    )

with st.expander("County-level heterogeneity", icon=":material/map:"):
    st.write(
        "For causes with a significant disruption, per-county disruption magnitude "
        "(aggregated post-period mean minus pre-period mean) is regressed against real "
        "County Health Rankings context variables (uninsured rate, smoking, obesity, income, "
        "rurality). Associational only — see the causal-language policy below."
    )

with st.expander("Causal language policy", icon=":material/gavel:"):
    st.write(
        "No result uses \"cause,\" \"led to,\" or \"resulted in.\" Approved language: "
        "associated with, temporally aligned with, consistent with, predictive of, correlated with."
    )

with st.expander("Known limitations", icon=":material/warning:"):
    st.write(
        "- Observational, ecological design — no individual-level causal inference\n"
        "- Mortality-vintage discontinuity between the two CDC WONDER databases\n"
        "- ICD-10 coding practices may have shifted during 2020–2021 due to strain on death-certification systems\n"
        "- Cancer's expected null result is a measurement-lag artifact of the data window, not evidence the mechanism doesn't exist\n"
        "- Small-county suppression at the county-level heterogeneity stage\n"
        "- CHR&R behavioral measures (smoking, obesity) are PLACES model-based small-area estimates, not raw counts\n"
        "- Multiple testing across both the 6-cause family and the per-cause context-variable family\n"
        "- Counties are not geographically independent (spatial autocorrelation not yet modeled)\n"
        "- All findings remain associational — the mechanism behind any confirmed disruption "
        "(direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be "
        "separated by mortality data alone"
    )

st.caption("See docs/research_protocol.md and docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md for full detail.")
