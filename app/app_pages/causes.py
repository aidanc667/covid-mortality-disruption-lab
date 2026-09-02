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
            st.badge(cause, icon=icon, color=badge_color)
            st.write(f"**{r['persistence_class']}**")
            st.caption(f"{r['acute_pct_deviation']:+.1f}% in 2020–21  •  p = {r['p_value']:.2g}")
            if not _trend_shape_robust(cause):
                st.badge("Not robust to trend shape", icon=":material/warning:", color="orange")
            if _delayed_disruption(r):
                st.badge("Delayed disruption (see 2020–24 p-value)", icon=":material/schedule:", color="blue")

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
        if _delayed_disruption(r):
            st.badge("Delayed disruption (see below)", icon=":material/schedule:", color="blue")
    with st.container(border=True):
        st.metric("2020–21 deviation", f"{r['acute_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric("2024 deviation", f"{r['latest_pct_deviation']:+.1f}%")
    with st.container(border=True):
        st.metric(
            "Primary p-value (2020–21)", f"{r['p_value']:.2g}",
            delta="FDR-significant" if r["fdr_significant"] else "not FDR-significant", delta_color="off",
            help="The pre-registered primary test: are 2020 and 2021 combined significantly off trend?",
        )

# Full-period p-value is deliberately its own separate, labeled row rather
# than a 5th card squeezed into the row above: at normal window widths
# Streamlit truncates both metric labels to "p-value (2020..." and they
# become visually indistinguishable, which is exactly how a reader can miss
# that this second number exists at all.
st.caption(
    "Secondary check, not the primary test: does the disruption still show up if all five "
    "post-2020 years are pooled instead of just the acute 2020–21 window?"
)
with st.container(border=True):
    st.metric(
        "Full-period p-value (2020–2024)", f"{r['full_period_p_value']:.2g}",
        delta=f"{r['full_period_pct_deviation']:+.1f}% average deviation", delta_color="off",
        help="Pools all five post-2020 years instead of just the acute 2020–21 window, since a "
             "disruption can keep evolving well past the acute phase. Can disagree with the primary "
             "test, most notably for Alzheimer's disease, where a real decline that only became "
             "individually significant in 2023–2024 is invisible to the acute-only test but shows "
             "up clearly here. Not used to replace the primary test or the headline result above: "
             "see the Methods page for why.",
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
    .encode(x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=-45)), y=alt.Y("pi_low:Q", title="Age-adjusted rate (per 100,000)"), y2="pi_high:Q")
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
onset_rule = alt.Chart(pd.DataFrame({"year": [2020]})).mark_rule(color="#9CA3AF", strokeDash=[2, 2]).encode(x="year:O")

chart = (band + gap_ribbon + observed_line + expected_line + onset_rule).properties(height=320)
baseline_start = int(fitted["year"].min()) if len(fitted) else 1999
total_years = 2024 - baseline_start + 1
st.altair_chart(chart, width="stretch")
st.caption(
    f"Solid line: observed. Dashed gray line: the same straight-line trend fit across all "
    f"{total_years} years, both where it was fit ({baseline_start}–2019, so you can judge for "
    f"yourself how well it tracks the real pre-pandemic trajectory) and where it's projected "
    f"forward (2020–2024, shaded band: its 95% prediction interval, the only years actually "
    f"tested). The filled gap between the two lines is colored red where observed ran above "
    f"trend and blue where it ran below, so the size of the deviation doesn't depend on "
    f"eyeballing two overlapping lines: a thin band can still be significant if this cause's "
    f"own pre-pandemic noise was small, and a thick band can still be non-significant if it "
    f"wasn't. Hover a point on the solid line to see whether that specific year fell inside or "
    f"outside the interval; the primary p-value (2020–21) pools those two years together, so a "
    f"single year can look unremarkable on its own while the combined result is still "
    f"significant. The 2020–24 p-value above pools all five years instead, as a secondary check "
    f"for disruption that shows up only later. "
    f"Independent cross-check (PELT, binary segmentation, segmented regression): "
    f"{r['cross_check_methods_agreeing']} of 3 methods confirm a breakpoint near 2020."
)
if _delayed_disruption(r):
    st.info(
        f"**{cause} looks unremarkable in 2020–21** (p = {r['p_value']:.2g}), which is why its "
        f"headline result above is \"No significant disruption.\" But pooled across all of "
        f"2020–2024, the same test finds a real, later decline (p = {r['full_period_p_value']:.2g}, "
        f"averaging {r['full_period_pct_deviation']:+.1f}% vs. trend): notice in the chart how the "
        f"gap widens and turns blue in the most recent years. This project's primary classification "
        f"stays scoped to the pre-registered acute window rather than switching after the fact to "
        f"whichever window makes a cause look significant, so the headline result above is correct "
        f"as reported. This is a real, additional finding the acute-only test just isn't built to "
        f"catch: a disruption that arrived late rather than at onset.",
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
