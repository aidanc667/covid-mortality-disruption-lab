import streamlit as st

from app.components.charts import deviation_pct, gap_from_trend_chart
from app.components.data_loading import (
    CAUSE_COLORS,
    HETEROGENEITY_CAUSES,
    TEST_CAUSES,
    data_available,
    display_cause,
    heterogeneity_synthetic_banner,
    load_county_disruption,
    load_disruption_deviations,
    load_national_series,
    load_negative_control,
    synthetic_banner,
)
from app.components.home_metrics import home_scope_metrics
from app.components.ui import (
    cause_chips_html,
    eyebrow_html,
    hero_text_html,
    metric_strip_html,
)

TITLE = "COVID Mortality Disruption Lab"
SUBTITLE = "How the pandemic impacted non-COVID mortality"
QUESTION = (
    "Did COVID-19 disrupt the trend for six other leading causes of death, "
    "has it recovered, and where did it hit hardest?"
)
# The two largest 2020-21 disruptions.
HIGHLIGHT = {"Drug overdose", "Diabetes mellitus"}
# End-of-line labels on chart A; "Alzheimer's" is shortened so it fits at phone width.
CHART_LABELS = {c: display_cause(c) for c in TEST_CAUSES} | {"Alzheimer's disease": "Alzheimer's"}
AGE_ADJUSTED_HELP = (
    "Age-adjusted: each year's rate is reweighted as if the U.S. had the same age mix every "
    "year, so a real change in risk isn't confused with the population getting older. "
    "0% is where the cause's own pre-pandemic trend, projected forward, says it should be. "
    "Disrupted means statistically distinguishable from that cause's normal year-to-year "
    "variation before 2020, not simply far from zero. So a steady cause like cancer can be "
    "significant at +5% while a volatile one like drug overdose isn't at -4%. Within normal "
    "range doesn't mean no effect, only that the gap can't be told apart from ordinary swings."
)

synthetic_banner()
heterogeneity_synthetic_banner()

if not data_available():
    st.title(TITLE)
    st.warning(
        "No precomputed results found yet. Run `python -m scripts.run_covid_disruption_pipeline` "
        "to populate outputs/models/.",
        icon=":material/warning:",
    )
    st.stop()

if not bool(load_negative_control().iloc[0]["passed"]):
    st.error(
        "The negative control did not pass. Per research_protocol.md §7 method 4, this is a hard "
        "gate. Results on the other 6 causes should not be trusted until this is resolved.",
        icon=":material/error:",
    )

scope = home_scope_metrics(load_national_series(), {c: load_county_disruption(c) for c in HETEROGENEITY_CAUSES})
dev = deviation_pct(load_disruption_deviations())

left, right = st.columns([1, 1.05], gap="large", vertical_alignment="center")
with left:
    st.html(eyebrow_html("CDC WONDER", f"Mortality research · {scope.first_year}–{scope.last_year}"))
    st.title(TITLE)
    st.html(hero_text_html(SUBTITLE, QUESTION))
    st.html(cause_chips_html([(display_cause(c), CAUSE_COLORS[c]) for c in TEST_CAUSES]))
with right, st.container(border=True):
    st.markdown("**How far each cause ran from its pre-pandemic trend**", help=AGE_ADJUSTED_HELP)
    last_year = int(dev["year"].max())
    st.caption(
        f"Age-adjusted death rate vs. expected, {int(dev['year'].min())}–{last_year}. "
        f"Solid end dot: still significantly off trend in {last_year}; faded: within normal range."
    )
    st.altair_chart(
        gap_from_trend_chart(dev, CAUSE_COLORS, CHART_LABELS, HIGHLIGHT),
        width="stretch",
    )

# County coverage differs by cause (rarer causes have more counties below
# CDC's reliability threshold), so show the widest and name the narrowest.
counts = scope.county_counts
widest, narrowest = max(counts, key=counts.get), min(counts, key=counts.get)
st.html(metric_strip_html([
    (str(scope.n_years), "years of CDC data", f"{scope.first_year}–{scope.last_year}, CDC WONDER"),
    (str(len(TEST_CAUSES)), "causes tested", "Plus a negative control"),
    (f"{counts[widest]:,}", "counties",
     f"Analyzed across {len(counts)} causes ({counts[narrowest]:,} for {display_cause(narrowest).lower()})"),
    ("Pre-registered", "", "Hypotheses locked before any 2020+ data"),
]))

st.markdown(
    "**Why this matters.** COVID-19 death counts miss part of the pandemic's toll. Delayed care, "
    "interrupted addiction treatment, and isolation can also change how many people die of heart "
    "disease, diabetes, overdose, and other causes, and those deaths never show up as COVID deaths. "
    "Knowing which causes moved, whether they've recovered, and where the changes were largest helps "
    "show where follow-up care and public health attention are most needed."
)

st.divider()
path, cta = st.columns([3, 1], vertical_alignment="center")
with path, st.container(horizontal=True):
    st.page_link("app_pages/findings.py", label="Findings", icon=":material/insights:")
    st.page_link("app_pages/causes.py", label="Causes of death", icon=":material/monitor_heart:")
    st.page_link("app_pages/geographic_heterogeneity.py", label="Geographic patterns", icon=":material/map:")
    st.page_link("app_pages/methods.py", label="Methods", icon=":material/school:")
with cta:
    if st.button("Read the findings", type="primary", icon=":material/arrow_forward:",
                 icon_position="right", width="stretch"):
        st.switch_page("app_pages/findings.py")
