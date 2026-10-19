import altair as alt
import pandas as pd
import streamlit as st

from app.components.data_loading import (
    COUNTY_PAGE_CAUSES,
    county_cause_label,
    data_available,
    heterogeneity_synthetic_banner,
    load_county_disruption,
)
from src.ingestion.county_health_rankings import load_year as load_chr_year

st.title("County lookup")
heterogeneity_synthetic_banner()
st.caption(
    "Pre (2015–2019) vs. post (2020–2024) crude death rates for the five disrupted causes "
    "and, as an exploratory sixth, Alzheimer's, plus local context. Only period averages exist at county level, not year-by-year trends "
    "(research_protocol.md §4)."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

frames = [load_county_disruption(c) for c in COUNTY_PAGE_CAUSES]
combined = pd.concat(frames, ignore_index=True)

# County names come from the real CDC WONDER export
# (src/analysis/heterogeneity.compute_county_disruption attaches them) --
# a bare 5-digit FIPS code isn't something anyone has memorized, so the
# selector needs a human-readable label even though FIPS remains the
# actual lookup key everywhere else on this page.
name_lookup = {}
if "county_name" in combined.columns:
    name_lookup = (
        combined.dropna(subset=["county_name"])
        .drop_duplicates("county_fips")
        .set_index("county_fips")["county_name"]
        .to_dict()
    )

county_fips = st.selectbox(
    "Select a county",
    options=sorted(combined["county_fips"].unique()),
    format_func=lambda fips: f"{name_lookup[fips]} ({fips})" if fips in name_lookup else fips,
)

st.subheader(name_lookup.get(county_fips, f"County {county_fips}"))

county_rows = combined[combined["county_fips"] == county_fips]

with st.container(horizontal=True):
    for cause in COUNTY_PAGE_CAUSES:
        row = county_rows[county_rows["cause"] == cause]
        with st.container(border=True):
            st.write(f"**{county_cause_label(cause)}**")
            if len(row):
                r = row.iloc[0]
                st.metric("Pre-period rate (crude)", f"{r['crude_rate_pre']:.1f}")
                # inverse: a falling death rate is the good direction (green).
                st.metric(
                    "Post-period rate (crude)", f"{r['crude_rate_post']:.1f}",
                    delta=f"{r['disruption']:+.1f}", delta_color="inverse",
                )
            else:
                st.caption("Excluded: insufficient non-missing years in one or both periods.")

if len(county_rows):
    rates = county_rows.melt(
        id_vars=["cause"], value_vars=["crude_rate_pre", "crude_rate_post"], var_name="period", value_name="rate",
    )
    rates["period"] = rates["period"].map({"crude_rate_pre": "2015–2019", "crude_rate_post": "2020–2024"})
    rates["cause"] = rates["cause"].map(county_cause_label)
    st.altair_chart(
        alt.Chart(rates)
        .mark_bar(cornerRadiusEnd=2)
        .encode(
            # Same order as the cards above; the two periods sit side by side per cause.
            y=alt.Y("cause:N", title=None, sort=[county_cause_label(c) for c in COUNTY_PAGE_CAUSES],
                    axis=alt.Axis(ticks=False, domain=False, labelFontSize=12, labelLimit=0)),
            yOffset=alt.YOffset("period:N", sort=["2015–2019", "2020–2024"]),
            x=alt.X("rate:Q", title="Crude death rate per 100,000"),
            color=alt.Color(
                "period:N", scale=alt.Scale(domain=["2015–2019", "2020–2024"], range=["#B4C0CC", "#2C5D86"]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=["cause:N", "period:N", alt.Tooltip("rate:Q", format=".1f")],
        )
        .properties(height=44 * rates["cause"].nunique(), padding={"left": 16, "top": 4, "right": 8, "bottom": 4}),
        width="stretch",
    )

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
