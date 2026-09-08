import altair as alt
import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_national_series, load_disruption_summary, load_disruption_deviations,
    load_baseline_fitted_trend, load_sensitivity_check, data_available,
    sensitivity_check_available, synthetic_banner, TEST_CAUSES, CAUSE_COLORS, CAUSE_BADGE_STYLE,
    display_cause,
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


def _delayed_disruption(r: pd.Series) -> bool:
    """True when the acute-only (2020-2021) test misses a disruption that
    the full-period (2020-2024) test catches -- currently only Alzheimer's
    disease, whose decline only became individually significant in
    2023-2024, well after the acute window this project's primary test is
    scoped to."""
    return bool(r["p_value"] >= 0.05 and r["full_period_p_value"] < 0.05)


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
            st.badge(display_cause(cause), icon=icon, color=badge_color)
            st.write(f"**{r['persistence_class']}**")
            st.caption(f"{r['acute_pct_deviation']:+.1f}% in 2020–21  •  p = {r['p_value']:.2g}")
            if not _trend_shape_robust(cause):
                st.badge("Not robust to trend shape", icon=":material/warning:", color="orange")
            if _delayed_disruption(r):
                st.badge("Delayed disruption (see 2020–24 p-value)", icon=":material/schedule:", color="blue")

st.subheader("Deep dive")
cause = st.segmented_control(
    "Select a cause", options=TEST_CAUSES, default=TEST_CAUSES[0], label_visibility="collapsed",
    format_func=display_cause,
)
if cause is None:
    st.stop()

r = summary.loc[cause]
color = CAUSE_COLORS[cause]
badge_color, icon = CAUSE_BADGE_STYLE[cause]
explanation = CAUSE_EXPLANATIONS[cause]

st.badge(display_cause(cause), icon=icon, color=badge_color)

