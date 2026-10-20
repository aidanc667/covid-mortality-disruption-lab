import altair as alt
import streamlit as st

from app.components.data_loading import (
    data_available,
    load_covid_reference_series,
    load_national_series,
    synthetic_banner,
)

AGE_ADJUSTED_EXPLAINER = (
    "It reweights each year's rate as if the U.S. had the exact same age mix every time, "
    "so a real change in risk isn't confused with the population simply getting older "
    "(older populations have higher death rates for almost any cause). Every national-level "
    "rate in this app is age-adjusted, not the raw \"crude\" rate, so different years can be "
    "compared fairly; the county-level maps use crude rate instead, since CDC WONDER "
    "doesn't offer age-adjustment at that granularity (see Data Quality)."
)

st.title("Methods")
synthetic_banner()
st.caption("The statistical plan below was written down in docs/research_protocol.md before results were inspected. Every later change, such as the heart disease and stroke baseline, is logged there as a dated addendum.")

overview, hypotheses_tab, data_tab, stats_tab, counties_tab, language_tab, limits_tab = st.tabs(
    ["Overview", "Hypotheses", "Data", "Statistics", "Counties", "Language policy", "Limitations & ethics"]
)

with overview:
    st.subheader("Why this matters")
    st.write(
        "The impact of a pandemic can't be understood from deaths attributed to the virus alone: "
        "disruption to healthcare, behavior, and daily life can also alter mortality from causes that "
        "have nothing to do with the infection itself. This project asks whether that happened, and "
        "left a measurable footprint in the mortality record."
    )
    if data_available():
        years = load_national_series()["year"]
        span = f"{int(years.max()) - int(years.min()) + 1} years of"
    else:
        span = "decades of"
    st.write(
        f"Using {span} CDC mortality data, each cause's pre-pandemic trend is projected forward to "
        "estimate 2020–2024 without a pandemic. The project then tests whether actual deaths departed "
        "from that, whether the gap lasted through 2024, and, for the five disrupted causes, how it "
        "varied across U.S. counties."
    )

    st.subheader("What we did")
    with st.container(horizontal=True):
        for icon, title, body in [
            (":material/database:", "Real data",
             "33 CDC WONDER mortality exports (15 national, 18 county), plus real County Health Rankings socioeconomic data."),
            (":material/edit_note:", "Locked before looking",
             "Hypotheses and confidence levels for each cause were written down before any 2020–2024 data was analyzed."),
            (":material/verified:", "Tested, not assumed",
             "A negative control, four sensitivity checks, and a correction for testing six causes at once."),
            (":material/travel_explore:", "Mapped and explained",
             "Results broken down by cause and by county, with research-grounded reasoning for what could explain each one."),
        ]:
            with st.container(border=True, width="stretch"):
                st.markdown(f"{icon} **{title}**")
                st.caption(body)

    st.subheader("The breaking point")
    st.caption(
        "COVID-19 itself isn't one of the causes tested. It's the shock the analysis is built around, "
        "and its start date is fixed in advance rather than searched for."
    )
    if data_available():
        covid_series = load_covid_reference_series()
        with st.container(border=True):
            st.markdown("**COVID-19 deaths: March 2020 is the fixed breakpoint**", help=AGE_ADJUSTED_EXPLAINER)
            covid_chart = (
                alt.Chart(covid_series)
                .mark_bar(color="#2C5D86")
                .encode(
                    x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
                    # Short title: the full "Age-adjusted rate (per 100,000)"
                    # rotated 90 degrees needs more height than this chart has
                    # and clips; units are in the tooltip and caption.
                    y=alt.Y("age_adjusted_rate:Q", title="Age-adjusted rate"),
                    tooltip=[
                        alt.Tooltip("year:O", title="Year"),
                        alt.Tooltip("age_adjusted_rate:Q", title="Rate per 100,000", format=".1f"),
                    ],
                )
                .properties(height=180, padding={"left": 5, "top": 5, "right": 5, "bottom": 5})
            )
            st.altair_chart(covid_chart, width="stretch")
            peak = covid_series.loc[covid_series["age_adjusted_rate"].idxmax()]
            st.caption(
                f"COVID-19's own age-adjusted mortality rate peaked at {peak['age_adjusted_rate']:.1f} per "
                f"100,000 in {int(peak['year'])}, then declined sharply through 2024."
            )

