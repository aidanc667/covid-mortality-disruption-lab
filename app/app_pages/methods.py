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
        "COVID-19 is treated as a system-wide shock, not the disease under study. The "
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
        "| Malignant neoplasms | C00-C97 | **Expected null** (measurement-lag comparison case) | Low (by design) |\n"
        "| Congenital malformations | Q00-Q99 | **Negative control** (expected null) | Validation case |\n"
        "| COVID-19 | U07.1 | Reference series, not a hypothesis test | N/A |\n"
    )

with st.expander("Data sources and vintage bridging", icon=":material/database:"):
    st.write(
        "Baseline: 1999–2019, CDC WONDER \"Underlying Cause of Death, 1999-2020\" (database D76) "
        "for 4 of the 6 test causes. Diseases of heart and Cerebrovascular disease use a shorter, "
        "corrected 2010–2019 baseline. See Known limitations for why."
    )
    st.write("Post-shock: 2020–2024, CDC WONDER \"Underlying Cause of Death, 2018-2024, Single Race\" (database D158). Confirmed live: no 2025 data exists yet.")
    st.write(
        "The two databases use different population-estimate methodologies. The pre-trend is "
        "fit using 1999–2019 only; the entire 2020–2024 comparison uses D158 exclusively (one "
        "consistent vintage). The 2018–2020 overlap years measure the size of the database "
        "jump itself, so it isn't mistaken for a COVID effect."
    )

with st.expander("Statistical methods", icon=":material/query_stats:"):
    st.write(
        "**Known-date interrupted time series (\"excess mortality\").** Fit an expected trend "
        "on the pre-pandemic baseline (1999–2019 for 4 of the 6 test causes, 2010–2019 for the "
        "2 causes with a corrected window), project it forward with a 95% prediction interval, "
        "and flag a year as significantly disrupted if the observed value falls outside that "
        "interval. The breakpoint (2020) is fixed by the shock's known date, not searched for."
    )
    st.write(
        "**Three-way persistence classification.** For causes with a significant acute-phase "
        "(2020–2021) disruption: *Persisted* (still significant, same direction, through "
        "2024), *Resolved* (shrank back within the prediction interval), or *Reversed* "
        "(flipped sign). A binary scheme would flatten a reversal into a false \"resolved.\""
    )
    st.write(
        "**Independent cross-check.** Three methods (reused unmodified from the project's "
        "diabetes-pilot phase), PELT, binary segmentation, and segmented regression, run on "
        "each bridged series, checking whether they land on a breakpoint near March 2020 "
        "without being told to. Disagreement here is **not** itself evidence against a "
        "significant result. The primary method tests one specific, pre-registered date, "
        "while the cross-check methods search the whole series for whichever single breakpoint "
        "fits best, which can legitimately fall elsewhere without the 2020 date being wrong. "
        "On the real data, all 6 test causes have at least one cross-check method confirm a "
        "breakpoint near 2020. Heart disease and cerebrovascular disease needed a baseline "
        "correction (see Known limitations) before this held; on the original, uncorrected "
        "baseline neither cause's cross-check had confirmed it."
    )
    st.write(
        "**Negative control.** The identical pipeline run on congenital-malformations "
        "mortality, a cause concentrated in infancy with no *direct* COVID mechanism (prenatal/"
        "obstetric care was also disrupted during the pandemic, so \"no plausible mechanism at "
        "all\" would overstate this; it's still far more insulated from adult pandemic-era "
        "behavior than any of the 6 test causes). A significant \"disruption\" there would "
        "indicate the method is detecting an artifact, not a real signal, and is a hard gate on "
        "trusting the other 6 causes. (Its gate decision uses raw death counts rather than "
        "age-adjusted rate: the rate is only reported to 1 decimal by CDC WONDER, which at "
        "this cause's low magnitude made the rate-based test oversensitive to rounding noise; "
        "see the Data Quality page.)"
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
        "**Autocorrelation-robust p-value (Newey-West/HAC).** The primary p-value's prediction-"
        "interval math assumes each baseline year's deviation from the fitted line is independent "
        "noise. Measured lag-1 autocorrelation is 0.50-0.82 for diabetes, drug overdose, Alzheimer's, "
        "and cerebrovascular disease, meaning a rough year really does tend to be followed by another "
        "rough year for these causes, which the classical formula doesn't know and can't account for. "
        "This produces a second p-value for the identical acute (2020-2021) window and identical "
        "trend line, replacing only the uncertainty calculation: a Newey-West sandwich covariance for "
        "the fitted line's own uncertainty, plus the exact variance of a mean of 2 new correlated "
        "observations (derived directly from the baseline's own lag-0 and lag-1 autocovariances, "
        "not assumed independent). On the real data this raises several causes' p-values by 1-2 "
        "orders of magnitude (e.g. drug overdose: 5.98e-8 to 2.5e-5) without changing which causes "
        "clear significance -- all 5 previously significant causes remain significant under this "
        "correction. See research_protocol.md's 2026-09-02 addendum for the full derivation."
    )

