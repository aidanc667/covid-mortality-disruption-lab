import altair as alt
import pandas as pd
import streamlit as st

from app.components.county_map import render_county_choropleth
from app.components.county_text import rurality_split_reading
from app.components.data_loading import (
    CONTEXT_VAR_LABELS,
    COUNTY_PAGE_CAUSES,
    EXPLORATORY_COUNTY_CAUSES,
    YEARLY_COMPARISON_CAUSES,
    county_cause_label,
    data_available,
    display_cause,
    heterogeneity_synthetic_banner,
    load_county_disruption,
    load_county_disruption_yearly,
    load_heterogeneity_rurality_robustness,
    load_heterogeneity_selection_bias,
    load_heterogeneity_summary,
    load_heterogeneity_summary_yearly,
    scale_context_slope_for_display,
)
from app.components.ui import takeaway_html
from src.ingestion.county_health_rankings import load_year as load_chr_year

st.title("Geographic patterns")
heterogeneity_synthetic_banner()

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

het = load_heterogeneity_summary()

cause = st.segmented_control(
    "Cause", options=COUNTY_PAGE_CAUSES, default=COUNTY_PAGE_CAUSES[0], format_func=county_cause_label,
)
if cause is None:
    st.stop()
cause_het = het[het["cause"] == cause].sort_values("p_value")
county_disruption = load_county_disruption(cause)

n_counties = len(county_disruption)
total_us_counties = load_chr_year(2024)["county_fips"].nunique()
excluded_pct = 1 - n_counties / total_us_counties


# Plain-language names for the takeaway sentence (CONTEXT_VAR_LABELS are
# column-header style: "% adult smokers", "Median household income (per $10k)").
PLAIN_VAR = {
    "pct_uninsured_chr": "the uninsured rate",
    "pct_smokers": "smoking",
    "pct_obese": "obesity",
    "median_income_chr": "household income",
    "pct_rural": "rurality",
}


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


sig = cause_het[cause_het["fdr_significant"]]
larger = [PLAIN_VAR.get(v, v) for v in sig.loc[sig["slope"] > 0, "variable"]]
smaller = [PLAIN_VAR.get(v, v) for v in sig.loc[sig["slope"] < 0, "variable"]]
clauses = []
if larger:
    clauses.append(f"larger where {_join(larger)} {'was' if len(larger) == 1 else 'were'} higher")
if smaller:
    clauses.append(f"smaller where {_join(smaller)} {'was' if len(smaller) == 1 else 'were'} higher")
# The rurality result carries a real selection-bias caveat (excluded counties
# are far more rural); flag it here rather than only inside a tab.
rurality_note = " The rurality result has caveats (see What predicts it)." if "rurality" in smaller + larger else ""
st.html(takeaway_html(
    (f"{display_cause(cause)} disruption was " + ", and ".join(clauses) + ". " if clauses
     else f"No context variable survives FDR correction for {display_cause(cause)}. ")
    + "These are county-level associations, not causes."
    + rurality_note
))

if cause in EXPLORATORY_COUNTY_CAUSES:
    st.info(
        f"**Exploratory.** {display_cause(cause)} had no significant 2020–21 disruption nationally, so it isn't "
        "part of the main county analysis. It's shown with the same method for comparison. Its national "
        "decline came in 2023–24, and averaging all of 2020–24 mixes that with the earlier years, so this "
        "is a blunt measure of it (research_protocol.md, 2026-10-19 exploratory addendum).",
        icon=":material/science:",
    )

map_tab, predicts_tab, all_tab = st.tabs(["Map", "What predicts it", "All counties"])

