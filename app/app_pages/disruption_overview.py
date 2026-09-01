import pandas as pd
import streamlit as st

from app.components.data_loading import (
    load_national_series, load_covid_reference_series, load_disruption_summary,
    load_disruption_deviations, data_available, synthetic_banner, TEST_CAUSES, NEGATIVE_CONTROL,
)

st.title("Disruption overview")
synthetic_banner()
st.caption(
    "Each cause's actual trajectory against its expected pre-pandemic trend (1999–2019), "
    "projected forward with a 95% prediction interval. A year outside the shaded band is "
    "flagged as a statistically significant deviation."
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

national = load_national_series()
covid_ref = load_covid_reference_series()
summary = load_disruption_summary()
deviations = load_disruption_deviations()

all_causes = TEST_CAUSES + [NEGATIVE_CONTROL]
show_covid = st.toggle("Include COVID-19 reference series", value=True)

for cause in all_causes:
    row = summary[summary["cause"] == cause]
    label = cause
    if len(row):
        label = f"{cause} — {row.iloc[0]['persistence_class']}"
    elif cause == NEGATIVE_CONTROL:
        label = f"{cause} (negative control)"

    with st.container(border=True):
        st.write(f"**{label}**")

        series = national[national["cause"] == cause].sort_values("year")
        dev = deviations[deviations["cause"] == cause].sort_values("year")

        chart_df = series[["year", "age_adjusted_rate"]].rename(
            columns={"age_adjusted_rate": "Observed"}
        )
        if len(dev):
            expected_df = dev[["year", "expected"]].rename(columns={"expected": "Expected trend"})
            chart_df = chart_df.merge(expected_df, on="year", how="left")

        st.line_chart(chart_df, x="year", y=[c for c in chart_df.columns if c != "year"])

        if len(row):
            r = row.iloc[0]
            with st.container(horizontal=True):
                st.caption(f"p = {r['p_value']:.4g}")
                st.caption(f"FDR-significant: {'Yes' if r['fdr_significant'] else 'No'}")
                st.caption(f"Cross-check (PELT/binseg) confirms ~2020: {'Yes' if r['cross_check_confirms_2020'] else 'No'}")
            with st.container(horizontal=True):
                st.caption(f"Acute-period (2020–21) deviation: {r['acute_pct_deviation']:+.1f}% vs. expected trend")
                st.caption(f"Latest (2024) deviation: {r['latest_pct_deviation']:+.1f}% vs. expected trend")
            if not r["cross_check_confirms_2020"]:
                st.caption(
                    "Cross-check disagreement isn't itself evidence against this result — PELT/binseg "
                    "search the whole series for any breakpoint, while the primary method tests this "
                    "one pre-registered date specifically. See Methods for why these can legitimately differ."
                )

if show_covid:
    st.subheader("COVID-19 (reference series, not a hypothesis test)")
    st.caption(
        "Didn't exist before 2020, so there is no pre-pandemic trend to compare against — "
        "shown for scale, not as a disruption test."
    )
    covid_chart = covid_ref[["year", "age_adjusted_rate"]].rename(columns={"age_adjusted_rate": "COVID-19"})
    st.line_chart(covid_chart, x="year", y="COVID-19")
