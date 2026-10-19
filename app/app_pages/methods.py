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
st.caption("Every statistical choice below is fixed in docs/research_protocol.md before results are inspected.")

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
        f"Using {span} CDC mortality data, we establish each cause's pre-pandemic trajectory, "
        "estimate what 2020–2024 mortality would have looked like without a pandemic, and test whether "
        "observed mortality significantly departed from that baseline, then whether any disruption was "
        "temporary or persisted through 2024, both nationally and, for the five disrupted causes, across U.S. counties "
        "by socioeconomic status, healthcare access, and rurality."
    )

    st.subheader("What we did")
    with st.container(horizontal=True):
        for icon, title, body in [
            (":material/database:", "Real data",
             "33 CDC WONDER mortality exports (15 national, 18 county), plus real County Health Rankings socioeconomic data."),
            (":material/edit_note:", "Locked before looking",
             "Hypotheses and confidence levels for each cause were written down before any 2020–2024 data was analyzed."),
            (":material/verified:", "Tested, not assumed",
             "A negative control, 3 independent sensitivity checks, and FDR correction: a passing grade wasn't assumed."),
            (":material/travel_explore:", "Mapped and explained",
             "Results broken down by cause and by county, with research-grounded reasoning for what could explain each one."),
        ]:
            with st.container(border=True, width="stretch"):
                st.markdown(f"{icon} **{title}**")
                st.caption(body)

    st.subheader("The breaking point")
    st.caption(
        "COVID-19 itself is not one of the causes tested. It's the fixed, known-date shock the whole "
        "analysis is built around. Every cause is compared against the trend it was already on before "
        "this date, not searched for after the fact."
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
                f"100,000 in {int(peak['year'])}, then declined sharply through 2024. It has no "
                "pre-pandemic baseline to test against (the cause didn't exist before 2020), so it's shown "
                "only as the event this analysis is built around, not one of the 6 causes tested."
            )

with hypotheses_tab:
    st.subheader("Research question")
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
        "corrected 2010–2019 baseline. See Known limitations for why."
    )
    st.write("Post-shock: 2020–2024, CDC WONDER \"Underlying Cause of Death, 2018-2024, Single Race\" (database D158). Confirmed live: no 2025 data exists yet.")
    st.write(
        "The two databases use different population-estimate methodologies. The pre-trend is "
        "fit using 1999–2019 only; the entire 2020–2024 comparison uses D158 exclusively (one "
        "consistent vintage). The 2018–2020 overlap years measure the size of the database "
        "jump itself, so it isn't mistaken for a COVID effect."
    )

with stats_tab:
    st.write(
        "**Outcome: age-adjusted mortality rate.** Every national-level test below uses this, "
        "not the raw \"crude\" rate. Age-adjustment reweights each year's real, observed "
        "age-specific death rates onto a fixed reference population's age distribution (the 2000 "
        "U.S. standard population), so a change in the rate over time reflects a real change in "
        "risk, not just the U.S. population aging in the background. County-level heterogeneity "
        "is the one exception: it uses crude rate, since CDC WONDER doesn't offer age-adjustment "
        "at county granularity (see Known limitations)."
    )
    st.write(
        "**Known-date interrupted time series (\"excess mortality\").** Fit an expected trend "
        "on the pre-pandemic baseline (1999–2019 for 4 of the 6 test causes, 2010–2019 for the "
        "2 causes with a corrected window), project it forward with a 95% prediction interval, "
        "and flag a year as significantly disrupted if the observed value falls outside that "
        "interval. The breakpoint (2020) is fixed by the shock's known date, not searched for."
    )
    st.write(
        "**Three-way persistence classification.** For causes with a significant acute-phase "
        "(2020–2021) disruption: *Persisted* (the 2022–2024 years that are still significantly "
        "off trend lean the same direction as 2020–21; it does not require 2024 itself to be "
        "significant), *Resolved* (no 2022–2024 year significantly off trend), or *Reversed* "
        "(those significant later years lean the opposite way). A binary scheme would flatten a "
        "reversal into a false \"resolved.\""
    )
    st.write(
        "**Independent cross-check.** Three methods (PELT, binary segmentation, segmented "
        "regression) run on each bridged series, checking whether they land on a breakpoint "
        "near March 2020 without being told to. Disagreement here is **not** itself evidence "
        "against a significant result: the primary method tests one specific, pre-registered "
        "date, while the cross-check methods search the whole series for whichever breakpoint "
        "fits best, which can legitimately land elsewhere without the 2020 date being wrong. On "
        "the real data, all 6 test causes have at least one cross-check method confirm a "
        "breakpoint near 2020, though heart disease and stroke only after their baseline "
        "correction (see Known limitations)."
    )
    st.write(
        "**Negative control.** The identical pipeline run on congenital-malformations "
        "mortality, concentrated in infancy with no *direct* COVID mechanism (prenatal/"
        "obstetric care was also disrupted, so \"no plausible mechanism at all\" would overstate "
        "this, but it's still far more insulated from adult pandemic-era behavior than any of "
        "the 6 test causes). A significant \"disruption\" there would mean the method is "
        "detecting an artifact, not a real signal, and is a hard gate on trusting the other 6. "
        "Its gate decision uses raw death counts, not age-adjusted rate: CDC WONDER reports the "
        "rate to only 1 decimal, which at this cause's low magnitude made the rate-based test "
        "oversensitive to rounding noise (see Data Quality)."
    )
    st.write(
        "**Multiple-testing correction.** Benjamini-Hochberg FDR correction applied across "
        "the 6 substantive test causes as one family, separately from the heterogeneity-stage "
        "correction applied per cause across its context variables."
    )
    st.write(
        "**Full-period p-value (secondary, not primary).** Alongside the pre-registered acute "
        "(2020-2021) test, each cause also gets a p-value pooling all five post-2020 years, using "
        "the identical t-test just over a wider window. This isn't used to replace the acute test or "
        "gate classification: averaging more years can hide a real reversal (drug overdose spikes, "
        "then declines below trend by 2024) as easily as it can reveal a delayed effect. It exists "
        "to catch disruptions the acute window is too narrow to see, which is exactly what it finds "
        "for Alzheimer's disease (not significant at 2020-2021, but significant once 2022-2024 are "
        "included, see Causes of death)."
    )
    st.write(
        "**Autocorrelation-robust p-value (Newey-West/HAC).** The primary p-value assumes each "
        "baseline year's deviation from trend is independent noise. Measured lag-1 autocorrelation "
        "is 0.50-0.82 for diabetes, drug overdose, Alzheimer's, and stroke, meaning a rough year "
        "really does tend to follow another rough year for these causes, which the classical "
        "formula can't account for. This produces a second p-value for the identical window and "
        "trend line, replacing only the uncertainty calculation (a Newey-West sandwich covariance, "
        "derived from the baseline's own lag-0 and lag-1 autocovariances, not assumed independent). "
        "On the real data this raises several causes' p-values by 1-2 orders of magnitude (e.g. "
        "drug overdose: 5.98e-8 to 2.5e-5) without changing which causes clear significance; all 5 "
        "remain significant. See research_protocol.md's 2026-09-02 addendum for the full derivation."
    )

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
        "No result uses \"cause,\" \"led to,\" or \"resulted in.\" Approved language: "
        "associated with, temporally aligned with, consistent with, predictive of, correlated with."
    )