with st.container(horizontal=True):
    with st.container(border=True):
        st.caption("Result")
        st.badge(r["persistence_class"], icon=CLASS_ICON.get(r["persistence_class"], ":material/help:"), color="gray" if r["persistence_class"] == "No significant disruption" else "red")
        if not _trend_shape_robust(cause):
            st.badge("Not robust to trend shape", icon=":material/warning:", color="orange")
        if _delayed_disruption(r):
            st.badge("Delayed disruption (see below)", icon=":material/schedule:", color="blue")
    with st.container(border=True):
        st.metric("2020–21 deviation", f"{r['acute_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric("2024 deviation", f"{r['latest_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric(
            "Primary p-value", f"{r['p_value']:.2g}",
            delta="FDR-significant" if r["fdr_significant"] else "not FDR-significant", delta_color="off",
            help="The pre-registered primary test (2020–21 combined): is it significantly off trend?",
        )

# Both secondary checks live inside one collapsed-by-default expander
# rather than as always-visible full-width blocks: for most causes they
# confirm the primary result without adding new information, so showing
# them at full size on every visit was pure clutter. Auto-expanded only
# when there's something genuinely worth seeing without an extra click
# (Alzheimer's delayed-disruption case).
with st.expander("Robustness checks: does the result hold up under alternate assumptions?", expanded=_delayed_disruption(r)):
    st.caption(
        "Same acute 2020–21 test, corrected for a real limitation: the primary p-value above assumes "
        "each baseline year is independent noise, which measured autocorrelation shows isn't true for "
        "this cause. Does the result survive an autocorrelation-robust standard error instead?"
    )
    st.metric(
        "HAC p-value", f"{r['hac_p_value']:.2g}",
        help="Newey-West (HAC) standard errors instead of the classical formula, which assumes "
             "independent year-to-year residuals -- measured autocorrelation is 0.50-0.82 for half "
             "the test causes, so that assumption is often false here. Keeps the same trend line and "
             "acute 2020–21 window; only the uncertainty calculation changes. See Methods for why "
             "this matters and how it's computed.",
    )
    st.caption(
        "Secondary check: does the disruption still show up if all five "
        "post-2020 years are pooled instead of just the acute 2020–21 window?"
    )
    st.metric(
        "Full-period p-value", f"{r['full_period_p_value']:.2g}",
        delta=f"{r['full_period_pct_deviation']:+.1f}% average deviation", delta_color="off",
        help="Pools all five post-2020 years instead of just the acute 2020–21 window. Not used to "
             "replace the primary test or the headline result above; see Methods for why.",
    )

# --- Trajectory chart ---
series = national[national["cause"] == cause].sort_values("year")
dev = deviations[deviations["cause"] == cause].sort_values("year")
fitted = baseline_fitted[baseline_fitted["cause"] == cause].sort_values("year")

observed = series.rename(columns={"age_adjusted_rate": "value"})[["year", "value"]]
band_df = dev[["year", "pi_low", "pi_high"]].copy()
# Per-year significance for the tooltip: only 2020-2024 are actually
# tested against the prediction interval (compute_deviations); baseline
# years were used to fit the model, not tested. Added after a reader
# question showed that eyeballing a single year's gap on the chart can
# be misleading -- the reported p-value pools 2020 and 2021 together, so
# a year that looks "inside" here (e.g. cancer's flat 2020) can still
# belong to a cause with a significant combined result once 2021, which
# was outside, is counted too.
sig_status = dict(zip(dev["year"], dev["significant"].map({True: "Outside prediction interval", False: "Within prediction interval"})))
observed["status"] = observed["year"].map(sig_status).fillna("Baseline year (not tested)")
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
    .encode(
        x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=-45)),
        # zero=False: a mortality rate never approaches 0, so 0 isn't a
        # meaningful reference point on this axis the way it would be for,
        # say, a count that could plausibly hit zero. Forcing the scale to
        # include it (Vega-Lite's default) shrinks every cause's real
        # observed-vs-expected gap down to a few pixels regardless of how
        # significant it is, which is exactly backwards: the meaningful
        # reference here is the shaded prediction interval, not zero, and
        # that's what should get the visual room. This does NOT cherry-pick
        # a domain to exaggerate any one cause -- it's the same rule
        # (auto-fit to the actual data range) applied identically to all 6.
        y=alt.Y("pi_low:Q", title="Age-adjusted rate (per 100,000)", scale=alt.Scale(zero=False)),
        y2="pi_high:Q",
    )
)
# Gap ribbon, added after a reader couldn't tell at a glance how big the
# observed-vs-expected gap actually was for causes where the two lines run
# close together (diseases of the heart, cerebrovascular disease, cancer)
# despite a significant result -- exactly the "the lines look close, so how
# can this be significant" confusion the p-value/prediction-interval
# explanation above addresses in words. Filling the gap itself, colored by
# direction, makes the deviation visible without requiring the reader to
# eyeball the space between two overlapping lines.
gap_df = dev[["year", "observed", "expected", "deviation"]].copy()
gap_df["gap_low"] = gap_df[["observed", "expected"]].min(axis=1)
gap_df["gap_high"] = gap_df[["observed", "expected"]].max(axis=1)
gap_df["direction"] = gap_df["deviation"].apply(
    lambda d: "Above expected" if d > 0 else ("Below expected" if d < 0 else "At expected")
)
gap_ribbon = (
    alt.Chart(gap_df)
    .mark_area(opacity=0.4)
    .encode(
        x="year:O", y="gap_low:Q", y2="gap_high:Q",
        color=alt.Color(
            "direction:N",
            scale=alt.Scale(
                domain=["Above expected", "Below expected", "At expected"],
                range=["#DC2626", "#2563EB", "#9CA3AF"],
            ),
            legend=alt.Legend(title="Gap vs. trend"),
        ),
        tooltip=[
            "year:O", alt.Tooltip("deviation:Q", format="+.1f", title="Gap (observed − expected)"),
        ],
    )
)
observed_line = (
    alt.Chart(observed)
    .mark_line(point=alt.OverlayMarkDef(size=40), strokeWidth=2.5, color=color)
    .encode(
        x="year:O", y="value:Q",
        tooltip=[
            "year:O", alt.Tooltip("value:Q", format=".1f", title="Observed"),
            alt.Tooltip("status:N", title="vs. prediction interval"),
        ],
    )
)
expected_line = (
    alt.Chart(expected_full)
    .mark_line(strokeDash=[5, 4], strokeWidth=1.5, color="#6B7280")
    .encode(x="year:O", y="value:Q", tooltip=["year:O", alt.Tooltip("value:Q", format=".1f", title="Trend fit")])
)
# Marks the years that actually drive significance -- points where the
# observed rate fell outside the 95% prediction interval -- so "is this
# significant" reads directly off the chart instead of requiring the
# reader to judge how far apart two lines look. Two layers, not one: a
# soft, larger halo behind a solid marker in front, the static-chart
# equivalent of a highlight/glow, since Vega-Lite in a Streamlit-rendered
# chart doesn't support a real pulsing animation. Matters most for a
# cause like cancer, where the real effect is genuinely small -- the
# marker needs to carry the "this is the significant part" signal on its
# own, since the gap itself is honestly too small to make that point by
# size alone (and shouldn't be stretched to fake it).
sig_years = observed[observed["status"] == "Outside prediction interval"]
sig_halo = (
    alt.Chart(sig_years)
    .mark_point(filled=True, size=500, color=color, opacity=0.25)
    .encode(x="year:O", y="value:Q")
)
sig_points = (
    alt.Chart(sig_years)
    .mark_point(filled=True, size=160, color=color, stroke="white", strokeWidth=2.2)
    .encode(
        x="year:O", y="value:Q",
        tooltip=["year:O", alt.Tooltip("value:Q", format=".1f", title="Observed (outside prediction interval)")],
    )
)
onset_rule = alt.Chart(pd.DataFrame({"year": [2020]})).mark_rule(color="#9CA3AF", strokeDash=[2, 2]).encode(x="year:O")