with hypotheses_tab:
    st.subheader("Original pre-registered question")
    st.write(
        "Which causes of death experienced the greatest and most statistically significant "
        "disruption during the COVID-19 pandemic (2020–2024), how persistent were those "
        "disruptions, and how did disruption severity vary across U.S. counties by "
        "socioeconomic status, healthcare access, and rurality?"
    )
    st.write(
        "COVID-19 is treated as a system-wide shock, not the disease under study. The "
        "question is scoped to *what/how much/where*, not *why*, since mortality data alone "
        "cannot separate direct viral effects from deferred care, isolation, or economic stress."
    )

    st.subheader("Pre-registered hypotheses")
    st.write("Stated before any 2020–2024 data was pulled or analyzed:")
    st.markdown(
        "| Cause | ICD-10 | Prior | Confidence |\n"
        "|---|---|---|---|\n"
        "| Drug overdose | X40-X44, X60-X64, X85, Y10-Y14 | Largest disruption; may reverse by 2023–24 | Very high |\n"
        "| Heart disease | I00-I09,I11,I13,I20-I51 | Real acute disruption; persistence uncertain | High |\n"
        "| Diabetes | E10-E14 | Real acute disruption; persistence uncertain | High |\n"
        "| Alzheimer's disease | G30 | Large, isolation-driven | High |\n"
        "| Stroke | I60-I69 | Real but harder to detect (smaller N) | Moderate |\n"
        "| Cancer | C00-C97 | **Expected null** (measurement-lag comparison case) | Low (by design) |\n"
        "| Congenital malformations | Q00-Q99 | **Negative control** (expected null) | Validation case |\n"
        "| COVID-19 | U07.1 | Reference series, not a hypothesis test | N/A |\n"
    )

with data_tab:
    st.write(
        "Baseline: 1999–2019, CDC WONDER \"Underlying Cause of Death, 1999-2020\" (database D76) "
        "for 4 of the 6 test causes. Heart disease and stroke use a shorter, "
        "corrected 2010–2019 baseline, because a check using only pre-2020 data showed the longer straight line no longer fit them (research_protocol.md, 2026-09-01 addendum)."
    )
    st.write("Post-shock: 2020–2024, CDC WONDER \"Underlying Cause of Death, 2018-2024, Single Race\" (database D158).")
    st.write(
        "The two databases use different race categories (bridged vs. single race). The pre-trend is "
        "fit using pre-2020 years only; the entire 2020–2024 comparison uses D158 exclusively (one "
        "consistent vintage). The 2018–2019 overlap years measure the size of the database "
        "jump itself, so it isn't mistaken for a COVID effect."
    )

with stats_tab:
    for title, body in [
        ("Outcome", ("Age-adjusted death rate (2000 U.S. standard population), so an aging population "
         "isn't mistaken for rising risk. County results are the one exception and use crude rates, "
         "because CDC WONDER doesn't offer age adjustment by county for 2018–2024.")),
        ("Excess-mortality test", ("Fit a straight-line trend to the pre-pandemic years (1999–2019, or "
         "2010–2019 for heart disease and stroke), project it forward with a 95% prediction interval, "
         "and flag a year as disrupted when the actual rate falls outside it. The breakpoint is fixed at "
         "2020, not searched for. The primary test averages the 2020 and 2021 gaps and compares that "
         "average against its exact standard error, which counts the trend line's own uncertainty once "
         "(shared by both years) and the year-to-year noise averaged over two years.")),
        ("Persistence", ("For causes disrupted in 2020–21: *Persisted* if any 2022–2024 year is still "
         "significantly off trend in the same direction, *Reversed* if the opposite direction, and "
         "*Resolved* if none are. Persisted doesn't require 2024 itself to be off trend.")),
        ("Multiple testing", ("Benjamini-Hochberg FDR correction across the six causes, and separately "
         "across the five county measures within each cause.")),
        ("Negative control", ("The same pipeline run on congenital malformations, which have no direct "
         "COVID link. It's tested on death counts because its rate is reported to one decimal at about "
         "3 per 100,000, too coarse for a reliable trend fit (see Data quality).")),
        ("Cross-check", ("Three change-point methods (PELT, binary segmentation, segmented regression) "
         "search each series for a break without being told about 2020. At least one finds a break near "
         "2020 for every cause. They search for the best-fitting break anywhere, so disagreement isn't "
         "evidence against the 2020 result.")),
        ("Full-period p-value", ("A secondary test pooling all five post-2020 years. It isn't the "
         "headline result, because averaging can hide a spike that later fades, but it catches delayed "
         "effects such as Alzheimer's later decline.")),
        ("Autocorrelation-robust p-value", ("The main test assumes each pre-pandemic year's gap from "
         "trend is independent. That's false for diabetes, drug overdose, Alzheimer's, and stroke "
         "(autocorrelation 0.50–0.82), so a Newey-West (HAC) version is also reported. It raises "
         "diabetes's p-value about 25 times and drug overdose's about 120 times, and every significant "
         "cause stays significant (research_protocol.md, 2026-09-02 addendum).")),
        ("Sensitivity checks", ("The 2020–21 test is rerun four ways, changing one choice at a time: the "
         "other baseline window, a stricter significance level (α = 0.01), a curved trend, and a trend "
         "that changes by a steady percentage each year (a straight line in log rate). Stroke fails the "
         "stricter level and the curved trend; cancer fails the steady-percentage trend. Everything else "
         "holds (Data quality → Sensitivity).")),
    ]:
        st.markdown(f"**{title}.** {body}")

