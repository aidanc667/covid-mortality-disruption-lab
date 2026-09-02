import altair as alt
import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_national_series, load_disruption_summary, load_disruption_deviations,
    load_baseline_fitted_trend, load_sensitivity_check, data_available,
    sensitivity_check_available, synthetic_banner, TEST_CAUSES, CAUSE_COLORS, CAUSE_BADGE_STYLE,
)
from app.components.cause_explanations import CAUSE_EXPLANATIONS

st.title("Causes of death")
synthetic_banner()
st.caption(
    "Six major causes of death, tested against their own pre-pandemic trend. For each: what "
    "happened, how confident we are it's real, and what the research literature suggests could "
    "plausibly explain it: background context this project's own mortality data cannot itself prove."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

summary = load_disruption_summary().set_index("cause")
national = load_national_series()
deviations = load_disruption_deviations()
baseline_fitted = load_baseline_fitted_trend()
sens = load_sensitivity_check() if sensitivity_check_available() else None

TREND_SHAPE_CHECK = "baseline_trend_shape (linear vs quadratic)"


def _trend_shape_robust(cause: str) -> bool:
    """False only when this cause's sensitivity check found the result
    flips under a curved baseline instead of the primary straight-line
    fit -- currently heart disease and cerebrovascular disease, whose
    straight-line baseline fit was already diverging from their actual
    1999-2019 trajectory before 2020 (see the trajectory chart's now
    fully-drawn dashed line). Defaults to True (don't flag) when the
    sensitivity check hasn't been run yet."""
    if sens is None:
        return True
    row = sens[(sens["cause"] == cause) & (sens["check"] == TREND_SHAPE_CHECK)]
    return bool(row.iloc[0]["agrees"]) if len(row) else True

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
            if not _trend_shape_robust(cause):
                st.badge("Not robust to trend shape", icon=":material/warning:", color="orange")

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
        st.caption("Result")
        st.badge(r["persistence_class"], icon=CLASS_ICON.get(r["persistence_class"], ":material/help:"), color="gray" if r["persistence_class"] == "No significant disruption" else "red")
        if not _trend_shape_robust(cause):
            st.badge("Not robust to trend shape", icon=":material/warning:", color="orange")
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
fitted = baseline_fitted[baseline_fitted["cause"] == cause].sort_values("year")

observed = series.rename(columns={"age_adjusted_rate": "value"})[["year", "value"]]
band_df = dev[["year", "pi_low", "pi_high"]].copy()
# The dashed trend line is drawn across the full 1999-2024 span, not just
# the 2020-2024 projection: fitted (1999-2019, the model's own fit to the
# years used to build it, no prediction interval since these weren't
# tested) concatenated with expected (2020-2024, the actual projection and
# what compute_deviations tests against). Drawing only the 2020+ segment,
# as this chart used to, hid exactly the evidence a reader would need to
# judge whether the straight-line assumption tracks the real pre-pandemic
# trajectory -- for heart disease and cerebrovascular disease it visibly
# doesn't (see the "Not robust to trend shape" flag above).
expected_full = pd.concat([
    fitted.rename(columns={"fitted": "value"})[["year", "value"]],
    dev[["year", "expected"]].rename(columns={"expected": "value"}),
], ignore_index=True)

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
    alt.Chart(expected_full)
    .mark_line(strokeDash=[5, 4], strokeWidth=1.5, color="#6B7280")
    .encode(x="year:O", y="value:Q", tooltip=["year:O", alt.Tooltip("value:Q", format=".1f", title="Trend fit")])
)
onset_rule = alt.Chart(pd.DataFrame({"year": [2020]})).mark_rule(color="#9CA3AF", strokeDash=[2, 2]).encode(x="year:O")

chart = (band + observed_line + expected_line + onset_rule).properties(height=320)
baseline_start = int(fitted["year"].min()) if len(fitted) else 1999
total_years = 2024 - baseline_start + 1
st.altair_chart(chart, width="stretch")
st.caption(
    f"Solid line: observed. Dashed gray line: the same straight-line trend fit across all "
    f"{total_years} years, both where it was fit ({baseline_start}–2019, so you can judge for "
    f"yourself how well it tracks the real pre-pandemic trajectory) and where it's projected "
    f"forward (2020–2024, shaded band: its 95% prediction interval, the only years actually "
    f"tested). Independent cross-check (PELT, binary segmentation, segmented regression): "
    f"{r['cross_check_methods_agreeing']} of 3 methods confirm a breakpoint near 2020."
)
if not r["cross_check_confirms_2020"]:
    st.caption(
        "This isn't evidence against the result above. The primary method tests this one "
        "pre-registered date specifically, while the cross-check searches the whole series for "
        "whichever single breakpoint fits best, which can legitimately land elsewhere. See Methods."
    )

if not _trend_shape_robust(cause):
    st.warning(
        "**Robustness flag:** this is now this project's single most uncertain \"Persisted\" "
        "result. Its baseline was already corrected once, from the full 1999–2019 range to the "
        "shorter, more recent window shown dashed above, after the original full-range fit was "
        "found to badly misdescribe the real pre-pandemic trend (see research_protocol.md's "
        "2026-09-01 addendum). That correction made the result more defensible, but even the "
        "corrected window's significance still doesn't fully survive an alternate curved-trend "
        "check. See Data Quality for the full sensitivity breakdown.", icon=":material/warning:",
    )

st.subheader("What could explain this?")
st.caption(
    "Background from the published research literature on pandemic-era mortality generally, "
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
    for i, source in enumerate(explanation["sources"], start=1):
        st.markdown(f"{i}. {source['citation']} [↗]({source['url']})")
