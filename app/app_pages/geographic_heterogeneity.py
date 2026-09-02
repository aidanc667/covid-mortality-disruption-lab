import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_heterogeneity_summary, load_county_disruption, load_heterogeneity_selection_bias,
    load_heterogeneity_rurality_robustness, data_available, heterogeneity_synthetic_banner,
    HETEROGENEITY_CAUSES, CONTEXT_VAR_LABELS, scale_context_slope_for_display,
)
from app.components.county_map import render_county_choropleth
from src.ingestion.county_health_rankings import load_year as load_chr_year

st.title("Geographic heterogeneity")
heterogeneity_synthetic_banner()
st.caption(
    "Is county-level disruption magnitude associated with socioeconomic status, healthcare "
    "access, or rurality? Associational only. See Methods for the causal-language policy."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

het = load_heterogeneity_summary()

cause = st.segmented_control("Cause", options=HETEROGENEITY_CAUSES, default=HETEROGENEITY_CAUSES[0])
if cause is None:
    st.stop()
cause_het = het[het["cause"] == cause].sort_values("p_value")
county_disruption = load_county_disruption(cause)

n_counties = len(county_disruption)
total_us_counties = load_chr_year(2024)["county_fips"].nunique()
excluded_pct = 1 - n_counties / total_us_counties

st.subheader("Where disruption was largest")
st.caption(
    f"Only {n_counties} of {total_us_counties} U.S. counties ({1 - excluded_pct:.0%}) have enough "
    f"non-suppressed years of data to appear here at all; the other {excluded_pct:.0%}, shown in "
    f"gray, are excluded, not zero. Blue = mortality rate fell relative to pre-pandemic trend. "
    "Orange = mortality rate rose (a colorblind-safe blue/orange scale, not red/green or red/blue, "
    "which are hard to distinguish for the ~8% of men with red-green color vision deficiency). "
    "Hover a county for its exact pre/post rates. Rates are **crude rate**, not age-adjusted: CDC "
    "WONDER does not offer age-adjustment at county granularity for the 2018–2024 database "
    "(research_protocol.md's 2026-09-01 addendum)."
)
st.altair_chart(render_county_choropleth(county_disruption, cause), width="stretch")

worsened = int((county_disruption["disruption"] > 0).sum())
improved = int((county_disruption["disruption"] < 0).sum())
with st.container(horizontal=True):
    with st.container(border=True):
        st.metric(
            "Counties included", f"{n_counties} of {total_us_counties}",
            delta=f"{1 - excluded_pct:.0%} of all U.S. counties", delta_color="off",
            help="The rest are excluded for insufficient non-suppressed years of data, "
                 "disproportionately rural counties -- see the rurality caveat below.",
        )
    with st.container(border=True):
        st.metric("Rate rose (worse)", f"{worsened} ({worsened / n_counties:.0%})")
    with st.container(border=True):
        st.metric("Rate fell (better)", f"{improved} ({improved / n_counties:.0%})")

st.subheader(f"Context-variable associations: {cause}")
cause_het_display = cause_het.copy()
cause_het_display["slope"] = cause_het_display.apply(
    lambda r: scale_context_slope_for_display(r["variable"], r["slope"]), axis=1
)
cause_het_display["variable"] = cause_het_display["variable"].map(CONTEXT_VAR_LABELS).fillna(cause_het_display["variable"])
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

    st.warning(
        f"**Rurality finding: read this before trusting it.** The counties *excluded* from this "
        f"analysis (too few non-suppressed years) are on average "
        f"**{bias_row['mean_excluded']*100:.0f}% rural**, vs. **{bias_row['mean_included']*100:.0f}% rural** "
        f"for the counties actually included. Suppression disproportionately drops small, rural "
        f"counties, so this regression describes suburban/small-city counties far more than it "
        f"describes rural America.", icon=":material/warning:",
    )
    if cause_robustness.loc["upper_half", "p_value"] < 0.05 and (
        cause_robustness.loc["upper_half", "slope"] < 0
    ) == (rural_row.iloc[0]["slope"] < 0):
        st.caption(
            f"For {cause}, the relationship holds up reasonably well as a robustness check: split "
            f"the *included* counties at the median rurality, and the rurality-disruption "
            f"relationship is still significant among the more-rural half (p={upper['p_value']:.3g}, "
            f"n={int(upper['n'])}); if anything, it's stronger there than among the less-rural half "
            f"(p={lower['p_value']:.3g}). Still doesn't cover the excluded, most-rural counties above."
        )
    else:
        st.caption(
            f"For {cause}, this robustness check is a real concern: split the *included* counties "
            f"at the median rurality, and the relationship is driven almost entirely by the "
            f"**less**-rural half (p={lower['p_value']:.3g}, n={int(lower['n'])}). Among the "
            f"more-rural half of the included sample, it's not significant "
            f"(p={upper['p_value']:.3g}, n={int(upper['n'])}). Read the pooled slope above with real "
            f"caution for this cause."
        )

with st.expander("County-level disruption distribution and full table"):
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