with map_tab:
    st.caption(
        f"{n_counties:,} of {total_us_counties:,} U.S. counties ({1 - excluded_pct:.0%}) had enough deaths "
        f"over 2015–19 and 2020–24 for CDC to report a reliable rate in both periods; the other "
        f"{excluded_pct:.0%}, shown in gray, are excluded, not zero. Blue = rate fell from 2015–19 to 2020–24; orange = rate rose "
        "(a colorblind-safe scale, since red/green or red/blue are hard to distinguish for the ~8% of "
        "men with red-green color vision deficiency). Hover a county for exact pre/post rates. Rates "
        "are **crude**, not age-adjusted: CDC WONDER doesn't offer age-adjustment at county "
        "granularity (research_protocol.md's 2026-09-01 addendum)."
    )
    st.altair_chart(render_county_choropleth(county_disruption, display_cause(cause)), width="stretch")

    worsened = int((county_disruption["disruption"] > 0).sum())
    improved = int((county_disruption["disruption"] < 0).sum())
    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric(
                "Counties included", f"{n_counties} of {total_us_counties}",
                delta=f"{1 - excluded_pct:.0%} of all U.S. counties", delta_color="off",
                help="The rest had too few deaths for CDC to report a reliable rate (fewer than about "
                     "20 over five years). They're mostly small, rural counties: see What predicts it.",
            )
        with st.container(border=True):
            st.metric("Rate rose (worse)", f"{worsened} ({worsened / n_counties:.0%})")
        with st.container(border=True):
            st.metric("Rate fell (better)", f"{improved} ({improved / n_counties:.0%})")

