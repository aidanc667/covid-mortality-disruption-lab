"""Numbers for the Home page's scope strip, derived from the pipeline
outputs rather than typed in, so they can't drift out of sync with the data."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScopeMetrics:
    first_year: int
    last_year: int
    n_years: int
    county_counts: dict[str, int]


def home_scope_metrics(national: pd.DataFrame, county_frames: dict[str, pd.DataFrame]) -> ScopeMetrics:
    if national.empty:
        raise ValueError("national mortality series is empty; cannot compute the year range")
    first, last = int(national["year"].min()), int(national["year"].max())
    counts = {cause: int(df["county_fips"].nunique()) for cause, df in county_frames.items()}
    return ScopeMetrics(first_year=first, last_year=last, n_years=last - first + 1, county_counts=counts)
