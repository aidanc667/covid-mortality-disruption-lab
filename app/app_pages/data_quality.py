import pandas as pd
import streamlit as st

from app.components.data_loading import load_changepoints, load_mortality_panel, load_context, data_available, synthetic_banner

st.title("Data quality")
synthetic_banner()
st.caption("Suppression, unreliability, and eligibility are shown directly, not hidden (brief §9).")

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

panel = load_mortality_panel()
changepoints = load_changepoints()
context = load_context()

st.subheader("Mortality panel suppression / reliability")
with st.container(horizontal=True):
    with st.container(border=True):
        pct_suppressed = panel["age_adjusted_rate_suppressed"].mean() * 100
        st.metric("County-years suppressed", f"{pct_suppressed:.1f}%")
        st.caption("CDC WONDER suppresses death counts < 10")
    with st.container(border=True):
        pct_unreliable = panel["age_adjusted_rate_unreliable"].mean() * 100
        st.metric("County-years unreliable", f"{pct_unreliable:.1f}%")
        st.caption("Death count < 20")
    with st.container(border=True):
        st.metric("Total county-years", f"{len(panel):,}")

st.subheader("Suppression by year")
by_year = panel.groupby("year").agg(
    pct_suppressed=("age_adjusted_rate_suppressed", "mean"),
    pct_unreliable=("age_adjusted_rate_unreliable", "mean"),
).reset_index()
by_year["pct_suppressed"] *= 100
by_year["pct_unreliable"] *= 100
st.line_chart(by_year, x="year", y=["pct_suppressed", "pct_unreliable"])

st.subheader("County eligibility for change-point modeling")
elig_counts = changepoints["data_eligible_changepoint"].value_counts().rename({True: "Eligible", False: "Not eligible"})
st.bar_chart(elig_counts)
st.caption(
    "Eligibility requires ≥15 non-suppressed/reliable years and mid-period population ≥ the threshold "
    "set in research_protocol.md §6 — see the Methods page for exact values."
)

st.subheader("Missingness in context variables (joined counties)")
context_vars = [c for c in context.columns if c != "county_fips" and c != "release_year"]
missingness = context[context_vars].isna().mean().sort_values(ascending=False) * 100
missingness_df = missingness.reset_index()
missingness_df.columns = ["Variable", "% missing"]
st.dataframe(missingness_df, hide_index=True)

st.caption(
    "Missing values here are never imputed for mortality; context-variable missingness is shown as-is, "
    "per research_protocol.md §8."
)
