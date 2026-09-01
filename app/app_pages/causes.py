import altair as alt
import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_national_series, load_disruption_summary, load_disruption_deviations,
    load_sensitivity_check, data_available, sensitivity_check_available,
    synthetic_banner, TEST_CAUSES, CAUSE_COLORS, CAUSE_BADGE_STYLE,
)
from app.components.cause_explanations import CAUSE_EXPLANATIONS

st.title("Causes of death")
synthetic_banner()
st.caption(
    "Six major causes of death, tested against their own pre-pandemic trend. For each: what "
    "happened, how confident we are it's real, and what the research literature suggests could "
    "plausibly explain it — background context this project's own mortality data cannot itself prove."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

summary = load_disruption_summary().set_index("cause")
national = load_national_series()
deviations = load_disruption_deviations()
sens = load_sensitivity_check() if sensitivity_check_available() else None

CLASS_ICON = {
    "Persisted": ":material/trending_up:",
    "Reversed": ":material/u_turn_right:",
    "Resolved": ":material/check_circle:",
    "No significant disruption": ":material/remove:",
}

st.subheader("At a glance")
cols = st.columns(3)
for i, cause in enumerate(TEST_CAUSES):
    r = summary.loc[cause]
    badge_color, icon = CAUSE_BADGE_STYLE[cause]
    with cols[i % 3]:
        with st.container(border=True):
            st.badge(cause, icon=icon, color=badge_color)
            st.write(f"**{r['persistence_class']}**")
            st.caption(f"{r['acute_pct_deviation']:+.1f}% in 2020–21  •  p = {r['p_value']:.2g}")

st.subheader("Deep dive")
cause = st.segmented_control("Select a cause", options=TEST_CAUSES, default=TEST_CAUSES[0], label_visibility="collapsed")
if cause is None:
    st.stop()

r = summary.loc[cause]
color = CAUSE_COLORS[cause]
badge_color, icon = CAUSE_BADGE_STYLE[cause]
explanation = CAUSE_EXPLANATIONS[cause]

st.badge(cause, icon=icon, color=badge_color)

with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Result", r["persistence_class"])
    with st.container(border=True):
        st.metric("2020–21 deviation", f"{r['acute_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric("2024 deviation", f"{r['latest_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric(
            "p-value", f"{r['p_value']:.2g}",
            delta="FDR-significant" if r["fdr_significant"] else "not FDR-significant", delta_color="off",
        )

# --- Trajectory chart ---
series = national[national["cause"] == cause].sort_values("year")
dev = deviations[deviations["cause"] == cause].sort_values("year")

observed = series.rename(columns={"age_adjusted_rate": "value"})[["year", "value"]]
band_df = dev[["year", "pi_low", "pi_high"]].copy()
expected_df = dev[["year", "expected"]].rename(columns={"expected": "value"})

band = (
    alt.Chart(band_df)
    .mark_area(opacity=0.15, color=color)
    .encode(x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=-45)), y=alt.Y("pi_low:Q", title="Age-adjusted rate (per 100,000)"), y2="pi_high:Q")
)
observed_line = (
    alt.Chart(observed)
    .mark_line(point=alt.OverlayMarkDef(size=40), strokeWidth=2.5, color=color)
    .encode(x="year:O", y="value:Q", tooltip=["year:O", alt.Tooltip("value:Q", format=".1f", title="Observed")])
)
expected_line = (
    alt.Chart(expected_df)
    .mark_line(strokeDash=[5, 4], strokeWidth=1.5, color="#6B7280")
    .encode(x="year:O", y="value:Q", tooltip=["year:O", alt.Tooltip("value:Q", format=".1f", title="Expected")])
)
onset_rule = alt.Chart(pd.DataFrame({"year": [2020]})).mark_rule(color="#9CA3AF", strokeDash=[2, 2]).encode(x="year:O")

chart = (band + observed_line + expected_line + onset_rule).properties(height=320)
st.altair_chart(chart, width="stretch")
st.caption(
    f"Solid line: observed. Dashed gray line + shaded band: expected trend and its 95% prediction "
    f"interval, projected from 1999–2019. Cross-check (PELT/binseg) confirms a breakpoint near "
    f"2020: {'yes' if r['cross_check_confirms_2020'] else 'no — see note below'}."
)
if not r["cross_check_confirms_2020"]:
    st.caption(
        "This isn't evidence against the result above — the primary method tests this one "
        "pre-registered date specifically, while the cross-check searches the whole series for "
        "whichever single breakpoint fits best, which can legitimately land elsewhere. See Methods."
    )

if sens is not None:
    quad_row = sens[(sens["cause"] == cause) & (sens["check"] == "baseline_trend_shape (linear vs quadratic)")]
    if len(quad_row) and not bool(quad_row.iloc[0]["agrees"]):
        st.warning(
            "**Robustness flag:** this result loses significance under a curved (quadratic) "
            "baseline trend instead of the primary straight-line assumption — see Data Quality "
            "for the full sensitivity breakdown.", icon=":material/warning:",
        )

st.subheader("What could explain this?")
st.caption(
    "Background from the published research literature on pandemic-era mortality generally — "
    "not something this project's own mortality data tested directly (research_protocol.md §11)."
)
st.write(explanation["summary"])
for title, desc in explanation["mechanisms"]:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(desc)
if explanation["note"]:
    st.info(explanation["note"], icon=":material/info:")
with st.expander("Sources"):
    for title, url in explanation["sources"]:
        st.markdown(f"- [{title}]({url})")