with predicts_tab:
    cause_het_display = cause_het.copy()
    cause_het_display["slope"] = cause_het_display.apply(
        lambda r: scale_context_slope_for_display(r["variable"], r["slope"]), axis=1
    )
    cause_het_display["variable"] = cause_het_display["variable"].map(CONTEXT_VAR_LABELS).fillna(cause_het_display["variable"])

    # A chart, not just the table below: which variables move disruption the
    # most, and in which direction, should be visible at a glance rather than
    # requiring the reader to scan 5 rows of numbers to find the pattern. Uses
    # a shorter income label than the table below (the full "Median household
    # income (per $10k)" is one factor in the clipping fixed below). Explicit
    # left padding is required, not optional: Vega-Lite auto-computed only
    # ~100px of left margin here (confirmed by inspecting the rendered SVG's
    # transform), nowhere near enough for a ~15-character label, so labels
    # rendered starting in negative x-space and were clipped by the SVG
    # canvas edge -- not a labelLimit/truncation issue, an under-computed
    # margin.
    het_bar_display = cause_het_display.copy()
    het_bar_display["variable"] = het_bar_display["variable"].replace(
        "Median household income (per $10k)", "Income (per $10k)"
    )
    het_bar = (
        alt.Chart(het_bar_display)
        .mark_bar()
        .encode(
            x=alt.X("slope:Q", title="Slope"),
            y=alt.Y("variable:N", sort="-x", title=None),
            color=alt.condition("datum.slope > 0", alt.value("#C26A2E"), alt.value("#2C5D86")),
            tooltip=[
                alt.Tooltip("variable:N", title="Context variable"),
                alt.Tooltip("slope:Q", title="Slope", format=".3f"),
                alt.Tooltip("p_value:Q", title="p-value", format=".3g"),
            ],
        )
        .properties(height=200, padding={"left": 150, "top": 5, "right": 5, "bottom": 5})
    )
    st.altair_chart(het_bar, width="stretch")
    st.caption("Orange bars predict **larger** disruption; blue bars predict **smaller** disruption. Exact numbers, sample size, and FDR status below.")
    st.dataframe(
        cause_het_display[["variable", "slope", "p_value", "n", "fdr_significant"]],
        column_config={
            "variable": st.column_config.TextColumn("Context variable", width="large"),
            "slope": st.column_config.NumberColumn("Slope", format="%.3f", width="small"),
            "p_value": st.column_config.NumberColumn("p-value", format="%.4g", width="small"),
            "n": st.column_config.NumberColumn("Counties", width="small"),
            "fdr_significant": st.column_config.CheckboxColumn("FDR-significant", width="small"),
        },
        hide_index=True,
        width="stretch",
    )

    n_fdr = int(cause_het["fdr_significant"].sum())
    st.caption(
        f"{n_fdr} of {len(cause_het)} context variables survive FDR correction across this "
        "cause's family of comparisons (research_protocol.md §10). Multiple correlated variables "
        "surviving together (e.g. uninsured rate, smoking, income) likely reflects that those "
        "variables are themselves correlated in the real data, not independent effects. This "
        "analysis cannot separate them."
    )

    rural_row = cause_het[cause_het["variable"] == "pct_rural"]
    if len(rural_row):
        bias = load_heterogeneity_selection_bias()
        bias_row = bias[bias["cause"] == cause].iloc[0]
        robustness = load_heterogeneity_rurality_robustness()
        cause_robustness = robustness[robustness["cause"] == cause].set_index("half")
        upper = cause_robustness.loc["upper_half"]
        lower = cause_robustness.loc["lower_half"]

        def _direction(row) -> str:
            if row["p_value"] >= 0.05:
                return f"no significant link (p={row['p_value']:.2g})"
            sign = "larger" if row["slope"] > 0 else "smaller"
            return f"{sign} disruption in more rural counties (p={row['p_value']:.2g})"

        st.warning(
            f"**Read the rurality result with two caveats.** First, the {int(bias_row['n_excluded']):,} "
            f"counties left out average **{bias_row['mean_excluded']*100:.0f}% rural**, vs. "
            f"**{bias_row['mean_included']*100:.0f}% rural** for the counties included, so the most rural "
            "places are under-represented. Second, these rates are crude, not age-adjusted, and rural "
            "counties tend to be older and aging faster, so part of any link between rurality and rising "
            "death rates could be population aging rather than the pandemic.",
            icon=":material/warning:",
        )
        reading = rurality_split_reading(upper["slope"], upper["p_value"], lower["slope"], lower["p_value"],
                                         full_significant=bool(rural_row.iloc[0]["fdr_significant"]))
        st.caption(
            f"Within the included counties, split at their median rurality: the more rural half shows "
            f"{_direction(upper)}, n={int(upper['n']):,}; the less rural half shows {_direction(lower)}, "
            f"n={int(lower['n']):,}. {reading}"
        )

    if cause in YEARLY_COMPARISON_CAUSES:
        yearly = load_heterogeneity_summary_yearly()
        yearly = yearly[yearly["cause"] == cause].set_index("variable")
        n_yearly = len(load_county_disruption_yearly(cause))
        with st.expander(f"Compare: the earlier year-by-year method ({n_yearly:,} counties)"):
            st.caption(
                "Before October 2026 this page used a stricter rule: a county needed a reliable rate in at "
                "least two individual years of each period, which dropped most rural counties. The pooled "
                f"five-year rates above keep {n_counties:,}. Same regression, same five measures."
            )
            compare = cause_het[["variable", "slope", "p_value", "fdr_significant"]].copy()
            compare["yearly_slope"] = compare["variable"].map(yearly["slope"])
            compare["yearly_p"] = compare["variable"].map(yearly["p_value"])
            compare["yearly_fdr"] = compare["variable"].map(yearly["fdr_significant"])
            for col in ("slope", "yearly_slope"):
                compare[col] = compare.apply(lambda r, c=col: scale_context_slope_for_display(r["variable"], r[c]), axis=1)
            compare["variable"] = compare["variable"].map(CONTEXT_VAR_LABELS).fillna(compare["variable"])
            st.dataframe(
                compare,
                column_config={
                    "variable": st.column_config.TextColumn("County measure", width="medium"),
                    "slope": st.column_config.NumberColumn("Slope (pooled)", format="%.3f"),
                    "p_value": st.column_config.NumberColumn("p (pooled)", format="%.3g"),
                    "fdr_significant": st.column_config.CheckboxColumn("FDR (pooled)"),
                    "yearly_slope": st.column_config.NumberColumn("Slope (year-by-year)", format="%.3f"),
                    "yearly_p": st.column_config.NumberColumn("p (year-by-year)", format="%.3g"),
                    "yearly_fdr": st.column_config.CheckboxColumn("FDR (year-by-year)"),
                },
                hide_index=True, width="stretch",
            )

with all_tab:
    bins = pd.cut(county_disruption["disruption"], bins=15)
    hist_df = bins.value_counts().sort_index().reset_index()
    hist_df.columns = ["range", "counties"]
    hist_df["range"] = hist_df["range"].apply(lambda iv: f"{iv.left:.1f} to {iv.right:.1f}")
    st.bar_chart(hist_df, x="range", y="counties")

    st.dataframe(
        county_disruption[["county_fips", "crude_rate_pre", "crude_rate_post", "disruption"]]
        .sort_values("disruption", ascending=False),
        column_config={
            "county_fips": "County FIPS",
            "crude_rate_pre": st.column_config.NumberColumn("Pre-period rate (crude)", format="%.1f"),
            "crude_rate_post": st.column_config.NumberColumn("Post-period rate (crude)", format="%.1f"),
            "disruption": st.column_config.NumberColumn("Disruption", format="%.1f"),
        },
        hide_index=True,
        width="stretch",
    )
