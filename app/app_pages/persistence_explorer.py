import streamlit as st

from app.components.data_loading import load_disruption_summary, data_available, synthetic_banner

st.title("Persistence explorer")
synthetic_banner()
st.caption(
    "For each cause with a significant acute-phase (2020–2021) disruption: did it persist "
    "through 2024, resolve back toward the expected trend, or reverse below it?"
)

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

summary = load_disruption_summary()

CLASS_ORDER = ["Persisted", "Reversed", "Resolved", "No significant disruption"]
CLASS_ICON = {
    "Persisted": ":material/trending_flat:",
    "Reversed": ":material/u_turn_right:",
    "Resolved": ":material/check_circle:",
    "No significant disruption": ":material/remove:",
}

with st.container(horizontal=True):
    for cls in CLASS_ORDER:
        with st.container(border=True):
            n = int((summary["persistence_class"] == cls).sum())
            st.metric(cls, n)

st.subheader("By cause")
for cls in CLASS_ORDER:
    subset = summary[summary["persistence_class"] == cls]
    if not len(subset):
        continue
    st.write(f"**{cls}**")
    for _, r in subset.iterrows():
        with st.container(border=True, horizontal=True):
            st.write(r["cause"])
            st.caption(f"p = {r['p_value']:.4g}")
            st.caption(f"FDR-significant: {'Yes' if r['fdr_significant'] else 'No'}")
            st.caption(f"Cross-check confirms ~2020: {'Yes' if r['cross_check_confirms_2020'] else 'No'}")

st.dataframe(
    summary[["cause", "persistence_class", "p_value", "fdr_significant", "cross_check_confirms_2020"]],
    column_config={
        "cause": "Cause",
        "persistence_class": "Persistence",
        "p_value": st.column_config.NumberColumn("p-value", format="%.4g"),
        "fdr_significant": "FDR-significant",
        "cross_check_confirms_2020": "Cross-check confirms ~2020",
    },
    hide_index=True,
)
