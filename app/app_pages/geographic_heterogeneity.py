import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_heterogeneity_summary, load_county_disruption, data_available, heterogeneity_synthetic_banner,
    HETEROGENEITY_CAUSES,
)
from app.components.county_map import render_county_choropleth

st.title("Geographic heterogeneity")
heterogeneity_synthetic_banner()
st.caption(
    "Is county-level disruption magnitude associated with socioeconomic status, healthcare "
    "access, or rurality? Associational only — see Methods for the causal-language policy."
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

st.subheader("Where disruption was largest")
st.caption(
    "Blue = mortality rate fell relative to pre-pandemic trend. Red = mortality rate rose. "
    "Gray = excluded (fewer than 2 non-suppressed years in one or both periods). Hover a county "
    "for its exact pre/post rates. Rates are **crude rate**, not age-adjusted — CDC WONDER does "
    "not offer age-adjustment at county granularity for the 2018–2024 database "
    "(research_protocol.md's 2026-09-01 addendum)."
)
st.altair_chart(render_county_choropleth(county_disruption, cause), width="stretch")

n_counties = len(county_disruption)
worsened = int((county_disruption["disruption"] > 0).sum())
improved = int((county_disruption["disruption"] < 0).sum())
with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Counties included", n_counties)
    with st.container(border=True):
        st.metric("Rate rose (worse)", f"{worsened} ({worsened / n_counties:.0%})")
    with st.container(border=True):
        st.metric("Rate fell (better)", f"{improved} ({improved / n_counties:.0%})")

st.subheader(f"Context-variable associations — {cause}")
st.dataframe(
    cause_het[["variable", "slope", "p_value", "n", "fdr_significant"]],
    column_config={
        "variable": st.column_config.TextColumn("Context variable", width="medium"),
        "slope": st.column_config.NumberColumn("Slope", format="%.3f"),
        "p_value": st.column_config.NumberColumn("p-value", format="%.4g"),
        "n": "Counties",
        "fdr_significant": "FDR-significant",
    },
    hide_index=True,
    width="stretch",
)

n_fdr = int(cause_het["fdr_significant"].sum())
st.caption(
    f"{n_fdr} of {len(cause_het)} context variables survive FDR correction across this "
    "cause's family of comparisons (research_protocol.md §10). Multiple correlated variables "
    "surviving together (e.g. uninsured rate, smoking, income) likely reflects that those "
    "variables are themselves correlated in the real data, not independent effects — this "
    "analysis cannot separate them."
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