with counties_tab:
    st.write(
        "For each of the five causes with a significant 2020–21 disruption, each county's change in "
        "death rate is its pooled 2020–2024 crude rate minus its pooled 2015–2019 crude rate (CDC "
        "WONDER grouped by County, so each period is one five-year total). A county is included when "
        "CDC reports a reliable rate in both periods, roughly 20+ deaths over five years. The change "
        "is regressed against five County Health Rankings measures (uninsured rate, smoking, obesity, "
        "income, rurality), with FDR correction within each cause. Associational only; see Language policy."
    )
    st.write(
        "An earlier version required a reliable rate in at least two individual years of each period. "
        "That rule kept only 926 counties for diabetes and 641 for drug overdose, mostly larger and less "
        "rural ones, and its rurality result (smaller disruption in more rural counties) did not hold up "
        "once rural counties were included. Its results are kept for comparison on Geographic patterns. "
        "The switch is logged in research_protocol.md (2026-10-19 addendum)."
    )

with language_tab:
    st.write(
        "No result claims the pandemic \"caused,\" \"led to,\" or \"resulted in\" a change. Approved language: "
        "associated with, temporally aligned with, consistent with, predictive of, correlated with."
    )

with limits_tab:
    st.subheader("Known limitations")
    st.markdown(
        "- **Associations only.** Mortality data can't separate direct viral harm from delayed care, "
        "isolation, or economic stress, and county patterns may not hold for individuals (ecological "
        "fallacy).\n"
        "- **Rural counties are under-represented.** Counties with too few deaths for a reliable rate are "
        "left out, and they're mostly rural (83–94% rural vs. 45–63% for included counties).\n"
        "- **County rates aren't age-adjusted,** so part of a county's change may reflect its population "
        "aging. This matters most for rurality.\n"
        "- **County measures are from 2024,** during the pandemic period rather than before it, and smoking "
        "and obesity are model-based estimates. Counties near each other aren't independent, which isn't "
        "modeled.\n"
        "- **Death-certificate coding** may have shifted in 2020–21, when some deaths could be recorded as "
        "either COVID-19 or another cause.\n"
        "- **Two different CDC databases** are combined: 1999–2019 from one and 2020–2024 from the other. They match exactly in "
        "the overlap years (Data quality → Vintage bridging).\n"
        "- **Stroke and cancer are the least certain results.** Stroke's baseline was corrected to "
        "2010–2019, and its 2020–21 result doesn't survive a curved trend (p = 0.18). Cancer's small "
        "2020–21 gap isn't significant with a steady-percentage trend (p = 0.43).\n"
        "- **Some 2024 results depend on the baseline window** (Findings → Robustness)."
    )

    st.subheader("Ethics and project checks")
    st.write(
        "This project uses publicly available aggregate data and is intended for research and "
        "educational purposes. It does not provide medical advice or individual-level risk predictions."
    )
    # Static, not computed live (running pytest inside the deployed app
    # would be slow and fragile). Update by hand when tests/ changes;
    # verify with `.venv/bin/python -m pytest --collect-only -q | tail -1`.
    st.caption(
        ":green-badge[232 automated tests] :blue-badge[Pre-registered protocol] "
        ":violet-badge[Real CDC WONDER data] :orange-badge[4-axis sensitivity analysis]"
    )

st.caption("Full detail, including every dated change: docs/research_protocol.md.")
