import streamlit as st

from app.components.data_loading import load_changepoints, data_available, synthetic_banner

st.title("Breakpoint explorer")
synthetic_banner()
st.caption("Every eligible county's detected breakpoint, method agreement, and trajectory classification.")

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

df = load_changepoints()
df["state_fips"] = df["county_fips"].str[:2]

with st.container(horizontal=True):
    trajectory_filter = st.multiselect(
        "Trajectory class",
        options=sorted(df["trajectory_class"].unique()),
        default=[c for c in df["trajectory_class"].unique() if c != "Insufficient data"],
    )
    eligible_only = st.toggle("Eligible counties only", value=True)

filtered = df[df["trajectory_class"].isin(trajectory_filter)] if trajectory_filter else df
if eligible_only:
    filtered = filtered[filtered["data_eligible_changepoint"]]

with st.container(horizontal=True):
    with st.container(border=True):
        st.metric("Counties shown", f"{len(filtered):,}")
    with st.container(border=True):
        n_sig = int(filtered["has_significant_break"].sum()) if len(filtered) else 0
        st.metric("With a significant break", f"{n_sig:,}")
    with st.container(border=True):
        median_year = filtered.loc[filtered["has_significant_break"], "breakpoint_year"].median()
        st.metric("Median breakpoint year", f"{median_year:.0f}" if median_year == median_year else "n/a")

st.subheader("Trajectory class distribution")
class_counts = filtered["trajectory_class"].value_counts().reset_index()
class_counts.columns = ["Trajectory class", "Counties"]
st.bar_chart(class_counts, x="Trajectory class", y="Counties")

st.subheader("Breakpoint-year distribution")
bp_years = filtered.loc[filtered["has_significant_break"], "breakpoint_year"].dropna()
if len(bp_years):
    hist = bp_years.value_counts().sort_index().reset_index()
    hist.columns = ["Year", "Counties"]
    st.bar_chart(hist, x="Year", y="Counties")
else:
    st.caption("No significant breakpoints in the current filter.")

st.subheader("County table")
display_cols = [
    "county_fips", "trajectory_class", "breakpoint_year", "pre_slope", "post_slope",
    "slope_diff", "p_value", "method_agreement_count", "n_obs", "data_eligible_changepoint",
]
st.dataframe(
    filtered[display_cols].sort_values("slope_diff"),
    column_config={
        "county_fips": "County FIPS",
        "trajectory_class": "Trajectory",
        "breakpoint_year": "Breakpoint year",
        "pre_slope": st.column_config.NumberColumn("Pre-slope", format="%.2f"),
        "post_slope": st.column_config.NumberColumn("Post-slope", format="%.2f"),
        "slope_diff": st.column_config.NumberColumn("Slope change", format="%.2f"),
        "p_value": st.column_config.NumberColumn("p-value", format="%.4f"),
        "method_agreement_count": "Method agreement",
        "n_obs": "Years observed",
        "data_eligible_changepoint": "Eligible",
    },
)
