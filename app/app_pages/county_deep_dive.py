import numpy as np
import pandas as pd
import streamlit as st

from app.components.data_loading import load_changepoints, load_context, load_mortality_panel, data_available, synthetic_banner

st.title("County deep dive")
synthetic_banner()

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

changepoints = load_changepoints()
context = load_context()
panel = load_mortality_panel()

eligible = changepoints[changepoints["data_eligible_changepoint"]].sort_values("county_fips")
county_fips = st.selectbox(
    "Select a county (FIPS)",
    options=eligible["county_fips"].tolist(),
    format_func=lambda f: f,
)

row = changepoints[changepoints["county_fips"] == county_fips].iloc[0]
county_series = panel[panel["county_fips"] == county_fips].sort_values("year").copy()
county_series.loc[
    county_series["age_adjusted_rate_suppressed"] | county_series["age_adjusted_rate_unreliable"],
    "age_adjusted_rate",
] = np.nan

st.subheader(f"County {county_fips}")

if row["trajectory_class"] == "Stable" and pd.notna(row["slope_diff"]) and abs(row["slope_diff"]) >= 0.3:
    st.caption(
        f"Best-fit slope change was {row['slope_diff']:+.2f}/yr, but the break was not statistically "
        f"significant (p={row['p_value']:.3f} ≥ 0.05) — classified Stable per the pre-registered rule, "
        "not because the fitted change was small."
    )

with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Trajectory class", row["trajectory_class"])
    with st.container(border=True):
        st.metric("Breakpoint year", int(row["breakpoint_year"]) if pd.notna(row["breakpoint_year"]) else "None detected")
    with st.container(border=True):
        st.metric("Slope change", f"{row['slope_diff']:+.2f}/yr" if pd.notna(row["slope_diff"]) else "n/a")
    with st.container(border=True):
        st.metric("Method agreement", f"{int(row['method_agreement_count'])}/3" if pd.notna(row["method_agreement_count"]) else "n/a")

st.subheader("Trajectory")
chart_df = county_series[["year", "age_adjusted_rate"]].rename(columns={"age_adjusted_rate": "Age-adjusted rate (per 100k)"})
st.line_chart(chart_df, x="year", y="Age-adjusted rate (per 100k)")

with st.container(horizontal=True):
    with st.container(border=True):
        st.write("**Before vs. after**")
        st.write(f"Pre-break slope: {row['pre_slope']:+.2f}/yr" if pd.notna(row["pre_slope"]) else "n/a")
        st.write(f"Post-break slope: {row['post_slope']:+.2f}/yr" if pd.notna(row["post_slope"]) else "n/a")
        st.write(f"p-value: {row['p_value']:.4f}" if pd.notna(row["p_value"]) else "n/a")
        st.caption(row["method_agreement_summary"] if pd.notna(row["method_agreement_summary"]) else "")

    with st.container(border=True):
        st.write("**Reliability**")
        n_suppressed = int(county_series["age_adjusted_rate_suppressed"].sum())
        n_unreliable = int(county_series["age_adjusted_rate_unreliable"].sum())
        st.write(f"Years observed: {row['n_obs']}")
        st.write(f"Suppressed years: {n_suppressed}")
        st.write(f"Unreliable years: {n_unreliable}")
        st.write(f"Mid-period population: {row['mid_period_population']:,.0f}")

st.subheader("Context (real 2024 data, joined by county FIPS)")
context_row = context[context["county_fips"] == county_fips]
if len(context_row):
    context_row = context_row.iloc[0]
    context_fields = {
        "% uninsured (CHR&R)": ("pct_uninsured_chr", "{:.1%}"),
        "% adult smokers": ("pct_smokers", "{:.1%}"),
        "% adult obesity": ("pct_obese", "{:.1%}"),
        "% physically inactive": ("pct_inactive", "{:.1%}"),
        "Median household income": ("median_income_chr", "${:,.0f}"),
        "Food environment index": ("food_environment_index", "{:.1f}/10"),
        "% rural": ("pct_rural", "{:.1%}"),
        "Primary care physicians": ("primary_care_physicians_count", "{:.0f}"),
        "Low food access (% pop)": ("pct_low_access_pop", "{:.1f}%"),
    }
    cols = st.container(horizontal=True)
    for label, (field, fmt) in context_fields.items():
        val = context_row.get(field)
        with cols.container(border=True):
            st.caption(label)
            st.write(fmt.format(val) if pd.notna(val) else "n/a")
else:
    st.caption("No context data available for this county.")

with st.expander("Why this breakpoint?", icon=":material/help:"):
    if pd.notna(row["breakpoint_year"]):
        st.write(f"**Statistical evidence:** Segmented regression identified a breakpoint at {int(row['breakpoint_year'])} "
                 f"(p={row['p_value']:.4f}), {row['method_agreement_summary'].split('.')[0].lower()}.")
        st.write(f"**Magnitude:** The trajectory's slope changed by {row['slope_diff']:+.2f} deaths per 100k per year.")
        st.write("**Alternative explanations to consider:** small-population instability, the CDC WONDER mortality-vintage "
                 "discontinuity (see Methods), and county boundary/classification changes — none of these have been "
                 "specifically ruled out for this individual county in this MVP; a per-county artifact check is a "
                 "planned addition (brief §27).")
    else:
        st.write("No statistically significant breakpoint was detected for this county at the current threshold.")
