import pandas as pd
import pytest

from app.components.home_metrics import ScopeMetrics, home_scope_metrics


def _national(years):
    return pd.DataFrame({"cause": ["Diabetes mellitus"] * len(years), "year": years})


def test_year_range_is_inclusive():
    # 1999..2024 inclusive is 26 calendar years.
    m = home_scope_metrics(_national(list(range(1999, 2025))), {})
    assert m == ScopeMetrics(first_year=1999, last_year=2024, n_years=26, county_counts={})


def test_single_year_series_counts_as_one_year():
    m = home_scope_metrics(_national([2020]), {})
    assert (m.first_year, m.last_year, m.n_years) == (2020, 2020, 1)


def test_county_counts_are_distinct_fips_per_cause():
    frames = {
        "Diabetes mellitus": pd.DataFrame({"county_fips": ["01001", "01003", "01003"]}),
        "Drug overdose": pd.DataFrame({"county_fips": pd.Series([], dtype="str")}),
    }
    m = home_scope_metrics(_national([2019, 2020]), frames)
    assert m.county_counts == {"Diabetes mellitus": 2, "Drug overdose": 0}


def test_empty_national_series_is_an_error():
    with pytest.raises(ValueError, match="empty"):
        home_scope_metrics(_national([]), {})
