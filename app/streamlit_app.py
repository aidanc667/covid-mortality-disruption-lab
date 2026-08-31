import sys
from pathlib import Path

# Ensure the project root (parent of app/) is importable as `src.*` and
# `app.*` regardless of the working directory `streamlit run` is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="COVID Mortality Disruption Lab",
    page_icon=":material/monitor_heart:",
    layout="wide",
)

page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Home", icon=":material/home:"),
        ],
        "Detection": [
            st.Page("app_pages/national.py", title="National trends", icon=":material/trending_up:"),
            st.Page("app_pages/breakpoint_explorer.py", title="Breakpoint explorer", icon=":material/query_stats:"),
            st.Page("app_pages/county_deep_dive.py", title="County deep dive", icon=":material/location_on:"),
        ],
        "Rigor": [
            st.Page("app_pages/data_quality.py", title="Data quality", icon=":material/fact_check:"),
            st.Page("app_pages/methods.py", title="Methods", icon=":material/school:"),
        ],
    },
    position="sidebar",
)

page.run()
