import streamlit as st

from app.components.data_loading import load_changepoints, data_available, synthetic_banner
from src.utils.config import PRIMARY_WINDOW, MIN_COUNTY_POPULATION

st.title("COVID Mortality Disruption Lab")
st.caption(
    "Detecting, validating, and investigating structural changes in U.S. disease mortality trajectories"
)

synthetic_banner()

st.markdown(
    "> **When and where do U.S. county-level diabetes mortality trajectories undergo statistically "
    "significant structural changes, and what demographic, socioeconomic, healthcare, behavioral, and "
    "environmental factors are associated with differences in post-breakpoint trajectories?**"
)

st.write(
    "This project investigates structural changes in U.S. county-level diabetes mortality trajectories "
    f"({PRIMARY_WINDOW[0]}–{PRIMARY_WINDOW[1]}) using public CDC mortality data and complementary "
    "socioeconomic, healthcare, behavioral, demographic, and environmental datasets."
)

if not data_available():
    st.warning(
        "No precomputed results found yet. Run `python scripts/run_synthetic_pipeline.py` "
        "(or the real pipeline, once available) to populate outputs/models/.",
        icon=":material/warning:",
    )
else:
    df = load_changepoints()
    eligible = df[df["data_eligible_changepoint"]]

    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric("Counties in panel", f"{len(df):,}")
            st.caption("Total counties with any mortality data in the primary window")
        with st.container(border=True):
            st.metric("Eligible for change-point modeling", f"{len(eligible):,}")
            st.caption(f"Meet minimum data-quality thresholds (§6): population ≥ {MIN_COUNTY_POPULATION:,}")
        with st.container(border=True):
            n_break = int(eligible["has_significant_break"].sum())
            st.metric("Counties with a detected breakpoint", f"{n_break:,}")
            st.caption("Statistically significant structural change (segmented regression, α=0.05)")
        with st.container(border=True):
            pct_improving = (eligible["trajectory_class"] == "Improving").mean() * 100 if len(eligible) else 0
            st.metric("Improving trajectories", f"{pct_improving:.0f}%")
            st.caption("Of eligible counties — see Trajectory classification in Methods")

    st.subheader("What this is")
    st.write(
        "A research-grade, reproducible analysis pipeline paired with this interactive application. "
        "The pipeline detects structural breaks in mortality trajectories using multiple independent "
        "statistical methods, validates them against each other, and investigates whether contextual "
        "factors are associated with more or less favorable post-breakpoint outcomes — always in "
        "associational language, never causal, per the research protocol."
    )

st.subheader("Explore")
st.write(
    "**National trends** — the aggregate mortality trajectory and its own, independently estimated breakpoint.\n\n"
    "**Breakpoint explorer** — filter and sort every eligible county's detected breakpoint and trajectory class.\n\n"
    "**County deep dive** — inspect one county's full trajectory, model fit, and context.\n\n"
    "**Data quality** — suppression, unreliability, and eligibility, shown rather than hidden.\n\n"
    "**Methods** — every statistical choice and threshold, made explicit."
)

with st.expander("Ethics statement", icon=":material/balance:"):
    st.write(
        "This project uses publicly available aggregate data and is intended for research and "
        "educational purposes. It does not provide medical advice or individual-level risk predictions."
    )
