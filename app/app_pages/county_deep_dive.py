import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_county_disruption, data_available, heterogeneity_synthetic_banner, HETEROGENEITY_CAUSES,
)
from src.ingestion.county_health_rankings import load_year as load_chr_year

st.title("County deep dive")
heterogeneity_synthetic_banner()
st.caption(
    "County-level heterogeneity data exists only as pre/post period aggregates for the "
    "causes analyzed in the Geographic Heterogeneity page — not full annual trajectories "
    "like the original diabetes-only pilot. See research_protocol.md §4 for why county-level "
    "analysis uses coarser aggregation than the national/state series."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

frames = [load_county_disruption(c) for c in HETEROGENEITY_CAUSES]
combined = pd.concat(frames, ignore_index=True)

county_fips = st.selectbox("Select a county (FIPS)", options=sorted(combined["county_fips"].unique()))

st.subheader(f"County {county_fips}")

county_rows = combined[combined["county_fips"] == county_fips]

with st.container(horizontal=True):
    for cause in HETEROGENEITY_CAUSES:
        row = county_rows[county_rows["cause"] == cause]
        with st.container(border=True):
            st.write(f"**{cause}**")
            if len(row):
                r = row.iloc[0]
                st.metric("Pre-period rate (crude)", f"{r['crude_rate_pre']:.1f}")
                st.metric("Post-period rate (crude)", f"{r['crude_rate_post']:.1f}", delta=f"{r['disruption']:+.1f}")
            else:
                st.caption("Excluded — insufficient non-missing years in one or both periods.")

st.subheader("Context (real 2024 CHR&R data)")
chr_df = load_chr_year(2024)
context_row = chr_df[chr_df["county_fips"] == county_fips]
if len(context_row):
    context_row = context_row.iloc[0]
    fields = {
        "% uninsured": ("pct_uninsured_chr", "{:.1%}"),
        "% adult smokers": ("pct_smokers", "{:.1%}"),
        "% adult obesity": ("pct_obese", "{:.1%}"),
        "Median household income": ("median_income_chr", "${:,.0f}"),
        "% rural": ("pct_rural", "{:.1%}"),
    }
    cols = st.container(horizontal=True)
    for label, (field, fmt) in fields.items():
        val = context_row.get(field)
        with cols.container(border=True):
            st.caption(label)
            st.write(fmt.format(val) if pd.notna(val) else "n/a")
else:
    st.caption("No context data available for this county.")
