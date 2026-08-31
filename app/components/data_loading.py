"""Cached loaders for precomputed pipeline outputs. The app never re-runs
excess-mortality or heterogeneity analysis itself (brief section 46) — it
only reads the parquet files scripts/run_covid_disruption_pipeline.py (or,
once real WONDER data exists, the equivalent real pipeline) already wrote
to outputs/models/.
"""
import streamlit as st
import pandas as pd

from src.utils.config import OUTPUTS_MODELS
from src.utils.synthetic_mortality import is_synthetic_active

TEST_CAUSES = [
    "Diseases of heart", "Diabetes mellitus", "Alzheimer's disease",
    "Cerebrovascular disease", "Drug overdose", "Malignant neoplasms",
]
NEGATIVE_CONTROL = "Accidental drowning"
HETEROGENEITY_CAUSES = ["Diabetes mellitus", "Drug overdose"]


@st.cache_data(ttl="1h")
def load_national_series() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "national_mortality_series.parquet")


@st.cache_data(ttl="1h")
def load_covid_reference_series() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "covid_reference_series.parquet")


@st.cache_data(ttl="1h")
def load_disruption_summary() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "disruption_summary.parquet")


@st.cache_data(ttl="1h")
def load_disruption_deviations() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "disruption_deviations.parquet")


@st.cache_data(ttl="1h")
def load_heterogeneity_summary() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_summary.parquet")


@st.cache_data(ttl="1h")
def load_negative_control() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "negative_control.parquet")


@st.cache_data(ttl="1h")
def load_county_disruption(cause: str) -> pd.DataFrame:
    fname = f"county_disruption_{cause.lower().replace(' ', '_')}.parquet"
    return pd.read_parquet(OUTPUTS_MODELS / fname)


def data_available() -> bool:
    return (OUTPUTS_MODELS / "disruption_summary.parquet").exists()


def synthetic_banner() -> None:
    """Renders a hard-to-miss warning whenever the pipeline last ran on
    fabricated placeholder data, so it can never be mistaken for a real
    research finding (brief section 56)."""
    if is_synthetic_active():
        st.error(
            "This app is currently displaying **synthetic placeholder data**, "
            "not real mortality statistics. Every disruption, persistence "
            "classification, and association shown below is fabricated for "
            "pipeline development, generated to match this project's own "
            "pre-registered priors (see Methods) — it does not validate them. "
            "See `docs/manual_data_acquisition.md` to load real CDC WONDER data.",
            icon=":material/science:",
        )