with limits_tab:
    st.subheader("Known limitations")
    st.write(
        "- Observational, ecological design: no individual-level causal inference. The "
        "county-level heterogeneity stage carries **ecological fallacy** risk by name: a "
        "county-average relationship doesn't necessarily hold at the individual level\n"
        "- **Selection bias in the county sample**: counties with too few deaths for a reliable rate "
        "are left out, and they're mostly rural (83-94% rural excluded vs. 45-63% included, depending "
        "on the cause). The pooled five-year rates cut this bias sharply, but the most rural places are "
        "still under-represented, and the rurality result varies by cause. See Geographic patterns for "
        "each cause's check\n"
        "- Mortality-vintage discontinuity between the two CDC WONDER databases\n"
        "- ICD-10 coding practices may have shifted during 2020–2021 due to strain on death-certification systems\n"
        "- Cancer's pre-registered prior was an expected null result (measurement-lag reasoning); the real result contradicts that. Cancer shows a significant disruption that was still above trend in 2024, not the null originally expected\n"
        "- Small-county suppression at the county-level heterogeneity stage\n"
        "- CHR&R behavioral measures (smoking, obesity) are PLACES model-based small-area estimates, not raw counts\n"
        "- **Context-variable vintage is post-period, not pre-period**: all five heterogeneity-stage "
        "context variables come from CHR&R's 2024 release, measured during or after the 2020–2024 "
        "disruption window they're being regressed against, not a pre-pandemic baseline. Rurality is "
        "effectively static, but income and the uninsured rate plausibly moved during the pandemic "
        "itself, so this stage can't rule out some feedback from the disruption's own economic "
        "aftermath into the context variable\n"
        "- Multiple testing across both the 6-cause family and the per-cause context-variable family\n"
        "- Counties are not geographically independent (spatial autocorrelation not yet modeled)\n"
        "- The primary p-value's prediction-interval math assumes independent baseline residuals, "
        "which is measurably false for half the test causes (lag-1 autocorrelation 0.65–0.82 for "
        "diabetes, overdose, and Alzheimer's; 0.50 for stroke; 0.12–0.19 for heart "
        "disease and cancer, where the assumption roughly holds). This was a disclosed-but-unmodeled "
        "gap; a Newey-West (HAC) autocorrelation-robust version of the test is now also reported "
        "(see the Statistics tab and Causes of death). It raises the classical p-value for "
        "the high-autocorrelation causes by roughly 1-2 orders of magnitude, but all 5 causes "
        "previously found significant remain significant under it\n"
        "- **Heart disease and stroke use a corrected 2010–2019 baseline, not "
        "1999–2019 like the other four test causes**, after finding the longer window was already "
        "diverging from their real trajectory before 2020. See research_protocol.md's 2026-09-01 "
        "addendum. Heart disease is now fully robust across every check; stroke is "
        "substantially improved but remains this project's single most uncertain \"Persisted\" "
        "result (its significance doesn't fully survive an alternate curved-trend check, p=0.096)\n"
        "- \"Significant\" and \"large\" are different claims: diabetes (+26.9%) and drug overdose "
        "(+40.9%) show the largest 2020-21 deviations; cancer (+1.7%), heart disease (+7.8%), and "
        "stroke (+8.8%) are all real and FDR-significant but modest by comparison. "
        "See the Findings page for effect sizes\n"
        "- All findings remain associational. The mechanism behind any confirmed disruption "
        "(direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be "
        "separated by mortality data alone"
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
        ":green-badge[193 automated tests] :blue-badge[Pre-registered protocol] "
        ":violet-badge[Real CDC WONDER data] :orange-badge[3-axis sensitivity analysis]"
    )

st.caption("See docs/research_protocol.md and docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md for full detail.")
