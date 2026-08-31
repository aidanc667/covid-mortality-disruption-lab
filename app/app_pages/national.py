import numpy as np
import pandas as pd
import streamlit as st

from app.components.data_loading import load_mortality_panel, data_available, synthetic_banner
from src.analysis.changepoints import fit_segmented_regression, fit_pelt, fit_binseg, summarize_method_agreement

st.title("National trends")
synthetic_banner()

st.caption(
    "Brief §19: county-level breakpoints are not assumed to imply a national breakpoint — this page "
    "estimates a national-level trajectory and its own breakpoint independently, on their own scale."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

panel = load_mortality_panel()

st.info(
    "This aggregate is the (unweighted) mean of the mortality panel's own sampled counties, not an "
    "independently pulled national CDC WONDER series — an actual national query is the correct source "
    "once the manual mortality export exists. Treat this series as illustrative.",
    icon=":material/info:",
)

usable = panel[~panel["age_adjusted_rate_suppressed"] & ~panel["age_adjusted_rate_unreliable"]]
national = usable.groupby("year")["age_adjusted_rate"].mean().reset_index()

years = national["year"].to_numpy()
rates = national["age_adjusted_rate"].to_numpy(dtype=float)

seg = fit_segmented_regression(years, rates)
pelt_bps = fit_pelt(years, rates)
binseg_bps = fit_binseg(years, rates)
agreement = summarize_method_agreement({
    "segmented_regression": seg.breakpoint_year,
    "pelt": pelt_bps[0] if pelt_bps else None,
    "binseg": binseg_bps[0] if binseg_bps else None,
})

chart_df = national.rename(columns={"age_adjusted_rate": "Age-adjusted rate (per 100k)"})
st.line_chart(chart_df, x="year", y="Age-adjusted rate (per 100k)")

if seg.has_significant_break:
    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric("Estimated breakpoint", seg.breakpoint_year)
        with st.container(border=True):
            st.metric("Pre-break slope", f"{seg.pre_slope:+.2f}/yr")
        with st.container(border=True):
            st.metric("Post-break slope", f"{seg.post_slope:+.2f}/yr")
        with st.container(border=True):
            st.metric("Method agreement", f"{agreement['agreement_count']}/{agreement['n_methods_run']}")
    st.caption(agreement["summary"])
else:
    st.info("No statistically significant national-level breakpoint detected at α=0.05.", icon=":material/info:")

with st.expander("Method details"):
    st.write(f"Segmented regression p-value: {seg.p_value:.4f}" if seg.p_value is not None else "p-value unavailable (insufficient data)")
    st.write(f"PELT candidate breakpoint(s): {pelt_bps or 'none'}")
    st.write(f"Binary segmentation candidate breakpoint(s): {binseg_bps or 'none'}")