with st.expander("County-level heterogeneity", icon=":material/map:"):
    st.write(
        "For causes with a significant disruption, per-county disruption magnitude "
        "(aggregated post-period mean minus pre-period mean) is regressed against real "
        "County Health Rankings context variables (uninsured rate, smoking, obesity, income, "
        "rurality). Associational only; see the causal-language policy below."
    )

with st.expander("Causal language policy", icon=":material/gavel:"):
    st.write(
        "No result uses \"cause,\" \"led to,\" or \"resulted in.\" Approved language: "
        "associated with, temporally aligned with, consistent with, predictive of, correlated with."
    )

with st.expander("Known limitations", icon=":material/warning:"):
    st.write(
        "- Observational, ecological design: no individual-level causal inference. The "
        "county-level heterogeneity stage carries **ecological fallacy** risk by name: a "
        "county-average relationship doesn't necessarily hold at the individual level\n"
        "- **Selection bias in the county-level heterogeneity sample**: counties excluded by the "
        "suppression filter are disproportionately rural (77.7% rural excluded vs. 31.5% "
        "included for diabetes; 74.4% vs. 23.8% for overdose). The rurality finding is more "
        "trustworthy for diabetes (holds up among more-rural included counties) than for drug "
        "overdose (driven by less-rural counties, not significant among more-rural ones). See "
        "Geographic Heterogeneity for the full check\n"
        "- Mortality-vintage discontinuity between the two CDC WONDER databases\n"
        "- ICD-10 coding practices may have shifted during 2020–2021 due to strain on death-certification systems\n"
        "- Cancer's pre-registered prior was an expected null result (measurement-lag reasoning); the real result contradicts that. Cancer shows a significant, still-persisting disruption, not the null originally expected\n"
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
        "diabetes, overdose, and Alzheimer's; 0.50 for cerebrovascular disease; 0.12–0.19 for heart "
        "disease and cancer, where the assumption roughly holds). This was a disclosed-but-unmodeled "
        "gap; a Newey-West (HAC) autocorrelation-robust version of the test is now also reported "
        "(see Statistical methods above and Causes of death). It raises the classical p-value for "
        "the high-autocorrelation causes by roughly 1-2 orders of magnitude, but all 5 causes "
        "previously found significant remain significant under it\n"
        "- **Diseases of heart and Cerebrovascular disease use a corrected 2010–2019 baseline, not "
        "1999–2019 like the other four test causes**, after finding the longer window was already "
        "diverging from their real trajectory before 2020. See research_protocol.md's 2026-09-01 "
        "addendum. Heart disease is now fully robust across every check; cerebrovascular disease is "
        "substantially improved but remains this project's single most uncertain \"Persisted\" "
        "result (its significance doesn't fully survive an alternate curved-trend check, p=0.096)\n"
        "- \"Significant\" and \"large\" are different claims: diabetes (+26.9%) and drug overdose "
        "(+40.9%) show the largest 2020-21 deviations; cancer (+1.7%), heart disease (+7.8%), and "
        "cerebrovascular disease (+8.8%) are all real and FDR-significant but modest by comparison. "
        "See the Findings page for effect sizes\n"
        "- All findings remain associational. The mechanism behind any confirmed disruption "
        "(direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be "
        "separated by mortality data alone"
    )

st.caption("See docs/research_protocol.md and docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md for full detail.")
