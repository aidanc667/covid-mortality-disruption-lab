import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_heterogeneity_summary, load_county_disruption, data_available, synthetic_banner, HETEROGENEITY_CAUSES,
)

st.title("Geographic heterogeneity")
synthetic_banner()
st.caption(
    "Is county-level disruption magnitude associated with socioeconomic status, healthcare "
    "access, or rurality? Associational only — see Methods for the causal-language policy."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

het = load_heterogeneity_summary()

cause = st.selectbox("Cause", options=HETEROGENEITY_CAUSES)
cause_het = het[het["cause"] == cause].sort_values("p_value")

st.subheader(f"Context-variable associations — {cause}")
st.dataframe(
    cause_het[["variable", "slope", "p_value", "n", "fdr_significant"]],
    column_config={
        "variable": "Context variable",
        "slope": st.column_config.NumberColumn("Slope", format="%.3f"),
        "p_value": st.column_config.NumberColumn("p-value", format="%.4g"),
        "n": "Counties",
        "fdr_significant": "FDR-significant",
    },
    hide_index=True,
)

n_fdr = int(cause_het["fdr_significant"].sum())
st.caption(
    f"{n_fdr} of {len(cause_het)} context variables survive FDR correction across this "
    "cause's family of comparisons (research_protocol.md §10). Multiple correlated variables "
    "surviving together (e.g. uninsured rate, smoking, income) likely reflects that those "
    "variables are themselves correlated in the real data, not independent effects — this "
    "analysis cannot separate them."
)

st.subheader("County-level disruption distribution")
county_disruption = load_county_disruption(cause)
bins = pd.cut(county_disruption["disruption"], bins=15)
hist_df = (
    bins.value_counts().sort_index().reset_index()
)
hist_df.columns = ["range", "counties"]
hist_df["range"] = hist_df["range"].apply(lambda iv: f"{iv.left:.1f} to {iv.right:.1f}")
st.bar_chart(hist_df, x="range", y="counties")

st.dataframe(
    county_disruption[["county_fips", "age_adjusted_rate_pre", "age_adjusted_rate_post", "disruption"]]
    .sort_values("disruption", ascending=False),
    column_config={
        "county_fips": "County FIPS",
        "age_adjusted_rate_pre": st.column_config.NumberColumn("Pre-period rate", format="%.1f"),
        "age_adjusted_rate_post": st.column_config.NumberColumn("Post-period rate", format="%.1f"),
        "disruption": st.column_config.NumberColumn("Disruption", format="%.1f"),
    },
    hide_index=True,
)