chart = (band + gap_ribbon + observed_line + expected_line + sig_halo + sig_points + onset_rule).properties(height=320)
baseline_start = int(fitted["year"].min()) if len(fitted) else 1999
total_years = 2024 - baseline_start + 1
st.altair_chart(chart, width="stretch")
st.caption(
    f"Solid line: observed. Dashed gray line: the same trend fit across all {total_years} years, "
    f"projected forward from {baseline_start}–2019 with a 95% prediction interval (shaded band, "
    f"the only years actually tested). Outlined circles mark years that landed outside that "
    f"interval; those circles, not the raw size of the gap, are the actual test. Independent "
    f"cross-check (PELT, binary segmentation, segmented regression): "
    f"{r['cross_check_methods_agreeing']} of 3 methods confirm a breakpoint near 2020."
)
with st.expander("How to read this chart"):
    st.caption(
        "The y-axis does not start at zero: a mortality rate never gets close to it, so zero "
        "isn't a meaningful reference point here (the meaningful reference is the shaded band). "
        "The filled gap is colored red where observed ran above trend and blue where it ran "
        "below. A thin band can still be significant if this cause's own pre-pandemic noise was "
        "small, and a thick band can still be non-significant if it wasn't, which is why the "
        "circles matter more than the gap's raw size. Hover a point on the solid line for that "
        "year's status; the primary p-value pools 2020 and 2021 together, so a single "
        "unremarkable-looking year can still belong to a significant combined result."
    )
if _delayed_disruption(r):
    st.info(
        f"**{display_cause(cause)}** shows no significant disruption in the pre-registered 2020–21 window "
        f"(p = {r['p_value']:.2g}), but pooling all five post-2020 years finds a real, later "
        f"decline (p = {r['full_period_p_value']:.2g}, averaging "
        f"{r['full_period_pct_deviation']:+.1f}% vs. trend); watch the gap widen and turn blue "
        f"after 2021. The headline result above still stands: this project doesn't switch its "
        f"primary test window after seeing what's significant. This is an additional finding, not "
        f"a contradiction.",
        icon=":material/schedule:",
    )
if not r["cross_check_confirms_2020"]:
    st.caption(
        "This isn't evidence against the result above. The primary method tests this one "
        "pre-registered date specifically, while the cross-check searches the whole series for "
        "whichever single breakpoint fits best, which can legitimately land elsewhere. See Methods."
    )

if not _trend_shape_robust(cause):
    st.warning(
        "**Robustness flag:** this is this project's single most uncertain \"Persisted\" result. "
        "Its baseline was already corrected once, from the full 1999–2019 range to the shorter "
        "window shown dashed above, after the original fit was found to badly misdescribe the "
        "real pre-pandemic trend (research_protocol.md's 2026-09-01 addendum). That correction "
        "made the result more defensible, but its significance still doesn't fully survive an "
        "alternate curved-trend check. See Data Quality for the full breakdown.", icon=":material/warning:",
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
