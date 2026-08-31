"""Quantifies the discontinuity between CDC WONDER's two mortality-data
vintages (1999-2020 bridged-race vs. 2018-2024 single-race — see
DATA_SOURCES.md #1-2) using the 2018-2020 years present in both, per
docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md
section 4. This does NOT correct or adjust the data — it only measures
the size of the jump, so the orchestration pipeline can decide whether
treating 2020-2024 as continuous with the pre-2020 baseline trend is
defensible (spec section 9: a large offset must be surfaced explicitly,
not silently absorbed into the trend fit).
"""
from __future__ import annotations

import pandas as pd


def estimate_vintage_offset(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    overlap_years: list[int],
    value_col: str = "age_adjusted_rate",
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    group_cols = group_cols or []
    merge_cols = ["year"] + group_cols

    old_overlap = old_df[old_df["year"].isin(overlap_years)][merge_cols + [value_col]]
    new_overlap = new_df[new_df["year"].isin(overlap_years)][merge_cols + [value_col]]

    merged = old_overlap.merge(new_overlap, on=merge_cols, suffixes=("_old", "_new"))
    merged["offset"] = merged[f"{value_col}_new"] - merged[f"{value_col}_old"]
    return merged


def is_bridging_reliable(
    offset_df: pd.DataFrame,
    value_col: str = "age_adjusted_rate",
    max_relative_offset: float = 0.10,
) -> bool:
    """False if the median |offset| relative to the old-vintage value
    exceeds max_relative_offset (10% by default) — i.e. the database
    switch itself moves the series by more than a defensible margin."""
    old_col = f"{value_col}_old"
    relative = (offset_df["offset"] / offset_df[old_col]).abs()
    return bool(relative.median() <= max_relative_offset)
