import streamlit as st

from src.utils.config import (
    DIABETES_ICD10_CODES, MIN_NONSUPPRESSED_YEARS, MIN_COUNTY_POPULATION,
    PRIMARY_WINDOW, EXTENSION_WINDOW, HETEROGENEITY_WINDOW,
)
from app.components.data_loading import synthetic_banner

st.title("Methods")
synthetic_banner()
st.caption("Every statistical choice below is fixed in docs/research_protocol.md before results are inspected.")

with st.expander("Outcome definition", icon=":material/monitor_heart:", expanded=True):
    st.write(f"Diabetes mellitus, underlying cause of death, ICD-10 codes **{', '.join(DIABETES_ICD10_CODES)}**.")
    st.write("Primary outcome: CDC WONDER age-adjusted mortality rate (2000 U.S. standard population), per 100,000.")
    st.write(f"Primary analysis window: **{PRIMARY_WINDOW[0]}–{PRIMARY_WINDOW[1]}** "
             "(one consistent CDC WONDER database vintage).")
    st.write(f"Secondary extension window: **{EXTENSION_WINDOW[0]}–{EXTENSION_WINDOW[1]}**, reported separately "
             "— the two mortality database vintages use different population denominators and are not "
             "concatenated into a single trend line.")
    st.write(f"Heterogeneity/context analysis is scoped to **{HETEROGENEITY_WINDOW[0]}–{HETEROGENEITY_WINDOW[1]}**, "
             "matching County Health Rankings' actual data availability.")

with st.expander("County eligibility for change-point modeling", icon=":material/rule:"):
    st.write(f"A county is eligible only if it has at least **{MIN_NONSUPPRESSED_YEARS}** non-suppressed, "
             f"non-unreliable years of data AND a mid-period population of at least "
             f"**{MIN_COUNTY_POPULATION:,}**.")
    st.write("Ineligible counties are retained in every table and view, flagged, never dropped.")

with st.expander("Change-point detection methods", icon=":material/query_stats:"):
    st.write("**Segmented regression (primary).** Grid search over candidate breakpoint years minimizing "
             "two-segment sum of squared errors, tested against a single-line null via a Chow (F) test. "
             "A break is only reported as detected if that test is significant at α=0.05.")
    st.write("**PELT** and **binary segmentation** (independent cross-checks, via `ruptures`). Both run on "
             "the *first-differenced* rate series, since standard change-point cost models detect shifts in "
             "mean, not in trend — differencing turns a slope change into a mean shift these methods can "
             "correctly detect.")
    st.write("**Method agreement** is reported as a plain count (e.g. \"3/3 methods agree within ±1 year\"), "
             "explicitly *not* a formal statistical probability.")

with st.expander("Trajectory classification", icon=":material/timeline:"):
    st.write("**Improving**: significant break AND slope change ≤ −0.3 deaths/100k/year.")
    st.write("**Worsening**: significant break AND slope change ≥ +0.3 deaths/100k/year.")
    st.write("**Stable**: no significant break, or a significant break with |slope change| < 0.3.")
    st.caption("This threshold is a placeholder pending calibration against real data — see the addendum "
               "in docs/research_protocol.md dated 2026-08-29.")

with st.expander("Causal language policy", icon=":material/gavel:"):
    st.write("No result in this app or its report uses \"cause,\" \"led to,\" or \"resulted in.\" "
             "Approved language: associated with, temporally aligned with, consistent with, predictive of, "
             "correlated with.")

with st.expander("Known limitations", icon=":material/warning:"):
    st.write(
        "- Observational, ecological design — no individual-level causal inference\n"
        "- Mortality-vintage discontinuity between the 1999–2020 and 2018–2024 CDC databases\n"
        "- Small-county suppression and instability\n"
        "- County Health Rankings' behavioral measures (smoking, obesity, inactivity) are PLACES "
        "model-based small-area estimates, not raw counts\n"
        "- PM2.5 coverage is limited to the ~20% of counties with an EPA monitor\n"
        "- No context data exists before 2010 (County Health Rankings' start)\n"
        "- Multiple testing across context-variable comparisons\n"
        "- Counties are not geographically independent (spatial autocorrelation not yet modeled)"
    )

st.caption("See docs/research_protocol.md, docs/data_feasibility_audit.md, and DATA_SOURCES.md for full detail.")
