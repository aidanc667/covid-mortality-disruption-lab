"""Cached loaders for precomputed pipeline outputs. The app never re-runs
excess-mortality or heterogeneity analysis itself (brief section 46) — it
only reads the parquet files scripts/run_covid_disruption_pipeline.py (or,
once real WONDER data exists, the equivalent real pipeline) already wrote
to outputs/models/.
"""
import streamlit as st
import pandas as pd

from src.utils.config import OUTPUTS_MODELS
from src.utils.synthetic_mortality import is_synthetic_active, SYNTHETIC_HETEROGENEITY_MARKER

TEST_CAUSES = [
    "Diseases of heart", "Diabetes mellitus", "Alzheimer's disease",
    "Cerebrovascular disease", "Drug overdose", "Malignant neoplasms",
]
NEGATIVE_CONTROL = "Congenital malformations, deformations and chromosomal abnormalities"
HETEROGENEITY_CAUSES = ["Diabetes mellitus", "Drug overdose"]

# Matches .streamlit/config.toml's chartCategoricalColors, in the same
# TEST_CAUSES + NEGATIVE_CONTROL order, so a cause renders the same color
# everywhere it appears in a chart (Altair mark color -- legitimate data
# encoding, not app-chrome theming, so it's not subject to the "no custom
# CSS" rule that governs st.markdown/st.html styling elsewhere in the app).
CAUSE_COLORS = {
    "Diseases of heart": "#DC2626",
    "Diabetes mellitus": "#2563EB",
    "Alzheimer's disease": "#7C3AED",
    "Cerebrovascular disease": "#EA580C",
    "Drug overdose": "#059669",
    "Malignant neoplasms": "#DB2777",
    NEGATIVE_CONTROL: "#64748B",
}

# Semantic st.badge color names (Streamlit's fixed palette) paired with
# Material Symbols icons, one per cause -- used for badges/metrics instead
# of raw HTML/CSS, per this project's "no custom CSS unless requested" rule.
CAUSE_BADGE_STYLE = {
    "Diseases of heart": ("red", ":material/favorite:"),
    "Diabetes mellitus": ("blue", ":material/water_drop:"),
    "Alzheimer's disease": ("violet", ":material/psychology:"),
    "Cerebrovascular disease": ("orange", ":material/bolt:"),
    "Drug overdose": ("green", ":material/medication:"),
    "Malignant neoplasms": ("yellow", ":material/biotech:"),
    NEGATIVE_CONTROL: ("gray", ":material/verified:"),
}


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
def load_heterogeneity_selection_bias() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_selection_bias.parquet")


@st.cache_data(ttl="1h")
def load_heterogeneity_rurality_robustness() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_rurality_robustness.parquet")


@st.cache_data(ttl="1h")
def load_negative_control() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "negative_control.parquet")


@st.cache_data(ttl="1h")
def load_bridging_summary() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "bridging_summary.parquet")


@st.cache_data(ttl="1h")
def load_sensitivity_check() -> pd.DataFrame:
    return pd.read_parquet(OUTPUTS_MODELS / "sensitivity_check.parquet")


@st.cache_data(ttl="1h")
def load_county_disruption(cause: str) -> pd.DataFrame:
    fname = f"county_disruption_{cause.lower().replace(' ', '_')}.parquet"
    return pd.read_parquet(OUTPUTS_MODELS / fname)


def data_available() -> bool:
    return (OUTPUTS_MODELS / "disruption_summary.parquet").exists()


def sensitivity_check_available() -> bool:
    return (OUTPUTS_MODELS / "sensitivity_check.parquet").exists()


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


def heterogeneity_synthetic_banner() -> None:
    """Renders a warning scoped to just the county-level heterogeneity
    stage, which still runs on synthetic data even after the national
    disruption/persistence analysis switched to real CDC WONDER data --
    a single blanket marker can't express that partial-realness honestly,
    so this checks the heterogeneity-specific marker instead of
    `synthetic_banner`'s project-wide one."""
    if is_synthetic_active(marker_path=SYNTHETIC_HETEROGENEITY_MARKER):
        st.error(
            "County-level heterogeneity below is currently **synthetic "
            "placeholder data** — no real county-level CDC WONDER pull "
            "exists yet (see `docs/manual_data_acquisition.md`'s "
            "'later, smaller scope' section). The national disruption and "
            "persistence results on other pages are real CDC WONDER data.",
            icon=":material/science:",
        )
