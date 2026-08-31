"""Cached loaders for precomputed pipeline outputs. The app never re-runs
change-point models itself (brief section 46) — it only reads the parquet
files scripts/run_synthetic_pipeline.py (or, once real data exists, the
equivalent real pipeline) already wrote to outputs/models/ and
data/processed/.
"""
import streamlit as st
import pandas as pd

from src.utils.config import OUTPUTS_MODELS, DATA_PROCESSED
from src.utils.synthetic_mortality import is_synthetic_active


@st.cache_data(ttl="1h")
def load_changepoints() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "county_changepoints.parquet")


@st.cache_data(ttl="1h")
def load_context() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "county_context.parquet")


@st.cache_data(ttl="1h")
def load_mortality_panel() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "mortality_panel.parquet")


def data_available() -> bool:
    return (OUTPUTS_MODELS / "county_changepoints.parquet").exists()


def synthetic_banner() -> None:
    """Renders a hard-to-miss warning whenever the pipeline last ran on
    fabricated placeholder data, so it can never be mistaken for a real
    research finding (brief section 56)."""
    if is_synthetic_active():
        st.error(
            "This app is currently displaying **synthetic placeholder data**, "
            "not real mortality statistics. Every trajectory, breakpoint, and "
            "association shown below is fabricated for pipeline development. "
            "See `docs/manual_data_acquisition.md` to load real CDC WONDER data.",
            icon=":material/science:",
        )
